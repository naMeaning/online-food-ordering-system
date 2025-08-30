from django.shortcuts import render,redirect, get_object_or_404
from decimal import Decimal
from django.utils import timezone
from django.db import transaction 
from django.db.models import F
from rest_framework import viewsets,status,mixins,permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth.decorators import login_required
from menu.models import Dish
from .models import Order ,OrderItem, OrderStatusHistory, Payment, OrderStatus, PaymentMethod,ServiceType
from .serializers import OrderSerializer, OrderCreateSerializer,OrderDetailSerializer
from cart.models import CartItem
from django.core.paginator import Paginator 
from django.contrib.admin.views.decorators import staff_member_required
from restaurants.utils import user_restaurants_qs
from restaurants.models import Restaurant
from cart.utils import get_cart, compute_summary, find_first_non_empty_rid

class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user_id == request.user.id

class IsRestaurantMember(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and user_restaurants_qs(request.user).exists()

class OrderViewSet(mixins.ListModelMixin,
                   mixins.RetrieveModelMixin,
                   mixins.CreateModelMixin,
                   viewsets.GenericViewSet):
    """
    - POST   /api/orders/            创建订单（从购物车）
    - GET    /api/orders/            我的订单列表
    - GET    /api/orders/{id}/       订单详情（含明细）
    - POST   /api/orders/{id}/pay/   模拟支付（把订单置为 PAID）
    - POST   /api/orders/{id}/cancel/取消未支付订单（回滚库存）
    """
    permission_classes = [permissions.IsAuthenticated, IsOwner]

    def get_queryset(self):
        # 你的 related_name：items（多）、status_history（多）、payment（OneToOne）
        return (Order.objects.filter(user=self.request.user)
                .select_related("payment")
                .prefetch_related("items", "status_history")
                .order_by("-id"))

    def get_serializer_class(self):
        if self.action in ["retrieve", "pay", "cancel"]:
            return OrderDetailSerializer
        if self.action == "create":
            return OrderCreateSerializer
        return OrderSerializer

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        order = ser.save()
        # ✅ 防止序列化时再触发懒加载/命名不一致的问题：拿一份“已预取”的对象来序列化
        order = (Order.objects.select_related("payment")
                 .prefetch_related("items", "status_history")
                 .get(pk=order.pk))
        data = OrderDetailSerializer(order, context={"request": request}).data
        return Response(data, status=status.HTTP_201_CREATED)
        
        
    @action(detail=True, methods=["POST"])
    def pay(self, request, pk=None):
        """
        模拟支付：
        - 仅 CREATED 可支付
        - 通过 exists() 判断是否已有支付记录（反向 OneToOne）
        - 用事务与异常捕获，避免 500
        """
        order = self.get_object()

        if order.status != OrderStatus.CREATED:
            return Response({"detail": "当前状态不可支付"}, status=status.HTTP_400_BAD_REQUEST)

        method = request.data.get("method") or PaymentMethod.DUMMY

        try:
            with transaction.atomic():
                # ✅ 关键：反向检查是否已有支付记录（不要用 order.payment_id）
                if Payment.objects.filter(order=order).exists():
                    return Response({"detail": "已存在支付记录"}, status=status.HTTP_400_BAD_REQUEST)

                # 创建支付记录（正向写入：Payment.order_id 存在）
                Payment.objects.create(
                    order=order,
                    method=method,
                    amount=order.total_amount,
                    paid_at=timezone.now(),
                )

                # 更新订单状态
                prev = order.status
                order.status = OrderStatus.PAID
                order.paid_at = timezone.now()
                order.save(update_fields=["status", "paid_at", "updated_at"])

                # 写入状态流转
                order.status_history.create(
                    from_status=prev, to_status=order.status, message="用户已支付"
                )

        except IntegrityError:
            # 极少见的并发重复创建
            return Response({"detail": "支付重复或并发冲突"}, status=status.HTTP_409_CONFLICT)
        except Exception as e:
            return Response({"detail": f"支付失败：{e.__class__.__name__}"}, status=status.HTTP_400_BAD_REQUEST)

        # 返回“已预取”的详情，避免序列化时再触发 N+1 或命名问题
        order = (
            Order.objects.select_related("payment")
            .prefetch_related("items", "status_history")
            .get(pk=order.pk)
        )
        return Response(OrderDetailSerializer(order, context={"request": request}).data)

    @action(detail=True, methods=["POST"])
    def cancel(self, request, pk=None):
        """取消订单：仅 CREATED 可取消（并回滚库存）"""
        order = self.get_object()
        if order.status != OrderStatus.CREATED:
            return Response({"detail": "当前状态不可取消"}, status=400)
        with transaction.atomic():
            # 用你的 related_name=items
            for it in order.items.select_related("dish").all():
                d = it.dish
                d.stock += it.quantity
                d.sold = max(0, d.sold - it.quantity)
                d.save(update_fields=["stock","sold"])
            prev = order.status
            order.status = OrderStatus.CANCELLED
            order.save(update_fields=["status","updated_at"])
            order.status_history.create(from_status=prev, to_status=order.status, message="用户取消订单")
        return Response(OrderDetailSerializer(order, context={"request": request}).data)
   
class StaffOnly(permissions.IsAdminUser):
    """只允许 is_staff=True 的账号访问（Django 后台账号即可）"""
    pass

class StaffOrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    商家端：只读列表/详情 + 状态流转动作
    仅 staff 可访问。你可以先用 superuser 或 is_staff 账号登录演示。
    """
    permission_classes = [IsRestaurantMember]
    serializer_class = OrderDetailSerializer

    def _allowed_restaurants(self):
        return user_restaurants_qs(self.request.user)

    def get_queryset(self):
        qs = (Order.objects
              .select_related("payment", "restaurant")
              .prefetch_related("items", "status_history")
              .order_by("-id"))

        # 只看自己能管的店
        allowed = self._allowed_restaurants()
        qs = qs.filter(restaurant__in=allowed)

        # 过滤参数
        rid = self.request.query_params.get("restaurant_id")
        if rid:
            qs = qs.filter(restaurant_id=rid)

        status_val = self.request.query_params.get("status") or ""
        service_val = self.request.query_params.get("service") or ""
        if status_val:
            qs = qs.filter(status=status_val)
        if service_val:
            qs = qs.filter(service_type=service_val)
        return qs


    # —— 状态流转动作 —— #
    @action(detail=True, methods=["POST"])
    def confirm(self, request, pk=None):
        """已支付 -> 已接单"""
        order = self.get_object()
        if order.status != OrderStatus.PAID:
            return Response({"detail": "仅已支付订单可接单"}, status=400)
        with transaction.atomic():
            prev = order.status
            order.status = OrderStatus.CONFIRMED
            order.save(update_fields=["status", "updated_at"])
            order.status_history.create(from_status=prev, to_status=order.status, message="商家已接单")
        return Response(OrderDetailSerializer(order).data)

    @action(detail=True, methods=["POST"])
    def ready(self, request, pk=None):
        """已接单 -> 已出餐"""
        order = self.get_object()
        if order.status != OrderStatus.CONFIRMED:
            return Response({"detail": "仅已接单订单可出餐"}, status=400)
        with transaction.atomic():
            prev = order.status
            order.status = OrderStatus.READY
            order.save(update_fields=["status", "updated_at"])
            order.status_history.create(from_status=prev, to_status=order.status, message="已出餐")
        return Response(OrderDetailSerializer(order).data)

    @action(detail=True, methods=["POST"])
    def deliver(self, request, pk=None):
        """已出餐 -> 配送中（仅外送）"""
        order = self.get_object()
        if order.status != OrderStatus.READY:
            return Response({"detail": "仅已出餐订单可配送"}, status=400)
        with transaction.atomic():
            prev = order.status
            order.status = OrderStatus.DELIVERING
            order.save(update_fields=["status", "updated_at"])
            order.status_history.create(from_status=prev, to_status=order.status, message="配送中")
        return Response(OrderDetailSerializer(order).data)

    @action(detail=True, methods=["POST"])
    def complete(self, request, pk=None):
        """
        完成：
        - 堂食：READY -> COMPLETED
        - 外送：DELIVERING -> COMPLETED（如果没走 deliver，也可以从 READY 直接完成，用于到店自取）
        """
        order = self.get_object()
        if order.service_type == "DELIVERY":
            if order.status not in [OrderStatus.DELIVERING, OrderStatus.READY]:
                return Response({"detail": "外送订单需在配送中或已出餐方可完成"}, status=400)
        else:  # DINE_IN
            if order.status != OrderStatus.READY:
                return Response({"detail": "堂食订单需先出餐"}, status=400)

        with transaction.atomic():
            prev = order.status
            order.status = OrderStatus.COMPLETED
            order.save(update_fields=["status", "updated_at"])
            order.status_history.create(from_status=prev, to_status=order.status, message="订单完成")
        return Response(OrderDetailSerializer(order).data)

   
   

@ensure_csrf_cookie
@login_required
def checkout_page(request):
    """结算页面，直接读取当前用户购物车"""
    cart = get_cart(request)
    if not cart["items"]:
        return render(request, "checkout.html", {
            "items": [],
            "total_qty": 0,
            "total_amount": "0.00",
            "message": "购物车为空，先去点菜吧～",
        })

    total_qty, total_amount = compute_summary(cart)
    return render(request, "checkout.html", {
        "items": cart["items"],
        "total_qty": total_qty,
        "total_amount": total_amount,
    })

@login_required
@ensure_csrf_cookie
def order_detail_page(request, order_id: int):
    """
    订单详情页（只允许订单所属用户查看）
    """
    order = get_object_or_404(
        Order.objects.select_related("payment").prefetch_related("items", "status_history"),
        id=order_id, user=request.user
    )
    return render(request, "order_detail.html", {"order": order})

@login_required
@ensure_csrf_cookie
def orders_list_page(request):
    """
    我的订单列表（服务端渲染首屏）
    支持 GET 参数：
      ?status=CREATED/PAID/...   订单状态筛选
      ?service=DELIVERY/DINE_IN  服务类型筛选
      ?page=1                    分页
    """
    qs = (Order.objects
          .filter(user=request.user)
          .select_related("payment")
          .prefetch_related("items")   # 注意：模板里遍历时要写 o.items.all
          .order_by("-id"))

    status_val = request.GET.get("status") or ""
    service_val = request.GET.get("service") or ""

    if status_val:
        qs = qs.filter(status=status_val)
    if service_val:
        qs = qs.filter(service_type=service_val)

    paginator = Paginator(qs, 8)  # 每页 8 条
    page_obj = paginator.get_page(request.GET.get("page") or 1)

    ctx = {
        "page_obj": page_obj,
        "status_val": status_val,
        "service_val": service_val,
        "status_choices": OrderStatus.choices,
        "service_choices": ServiceType.choices,
    }
    return render(request, "orders_list.html", ctx)


@staff_member_required
@ensure_csrf_cookie
def staff_orders_page(request):
    # 首屏用模板渲染，列表数据走 JS 调 /api/staff/orders/
    return render(request, "staff_orders.html", {})

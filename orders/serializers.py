from decimal import Decimal
from django.db import transaction
from django.db.models import F
from rest_framework import serializers
from menu.models import Dish
from cart.models import CartItem
from cart.utils import get_cart, find_first_non_empty_rid
from .models import Order, OrderItem, OrderStatusHistory, Payment, OrderStatus, PaymentMethod,ServiceType

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["id","dish","dish_name","unit_price","quantity","line_total"]
        
    
class OrderSerializer(serializers.ModelSerializer):
    # 用你的 related_name=items
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model  = Order
        fields = [
            "id","status","service_type","table_no","total_amount",
            "contact_name","contact_phone","address_line",
            "created_at","paid_at","items"
        ]
        
        
class OrderCreateSerializer(serializers.Serializer):
    """
    从“当前用户的购物车”创建订单。
    只让用户提交收件信息 + 可选 client_token（幂等）。
    """

    service_type  = serializers.ChoiceField(choices=ServiceType.choices, default=ServiceType.DELIVERY)
    table_no      = serializers.CharField(max_length=16, required=False, allow_blank=True, allow_null=True)

    contact_name  = serializers.CharField(max_length=32, required=False, allow_blank=True, allow_null=True)
    contact_phone = serializers.CharField(max_length=20, required=False, allow_blank=True, allow_null=True)
    address_line  = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)

    client_token  = serializers.CharField(max_length=64, required=False, allow_null=True, allow_blank=True)
    payment_method = serializers.ChoiceField(choices=PaymentMethod.choices, default=PaymentMethod.DUMMY)
    restaurant_id = serializers.IntegerField(required=False)
    
    def validate(self, attrs):
        st = attrs.get("service_type", ServiceType.DELIVERY)
        if st == ServiceType.DELIVERY:
            # 外送：三项都必填
            for f in ("contact_name","contact_phone","address_line"):
                if not (attrs.get(f) or "").strip():
                    raise serializers.ValidationError({f: "外送必须填写该项"})
        elif st == ServiceType.DINE_IN:
            # 堂食：必须有桌号
            if not (attrs.get("table_no") or "").strip():
                raise serializers.ValidationError({"table_no": "堂食必须填写桌号/取餐码"})
        else:
            raise serializers.ValidationError({"service_type": "不支持的服务类型"})
        return attrs

    def create(self, validated_data):
        """
        订单创建核心流程（在一次事务里完成）：
        1) 读取“我的购物车”条目，校验上架&库存
        2) 锁定涉及到的菜品行（select_for_update）
        3) 逐条扣减库存 / 增加销量
        4) 创建订单与明细（价格快照）
        5) 写状态流水（CREATED）
        6) 清空购物车
        """
        request = self.context["request"]
        user = request.user

        rid = validated_data.get("restaurant_id")
        if not rid:
            rid = find_first_non_empty_rid(request)
        if not rid:
            raise serializers.ValidationError("未找到可结算的店铺购物车")

        cart = get_cart(request, rid)
        if not cart["items"]:
            raise serializers.ValidationError("购物车为空")

        # 汇总 & 校验库存
        total = Decimal("0.00")
        items_data = []
        for row in cart["items"]:
            dish = Dish.objects.select_for_update().get(pk=row["dish_id"])
            qty = int(row["qty"])
            unit = dish.price  # Decimal
            line = (unit * qty).quantize(Decimal("0.01"))
            total += line
            # 这里若需要扣库存，写 dish.stock 检查 & 扣减
            items_data.append((dish, row["name"], unit, qty, line))

        st = validated_data["service_type"]
        table_no = validated_data.get("table_no") or None
        contact_name = (validated_data.get("contact_name") or "") if st=="DINE_IN" else validated_data.get("contact_name") or ""
        contact_phone = (validated_data.get("contact_phone") or "") if st=="DINE_IN" else validated_data.get("contact_phone") or ""
        address_line = (validated_data.get("address_line") or "") if st=="DINE_IN" else validated_data.get("address_line") or ""

        with transaction.atomic():
            order = Order.objects.create(
                user=user, restaurant_id=rid, status=OrderStatus.CREATED,
                service_type=st, table_no=table_no,
                contact_name=contact_name, contact_phone=contact_phone, address_line=address_line,
                total_amount=total, client_token=(validated_data.get("client_token") or None),
            )
            # 明细
            for dish, dish_name, unit, qty, line in items_data:
                OrderItem.objects.create(
                    order=order, dish=dish, dish_name=dish_name,
                    unit_price=unit, quantity=qty, line_total=line
                )
            # 首条状态
            order.status_history.create(from_status=OrderStatus.CREATED, to_status=OrderStatus.CREATED, message="订单已创建")
            # 清空该店购物车
            from cart.utils import clear_cart
            clear_cart(request, rid)
        return order


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusHistory
        fields = ["id", "from_status", "to_status", "message", "created_at"]

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "method", "amount", "trade_no", "paid_at", "created_at"]



class OrderDetailSerializer(OrderSerializer):
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)
    payment = PaymentSerializer(read_only=True)  # OneToOne -> 单个对象

    class Meta(OrderSerializer.Meta):
        fields = OrderSerializer.Meta.fields + ["status_history", "payment"]

    def get_status_history(self, obj):
        # 不依赖 related_name，直接按外键过滤
        qs = OrderStatusHistory.objects.filter(order=obj).order_by("created_at")
        return OrderStatusHistorySerializer(qs, many=True).data

    def get_payments(self, obj):
        qs = Payment.objects.filter(order=obj).order_by("-created_at")
        return PaymentSerializer(qs, many=True).data
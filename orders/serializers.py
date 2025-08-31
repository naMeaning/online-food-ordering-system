from decimal import Decimal
from django.db import transaction
from django.db.models import F
from rest_framework import serializers
from menu.models import Dish
from cart.models import CartItem
from cart.utils import get_cart, find_first_non_empty_rid,clear_cart
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
    # restaurant_id = serializers.IntegerField(required=False)
    
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
        request = self.context["request"]
        user = request.user

        cart_qs = CartItem.objects.select_related("dish").filter(user=user).order_by("id")
        if not cart_qs.exists():
            raise serializers.ValidationError("购物车为空")

        total = Decimal("0.00")
        items_data = []
        first_restaurant_id = None

        # 事务内锁行（如果你做库存控制）
        with transaction.atomic():
            dish_ids = list(cart_qs.values_list("dish_id", flat=True))
            dishes_map = {d.id: d for d in Dish.objects.select_for_update().filter(id__in=dish_ids)}

            for ci in cart_qs:
                dish = dishes_map[ci.dish_id]
                qty  = int(ci.quantity)
                unit = dish.price
                line = (unit * qty).quantize(Decimal("0.01"))
                total += line
                items_data.append((dish, dish.name, unit, qty, line))
                if first_restaurant_id is None and hasattr(dish, "restaurant_id"):
                    first_restaurant_id = dish.restaurant_id

            st = validated_data["service_type"]

            # ❌ 不要把 payment_method 传给 Order
            order = Order.objects.create(
                user=user,
                status=OrderStatus.CREATED,
                service_type=st,
                table_no=(validated_data.get("table_no") or None),
                contact_name=(validated_data.get("contact_name") or ""),
                contact_phone=(validated_data.get("contact_phone") or ""),
                address_line=(validated_data.get("address_line") or ""),
                total_amount=total,
                client_token=(validated_data.get("client_token") or None),
                **({"restaurant_id": first_restaurant_id} if first_restaurant_id is not None else {})
            )

            for dish, dish_name, unit, qty, line in items_data:
                OrderItem.objects.create(
                    order=order, dish=dish, dish_name=dish_name,
                    unit_price=unit, quantity=qty, line_total=line
                )

            order.status_history.create(
                from_status=OrderStatus.CREATED, to_status=OrderStatus.CREATED, message="订单已创建"
            )

            # 清空购物车
            cart_qs.delete()

        # 这里**不**创建 Payment 记录；在 pay() 时再用前端上传的 method 创建即可
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
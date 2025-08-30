from decimal import Decimal
from rest_framework import serializers
from django.db import transaction
from django.db.utils import IntegrityError
from .models import CartItem
from menu.models import Dish


class CartItemSerializer(serializers.ModelSerializer):
    # —— 只读展示字段（来自关联表）——
    dish_name  = serializers.CharField(source="dish.name", read_only=True)
    dish_price = serializers.DecimalField(source="dish.price", read_only=True, max_digits=8, decimal_places=2)
    cover_url  = serializers.SerializerMethodField()
    line_amount = serializers.SerializerMethodField()
    
    class Meta:
        model = CartItem
        fields = [
            "id", "dish", "quantity",
            "dish_name", "dish_price", "cover_url", "line_amount",
            "created_at", "updated_at"
        ]
        read_only_fields = ["created_at", "updated_at", "dish_name", "dish_price", "cover_url", "line_amount"]

    def get_cover_url(self, obj):
        req = self.context.get("request")
        if obj.dish.cover and hasattr(obj.dish.cover, "url"):
            return req.build_absolute_uri(obj.dish.cover.url) if req else obj.dish.cover.url
        return None
    
    def get_line_amount(self, obj):
        price = obj.dish.price or Decimal("0.00")
        return price * obj.quantity
    
    # —— 字段级/对象级校验 —— 
    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("数量必须 ≥ 1")
        return value
    
    def validate(self, attrs):
        """
        复合校验：菜品必须上架；数量不能超过库存。
        在 create 时，attrs 里有 dish/quantity；在 update 时通常只有 quantity。
        """
        dish = attrs.get("dish") or getattr(self.instance, "dish", None)
        quantity = attrs.get("quantity") or getattr(self.instance, "quantity", 1)
        if not dish:
            return attrs

        if not dish.status:
            raise serializers.ValidationError({"dish": "该菜品已下架，无法加入购物车"})

        if quantity > dish.stock:
            raise serializers.ValidationError({"quantity": f"库存不足，最多可选 {dish.stock} 份"})

        return attrs

    # —— 新增与更新 —— 
    def create(self, validated_data):
        """
        行为：如果已有同一 dish 的条目，则在原有数量上叠加；否则创建。
        注意唯一约束（user,dish）：可能触发并发异常，这里做一次兜底重试。
        """
        user = self.context['request'].user
        dish = validated_data['dish']
        add_qty = validated_data.get('quantity',1)

        if not user.is_authenticated:
            raise serializers.ValidationError("请先登录后再加入购物车。")

         # 再次兜底库存（并发下：别人也在加）
        if add_qty > dish.stock:
            raise serializers.ValidationError({"quantity": f"库存不足，最多可选 {dish.stock} 份"})
        
        from .models import CartItem  # 避免循环引用
        for _ in range(2):  # 简单重试 2 次，处理极短窗口的竞争
            try:
                with transaction.atomic():
                    obj, created = CartItem.objects.select_for_update(of=("self",)).get_or_create(
                        user=user, dish=dish, defaults={"quantity": add_qty}
                    )
                    if not created:
                        new_qty = obj.quantity + add_qty
                        if new_qty > dish.stock:
                            raise serializers.ValidationError({"quantity": f"库存不足，最多可选 {dish.stock} 份"})
                        obj.quantity = new_qty
                        obj.save(update_fields=["quantity", "updated_at"])
                    return obj
            except IntegrityError:
                # 并发 get_or_create 罕见撞车，重试一次
                continue
        # 理论到不了这里
        raise serializers.ValidationError("系统繁忙，请稍后重试。")
    
    def update(self, instance, validated_data):
        """
        行为：把数量“设置”为指定值（不是叠加）；0 或负值一律不允许。
        """
        new_qty = validated_data.get("quantity", instance.quantity)
        dish = instance.dish
        if new_qty < 1:
            raise serializers.ValidationError({"quantity": "数量必须 ≥ 1"})
        if new_qty > dish.stock:
            raise serializers.ValidationError({"quantity": f"库存不足，最多可选 {dish.stock} 份"})
        instance.quantity = new_qty
        instance.save(update_fields=["quantity", "updated_at"])
        return instance
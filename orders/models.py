from django.db import models
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db.models import Q,UniqueConstraint
from restaurants.models import Restaurant
# Create your models here.

User = get_user_model()

class OrderStatus(models.TextChoices):
    
    CREATED    = "CREATED",    "已创建"
    PAID       = "PAID",       "已支付"
    CONFIRMED  = "CONFIRMED",  "已接单"
    READY      = "READY",      "已出餐"
    DELIVERING = "DELIVERING", "配送中"
    COMPLETED  = "COMPLETED",  "已完成"
    CANCELLED  = "CANCELLED",  "已取消"
    

class ServiceType(models.TextChoices):
    DELIVERY = "DELIVERY", "外送"
    DINE_IN  = "DINE_IN",  "堂食"

    
class PaymentMethod(models.TextChoices):
    DUMMY   = "DUMMY",   "模拟支付"
    CASH    = "CASH",    "现金"
    WECHAT  = "WECHAT",  "微信"
    ALIPAY  = "ALIPAY",  "支付宝"
    
    
class Order(models.Model):
    
    restaurant = models.ForeignKey(Restaurant, on_delete=models.PROTECT, related_name="orders", null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=16, choices=OrderStatus.choices, default=OrderStatus.CREATED)

        # ✅ 新增：服务类型 & 桌号（堂食用）
    service_type = models.CharField(max_length=16, choices=ServiceType.choices, default=ServiceType.DELIVERY)
    table_no = models.CharField(max_length=16, blank=True, null=True)

    # —— 收件信息（课程项目可简单放在订单上；实际业务可做 Address 独立表）——
    contact_name  = models.CharField(max_length=32)
    contact_phone = models.CharField(max_length=20)
    address_line  = models.CharField(max_length=255)

    # 金额汇总（从明细汇总而来）
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])

    # 幂等：客户端可传一个随机 token，避免重复提交生成两笔相同订单（可选）
    client_token = models.CharField(max_length=64, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    paid_at    = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-id']
        constraints = [
            # 仅当 client_token 不为空时，限制“同一用户+同一 token 只能下一次单”
            UniqueConstraint(fields=["user", "client_token"],
                             condition=Q(client_token__isnull=False),
                             name="uniq_order_user_client_token"),
            models.CheckConstraint(check=Q(total_amount__gte=0), name="order_amount_non_negative"),
        ]
    
    def __str__(self):
        return f"Order#{self.id} {self.user} {self.status}"
    
    
class OrderItem(models.Model):
    order      = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    dish       = models.ForeignKey("menu.Dish", on_delete=models.PROTECT)
    dish_name  = models.CharField(max_length=64)  # 快照：下单时的菜名
    unit_price = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])  # 快照单价
    quantity   = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    line_total = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))]) # unit_price * quantity

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.dish_name} x{self.quantity}"
    
    
class OrderStatusHistory(models.Model):
    order     = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=16, choices=OrderStatus.choices)
    to_status   = models.CharField(max_length=16, choices=OrderStatus.choices)
    message     = models.CharField(max_length=200, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]


class Payment(models.Model):
    order     = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="payment", null=True, blank=True)
    method    = models.CharField(max_length=16, choices=PaymentMethod.choices, default=PaymentMethod.DUMMY)
    amount    = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    trade_no  = models.CharField(max_length=64, blank=True, null=True)  # 第三方交易号（模拟支付可留空或随便生成）
    paid_at   = models.DateTimeField(blank=True, null=True)
    created_at= models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
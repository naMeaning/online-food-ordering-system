from django.db import models
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db.models import UniqueConstraint,Q
# Create your models here.

User = get_user_model()

class CartItem(models.Model):
    """
    购物车条目：一个用户选择了某个菜品若干数量。
    注意：库存真正扣减发生在“下单”阶段，这里只是暂存意向。
    """
    user = models.ForeignKey(User,on_delete=models.CASCADE,related_name='cart_items')
    dish = models.ForeignKey('menu.Dish',on_delete=models.CASCADE,related_name='in_carts')
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="该菜品加入购物车的分数，最少1份"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # —— 派生字段（方便模板/调试，不入库）——
    @property
    def line_amount(self)->Decimal:
        """该条目的小计（单价 * 数量），注意金额用 Decimal。"""
        price = self.dish.price or Decimal('0.00')
        return price * self.quantity

    class Meta:
        ordering = ['-id']
        # 关键：同一用户 + 同一道菜 只能有一条记录
        constraints = [
            UniqueConstraint(
                fields=['user','dish'],
                name = 'uniq_cart_user_dish'
                )
            ]
        verbose_name = "购物车条目"
        verbose_name_plural = verbose_name
    
    def __str__(self):
        return f'{self.user} x {self.dish}({self.quantity})'
    
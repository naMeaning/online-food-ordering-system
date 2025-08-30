from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from restaurants.models import Restaurant
# Create your models here.
class Category(models.Model):
    """ 
    菜品分类： 
    """
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="categories", null=True, blank=True)
    name = models.CharField(max_length=32,unique=True) # 菜品名称
    sort = models.PositiveIntegerField(default=0) # 排序值
    status = models.BooleanField(default=True) # 是否启用
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("restaurant", "name")]  # 同店分类名不重复
        ordering = ['sort','id']
        

    def __str__(self):return self.name

def dish_image_path(instance,filename):
    # 图片将保存到 media/dishes/<id或new>/<文件名>
    return f"dishes/{instance.id or 'new'}/{filename}"


class Dish(models.Model):
    """
    菜品
    """
    
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="dishes", null=True, blank=True)
    
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,  # 防止菜品被误删
        related_name = 'dishes'
    )
    name = models.CharField(max_length=64)
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))], # 价格>= 0
    )
    cover = models.ImageField(
        upload_to=dish_image_path,
        blank = True,null = True,
    )
    stock = models.PositiveIntegerField(default=100)  # 库存
    status = models.BooleanField(
        default=True,
        help_text="是否上架"
    )
    sold = models.PositiveIntegerField(default = 0) # 销量计数

    description = models.TextField(blank = True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now = True)

    class Meta:
        unique_together = [("restaurant", "name")]  # 同店菜名不重复
        # 索引：我们查询时常按“是否上架”“分类+是否上架”“价格排序/销量排序”
        indexes = [
            models.Index(fields = ['status']),
            models.Index(fields=['category','status']),
            models.Index(fields=['-sold']), # 常见热销列表
            models.Index(fields=['price']), # 价格排序/筛选
        ]

        ordering = ['-id'] # 默认最新的在前

        # 数据库层约束
        constraints = [
            models.CheckConstraint(
                check=Q(price__gte=0),
                name="dish_price_non_negative"
            ),
            models.CheckConstraint(
                check=Q(stock__gte=0),
                name="dish_stock_non_negative"
            ),
            models.CheckConstraint(
                check=Q(sold__gte=0),
                name="dish_sold_non_negative"
            ),
        ]

    def __str__(self):
        return self.name
        

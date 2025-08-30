from django.contrib import admin
from django.utils.html import format_html
from .models import Category,Dish

# Register your models here.

# --- 分类在后台的展示与操作 ---
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    为什么这样配：后台常见需求是“快速查+快速排布”。
    - list_display：列表页面看到哪些列
    - list_filter：右侧过滤器
    - search_fields：顶部搜索框支持哪些字段
    - ordering：默认排序（这里和模型 Meta 的 ordering 一致即可）
    """
    
    list_display = ('id','name','sort','status','created_at')
    list_filter = ('status',)
    search_fields = ('name',)
    ordering = ('sort','id')
    list_per_page = 20


# --- 菜品在后台的展示与操作 ---
@admin.register(Dish)
class DishAdmin(admin.ModelAdmin):
    """
    这里多做了几件实用的小事：
    1) cover_thumb：在列表页显示一个 60px 的缩略图（方便肉眼核对）
    2) actions：批量上架/下架
    3) list_filter/search_fields：按状态、分类、名称快速定位
    """
    def cover_thumb(self,obj):
        if obj.cover:
            return format_html('<img src="{}" style="height:60px;border-radius:6px;" />', obj.cover.url)
        return '-'
    
    cover_thumb.short_description = '封面'

    @admin.action(description='批量上架所选菜品')
    def action_publish(self,request,queryset):
        updated = queryset.update(status = True)
        self.message_user(request,f'已上架{updated}条菜品.')
    
    @admin.action(description='批量下架所有菜品')
    def action_unpublish(self,request,queryset):
        updated = queryset.update(status=False)
        self.message_user(request,f'已下架{updated}条菜品.')
    
    list_display  = ("id", "cover_thumb", "name", "category", "price", "status", "stock", "sold", "created_at")
    list_filter   = ("status", "category")
    search_fields = ("name", "category__name")
    ordering      = ("-id",)
    actions       = ("action_publish", "action_unpublish")
    list_per_page = 20

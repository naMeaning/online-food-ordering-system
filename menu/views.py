from django.shortcuts import render
from rest_framework import viewsets, filters
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from .models import Category, Dish
from .serializers import CategorySerializer, DishSerializer
from django.views.decorators.csrf import ensure_csrf_cookie
from django.shortcuts import render, get_object_or_404
from restaurants.models import Restaurant
from django.contrib.auth.decorators import login_required # 登录需要



# Create your views here.

# ---- API：只读视图集 ----
class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ReadOnlyModelViewSet = 只有 list / retrieve，不提供增删改（安全些）
    """
    queryset = Category.objects.filter(status= True)
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter,filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['sort','id']
    ordering = ['sort','id']

    
class DishViewSet(viewsets.ReadOnlyModelViewSet):
    """
    - select_related("category")：一并拉取外键，避免 N+1 查询
    - 过滤：支持 ?category=1、?status=true
    - 搜索：?search=米饭
    - 排序：?ordering=price 或 -sold
    """
    queryset = Dish.objects.select_related('category').filter(status = True)
    serializer_class = DishSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend,filters.SearchFilter,filters.OrderingFilter]
    filterset_fields = ['category','status']
    search_fields = ['name','category__name','description']
    ordering_fields = ['id','price','sold','created_at']
    ordering = ['-id']

# ---- 页面视图（把数据塞给模板）----
# @ensure_csrf_cookie
# @login_required
# def home_page(request):
#     """
#     首页：展示店铺选择 + 某店的菜品（按 rid 过滤）。
#     如果没传 rid，就选第一个 is_active 的店。
#     """
#     rid = request.GET.get("rid")
#     restaurants = Restaurant.objects.filter(is_active=True).order_by("id")

#     current = None
#     if rid:
#         current = get_object_or_404(restaurants, id=rid)
#     else:
#         current = restaurants.first()

#     categories = Category.objects.filter(restaurant=current).order_by("id") if current else []
#     dishes = Dish.objects.filter(restaurant=current, ).order_by("id") if current else []

#     ctx = {
#         "restaurants": restaurants,
#         "current_restaurant": current,
#         "categories": categories,
#         "dishes": dishes,
#     }
#     return render(request, "index.html", ctx)



@ensure_csrf_cookie
@login_required
def home_page(request):
    """
    首页：展示店铺选择 + 某店的菜品（按 rid 过滤），并支持按分类 ?category=xx 过滤。
    """
    # —— 保持你原来的 rid 逻辑不变 —— #
    rid = request.GET.get("rid")
    restaurants = Restaurant.objects.filter(is_active=True).order_by("id")

    current = None
    if rid:
        current = get_object_or_404(restaurants, id=rid)
    else:
        current = restaurants.first()

    # —— 分类列表（只列出当前店铺的分类）—— #
    categories = Category.objects.filter(restaurant=current).order_by("id") if current else []

    # —— 读取分类参数并校验“是否属于当前店铺” —— #
    cat_param = request.GET.get("category")
    current_cat = None
    if cat_param and cat_param.isdigit() and current:
        current_cat = Category.objects.filter(restaurant=current, id=int(cat_param)).first()

    # —— 菜品查询（先按店铺过滤，再按分类可选过滤）—— #
    dishes_qs = Dish.objects.filter(restaurant=current).select_related("category").order_by("id") if current else []
    if current_cat:
        dishes_qs = dishes_qs.filter(category=current_cat)

    ctx = {
        "restaurants": restaurants,
        "current_restaurant": current,
        "categories": categories,
        "current_cat": current_cat,   # ← 模板用于高亮
        "dishes": dishes_qs,
    }
    return render(request, "index.html", ctx)
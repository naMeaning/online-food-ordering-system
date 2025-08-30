from django.shortcuts import render
from rest_framework import viewsets, filters
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from .models import Category, Dish
from .serializers import CategorySerializer, DishSerializer
from django.views.decorators.csrf import ensure_csrf_cookie
from django.shortcuts import render, get_object_or_404
from restaurants.models import Restaurant



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
@ensure_csrf_cookie
def home_page(request):
    """
    首页：展示店铺选择 + 某店的菜品（按 rid 过滤）。
    如果没传 rid，就选第一个 is_active 的店。
    """
    rid = request.GET.get("rid")
    restaurants = Restaurant.objects.filter(is_active=True).order_by("id")

    current = None
    if rid:
        current = get_object_or_404(restaurants, id=rid)
    else:
        current = restaurants.first()

    categories = Category.objects.filter(restaurant=current).order_by("id") if current else []
    dishes = Dish.objects.filter(restaurant=current, ).order_by("id") if current else []

    ctx = {
        "restaurants": restaurants,
        "current_restaurant": current,
        "categories": categories,
        "dishes": dishes,
    }
    return render(request, "index.html", ctx)
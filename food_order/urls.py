"""
URL configuration for food_order project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter
from menu.views import CategoryViewSet, DishViewSet, home_page
from cart.views import CartViewSet,cart_page
from orders.views import OrderViewSet, orders_list_page, checkout_page,order_detail_page,StaffOrderViewSet,staff_orders_page
from accounts.views import RegisterView, MyTokenObtainPairView, MeView
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from cart import views as cart_views

router = DefaultRouter()
router.register(f'categories',CategoryViewSet, basename='category')
router.register(f'dishes',    DishViewSet,     basename='dish')
router.register(r'cart',      CartViewSet,     basename="cart")
router.register(r'orders',OrderViewSet,basename='order')
router.register(r"staff/orders", StaffOrderViewSet, basename="staff-orders")

urlpatterns = [
    path("admin/", admin.site.urls),
    path('', home_page,name='home'),
    path("checkout/", checkout_page, name="checkout"),      
    path("orders/", orders_list_page, name="orders_list"),
    path("orders/<int:order_id>/", order_detail_page, name="order_detail"), 
    path('cart/',cart_page,name = 'cart'),
    path("accounts/", include("accounts.urls")),    
     # 购物车 API
    path("api/sess-cart/", cart_views.cart_api, name="api_sess_cart"),                # GET/DELETE，带 rid
    path("api/sess-cart/clear/", cart_views.clear_cart_view, name="api_sess_cart_clear"),  # POST JSON {rid}
    path("api/sess-cart/add/", cart_views.add_to_cart, name="api_sess_cart_add"),          # POST JSON {dish_id, qty}
    path("api/sess-cart/update/", cart_views.update_cart_item, name="api_sess_cart_update"),


    
    path("staff/orders/", staff_orders_page, name="staff_orders"),
    
    path('api/',include(router.urls)),
    path("api-auth/", include("rest_framework.urls")),
    
    path("api/auth/register/", RegisterView.as_view(), name="auth_register"),
    path("api/auth/token/", MyTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("api/auth/me/", MeView.as_view(), name="auth_me"),
    

]

# 开发环境暴露媒体文件
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
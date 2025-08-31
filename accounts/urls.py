# accounts/urls.py
from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from .views import register_page  # 这是你写的基于模板的注册页视图

urlpatterns = [
    # 登录：已登录的用户再访问，自动跳回首页
    path("login/", LoginView.as_view(
        template_name="accounts/login.html",
        redirect_authenticated_user=True
    ), name="login"),

   
    path("logout/", LogoutView.as_view(next_page="login"), name="logout"),

    # 注册页（模板）
    path("register/", register_page, name="register"),
]

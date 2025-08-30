from django.urls import path
from django.contrib.auth import views as auth_views
from .views import RegisterView, MeView  ,register_page

urlpatterns = [
    path("login/",
         auth_views.LoginView.as_view(template_name="accounts/login.html",
                                      redirect_authenticated_user=True),
         name="login"),
    path("logout/",
         auth_views.LogoutView.as_view(next_page="/"),  # 退出后重定向首页
         name="logout"),
    path("register/", register_page, name="register"),
    path("me/", MeView.as_view(), name="me"),  # 可选：个人信息 API
]
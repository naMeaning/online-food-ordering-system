

# Create your views here.
# accounts/views.py
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import RegisterSerializer, MyTokenObtainPairSerializer

from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth import authenticate, login, logout


User = get_user_model()

class RegisterView(generics.CreateAPIView):
    """注册：公开接口"""
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

class MyTokenObtainPairView(TokenObtainPairView):
    """登录：返回 access/refresh + 用户信息"""
    serializer_class = MyTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]

class MeView(APIView):
    """获取当前登录用户信息：支持 JWT 或 Session"""
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        u = request.user
        return Response({
            "id": u.id,
            "username": u.get_username(),
            "email": u.email,
            "is_staff": u.is_staff,
            "is_superuser": u.is_superuser,
        })


@csrf_protect
def register_page(request):
    """
    渲染注册页面 + 处理表单提交（Session 风格）
    注意：这与 /api/auth/register/ 的 DRF 注册接口并存，互不影响
    """
    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""
        email    = (request.POST.get("email") or "").strip()

        # 最基本校验（够用即可；更严格可以用 UserCreationForm 或自定义 Form）
        if not username or not password:
            messages.error(request, "用户名与密码必填")
            return render(request, "accounts/register.html", {"username": username, "email": email})

        if len(password) < 6:
            messages.error(request, "密码至少 6 位")
            return render(request, "accounts/register.html", {"username": username, "email": email})

        if User.objects.filter(username=username).exists():
            messages.error(request, "用户名已存在")
            return render(request, "accounts/register.html", {"username": username, "email": email})

        # 创建用户（create_user 会自动哈希密码）
        User.objects.create_user(username=username, password=password, email=email or "")
        messages.success(request, "注册成功，请登录")
        return redirect("login")

    # GET 渲染空表单
    return render(request, "accounts/register.html")


@csrf_protect
def login_page(request):
    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)  # 写入 session
            next_url = request.POST.get("next") or request.GET.get("next") or "/"
            return redirect(next_url)
        messages.error(request, "用户名或密码错误")
    return render(request, "accounts/login.html")

@csrf_protect
def logout_view(request):
    if request.method == "POST":   # 推荐只允许 POST
        logout(request)            # 清理 session
        return redirect("/")
    # GET 请求可返回一个确认页面（可选）
    return render(request, "accounts/logged_out.html")
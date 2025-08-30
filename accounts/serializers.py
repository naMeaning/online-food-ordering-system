# accounts/serializers.py
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ["username", "password", "email", "first_name", "last_name"]
        extra_kwargs = {
            "email": {"required": False, "allow_blank": True},
            "first_name": {"required": False, "allow_blank": True},
            "last_name": {"required": False, "allow_blank": True},
        }

    def create(self, validated_data):
        # 用 create_user 自动做密码哈希
        return User.objects.create_user(**validated_data)

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    """自定义 JWT 载荷：给前端多点有用信息（答辩也好讲）"""
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # 自定义声明（不要放敏感信息）
        token["username"] = user.get_username()
        token["is_staff"] = user.is_staff
        token["is_superuser"] = user.is_superuser
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        # 登录响应里也顺带给点用户信息
        data["user"] = {
            "id": self.user.id,
            "username": self.user.get_username(),
            "is_staff": self.user.is_staff,
            "is_superuser": self.user.is_superuser,
            "email": self.user.email,
        }
        return data

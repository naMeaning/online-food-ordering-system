from rest_framework import serializers
from .models import Category,Dish

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"
        
class DishSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source = 'category.name',read_only = True)
    cover_url = serializers.SerializerMethodField()

    class Meta:
        model = Dish
        fields = [
            "id", "name", "price", "category", "category_name",
            "cover", "cover_url", "stock", "status", "sold",
            "description", "created_at", "updated_at"
        ]
        
    def get_cover_url(self, obj):
        """
        把 ImageField 转成可直接访问的绝对 URL：
        - 开发期由 urls.py 的 static() 提供 /media/ 服务
        - 生产期通常由 Nginx 直接服务 MEDIA_URL
        """

        req = self.context.get('request')
        if obj.cover and hasattr(obj.cover,'url'):
            return req.build_absolute_uri(obj.cover.url) if req else obj.cover.url
        return None
        
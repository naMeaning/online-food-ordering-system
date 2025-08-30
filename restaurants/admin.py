# restaurants/admin.py
from django.contrib import admin
from .models import Restaurant, RestaurantMember

@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "owner", "is_active", "created_at")
    search_fields = ("name", "slug", "owner__username")

@admin.register(RestaurantMember)
class RestaurantMemberAdmin(admin.ModelAdmin):
    list_display = ("id", "restaurant", "user", "role", "joined_at")
    search_fields = ("restaurant__name", "user__username")

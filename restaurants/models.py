from django.db import models
from django.contrib.auth import get_user_model
# Create your models here.

User = get_user_model()

class Restaurant(models.Model):
    name = models.CharField(max_length=64, unique=True)
    slug = models.SlugField(max_length=64, unique=True)  # URL 友好
    owner = models.ForeignKey(User, on_delete=models.PROTECT, related_name="owned_restaurants")
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name

class MemberRole(models.TextChoices):
    OWNER = "OWNER", "店主"
    MANAGER = "MANAGER", "经理"
    CLERK = "CLERK", "店员"

class RestaurantMember(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="restaurant_memberships")
    role = models.CharField(max_length=16, choices=MemberRole.choices, default=MemberRole.CLERK)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("restaurant", "user")]
        ordering = ["id"]

    def __str__(self):
        return f"{self.user} @ {self.restaurant} ({self.role})"
# restaurants/utils.py
from .models import Restaurant, RestaurantMember

def user_restaurants_qs(user):
    """
    可管理的店：自己是 owner 的 + 成员表中出现的。
    非 staff 也能管理自己拥有/加入的店；你也可以再叠加 is_staff 判断。
    """
    if not user.is_authenticated:
        return Restaurant.objects.none()
    owned = Restaurant.objects.filter(owner=user)
    joined = Restaurant.objects.filter(members__user=user)
    return (owned | joined).distinct()

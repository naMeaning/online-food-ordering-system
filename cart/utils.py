# cart/utils.py
import re
from decimal import Decimal
from django.shortcuts import render, get_object_or_404
from .models import CartItem
from menu.models import Dish

from django.http import JsonResponse


def cart_session_key(user_id: int) -> str:
    """根据用户 ID 生成购物车 session key"""
    key = f"cart:{user_id}"
    print(f"Generated Cart Session Key: {key}")  # 打印生成的 session 键
    return f"cart:{user_id}"

# def get_cart(request):
#     """取出用户的购物车；没有就返回一个空框架。"""
#     key = cart_session_key(request.user.id)
#     print(f"Session Data: {request.session.items()}")  # 调试：打印 session 数据
#     cart = request.session.get(key)
#     if not cart:
#         cart = {"items": []}
#     return cart

def get_cart(request):
    """直接从数据库获取购物车"""
    if not request.user.is_authenticated:
        return render(request, "cart.html", {
            "items": [],
            "total_qty": 0,
            "total_amount": "0.00",
            "message": "请先登录！"
        })

    cart = CartItem.objects.filter(user=request.user)
    items = []
    total_qty = 0
    total_amount = 0
    for item in cart:
        items.append({
            "id": item.id,
            "dish_name": item.dish.name,
            "dish_price": item.dish.price,
            "quantity": item.quantity,
            "line_amount": item.dish.price * item.quantity,
        })
        total_qty += item.quantity
        total_amount += item.dish.price * item.quantity

    return render(request, "cart.html", {
        "items": items,
        "total_qty": total_qty,
        "total_amount": total_amount,
    })



# def set_cart(request,  cart: dict):
#     """保存购物车到 session 中。"""
#     key = cart_session_key(request.user.id)
#     print(f"Saving Cart to Session with key: {key}")  # 打印 session 键
#     print(f"Cart data to save: {cart}")  # 打印要保存的数据

#     request.session[key] = cart
#     request.session.modified = True
#     print(f"Updated Session Data: {request.session.items()}")  # 打印更新后的 session 数据

def clear_cart(request):
    """ 清空当前用户的购物车 """
    if not request.user.is_authenticated:
        return JsonResponse({"error": "请先登录"}, status=400)
    
    # 删除该用户的所有购物车条目
    CartItem.objects.filter(user=request.user).delete()
    
    return JsonResponse({"ok": True, "total_qty": 0, "total_amount": "0.00"})

def compute_summary(cart: dict):
    """
    计算购物车汇总。
    由于 session 默认 JSONSerializer，不能存 Decimal，所以单价推荐存字符串；这里再转 Decimal。
    """
    total_qty = 0
    total_amount = Decimal("0.00")
    for it in cart.get("items", []):
        qty = int(it.get("qty", 0))
        total_qty += qty
        unit = Decimal(str(it.get("unit_price", "0")))
        total_amount += unit * qty
    # 保留两位
    total_amount = total_amount.quantize(Decimal("0.01"))
    return total_qty, total_amount

def find_first_non_empty_rid(request):
    """
    在会话里找第一辆非空购物车的 rid（给下单流程兜底用）。
    形如 'cart:12' 这样的 key。
    """
    for k, v in request.session.items():
        m = re.match(r"^cart:(\d+)$", str(k))
        if m and isinstance(v, dict) and v.get("items"):
            return int(m.group(1))
    return None

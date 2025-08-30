# cart/utils.py
import re
from decimal import Decimal

def cart_session_key(user_id: int) -> str:
    """根据用户 ID 生成购物车 session key"""
    return f"cart:{user_id}"

def get_cart(request):
    """取出用户的购物车；没有就返回一个空框架。"""
    key = cart_session_key(request.user.id)
    cart = request.session.get(key)
    if not cart:
        cart = {"items": []}
    return cart

def set_cart(request,  cart: dict):
    """保存购物车到 session 中。"""
    key = cart_session_key(request.user.id)
    request.session[key] = cart
    request.session.modified = True

def clear_cart(request):
    """ 清空当前用户的购物车，不依赖 restaurant_id """
    # 获取当前用户购物车
    cart = get_cart(request)
    if not cart:
        return  # 如果购物车为空，则直接返回
    cart["items"] = []  # 清空购物车条目
    set_cart(request, cart)  # 保存清空后的购物车

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

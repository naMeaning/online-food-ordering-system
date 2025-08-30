# cart/utils.py
import re
from decimal import Decimal

def cart_session_key(rid: int) -> str:
    """同一家店铺用同一个 session key，互不影响。"""
    return f"cart:{rid}"

def get_cart(request, rid: int):
    """取出某店购物车；没有就返回一个空框架。注意：不能在 session 里存 Decimal。"""
    key = cart_session_key(rid)
    cart = request.session.get(key)
    if not cart:
        cart = {"rid": rid, "items": []}
    return cart

def set_cart(request, rid: int, cart: dict):
    key = cart_session_key(rid)
    request.session[key] = cart
    request.session.modified = True

def clear_cart(request, rid: int):
    key = cart_session_key(rid)
    if key in request.session:
        del request.session[key]
        request.session.modified = True

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

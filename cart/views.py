from django.shortcuts import render

# Create your views here.
from decimal import Decimal
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseNotAllowed
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import F
from .models import CartItem
from .serializers import CartItemSerializer
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db.models import Sum
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
import json
from django.contrib.auth.decorators import login_required  # 购物车可不强制登录，下单再要求
from menu.models import Dish
from .utils import (
    cart_session_key, get_cart,  clear_cart, compute_summary, find_first_non_empty_rid
)



class CartViewSet(viewsets.ModelViewSet):
    """
    标准 CRUD：
    - GET    /api/cart/           列出我的购物车（含总件数、总金额）
    - POST   /api/cart/           加入购物车（dish, quantity），若已存在则叠加
    - PATCH  /api/cart/{id}/      修改数量为指定值
    - DELETE /api/cart/{id}/      删除该条目
    - DELETE /api/cart/clear/     清空我的购物车（自定义动作）
    """
    serializer_class = CartItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CartItem.objects.select_related("dish", "user").filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page or queryset, many=True, context={"request": request})

        items = serializer.data
        # 计算总件数和总金额
        total_qty = sum(i["quantity"] for i in items)
        total_amount = sum(Decimal(str(i["line_amount"])) for i in items)

        data = {
            "items": items if page is None else self.get_paginated_response(items).data,
            "total_quantity": total_qty,
            "total_amount": f"{total_amount:.2f}",
        }
        if page is not None and isinstance(data["items"], dict) and "results" in data["items"]:
            data["items"] = data["items"]["results"]
        return Response(data)

    @action(detail=False, methods=["delete"])
    def clear(self, request):
        """
        清空我的购物车
        """
        deleted, _ = self.get_queryset().delete()
        return Response({"deleted": deleted}, status=status.HTTP_200_OK)


# cart/views.py

# @require_POST
# def add_to_cart(request):
#     """
#     请求体 JSON: { "dish_id": 1, "qty": 2 }
#     - 无需考虑餐厅，直接根据菜品和用户加入购物车
#     - 如果已有该菜品则累加数量
#     返回: { ok, total_qty, total_amount, item_count }
#     """
#     try:
#         data = json.loads(request.body.decode("utf-8"))
#         dish_id = int(data.get("dish_id"))
#         qty = int(data.get("qty", 1))
#         if qty <= 0:
#             return HttpResponseBadRequest("qty 必须 > 0")
#     except Exception:
#         return HttpResponseBadRequest("非法 JSON")

#     dish = get_object_or_404(Dish, id=dish_id)
#     user = request.user
#     cart = get_cart(request)

#     # 查找是否已有该菜
#     for it in cart["items"]:
#         if it["dish_id"] == dish.id:
#             it["qty"] += qty
#             break
#     else:
#         # 新增一行。单价用字符串存，避免 session JSON 序列化问题
#         cart["items"].append({
#             "dish_id": dish.id,
#             "name": dish.name,
#             "unit_price": str(dish.price),
#             "qty": qty,
#         })

#     set_cart(request, cart)
#     total_qty, total_amount = compute_summary(cart)
#     return JsonResponse({
#         "ok": True,
#         "total_qty": total_qty,
#         "total_amount": str(total_amount),
#         "item_count": len(cart["items"]),
#     })
def add_to_cart(request):
    """请求体 JSON: { "dish_id": 1, "qty": 2 }"""
    try:
        data = json.loads(request.body.decode("utf-8"))
        dish_id = int(data.get("dish_id"))
        qty = int(data.get("qty", 1))
        if qty <= 0:
            return HttpResponseBadRequest("qty 必须 > 0")
    except Exception:
        return HttpResponseBadRequest("非法 JSON")

    dish = get_object_or_404(Dish, id=dish_id)
    user = request.user

    # 查找该用户是否已经有该菜品的购物车条目
    cart_item, created = CartItem.objects.get_or_create(user=user, dish=dish)

    if created:
        cart_item.quantity = qty
    else:
        cart_item.quantity += qty

    cart_item.save()  # 保存购物车条目

    # 计算购物车的总数量和金额
    cart = CartItem.objects.filter(user=user)
    total_qty = cart.aggregate(total_qty=Sum('quantity'))['total_qty'] or 0
    total_amount = sum(item.dish.price * item.quantity for item in cart)

    return JsonResponse({
        "ok": True,
        "total_qty": total_qty,
        "total_amount": str(total_amount),
        "item_count": len(cart),
    })
# @require_POST
# def update_cart_item(request):
#     """
#     请求体 JSON: { "rid": 10, "dish_id": 1, "qty": 3 }
#     - qty == 0 表示移除该菜
#     """
#     try:
#         data = json.loads(request.body.decode("utf-8"))
#         rid = int(data.get("rid"))
#         dish_id = int(data.get("dish_id"))
#         qty = int(data.get("qty", 1))
#     except Exception:
#         return HttpResponseBadRequest("非法 JSON")

#     cart = get_cart(request)
#     new_items = []
#     found = False
#     for it in cart["items"]:
#         if it["dish_id"] == dish_id:
#             found = True
#             if qty > 0:
#                 it["qty"] = qty
#                 new_items.append(it)
#             # qty==0 则删除
#         else:
#             new_items.append(it)
#     if not found:
#         return HttpResponseBadRequest("购物车中找不到该菜品")

#     cart["items"] = new_items
#     set_cart(request, rid, cart)
#     total_qty, total_amount = compute_summary(cart)
#     return JsonResponse({"ok": True, "rid": rid, "total_qty": total_qty, "total_amount": str(total_amount)})
@require_POST
def update_cart_item(request):
    """请求体 JSON: { "dish_id": 1, "qty": 3 }"""
    try:
        data = json.loads(request.body.decode("utf-8"))
        dish_id = int(data.get("dish_id"))
        qty = int(data.get("qty", 1))
    except Exception:
        return HttpResponseBadRequest("非法 JSON")

    # 查找该用户是否有该菜品的购物车条目
    cart_item = CartItem.objects.filter(user=request.user, dish_id=dish_id).first()

    if not cart_item:
        return HttpResponseBadRequest("购物车中找不到该菜品")

    if qty == 0:
        cart_item.delete()  # 删除该条目
    else:
        cart_item.quantity = qty
        cart_item.save()  # 更新数量

    # 重新计算购物车总数量和金额
    cart = CartItem.objects.filter(user=request.user)
    total_qty = cart.aggregate(total_qty=Sum('quantity'))['total_qty'] or 0
    total_amount = sum(item.dish.price * item.quantity for item in cart)

    return JsonResponse({
        "ok": True,
        "total_qty": total_qty,
        "total_amount": str(total_amount),
    })


@require_POST
def remove_cart_item(request):
    """从购物车中移除商品"""
    try:
        data = json.loads(request.body.decode("utf-8"))
        dish_id = int(data.get("dish_id"))
    except Exception:
        return HttpResponseBadRequest("非法 JSON")

    # 查找购物车条目并删除
    cart_item = CartItem.objects.filter(user=request.user, dish_id=dish_id).first()
    if cart_item:
        cart_item.delete()

    # 重新计算购物车总数量和金额
    cart = CartItem.objects.filter(user=request.user)
    total_qty = cart.aggregate(total_qty=Sum('quantity'))['total_qty'] or 0
    total_amount = sum(item.dish.price * item.quantity for item in cart)

    return JsonResponse({
        "ok": True,
        "total_qty": total_qty,
        "total_amount": str(total_amount),
    })
    
    
# @require_POST
# def clear_cart_view(request):
#     """
#     请求体 JSON: { "rid": 10 }
#     清空某店的购物车
#     """
#     try:
#         data = json.loads(request.body.decode("utf-8"))
#         rid = int(data.get("rid"))
#     except Exception:
#         return HttpResponseBadRequest("非法 JSON")

#     clear_cart(request, rid)
#     return JsonResponse({"ok": True, "rid": rid, "total_qty": 0, "total_amount": "0.00"})
@require_POST
def clear_cart_view(request):
    """ 清空购物车 """
    if not request.user.is_authenticated:
        return JsonResponse({"error": "请先登录"}, status=400)
    
    # 删除该用户所有的购物车条目
    CartItem.objects.filter(user=request.user).delete()

    return JsonResponse({"ok": True, "total_qty": 0, "total_amount": "0.00"})

# cart/views.py

@ensure_csrf_cookie
def cart_page(request):
    """购物车页面"""
    if not request.user.is_authenticated:
        return render(request, "cart.html", {
            "items": [],
            "total_qty": 0,
            "total_amount": "0.00",
            "message": "请先登录！"
        })

    # 获取当前用户的购物车数据
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
    
    
    


# 新建文件：restaurants/context_processors.py
def nav_restaurant(request):
    """
    提供导航可用的 nav_rid：
    - 优先用 session 里记住的最近店铺 rid（我们会在加购物车/切店时写入）
    """
    return {"nav_rid": request.session.get("current_rid")}

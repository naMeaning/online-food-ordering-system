// ---- 通用：CSRF / Toast ----

const RID = (typeof window !== "undefined" && window.__RID__) ? window.__RID__ : null;

function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.content && meta.content !== "NOTPROVIDED") return meta.content;
    const m = document.cookie.match(/(^|;)\s*csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[2]) : "";
}
function toast(text, ok = true) {
    const t = document.getElementById("toast");
    if (!t) return alert(text);
    t.className = `px-4 py-2 rounded-xl shadow ${ok ? "bg-emerald-600 text-white" : "bg-rose-600 text-white"}`;
    t.textContent = text;
    t.style.display = "block";
    clearTimeout(t._timer);
    t._timer = setTimeout(() => (t.style.display = "none"), 1500);
}

// ---- 购物车 API 封装（供首页迷你购物车和“加入购物车”复用）----
function normalizeCartData(raw) {
    // 情况 A：我们的自定义结构 { items, total_quantity, total_amount }
    if (raw && Array.isArray(raw.items)) {
        return {
            items: raw.items,
            total_quantity: raw.total_quantity ?? raw.items.reduce((s, i) => s + (i.quantity || 0), 0),
            total_amount: raw.total_amount ?? raw.items.reduce((s, i) => s + parseFloat(i.line_amount || 0), 0).toFixed(2),
            unauthorized: raw.unauthorized || false
        };
    }
    // 情况 B：DRF 默认分页 { results: [...] }
    if (raw && Array.isArray(raw.results)) {
        const items = raw.results;
        return {
            items,
            total_quantity: items.reduce((s, i) => s + (i.quantity || 0), 0),
            total_amount: items.reduce((s, i) => s + parseFloat(i.line_amount || 0), 0).toFixed(2),
            unauthorized: false
        };
    }
    // 情况 C：直接返回数组
    if (Array.isArray(raw)) {
        const items = raw;
        return {
            items,
            total_quantity: items.reduce((s, i) => s + (i.quantity || 0), 0),
            total_amount: items.reduce((s, i) => s + parseFloat(i.line_amount || 0), 0).toFixed(2),
            unauthorized: false
        };
    }
    // E) Session 结构：{ items: [{ dish_id, name, unit_price, qty }, ...] }
    if (raw && Array.isArray(raw.items) && raw.items.length && raw.items[0].dish_id) {
        const items = raw.items.map(it => {
            const price = parseFloat(it.unit_price || "0");
            const qty = parseInt(it.qty || 0, 10);
            return {
                id: it.dish_id,               // 用 dish_id 作为行标识
                dish_name: it.name,
                dish_price: price.toFixed(2),
                quantity: qty,
                line_amount: (price * qty).toFixed(2),
            };
        });
        const total_quantity = items.reduce((s, i) => s + (i.quantity || 0), 0);
        const total_amount = items.reduce((s, i) => s + parseFloat(i.line_amount || 0), 0).toFixed(2);
        return { items, total_quantity, total_amount, unauthorized: false };
    }

    return { items: [], total_quantity: 0, total_amount: "0.00", unauthorized: !!raw?.unauthorized };
}


async function apiFetchCart() {
    if (!RID) return { items: [], total_quantity: 0, total_amount: "0.00" };
    const res = await fetch(`/api/cart/?rid=${RID}`, { credentials: "include" });
    if (res.status === 401 || res.status === 403) return { unauthorized: true };
    if (!res.ok) throw new Error("获取购物车失败");
    return res.json();
}


async function apiAddToCart(dishId, qty = 1) {
    // 后端 add 接口现在是独立的 /api/cart/add/，入参是 {dish_id, qty}
    const res = await fetch("/api/cart/add/", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrfToken() },
        credentials: "include",
        body: JSON.stringify({ dish_id: dishId, qty })
    });
    if (!res.ok) throw new Error((await res.text()) || "加入购物车失败");
    return res.json();
}


async function apiPatchCart(itemId, newQty) {
    // Session 购物车没有“购物车行 id”，用 dish_id + rid 来更新
    const res = await fetch("/api/cart/update/", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrfToken() },
        credentials: "include",
        body: JSON.stringify({ rid: RID, dish_id: Number(dishId), qty: Number(newQty) })
    });
    if (!res.ok) throw new Error((await res.text()) || "更新数量失败");
    return res.json();
}

async function apiDeleteCartItem(dishId) {
    // 没有专门 remove 接口，用 update qty=0 代表删除
    const res = await fetch("/api/cart/update/", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrfToken() },
        credentials: "include",
        body: JSON.stringify({ rid: RID, dish_id: Number(dishId), qty: 0 })
    });
    if (!res.ok) throw new Error((await res.text()) || "删除失败");
}

async function apiClearCart() {
    // 两种任选其一：① DELETE /api/cart/?rid=RID ② POST /api/cart/clear/ {rid}
    const res = await fetch(`/api/cart/?rid=${RID}`, {
        method: "DELETE",
        headers: { "X-CSRFToken": getCsrfToken() },
        credentials: "include",
    });
    if (!res.ok) throw new Error("清空失败");
    return res.json();
}

// ---- 迷你购物车渲染 ----
function renderMiniCart(data) {
    const loading = document.getElementById("mini-cart-loading");
    const notice = document.getElementById("mini-cart-notice");
    const empty = document.getElementById("mini-cart-empty");
    const list = document.getElementById("mini-cart-list");
    const summary = document.getElementById("mini-cart-summary");
    const qtyEl = document.getElementById("mini-cart-qty");
    const amtEl = document.getElementById("mini-cart-amount");

    if (!loading) return; // 不在首页就不处理

    loading.classList.add("hidden");
    notice.classList.add("hidden");
    empty.classList.add("hidden");
    list.classList.add("hidden");
    summary.classList.add("hidden");

    if (data.unauthorized) { notice.classList.remove("hidden"); return; }

    const items = data.items || [];
    if (!items.length) { empty.classList.remove("hidden"); return; }

    list.innerHTML = items.map(i => `
    <li class="py-2 flex items-start gap-3" data-id="${i.id}">
      <div class="flex-1 min-w-0">
        <div class="truncate">${i.dish_name}</div>
        <div class="text-xs text-slate-500">¥ ${i.dish_price} × 
          <button class="px-1 border rounded mini-minus">-</button>
          <input type="number" min="1" value="${i.quantity}" class="w-14 text-center border rounded mini-qty">
          <button class="px-1 border rounded mini-plus">+</button>
        </div>
      </div>
      <div class="text-right">
        <div class="text-rose-600 font-medium">¥ ${i.line_amount}</div>
        <button class="text-xs text-rose-700 underline mini-remove">删除</button>
      </div>
    </li>
  `).join("");

    qtyEl.textContent = data.total_quantity || 0;
    amtEl.textContent = "¥ " + (data.total_amount || "0.00");

    list.classList.remove("hidden");
    summary.classList.remove("hidden");
}

async function refreshMiniCart() {
    try {
        console.log("refresh mini cart now");
        const raw = await apiFetchCart();
        const data = normalizeCartData(raw);   // ← 新增：归一化
        renderMiniCart(data);
    } catch (e) {
        console.error(e);
        toast("加载购物车失败", false);
    }
}

// ---- 首页“加入购物车”按钮 ----
document.addEventListener("click", async (e) => {
    const btn = e.target.closest(".add-to-cart");
    if (!btn) return;
    const id = parseInt(btn.dataset.dish, 10);
    btn.disabled = true;
    try {
        await apiAddToCart(id, 1);
        await refreshMiniCart();     // 加入后刷新右侧
        toast("已加入购物车");
    } catch (err) {
        toast(err.message || "加入购物车失败", false);
    } finally {
        btn.disabled = false;
    }
});

// ---- 迷你购物车交互：+ / - / 直接改 / 删除 / 清空 ----
document.addEventListener("click", async (e) => {
    // 只处理在迷你购物车里的点击
    const li = e.target.closest("#mini-cart-list li");
    if (!li) return;

    const id = li.dataset.id;
    const qtyInput = li.querySelector(".mini-qty");
    const cur = parseInt(qtyInput.value, 10) || 1;

    if (e.target.closest(".mini-plus")) {
        try { await apiPatchCart(id, cur + 1); await refreshMiniCart(); }
        catch (err) { toast(err.message, false); }
    }
    if (e.target.closest(".mini-minus")) {
        if (cur <= 1) return;
        try { await apiPatchCart(id, cur - 1); await refreshMiniCart(); }
        catch (err) { toast(err.message, false); }
    }
    if (e.target.closest(".mini-remove")) {
        try { await apiDeleteCartItem(id); await refreshMiniCart(); toast("已删除"); }
        catch (err) { toast(err.message, false); }
    }
});

document.addEventListener("change", async (e) => {
    const input = e.target.closest("#mini-cart-list .mini-qty");
    if (!input) return;
    const li = input.closest("li[data-id]");
    const id = li.dataset.id;
    let v = parseInt(input.value, 10) || 1;
    if (v < 1) v = 1;
    input.value = v;
    try { await apiPatchCart(id, v); await refreshMiniCart(); }
    catch (err) { toast(err.message, false); }
});

// 清空
document.getElementById("mini-cart-clear")?.addEventListener("click", async () => {
    try { await apiClearCart(); await refreshMiniCart(); toast("已清空"); }
    catch (err) { toast(err.message, false); }
});

// 页面载入时，尝试拉取一次迷你购物车
document.addEventListener("DOMContentLoaded", () => {
    if (document.getElementById("mini-cart-loading")) {
        refreshMiniCart();
    }
});

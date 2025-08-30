// 依赖 app.js 中的 getCsrfToken() / toast()。如果分文件加载顺序，请确保 app.js 在前。
async function patchQuantity(itemId, newQty) {
    const res = await fetch(`/api/cart/${itemId}/`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrfToken() },
        credentials: "include",
        body: JSON.stringify({ quantity: newQty })
    });
    if (!res.ok) throw new Error((await res.json()).detail || "修改数量失败");
    return res.json();
}

async function deleteItem(itemId) {
    const res = await fetch(`/api/cart/${itemId}/`, {
        method: "DELETE",
        headers: { "X-CSRFToken": getCsrfToken() },
        credentials: "include",
    });
    if (!res.ok && res.status !== 204) throw new Error("删除失败");
}

async function clearCart() {
    const res = await fetch(`/api/cart/clear/`, {
        method: "DELETE",
        headers: { "X-CSRFToken": getCsrfToken() },
        credentials: "include",
    });
    if (!res.ok) throw new Error("清空失败");
    return res.json();
}

function recalcRow(tr) {
    const priceText = tr.querySelector("td:nth-child(2)").textContent.replace(/[^\d.]/g, "");
    const price = parseFloat(priceText || "0");
    const qty = parseInt(tr.querySelector(".qty-input").value, 10) || 1;
    const line = (price * qty).toFixed(2);
    tr.querySelector(".line-total").textContent = "¥ " + line;
    return { qty, line: parseFloat(line) };
}
function recalcSummary() {
    let sumQty = 0, sumAmount = 0;
    document.querySelectorAll("#cart-tbody tr").forEach(tr => {
        const qty = parseInt(tr.querySelector(".qty-input").value, 10) || 0;
        const lineText = tr.querySelector(".line-total").textContent.replace(/[^\d.]/g, "");
        sumQty += qty;
        sumAmount += parseFloat(lineText || "0");
    });
    document.getElementById("sum-qty").textContent = sumQty;
    document.getElementById("sum-amount").textContent = "¥ " + sumAmount.toFixed(2);
}

document.addEventListener("click", async (e) => {
    const tr = e.target.closest("tr[data-id]");
    if (e.target.closest(".plus")) {
        const input = tr.querySelector(".qty-input");
        const newQty = (parseInt(input.value, 10) || 1) + 1;
        try {
            await patchQuantity(tr.dataset.id, newQty);
            input.value = newQty;
            recalcRow(tr); recalcSummary();
            toast("已更新数量");
        } catch (err) { toast(err.message, false); }
    }
    if (e.target.closest(".minus")) {
        const input = tr.querySelector(".qty-input");
        const cur = parseInt(input.value, 10) || 1;
        const newQty = Math.max(1, cur - 1);
        if (newQty === cur) return;
        try {
            await patchQuantity(tr.dataset.id, newQty);
            input.value = newQty;
            recalcRow(tr); recalcSummary();
            toast("已更新数量");
        } catch (err) { toast(err.message, false); }
    }
    if (e.target.closest(".remove")) {
        try {
            await deleteItem(tr.dataset.id);
            tr.remove();
            recalcSummary();
            toast("已删除");
        } catch (err) { toast(err.message, false); }
    }
});

document.addEventListener("change", async (e) => {
    const input = e.target.closest(".qty-input");
    if (!input) return;
    const tr = e.target.closest("tr[data-id]");
    let newQty = parseInt(input.value, 10) || 1;
    if (newQty < 1) newQty = 1;
    input.value = newQty;
    try {
        await patchQuantity(tr.dataset.id, newQty);
        recalcRow(tr); recalcSummary();
        toast("已更新数量");
    } catch (err) { toast(err.message, false); }
});

document.getElementById("clear-cart")?.addEventListener("click", async () => {
    try {
        const res = await fetch(`/api/cart/clear/`, {
            method: "DELETE",
            headers: { "X-CSRFToken": getCsrfToken() },
            credentials: "include",
        });
        if (res.status === 401 || res.status === 403) {
            window.location.href = "/admin/login/?next=/cart/";
            return;
        }
        if (!res.ok) throw new Error("清空失败");
        document.getElementById("cart-tbody").innerHTML = "";
        recalcSummary();
        toast("已清空");
        // 清空后把按钮禁用
        const btn = document.getElementById("clear-cart");
        if (btn) btn.disabled = true;
    } catch (err) {
        toast(err.message || "清空失败", false);
    }
});


async function addToCart(dishId, qty = 1) {
    const r = await fetch("/api/cart/add/", {
        method: "POST",
        headers: { "X-CSRFToken": getCsrfToken(), "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ dish_id: dishId, qty })
    });
    const data = await r.json();
    if (!r.ok) { alert("加入失败"); return; }
    // data.rid / data.total_qty / data.total_amount 可更新右侧视图
}

async function updateCartItem(dishId, qty) {
    const rid = window.__RID__;
    const r = await fetch("/api/cart/update/", {
        method: "POST",
        headers: { "X-CSRFToken": getCsrfToken(), "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ rid, dish_id: dishId, qty })
    });
    const data = await r.json();
    if (!r.ok) { alert(data.detail || "更新失败"); return; }
    // 刷新右侧
}

async function clearCart() {
    const rid = window.__RID__;
    const r = await fetch("/api/cart/clear/", {
        method: "POST",
        headers: { "X-CSRFToken": getCsrfToken(), "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ rid })
    });
    const data = await r.json();
    if (!r.ok) { alert(data.detail || "清空失败"); return; }
    // 清空右侧
}
// cart.js —— 购物车页面脚本（只用 DRF ViewSet 接口）

// 依赖 app.js 里已提供的 getCsrfToken() / toast()

async function patchQuantity(itemId, newQty) {
    const res = await fetch(`/api/cart/${itemId}/`, {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrfToken(),
        },
        credentials: "include",
        body: JSON.stringify({ quantity: newQty }),
    });
    if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "修改数量失败");
    }
    return res.json(); // 一般不强依赖返回体，成功即可本地改 DOM
}

async function deleteItem(itemId) {
    const res = await fetch(`/api/cart/${itemId}/`, {
        method: "DELETE",
        headers: { "X-CSRFToken": getCsrfToken() },
        credentials: "include",
    });
    if (!res.ok && res.status !== 204) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "删除失败");
    }
}

async function clearAll() {
    const res = await fetch(`/api/cart/clear/`, {
        method: "DELETE",
        headers: { "X-CSRFToken": getCsrfToken() },
        credentials: "include",
    });
    if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "清空失败");
    }
    return res.json().catch(() => ({}));
}

// —— 纯前端：根据行内单价和数量，重算该行小计
function recalcRow(tr) {
    const priceText = tr.querySelector("td:nth-child(2)").textContent.replace(/[^\d.]/g, "");
    const price = parseFloat(priceText || "0");
    const qty = parseInt(tr.querySelector(".qty-input").value, 10) || 1;
    const line = (price * qty).toFixed(2);
    tr.querySelector(".line-total").textContent = "¥ " + line;
    return { qty, line: parseFloat(line) };
}

// —— 纯前端：重算整单汇总
function recalcSummary() {
    let sumQty = 0, sumAmount = 0;
    document.querySelectorAll("#cart-tbody tr[data-id]").forEach(tr => {
        const qty = parseInt(tr.querySelector(".qty-input").value, 10) || 0;
        const lineText = tr.querySelector(".line-total").textContent.replace(/[^\d.]/g, "");
        sumQty += qty;
        sumAmount += parseFloat(lineText || "0");
    });
    const qtyEl = document.getElementById("sum-qty");
    const amtEl = document.getElementById("sum-amount");
    if (qtyEl) qtyEl.textContent = sumQty;
    if (amtEl) amtEl.textContent = "¥ " + sumAmount.toFixed(2);
}

document.addEventListener("DOMContentLoaded", () => {
    const tbody = document.getElementById("cart-tbody");
    if (!tbody) return; // 页面为空车或未登录时没有表格

    // 加号 / 减号 / 删除（事件委托）
    document.addEventListener("click", async (e) => {
        const tr = e.target.closest("tr[data-id]");
        if (!tr) return;
        const itemId = tr.dataset.id;

        // + 按钮
        if (e.target.closest(".plus")) {
            const input = tr.querySelector(".qty-input");
            const newQty = (parseInt(input.value, 10) || 1) + 1;
            try {
                await patchQuantity(itemId, newQty);
                input.value = newQty;
                recalcRow(tr); recalcSummary();
                toast("已更新数量");
            } catch (err) {
                toast(err.message || "更新失败", false);
            }
            return;
        }

        // - 按钮
        if (e.target.closest(".minus")) {
            const input = tr.querySelector(".qty-input");
            const cur = parseInt(input.value, 10) || 1;
            const newQty = Math.max(1, cur - 1);
            if (newQty === cur) return;
            try {
                await patchQuantity(itemId, newQty);
                input.value = newQty;
                recalcRow(tr); recalcSummary();
                toast("已更新数量");
            } catch (err) {
                toast(err.message || "更新失败", false);
            }
            return;
        }

        // 删除
        if (e.target.closest(".remove")) {
            try {
                await deleteItem(itemId);
                tr.remove();
                recalcSummary();
                toast("已删除");
                // 如果清空了，就禁用“清空购物车”按钮
                if (!document.querySelector("#cart-tbody tr[data-id]")) {
                    const btn = document.getElementById("clear-cart");
                    if (btn) btn.disabled = true;
                }
            } catch (err) {
                toast(err.message || "删除失败", false);
            }
        }
    });

    // 直接修改数量（输入框）
    document.addEventListener("change", async (e) => {
        const input = e.target.closest(".qty-input");
        if (!input) return;
        const tr = e.target.closest("tr[data-id]");
        const itemId = tr.dataset.id;
        let newQty = parseInt(input.value, 10) || 1;
        if (newQty < 1) newQty = 1;
        input.value = newQty;
        try {
            await patchQuantity(itemId, newQty);
            recalcRow(tr); recalcSummary();
            toast("已更新数量");
        } catch (err) {
            toast(err.message || "更新失败", false);
        }
    });

    // 清空
    document.getElementById("clear-cart")?.addEventListener("click", async () => {
        try {
            await clearAll();
            tbody.innerHTML = "";
            recalcSummary();
            toast("已清空");
            const btn = document.getElementById("clear-cart");
            if (btn) btn.disabled = true;
        } catch (err) {
            toast(err.message || "清空失败", false);
        }
    });
});

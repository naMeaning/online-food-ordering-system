document.addEventListener("DOMContentLoaded", () => {
    // 确保 #cart-tbody 元素存在
    const cartTableBody = document.querySelector("#cart-tbody");
    if (cartTableBody) {
        fetchCartData();
    } else {
        console.error("#cart-tbody not found");
    }

    // 其他初始化代码...
    document.querySelector("#cart-tbody").addEventListener("click", (e) => {
        // 确保事件绑定在正确的元素上
        if (e.target.classList.contains("minus") || e.target.classList.contains("plus")) {
            // Handle + / - actions
        } else if (e.target.classList.contains("remove")) {
            // Handle remove action
        }
    });
});



// 获取购物车数据并渲染到页面
async function fetchCartData() {
    const res = await fetch("/api/cart/", { credentials: "include" });
    if (!res.ok) {
        console.error("获取购物车数据失败", await res.json());
        return;
    }
    const data = await res.json();
    renderCartItems(data.items, data.total_qty, data.total_amount);
}

// 渲染购物车条目
function renderCartItems(items, totalQty, totalAmount) {
    const cartTableBody = document.querySelector("#cart-tbody");
    const totalQtyElement = document.querySelector("#sum-qty");
    const totalAmountElement = document.querySelector("#sum-amount");

    if (items.length === 0) {
        cartTableBody.innerHTML = "<tr><td colspan='5'>购物车为空</td></tr>";
    } else {
        cartTableBody.innerHTML = ""; // 清空原有的内容
        items.forEach(item => {
            const row = document.createElement("tr");
            row.classList.add("border-t");
            row.dataset.id = item.id;

            row.innerHTML = `
                <td class="p-3">
                    <div class="flex items-center gap-3">
                        ${item.dish.cover ? `<img src="${item.dish.cover_url}" class="w-14 h-14 object-cover rounded-md">` : ""}
                        <div>
                            <div class="font-medium">${item.dish_name}</div>
                            <div class="text-slate-500 text-xs">#${item.dish.category_name}</div>
                        </div>
                    </div>
                </td>
                <td class="p-3 text-rose-600 font-semibold">¥ ${item.dish_price}</td>
                <td class="p-3">
                    <div class="inline-flex items-center gap-1">
                        <button class="px-2 py-1 rounded border minus">-</button>
                        <input type="number" min="1" value="${item.quantity}" class="w-16 text-center rounded border qty-input">
                        <button class="px-2 py-1 rounded border plus">+</button>
                    </div>
                </td>
                <td class="p-3 font-medium line-total">¥ ${item.line_amount}</td>
                <td class="p-3">
                    <button class="px-3 py-1 rounded border border-rose-300 text-rose-700 remove">删除</button>
                </td>
            `;
            cartTableBody.appendChild(row);
        });
    }

    // 更新总数和总金额
    totalQtyElement.textContent = totalQty;
    totalAmountElement.textContent = `¥ ${totalAmount}`;
}

// 页面加载时获取购物车数据
document.addEventListener("DOMContentLoaded", () => {
    fetchCartData();
});





// 更新购物车的数量或移除商品时调用的函数
document.querySelector("#cart-tbody").addEventListener("click", (e) => {
    if (e.target.classList.contains("minus") || e.target.classList.contains("plus")) {
        // 调用API更新数量
        const id = e.target.closest("tr").dataset.id;
        const qtyInput = e.target.closest("tr").querySelector(".qty-input");
        const newQty = e.target.classList.contains("plus") ? parseInt(qtyInput.value) + 1 : parseInt(qtyInput.value) - 1;

        if (newQty < 1) return;

        updateCartItem(id, newQty);
    } else if (e.target.classList.contains("remove")) {
        // 调用API移除商品
        const id = e.target.closest("tr").dataset.id;
        removeCartItem(id);
    }
});







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
        headers: { "X-CSRFToken": getCsrfToken(), "Content-Type": getCsrfToken() },
        credentials: "include",
        body: JSON.stringify({ dish_id: dishId, qty })
    });
    const data = await r.json();
    if (!r.ok) { alert("加入失败"); return; }
    // data.rid / data.total_qty / data.total_amount 可更新右侧视图
}

// async function updateCartItem(dishId, qty) {
//     const rid = window.__RID__;
//     const r = await fetch("/api/cart/update/", {
//         method: "POST",
//         headers: {  "Content-Type": "application/json" ,"X-CSRFToken": getCsrfToken()},
//         credentials: "include",
//         body: JSON.stringify({ rid, dish_id: dishId, qty })
//     });
//     const data = await r.json();
//     if (!r.ok) { alert(data.detail || "更新失败"); return; }
//     // 刷新右侧
// }
// 更新购物车条目的数量
async function updateCartItem(id, quantity) {
    const res = await fetch("/api/cart/update/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrfToken(),
        },
        body: JSON.stringify({ id, quantity })
    });
    const data = await res.json();
    if (res.ok) {
        fetchCartData();
    } else {
        console.error("更新购物车条目失败:", data);
    }
}


// 从购物车中移除商品
async function removeCartItem(id) {
    const res = await fetch("/api/cart/remove/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrfToken(),
        },
        body: JSON.stringify({ id })
    });
    const data = await res.json();
    if (res.ok) {
        fetchCartData();
    } else {
        console.error("移除购物车条目失败:", data);
    }
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


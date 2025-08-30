


function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.content && meta.content !== "NOTPROVIDED") return meta.content;
    const m = document.cookie.match(/(^|;)\s*csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[2]) : "";
}
function uuid() { // 简单 UUID（幂等用）
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
        const r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8); return v.toString(16);
    });
}
const $ = s => document.querySelector(s);

function toggleSections() {
    const st = document.querySelector('input[name="service_type"]:checked').value;
    $("#section-delivery").classList.toggle("hidden", st !== "DELIVERY");
    $("#section-dinein").classList.toggle("hidden", st !== "DINE_IN");
}
document.addEventListener("change", (e) => {
    if (e.target.name === "service_type") toggleSections();
});
document.addEventListener("DOMContentLoaded", toggleSections);

// 提交订单
$("#checkout-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const st = document.querySelector('input[name="service_type"]:checked').value;
    const body = {
        service_type: st,
        payment_method: (document.querySelector('input[name="payment_method"]:checked')?.value) || "DUMMY",
        client_token: uuid()
    };
    body.restaurant_id = window.__RID__ || null;

    if (st === "DELIVERY") {
        body.contact_name = document.querySelector('input[name="contact_name"]').value.trim();
        body.contact_phone = document.querySelector('input[name="contact_phone"]').value.trim();
        body.address_line = document.querySelector('textarea[name="address_line"]').value.trim();
    } else {
        body.table_no = document.querySelector('input[name="table_no"]').value.trim();
    }

    const err = $("#checkout-error");
    err.classList.add("hidden");
    $("#btn-submit").disabled = true;
    try {
        const res = await fetch("/api/orders/", {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrfToken() },
            credentials: "include",
            body: JSON.stringify(body)
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            err.textContent = data.detail || JSON.stringify(data);
            err.classList.remove("hidden");
            return;
        }
        // 跳到订单详情页
        location.href = `/orders/${data.id}/`;
    } catch (e) {
        err.textContent = "提交失败，请稍后重试";
        err.classList.remove("hidden");
    } finally {
        $("#btn-submit").disabled = false;
    }
});


async function submitOrder() {
    const rid = window.__RID__;                // 来自模板注入
    const service = getSelectedServiceType();  // "DELIVERY" / "DINE_IN"
    const payload = {
        restaurant_id: rid,                      // ← 必带！否则后端只能靠“猜”
        service_type: service,
        table_no: service === "DINE_IN" ? getTableNo() : null,
        contact_name: service === "DELIVERY" ? getContactName() : "",
        contact_phone: service === "DELIVERY" ? getContactPhone() : "",
        address_line: service === "DELIVERY" ? getAddress() : "",
    };

    const r = await fetch("/api/orders/", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrfToken() },
        credentials: "include",  // ← 用 Session 必须带 cookie
        body: JSON.stringify(payload)
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) {
        alert((data && (data.detail || JSON.stringify(data))) || "提交失败");
        return;
    }
    // 成功：跳转到订单详情
    window.location.href = `/orders/${data.id}/`;
}

// 清空当前店购物车
async function clearCart() {
    const rid = window.__RID__;
    const r = await fetch(`/api/sess-cart/?rid=${rid}`, {
        method: "DELETE",
        headers: { "X-CSRFToken": getCsrfToken() },
        credentials: "include",
    });
    if (!r.ok) { alert("清空失败"); return; }
    // 刷新右侧 UI ...
}

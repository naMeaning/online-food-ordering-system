// static/js/orders_list.js
function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.content && meta.content !== "NOTPROVIDED") return meta.content;
    const m = document.cookie.match(/(^|;)\s*csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[2]) : "";
}
async function postJSON(url, body) {
    const r = await fetch(url, {
        method: "POST",
        headers: { "X-CSRFToken": getCsrfToken(), "Content-Type": "application/json" },
        credentials: "include",
        body: body ? JSON.stringify(body) : null
    });
    const data = await r.json().catch(() => ({}));
    return { ok: r.ok, data };
}
document.addEventListener("click", async (e) => {
    const payBtn = e.target.closest(".pay");
    const cancelBtn = e.target.closest(".cancel");

    if (payBtn) {
        const id = payBtn.dataset.id;
        payBtn.disabled = true;
        const { ok, data } = await postJSON(`/api/orders/${id}/pay/`, { method: "DUMMY" });
        if (!ok) alert(data.detail || "支付失败");
        location.reload();
    }
    if (cancelBtn) {
        const id = cancelBtn.dataset.id;
        if (!confirm("确定取消该订单？")) return;
        cancelBtn.disabled = true;
        const { ok, data } = await postJSON(`/api/orders/${id}/cancel/`);
        if (!ok) alert(data.detail || "取消失败");
        location.reload();
    }
});

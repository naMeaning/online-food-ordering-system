// static/js/checkout.js
document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("checkout-form");
    const btn = document.getElementById("btn-submit");
    const err = document.getElementById("checkout-error");

    if (!form) return;

    toggleSectionsSafe();

    form.addEventListener("change", (e) => {
        if (e.target.name === "service_type") toggleSectionsSafe();
    });

    form.addEventListener("submit", onSubmit);

    async function onSubmit(e) {
        e.preventDefault();
        if (err) { err.textContent = ""; err.classList.add("hidden"); }
        if (btn) btn.disabled = true;

        try {
            const st = form.querySelector('input[name="service_type"]:checked')?.value || "DELIVERY";
            const payload = {
                service_type: st,
                payment_method: (form.querySelector('input[name="payment_method"]:checked')?.value) || "DUMMY",
                client_token: uuid(),
            };
            if (st === "DELIVERY") {
                payload.contact_name = form.querySelector('input[name="contact_name"]')?.value.trim() || "";
                payload.contact_phone = form.querySelector('input[name="contact_phone"]')?.value.trim() || "";
                payload.address_line = form.querySelector('textarea[name="address_line"]')?.value.trim() || "";
            } else {
                payload.table_no = form.querySelector('input[name="table_no"]')?.value.trim() || "";
            }

            const res = await fetch("/api/orders/", {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrfToken() },
                credentials: "include",
                body: JSON.stringify(payload),
            });
            const data = await res.json().catch(() => ({}));

            if (!res.ok) {
                showErr(err, data.detail || JSON.stringify(data) || "提交失败");
                return;
            }

            location.href = `/orders/${data.id}/`;
        } catch (ex) {
            showErr(err, "提交失败，请稍后重试");
        } finally {
            if (btn) btn.disabled = false;
        }
    }
});

function toggleSectionsSafe() {
    const st = document.querySelector('input[name="service_type"]:checked')?.value;
    const del = document.getElementById("section-delivery");
    const din = document.getElementById("section-dinein");
    if (!st || !del || !din) return;
    del.classList.toggle("hidden", st !== "DELIVERY");
    din.classList.toggle("hidden", st !== "DINE_IN");
}

// 兜底：如果 app.js 已提供这两个函数，就用它们；否则用这里的版本
function getCsrfToken() {
    if (typeof window.getCsrfToken === "function") return window.getCsrfToken();
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta?.content && meta.content !== "NOTPROVIDED") return meta.content;
    const m = document.cookie.match(/(^|;)\s*csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[2]) : "";
}
function uuid() {
    if (typeof window.uuid === "function") return window.uuid();
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
        const r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}
function showErr(el, text) {
    if (!el) return alert(text);
    el.textContent = text;
    el.classList.remove("hidden");
}

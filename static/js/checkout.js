// static/js/checkout.js
(function () {
    // 标记脚本是否加载
    window.__checkout_loaded = true;

    // ---- 小工具：CSRF / UUID / 错误提示（若 app.js 已提供则复用） ----
    function getCsrfToken() {
        if (typeof window.getCsrfToken === "function") return window.getCsrfToken();
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta?.content && meta.content !== "NOTPROVIDED") return meta.content;
        const m = document.cookie.match(/(^|;)\s*csrftoken=([^;]+)/);
        return m ? decodeURIComponent(m[2]) : "";
    }
    function uuid() {
        if (typeof window.uuid === "function") return window.uuid();
        return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, c => {
            const r = Math.random() * 16 | 0, v = c === "x" ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }
    function showErr(el, text) {
        if (!el) return alert(text);
        el.textContent = text;
        el.classList.remove("hidden");
    }

    // ---- 切换外送/堂食区域 ----
    function updateSections() {
        const st = document.querySelector('input[name="service_type"]:checked')?.value;
        const delivery = document.getElementById("section-delivery");
        const dinein = document.getElementById("section-dinein");
        if (!delivery || !dinein) return;

        const showDelivery = (st === "DELIVERY");
        // Tailwind 的 hidden + 兜底 display
        delivery.classList.toggle("hidden", !showDelivery);
        dinein.classList.toggle("hidden", showDelivery);
        delivery.style.display = showDelivery ? "" : "none";
        dinein.style.display = showDelivery ? "none" : "";
    }

    // ---- 提交订单 ----
    async function handleSubmit(e) {
        e.preventDefault();

        const form = document.getElementById("checkout-form");
        const btn = document.getElementById("btn-submit");
        const err = document.getElementById("checkout-error");
        if (!form) return;

        // 清掉上次错误
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

                // 前端做个最小校验，避免 400
                if (!payload.contact_name || !payload.contact_phone || !payload.address_line) {
                    showErr(err, "外送需填写 收货人 / 手机号 / 地址");
                    return;
                }
            } else { // DINE_IN
                payload.table_no = form.querySelector('input[name="table_no"]')?.value.trim() || "";
                if (!payload.table_no) {
                    showErr(err, "堂食需填写 桌号/取餐码");
                    return;
                }
                // 堂食时允许联系信息留空，后端已放宽
                payload.contact_name = "";
                payload.contact_phone = "";
                payload.address_line = "";
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

            // ✅ 后端已在 OrderCreateSerializer.create() 里清空购物车（cart_qs.delete()）
            // 成功后跳转到订单详情
            location.href = `/orders/${data.id}/`;
        } catch (ex) {
            console.error(ex);
            showErr(err, "提交失败，请稍后重试");
        } finally {
            if (btn) btn.disabled = false;
        }
    }

    // ---- 绑定 ----
    document.addEventListener("DOMContentLoaded", () => {
        // 先初始化分区显示
        updateSections();
        // 给 radio 绑监听（change+click 更稳）
        document.querySelectorAll('input[name="service_type"]').forEach(r => {
            r.addEventListener("change", updateSections);
            r.addEventListener("click", updateSections);
        });
        // 绑定提交
        const form = document.getElementById("checkout-form");
        if (form) form.addEventListener("submit", handleSubmit);
    });
})();

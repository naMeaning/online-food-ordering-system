function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.content && meta.content !== "NOTPROVIDED") return meta.content;
    const m = document.cookie.match(/(^|;)\s*csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[2]) : "";
}

const STATUS_LABEL = {
    CREATED: "已创建",
    PAID: "已支付",
    CONFIRMED: "已接单",
    READY: "已出餐",
    DELIVERING: "配送中",
    COMPLETED: "已完成",
    CANCELLED: "已取消",
};
const STATUS_BADGE = {
    CREATED: "badge-slate",
    PAID: "badge-emerald",
    CONFIRMED: "badge-indigo",
    READY: "badge-indigo",
    DELIVERING: "badge-amber",
    COMPLETED: "badge-emerald",
    CANCELLED: "badge-rose",
};
const SERVICE_LABEL = { DELIVERY: "外送", DINE_IN: "堂食" };
const TERMINAL = new Set(["COMPLETED", "CANCELLED"]);

async function fetchOrderDetail(id) {
    const res = await fetch(`/api/orders/${id}/`, { credentials: "include" });
    if (!res.ok) throw new Error("获取订单失败");
    return res.json();
}
function fmtTime(t) {
    if (!t) return "";
    // 简单截断：YYYY-MM-DD HH:mm
    return ("" + t).replace("T", " ").slice(0, 16);
}

function renderInfo(o) {
    // 徽章
    const bs = document.getElementById("badge-status");
    const bt = document.getElementById("badge-service");
    bs.textContent = STATUS_LABEL[o.status] || o.status;
    bs.className = `badge ${STATUS_BADGE[o.status] || "badge-slate"}`;
    bt.textContent = SERVICE_LABEL[o.service_type] || o.service_type;
    bt.className = `badge ${o.service_type === "DELIVERY" ? "badge-indigo" : "badge-amber"}`;

    // 地址或桌号
    const addr = document.getElementById("od-address");
    if (o.service_type === "DELIVERY") {
        addr.innerHTML = `
      <div>收货人：${o.contact_name || "-"}　电话：${o.contact_phone || "-"}</div>
      <div>地址：${o.address_line || "-"}</div>
    `;
    } else {
        addr.innerHTML = `<div>堂食　桌号/取餐码：<span class="font-medium">${o.table_no || "-"}</span></div>`;
    }

    // 金额
    document.getElementById("od-total").textContent = "¥ " + o.total_amount;

    // 动作按钮
    const act = document.getElementById("od-actions");
    act.innerHTML = "";
    if (o.status === "CREATED") {
        act.innerHTML = `
      <button id="btn-pay" class="btn">模拟支付</button>
      <button id="btn-cancel" class="btn bg-rose-600 hover:bg-rose-700">取消订单</button>
    `;
        document.getElementById("btn-pay").onclick = async () => {
            const r = await fetch(`/api/orders/${o.id}/pay/`, {
                method: "POST",
                headers: { "X-CSRFToken": getCsrfToken(), "Content-Type": "application/json" },
                credentials: "include",
                body: JSON.stringify({ method: "DUMMY" })
            });
            if (r.ok) load(); else alert("支付失败");
        };
        document.getElementById("btn-cancel").onclick = async () => {
            if (!confirm("确定取消该订单？")) return;
            const r = await fetch(`/api/orders/${o.id}/cancel/`, {
                method: "POST",
                headers: { "X-CSRFToken": getCsrfToken() },
                credentials: "include",
            });
            if (r.ok) load(); else alert("取消失败");
        };
    } else if (o.status === "PAID") {
        act.innerHTML = `<span class="text-emerald-600 text-sm">已支付，等待商家接单</span>`;
    } else if (o.status === "CONFIRMED") {
        act.innerHTML = `<span class="text-slate-600 text-sm">商家已接单，制作中…</span>`;
    } else if (o.status === "READY") {
        act.innerHTML = `<span class="text-indigo-700 text-sm">已出餐，${o.service_type === "DELIVERY" ? "等待配送" : "请到前台取餐"}</span>`;
    } else if (o.status === "DELIVERING") {
        act.innerHTML = `<span class="text-amber-700 text-sm">配送中…</span>`;
    } else if (o.status === "COMPLETED") {
        act.innerHTML = `<a href="/" class="btn">再来一单</a>`;
    } else if (o.status === "CANCELLED") {
        act.innerHTML = `<a href="/" class="btn">重新下单</a>`;
    }
}

function renderTimeline(o) {
    const ul = document.getElementById("od-timeline");
    const arr = (o.status_history || []).map(h => `
    <li class="timeline-item">
      <div class="timeline-dot"></div>
      <div class="timeline-content">
        <div class="font-medium">${STATUS_LABEL[h.to_status] || h.to_status}</div>
        <div class="text-xs text-slate-500">${fmtTime(h.created_at)}　${h.message || ""}</div>
      </div>
    </li>
  `);
    ul.innerHTML = arr.join("") || `<li class="text-slate-500 text-sm">暂无记录</li>`;
}

let timer = null;
async function load() {
    const id = window.__ORDER_ID__;
    try {
        const o = await fetchOrderDetail(id);
        renderInfo(o);
        renderTimeline(o);
        // 非终态则轮询
        if (!TERMINAL.has(o.status)) {
            clearTimeout(timer);
            timer = setTimeout(load, 7000);
        }
    } catch (e) {
        console.error(e);
        alert("加载订单失败");
    }
}
document.addEventListener("DOMContentLoaded", load);

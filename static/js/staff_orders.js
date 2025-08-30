function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.content && meta.content !== "NOTPROVIDED") return meta.content;
    const m = document.cookie.match(/(^|;)\s*csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[2]) : "";
}

async function getStaffOrders(params = {}) {
    const qs = new URLSearchParams(params).toString();
    const url = "/api/staff/orders/" + (qs ? `?${qs}` : "");
    const r = await fetch(url, { credentials: "include" });
    if (!r.ok) throw new Error("加载失败：" + r.status);
    return r.json();
}

async function postAction(id, action) {
    const r = await fetch(`/api/staff/orders/${id}/${action}/`, {
        method: "POST",
        credentials: "include",
        headers: { "X-CSRFToken": getCsrfToken() },
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.detail || `${action} 失败`);
    return data;
}

function badgeStatus(s, text) {
    const map = {
        CREATED: "badge-slate",
        PAID: "badge-emerald",
        CONFIRMED: "badge-indigo",
        READY: "badge-indigo",
        DELIVERING: "badge-amber",
        COMPLETED: "badge-emerald",
        CANCELLED: "badge-rose",
    };
    const cls = map[s] || "badge-slate";
    return `<span class="badge ${cls}">${text || s}</span>`;
}
function badgeService(s, text) {
    return `<span class="badge ${s === 'DELIVERY' ? 'badge-indigo' : 'badge-amber'}">${text || s}</span>`;
}

function renderList(data) {
    const box = document.getElementById("list");
    if (!data || !data.results || data.results.length === 0) {
        box.innerHTML = `<div class="card text-slate-600">暂无符合条件的订单。</div>`;
        return;
    }
    box.innerHTML = data.results.map(o => `
    <div class="card">
      <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        <div>
          <div class="flex items-center gap-2">
            <a href="/orders/${o.id}/" class="font-semibold">订单 #${o.id}</a>
            ${badgeStatus(o.status, o.status_display || "")}
            ${badgeService(o.service_type, o.service_type_display || "")}
          </div>
          <div class="text-xs text-slate-500 mt-1">创建于 ${o.created_at || ""}</div>
          <ul class="mt-2 text-sm text-slate-700">
            ${(o.items || []).slice(0, 2).map(it => (
        `<li>${it.dish_name} × ${it.quantity}（¥${Number(it.unit_price).toFixed(2)}）</li>`
    )).join("")}
            ${o.items && o.items.length > 2 ? `<li class="text-slate-500 text-xs">…… 等共 ${o.items.length} 件</li>` : ""}
          </ul>
        </div>
        <div class="text-right">
          <div class="text-lg">合计：<span class="text-rose-600 font-semibold">¥ ${o.total_amount}</span></div>
          <div class="mt-2 flex justify-end gap-2">
            ${o.status === 'PAID' ? `<button class="btn act" data-id="${o.id}" data-act="confirm">接单</button>` : ""}
            ${o.status === 'CONFIRMED' ? `<button class="btn act" data-id="${o.id}" data-act="ready">出餐</button>` : ""}
            ${o.status === 'READY' && o.service_type === 'DELIVERY' ? `<button class="btn act" data-id="${o.id}" data-act="deliver">配送中</button>` : ""}
            ${(o.status === 'DELIVERING' && o.service_type === 'DELIVERY') || (o.status === 'READY' && o.service_type === 'DINE_IN') ? `<button class="btn act" data-id="${o.id}" data-act="complete">完成</button>` : ""}
          </div>
        </div>
      </div>
    </div>
  `).join("");
}

let timer = null;
async function load() {
    const params = {};
    const st = document.getElementById("f-status").value;
    const sv = document.getElementById("f-service").value;
    if (st) params.status = st;
    if (sv) params.service = sv;
    try {
        const data = await getStaffOrders(params);
        renderList(data);
    } catch (e) {
        document.getElementById("list").innerHTML = `<div class="card text-rose-700">${e.message}</div>`;
    } finally {
        clearTimeout(timer);
        timer = setTimeout(load, 7000);
    }
}

document.addEventListener("click", async (e) => {
    const actBtn = e.target.closest(".act");
    if (!actBtn) return;
    const { id, act } = actBtn.dataset;
    actBtn.disabled = true;
    try {
        await postAction(id, act);
        await load();
    } catch (e2) {
        alert(e2.message);
    } finally {
        actBtn.disabled = false;
    }
});
document.getElementById("btn-refresh")?.addEventListener("click", load);
document.getElementById("f-status")?.addEventListener("change", load);
document.getElementById("f-service")?.addEventListener("change", load);

document.addEventListener("DOMContentLoaded", load);

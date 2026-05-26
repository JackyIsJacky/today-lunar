"use strict";

const Utils = {
    apiGet(url) {
        return fetch(url, {
            headers: { "Content-Type": "application/json" },
        }).then((r) => r.json());
    },

    apiPost(url, data) {
        return fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
        }).then((r) => r.json());
    },

    formatMoney(n) {
        if (n === null || n === undefined) return "--";
        if (Math.abs(n) >= 1e8) return (n / 1e8).toFixed(2) + " 億";
        if (Math.abs(n) >= 1e4) return (n / 1e4).toFixed(1) + " 萬";
        return n.toLocaleString();
    },

    formatPercent(n, decimals) {
        if (n === null || n === undefined) return "--";
        return (n * 100).toFixed(decimals ?? 2) + "%";
    },

    formatPnL(n) {
        if (n === null || n === undefined) return "--";
        const sign = n >= 0 ? "+" : "";
        return sign + n.toLocaleString();
    },

    colorClassPnL(n) {
        if (n === null || n === undefined) return "";
        return n >= 0 ? "text-danger" : "text-success";
    },

    updateStatusDot(type) {
        const dot = document.getElementById("statusDot");
        const txt = document.getElementById("statusText");
        if (!dot) return;
        dot.className = "status-dot";
        if (type === "warning") dot.classList.add("warning");
        if (type === "error") dot.classList.add("error");
        if (txt) {
            const map = { ok: "系統就緒", warning: "處理中...", error: "異常" };
            txt.textContent = map[type] || "系統就緒";
        }
    },

    showToast(msg, type) {
        const cls = type === "error" ? "bg-danger" : type === "success" ? "bg-success" : "bg-secondary";
        const div = document.createElement("div");
        div.className = `toast align-items-center text-white ${cls} border-0 position-fixed top-0 end-0 m-3`;
        div.style.zIndex = "9999";
        div.innerHTML = `<div class="d-flex"><div class="toast-body">${msg}</div><button class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button></div>`;
        document.body.appendChild(div);
        const toast = new bootstrap.Toast(div);
        toast.show();
        setTimeout(() => div.remove(), 5000);
    },
};

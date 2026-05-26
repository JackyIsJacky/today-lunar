"use strict";

document.addEventListener("DOMContentLoaded", () => {
    loadPortfolio();
    bindButtons();
});

async function loadPortfolio() {
    try {
        const [summary, positions, history] = await Promise.all([
            Utils.apiGet("/api/portfolio/summary"),
            Utils.apiGet("/api/portfolio/positions"),
            Utils.apiGet("/api/portfolio/history"),
        ]);
        renderSummary(summary);
        renderPositions(positions);
        renderHistory(history);
        loadExitAlerts();
    } catch (e) {
        console.error("Failed to load portfolio:", e);
    }
}

async function loadExitAlerts() {
    try {
        const alerts = await Utils.apiGet("/api/portfolio/exit_alerts");
        const panel = document.getElementById("exitAlertPanel");
        const tbody = document.getElementById("exitAlertTableBody");
        const count = document.getElementById("exitAlertCount");

        if (!alerts || alerts.length === 0) {
            if (panel) panel.style.display = "none";
            return;
        }

        if (panel) panel.style.display = "";
        if (count) count.textContent = alerts.length;

        if (tbody) {
            tbody.innerHTML = alerts.map((a) => `
                <tr>
                    <td><a href="/stock/${a.stock_id}">${a.stock_id}</a></td>
                    <td>${a.stock_name || a.stock_id}</td>
                    <td>${a.cost_price || "--"}</td>
                    <td>${a.support_price || "--"}</td>
                    <td>${a.current_price || "--"}</td>
                    <td><span class="badge bg-danger">${a.alert_type || "警示"}</span></td>
                    <td class="small">${a.description || "--"}</td>
                </tr>
            `).join("");
        }
    } catch (e) {
        console.error("Exit alerts:", e);
    }
}

function renderSummary(s) {
    document.getElementById("initialCapital").textContent = (s.initial_capital || 0).toLocaleString();
    document.getElementById("availableCash").textContent = (s.cash || 0).toLocaleString();
    document.getElementById("totalMarketValue").textContent = (s.total_market_value || 0).toLocaleString();
    document.getElementById("totalPnL").textContent = Utils.formatPnL(s.total_pnl);
    document.getElementById("totalPnL").className = "info-card-value " + Utils.colorClassPnL(s.total_pnl);
    document.getElementById("totalReturnPct").textContent = Utils.formatPercent(s.total_return / 100);
    document.getElementById("totalReturnPct").className = "info-card-value " + Utils.colorClassPnL(s.total_return);
    document.getElementById("winRate").textContent = (s.win_rate || 0) + "%";
    document.getElementById("positionCount").textContent = (s.position_count || 0) + " 檔";
}

function renderPositions(positions) {
    const tbody = document.getElementById("positionTableBody");
    if (!tbody) return;
    if (!positions || positions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10" class="text-center text-muted">尚無庫存</td></tr>';
        return;
    }
    tbody.innerHTML = positions.map((p) => {
        const pnlClass = (p.pnl_pct || 0) >= 0 ? "text-danger" : "text-success";
        const pnlSign = (p.pnl_pct || 0) >= 0 ? "+" : "";
        return `
            <tr>
                <td><a href="/stock/${p.stock_id}">${p.stock_id}</a></td>
                <td>${p.stock_name || p.stock_id}</td>
                <td>${p.shares || 0}</td>
                <td>${(p.buy_price || 0).toFixed(2)}</td>
                <td>${(p.current_price || 0).toFixed(2)}</td>
                <td class="${pnlClass}">${pnlSign}${(p.pnl_pct || 0).toFixed(2)}%</td>
                <td>${(p.support_price || 0).toFixed(2)}</td>
                <td class="small text-muted">${p.entry_reason || "--"}</td>
                <td><span class="badge bg-secondary">持有</span></td>
                <td>
                    <button class="btn btn-sm btn-danger sell-btn" data-id="${p.id}" data-stock="${p.stock_id}">
                        <i class="bi bi-cart-dash"></i> 賣出
                    </button>
                </td>
            </tr>
        `;
    }).join("");

    tbody.querySelectorAll(".sell-btn").forEach((btn) => {
        btn.addEventListener("click", async () => {
            const pid = btn.dataset.id;
            const sid = btn.dataset.stock;
            try {
                const daily = await Utils.apiGet(`/api/stock/${sid}`);
                const price = daily.kline && daily.kline.length > 0
                    ? daily.kline[daily.kline.length - 1].close
                    : 0;
                if (!price || !confirm(`確定以 ${price} 賣出 ${sid}？`)) return;
                const res = await Utils.apiPost("/api/portfolio/sell", {
                    position_id: parseInt(pid),
                    price: price,
                    reason: "手動賣出",
                });
                if (res.success) {
                    Utils.showToast(res.message, "success");
                    loadPortfolio();
                } else {
                    Utils.showToast(res.message, "error");
                }
            } catch (e) {
                Utils.showToast("賣出失敗", "error");
            }
        });
    });
}

function renderHistory(history) {
    const tbody = document.getElementById("tradeHistoryBody");
    if (!tbody) return;
    if (!history || history.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">尚無交易紀錄</td></tr>';
        return;
    }
    tbody.innerHTML = history.map((h) => {
        const dirBadge = h.direction === "buy"
            ? '<span class="badge bg-danger">買進</span>'
            : '<span class="badge bg-success">賣出</span>';
        const pnlClass = (h.pnl || 0) >= 0 ? "text-danger" : "text-success";
        return `
            <tr>
                <td>${h.date || "--"}</td>
                <td><a href="/stock/${h.stock_id}">${h.stock_id}</a></td>
                <td>${dirBadge}</td>
                <td>${h.shares || 0}</td>
                <td>${(h.price || 0).toFixed(2)}</td>
                <td class="small text-muted">${h.reason || "--"}</td>
                <td class="${pnlClass}">${h.pnl != null ? Utils.formatPnL(h.pnl) : "--"}</td>
            </tr>
        `;
    }).join("");
}

function bindButtons() {
    document.getElementById("btnManualBuy")?.addEventListener("click", () => {
        const sid = prompt("請輸入股票代碼:");
        if (!sid) return;
        const name = prompt("股票名稱:", sid);
        const price = parseFloat(prompt("買入價格(元):", "0"));
        const shares = parseInt(prompt("買入張數:", "1"));
        if (!price || !shares) return;

        Utils.apiPost("/api/portfolio/buy", {
            stock_id: sid, stock_name: name || sid, price, shares,
            reason: "手動買入",
        }).then((r) => {
            if (r.success) {
                Utils.showToast(r.message, "success");
                loadPortfolio();
            } else {
                Utils.showToast(r.message, "error");
            }
        });
    });

    document.getElementById("btnManualSell")?.addEventListener("click", () => {
        const pid = prompt("請輸入庫存ID (在庫存表格中顯示):");
        if (!pid) return;
        const price = parseFloat(prompt("賣出價格(元):", "0"));
        if (!price) return;
        Utils.apiPost("/api/portfolio/sell", {
            position_id: parseInt(pid), price, reason: "手動賣出",
        }).then((r) => {
            if (r.success) {
                Utils.showToast(r.message, "success");
                loadPortfolio();
            } else {
                Utils.showToast(r.message, "error");
            }
        });
    });

    document.getElementById("btnResetAccount")?.addEventListener("click", async () => {
        if (!confirm("確定要重設虛擬帳戶？所有庫存與交易紀錄將被清除。")) return;
        const r = await Utils.apiPost("/api/portfolio/reset", {});
        if (r.success) {
            Utils.showToast("帳戶已重設", "success");
            loadPortfolio();
        }
    });

    document.getElementById("btnExportRecords")?.addEventListener("click", () => {
        Utils.showToast("匯出功能尚未實作", "warning");
    });

    document.getElementById("btnSellAllAlerts")?.addEventListener("click", async () => {
        if (!confirm("確定要賣出所有警示庫存？")) return;
        try {
            const r = await Utils.apiPost("/api/portfolio/sell", { position_id: "all", reason: "出場警示" });
            Utils.showToast("已全數賣出", "success");
            loadPortfolio();
        } catch (e) {
            Utils.showToast("賣出失敗", "error");
        }
    });
}

"use strict";

document.addEventListener("DOMContentLoaded", () => {
    bindButtons();
});

function bindButtons() {
    const btnStart = document.getElementById("btnStartBacktest");
    const btnStop = document.getElementById("btnStopBacktest");
    const progressDiv = document.getElementById("btProgress");

    btnStart?.addEventListener("click", async () => {
        const startDate = document.getElementById("btStartDate").value;
        const endDate = document.getElementById("btEndDate").value;
        const capital = parseFloat(document.getElementById("btCapital").value);
        const commission = parseFloat(document.getElementById("btCommission").value);
        const ratio = parseFloat(document.getElementById("btTradeRatio").value);

        const steps = [];
        if (document.getElementById("btStep1")?.checked) steps.push(1);
        if (document.getElementById("btStep2")?.checked) steps.push(2);
        if (document.getElementById("btStep3")?.checked) steps.push(3);
        if (document.getElementById("btStep4")?.checked) steps.push(4);

        btnStart.style.display = "none";
        btnStop.style.display = "inline-block";
        if (progressDiv) progressDiv.style.display = "block";
        document.getElementById("btnExportReport").disabled = true;

        try {
            await Utils.apiPost("/api/backtest/run", {
                start_date: startDate,
                end_date: endDate,
                capital, trade_ratio: ratio, steps,
            });

            const poll = setInterval(async () => {
                try {
                    const status = await Utils.apiGet("/api/backtest/status");
                    if (status.status === "done") {
                        clearInterval(poll);
                        btnStart.style.display = "inline-block";
                        btnStop.style.display = "none";
                        if (progressDiv) progressDiv.style.display = "none";
                        document.getElementById("btnExportReport").disabled = false;

                        if (status.result && status.result.error) {
                            Utils.showToast("回測錯誤: " + status.result.error, "error");
                        } else {
                            renderResults(status.result);
                            Utils.showToast("回測完成", "success");
                        }
                    } else if (status.status === "idle") {
                        clearInterval(poll);
                        btnStart.style.display = "inline-block";
                        btnStop.style.display = "none";
                        if (progressDiv) progressDiv.style.display = "none";
                    }
                } catch (e) {
                    clearInterval(poll);
                    btnStart.style.display = "inline-block";
                    btnStop.style.display = "none";
                    if (progressDiv) progressDiv.style.display = "none";
                }
            }, 1500);

        } catch (e) {
            Utils.showToast("回測啟動失敗", "error");
            btnStart.style.display = "inline-block";
            btnStop.style.display = "none";
            if (progressDiv) progressDiv.style.display = "none";
        }
    });

    btnStop?.addEventListener("click", () => {
        btnStart.style.display = "inline-block";
        btnStop.style.display = "none";
        if (progressDiv) progressDiv.style.display = "none";
        Utils.showToast("回測已停止", "warning");
    });

    document.getElementById("btnExportReport")?.addEventListener("click", () => {
        Utils.showToast("匯出報告功能尚未實作", "warning");
    });
}

function renderResults(result) {
    if (!result) return;

    document.getElementById("btTotalReturn").textContent = (result.total_return || 0) + "%";
    document.getElementById("btTotalReturn").className = "info-card-value " +
        ((result.total_return || 0) >= 0 ? "text-danger" : "text-success");
    document.getElementById("btAnnualReturn").textContent = (result.annual_return || 0) + "%";
    document.getElementById("btWinRate").textContent = (result.win_rate || 0) + "%";
    document.getElementById("btMDD").textContent = "-" + (result.max_drawdown || 0) + "%";
    document.getElementById("btSharpe").textContent = (result.sharpe || 0).toFixed(2);
    document.getElementById("btTradeCount").textContent = result.trade_count || 0;

    if (result.equity_curve && result.equity_curve.length > 0) {
        renderEquityChart(result.equity_curve);
    }

    if (result.trades) {
        renderTrades(result.trades);
    }
}

function renderEquityChart(curve) {
    const container = document.getElementById("equityChart");
    if (!container || !curve) return;

    if (window._equityChart) {
        window._equityChart.remove();
    }

    const chart = LightweightCharts.createChart(container, {
        layout: {
            background: { type: "solid", color: "#1a1d2e" },
            textColor: "#8890a8",
        },
        grid: {
            vertLines: { color: "rgba(42, 45, 62, 0.5)" },
            horzLines: { color: "rgba(42, 45, 62, 0.5)" },
        },
        rightPriceScale: { borderColor: "#2a2d3e" },
        timeScale: { borderColor: "#2a2d3e", timeVisible: true },
        width: container.clientWidth,
        height: 350,
    });

    const lineSeries = chart.addLineSeries({
        color: "#3b82f6",
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: true,
    });

    const data = curve.map((p) => ({
        time: p.date,
        value: p.equity,
    }));

    lineSeries.setData(data);
    window._equityChart = chart;
}

function renderTrades(trades) {
    const tbody = document.getElementById("btTradeTableBody");
    if (!tbody) return;
    if (!trades || trades.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">無交易紀錄</td></tr>';
        return;
    }
    tbody.innerHTML = trades.reverse().map((t) => {
        const dirBadge = t.direction === "buy"
            ? '<span class="badge bg-danger">買進</span>'
            : '<span class="badge bg-success">賣出</span>';
        const pnlClass = (t.pnl || 0) >= 0 ? "text-danger" : "text-success";
        return `
            <tr>
                <td>${t.date || "--"}</td>
                <td><a href="/stock/${t.stock_id}">${t.stock_id}</a></td>
                <td>${dirBadge}</td>
                <td>${(t.price || 0).toFixed(2)}</td>
                <td>${t.shares || 0}</td>
                <td class="small text-muted">${t.reason || "--"}</td>
                <td>${t.holding_days || "--"}</td>
                <td class="${pnlClass}">${t.pnl != null ? Utils.formatPnL(t.pnl) : "--"}</td>
            </tr>
        `;
    }).join("");
}

"use strict";

document.addEventListener("DOMContentLoaded", () => {
    bindButtons();
});

function bindButtons() {
    const btnAll = document.getElementById("btnRunAll");
    const btn1 = document.getElementById("btnRunStep1");
    const btn2 = document.getElementById("btnRunStep2");
    const btn3 = document.getElementById("btnRunStep3");

    btnAll?.addEventListener("click", async () => {
        Utils.updateStatusDot("warning");
        Utils.showToast("執行全部篩選中...", "warning");
        try {
            const r = await Utils.apiPost("/api/run_screening", { step: 0 });
            renderResults(r);
            Utils.showToast("篩選完成", "success");
            Utils.updateStatusDot("ok");
        } catch (e) {
            Utils.showToast("篩選失敗", "error");
            Utils.updateStatusDot("error");
        }
    });

    btn1?.addEventListener("click", async () => {
        Utils.showToast("執行步驟一中...", "warning");
        try {
            const r = await Utils.apiPost("/api/run_screening", { step: 1 });
            renderResults(r);
            Utils.showToast("步驟一完成", "success");
        } catch (e) {
            Utils.showToast("步驟一失敗", "error");
        }
    });

    btn2?.addEventListener("click", async () => {
        Utils.showToast("執行步驟二中...", "warning");
        try {
            const r = await Utils.apiPost("/api/run_screening", { step: 2 });
            renderResults(r);
            Utils.showToast("步驟二完成", "success");
        } catch (e) {
            Utils.showToast("步驟二失敗", "error");
        }
    });

    btn3?.addEventListener("click", async () => {
        Utils.showToast("執行步驟三中...", "warning");
        try {
            const r = await Utils.apiPost("/api/run_screening", { step: 3 });
            renderResults(r);
            Utils.showToast("步驟三完成", "success");
        } catch (e) {
            Utils.showToast("步驟三失敗", "error");
        }
    });

    document.getElementById("btnExport")?.addEventListener("click", () => {
        Utils.showToast("匯出功能尚未實作 (後端待補)", "warning");
    });
}

function renderResults(r) {
    if (r.step1) {
        renderStep1(r.step1);
        document.getElementById("step1PassCount").textContent = r.step1.count || 0;
        const volStatus = document.getElementById("step1VolumeStatus");
        const ms = r.step1.market_status;
        if (volStatus) {
            volStatus.innerHTML = ms?.is_contraction
                ? '<span class="status-pill status-active">量縮 - 啟動選股</span>'
                : '<span class="status-pill status-pending">放量 - 未啟動</span>';
        }
    }
    if (r.step2) {
        renderStep2(r.step2);
        document.getElementById("step2PassCount").textContent = r.step2.count || 0;
    }
    if (r.step3) {
        renderStep3(r.step3);
        document.getElementById("step3PassCount").textContent = r.step3.count || 0;
    }
}

function renderStep1(data) {
    const tbody = document.getElementById("step1TableBody");
    if (!data.passed || data.passed.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">無符合標的</td></tr>';
        return;
    }
    tbody.innerHTML = data.passed.map((s) => `
        <tr>
            <td><a href="/stock/${s.stock_id}">${s.stock_id}</a></td>
            <td>${s.stock_name || s.stock_id}</td>
            <td>${s.close || "--"}</td>
            <td>${s.capital || "--"}</td>
            <td>${(s.volume || 0).toLocaleString()}</td>
            <td><span class="status-pill status-active">通過</span></td>
        </tr>
    `).join("");
}

function renderStep2(data) {
    const tbody = document.getElementById("step2TableBody");
    if (!data.passed || data.passed.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">無符合標的</td></tr>';
    } else {
        tbody.innerHTML = data.passed.map((s) => `
            <tr>
                <td><a href="/stock/${s.stock_id}">${s.stock_id}</a></td>
                <td>${s.stock_name || s.stock_id}</td>
                <td>${s.key_candle_date || "--"}</td>
                <td>${(s.key_candle_volume || 0).toLocaleString()}</td>
                <td>${s.support_price || "--"}</td>
                <td>${s.close || "--"}</td>
                <td><span class="status-pill status-active">通過</span></td>
            </tr>
        `).join("");
    }

    const excludedTbody = document.getElementById("step2ExcludedBody");
    if (excludedTbody && data.excluded && data.excluded.length > 0) {
        excludedTbody.innerHTML = data.excluded.map((s) => `
            <tr>
                <td>${s.stock_id}</td>
                <td>${s.stock_name || s.stock_id}</td>
                <td class="text-danger">${s.reason || "--"}</td>
            </tr>
        `).join("");
    }
}

function renderStep3(data) {
    const tbody = document.getElementById("step3TableBody");
    if (!data.passed || data.passed.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">無符合標的</td></tr>';
    } else {
        tbody.innerHTML = data.passed.map((s) => `
            <tr>
                <td><a href="/stock/${s.stock_id}">${s.stock_id}</a></td>
                <td>${s.stock_name || s.stock_id}</td>
                <td>${s.broker_name || s.broker_id || "--"}</td>
                <td>${s.consecutive_days || 0} 天</td>
                <td>${(s.total_net_buy || 0).toLocaleString()}</td>
                <td>${s.daytrade_warning ? '<span class="status-pill status-warning">警示</span>' : '<span class="status-pill status-active">無</span>'}</td>
                <td>${s.dip_signal ? '<span class="status-pill status-active">攤平訊號</span>' : '<span class="status-pill status-pending">--</span>'}</td>
            </tr>
        `).join("");
    }

    const excludedTbody = document.getElementById("step3ExcludedBody");
    if (excludedTbody && data.excluded && data.excluded.length > 0) {
        excludedTbody.innerHTML = data.excluded.map((s) => `
            <tr>
                <td>${s.stock_id}</td>
                <td>${s.stock_name || s.stock_id}</td>
                <td>${s.broker_name || s.broker_id || "--"}</td>
                <td class="text-danger">${s.reason || "--"}</td>
            </tr>
        `).join("");
    }
}

"use strict";

const Dashboard = {
    initCheckInterval: null,

    async init() {
        Utils.updateStatusDot("ok");
        this.updateTime();
        setInterval(() => this.updateTime(), 30000);
        this.bindButtons();
        this.checkInitStatus();
        this.loadData();
    },

    async checkInitStatus() {
        try {
            const r = await Utils.apiGet("/api/status");
            if (r.init_progress && r.init_progress.status === "running") {
                this.showInitProgress(r.init_progress);
                this.pollInitProgress();
            }
        } catch (e) { /* ignore */ }
    },

    showInitProgress(p) {
        const panel = document.getElementById("initProgressPanel");
        if (panel) panel.style.display = "block";
        const bar = document.getElementById("initProgressBar");
        const text = document.getElementById("initProgressText");
        if (bar && p.total > 0) {
            bar.style.width = (p.current / p.total * 100) + "%";
        }
        if (text) text.textContent = p.message || "載入中...";
    },

    pollInitProgress() {
        if (this.initCheckInterval) clearInterval(this.initCheckInterval);
        this.initCheckInterval = setInterval(async () => {
            try {
                const r = await Utils.apiGet("/api/status");
                if (!r.init_progress || r.init_progress.status !== "running") {
                    clearInterval(this.initCheckInterval);
                    this.initCheckInterval = null;
                    document.getElementById("initProgressPanel").style.display = "none";
                    Utils.updateStatusDot("ok");
                    Utils.showToast("資料初始化完成", "success");
                    this.loadData();
                } else {
                    this.showInitProgress(r.init_progress);
                }
            } catch (e) {
                clearInterval(this.initCheckInterval);
                this.initCheckInterval = null;
            }
        }, 2000);
    },

    async loadData() {
        try {
            const data = await Utils.apiGet("/api/dashboard");
            this.renderMarket(data.market);
            this.renderStepCounts(data);
            this.renderSignals(data.signals || []);
            Utils.updateStatusDot("ok");
        } catch (e) {
            Utils.updateStatusDot("error");
        }
    },

    renderMarket(m) {
        if (!m) return;
        document.getElementById("taiIndex").textContent = (m.index_close || 0).toLocaleString();
        document.getElementById("taiVolume").textContent =
            m.today_volume ? Utils.formatMoney(m.today_volume) : "--";
        document.getElementById("taiVolMA").textContent =
            m.volume_ma ? Utils.formatMoney(m.volume_ma) : "--";

        const statusEl = document.getElementById("volumeContraction");
        if (m.status === "insufficient_data") {
            statusEl.innerHTML = '<span class="status-pill status-pending">無資料</span>';
        } else if (m.is_contraction) {
            statusEl.innerHTML = '<span class="status-pill status-active">量縮</span>';
        } else {
            statusEl.innerHTML = '<span class="status-pill status-pending">放量</span>';
        }
    },

    renderStepCounts(data) {
        document.getElementById("step1Count").textContent = (data.step1_count || 0) + " 檔";
        document.getElementById("step1Badge").textContent = data.step1_count || 0;
        document.getElementById("step2Count").textContent = (data.step2_count || 0) + " 檔";
        document.getElementById("step2Badge").textContent = data.step2_count || 0;
        document.getElementById("step3Count").textContent = (data.step3_count || 0) + " 檔";
        document.getElementById("step3Badge").textContent = data.step3_count || 0;
    },

    renderSignals(signals) {
        const tbody = document.getElementById("signalTableBody");
        if (!tbody) return;
        if (!signals || signals.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">尚無交易訊號</td></tr>';
            return;
        }
        tbody.innerHTML = signals.map((s) => `
            <tr>
                <td>${s.date || "--"}</td>
                <td><a href="/stock/${s.stock_id}">${s.stock_id} ${s.stock_name || ""}</a></td>
                <td><span class="badge ${s.direction === 'buy' ? 'bg-danger' : 'bg-success'}">${s.direction === 'buy' ? '買進' : '賣出'}</span></td>
                <td>${s.price || "--"}</td>
                <td class="text-muted small">${s.reason || "--"}</td>
            </tr>
        `).join("");
    },

    updateTime() {
        const el = document.getElementById("lastUpdate");
        if (!el) return;
        const n = new Date();
        el.textContent = `${n.getHours().toString().padStart(2, "0")}:${n.getMinutes().toString().padStart(2, "0")}:${n.getSeconds().toString().padStart(2, "0")}`;
    },

    bindButtons() {
        const btnInit = document.getElementById("btnInitData");
        btnInit?.addEventListener("click", async () => {
            Utils.updateStatusDot("warning");
            Utils.showToast("初始化資料中...", "warning");
            try {
                await Utils.apiPost("/api/init", { count: 50 });
                this.pollInitProgress();
                document.getElementById("initProgressPanel").style.display = "block";
            } catch (e) {
                Utils.showToast("初始化失敗", "error");
                Utils.updateStatusDot("error");
            }
        });

        const btnRun = document.getElementById("btnRunScreening");
        btnRun?.addEventListener("click", async () => {
            Utils.updateStatusDot("warning");
            try {
                const r = await Utils.apiPost("/api/run_screening", { step: 0 });
                await this.loadData();
                Utils.showToast("選股完成", "success");
            } catch (e) {
                Utils.showToast("選股執行失敗", "error");
                Utils.updateStatusDot("error");
            }
        });

        const btnUpdate = document.getElementById("btnUpdateData");
        btnUpdate?.addEventListener("click", async () => {
            Utils.updateStatusDot("warning");
            try {
                await Utils.apiPost("/api/update_data", { type: "market" });
                await this.loadData();
                Utils.showToast("資料更新完成", "success");
            } catch (e) {
                Utils.showToast("資料更新失敗", "error");
                Utils.updateStatusDot("error");
            }
        });

        const btnExport = document.getElementById("btnExportCSV");
        btnExport?.addEventListener("click", () => {
            Utils.showToast("匯出功能尚未實作", "warning");
        });
    },
};

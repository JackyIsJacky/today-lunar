"use strict";

const KlineChart = {
    chart: null,
    candleSeries: null,
    volumeSeries: null,
    maSeries: { ma5: null, ma20: null, ma60: null, ma120: null },
    stockId: null,
    data: [],
    klineData: [],

    async init(stockId) {
        this.stockId = stockId;
        this.createChart();
        this.bindMAToggles();
        this.bindResize();
        await this.loadRealData();
    },

    async loadRealData() {
        try {
            const resp = await Utils.apiGet("/api/stock/" + this.stockId);
            this.klineData = resp.kline || [];
            this.updateStockInfo(resp);
            if (this.klineData.length > 0) {
                this.renderKline(this.klineData);
                this.computeMA();
            }
            this.renderBrokers(resp.brokers || []);
        } catch (e) {
            this.renderMockData();
        }
    },

    updateStockInfo(resp) {
        const name = resp.stock_name || this.stockId;
        document.getElementById("stockName").textContent = name;
        const info = resp.info || {};
        if (info.capital) {
            document.getElementById("stockCapital").textContent = (info.capital / 1e8).toFixed(1) + " 億";
        }
    },

    createChart() {
        const container = document.getElementById("klineChart");
        if (!container) return;

        this.chart = LightweightCharts.createChart(container, {
            layout: {
                background: { type: "solid", color: "#1a1d2e" },
                textColor: "#8890a8",
            },
            grid: {
                vertLines: { color: "rgba(42, 45, 62, 0.5)" },
                horzLines: { color: "rgba(42, 45, 62, 0.5)" },
            },
            crosshair: { mode: 0 },
            rightPriceScale: { borderColor: "#2a2d3e" },
            timeScale: { borderColor: "#2a2d3e", timeVisible: true },
            width: container.clientWidth,
            height: 500,
        });

        this.candleSeries = this.chart.addCandlestickSeries({
            upColor: "#ef4444",
            downColor: "#10b981",
            borderUpColor: "#ef4444",
            borderDownColor: "#10b981",
            wickUpColor: "#ef4444",
            wickDownColor: "#10b981",
        });

        this.volumeSeries = this.chart.addHistogramSeries({
            priceFormat: { type: "volume" },
            priceScaleId: "",
        });
        this.volumeSeries.priceScale().applyOptions({
            scaleMargins: { top: 0.8, bottom: 0 },
        });
    },

    renderKline(data) {
        const candles = data.map((d) => ({
            time: d.time || d.date,
            open: Number(d.open),
            high: Number(d.high),
            low: Number(d.low),
            close: Number(d.close),
        }));

        const volumes = data.map((d) => ({
            time: d.time || d.date,
            value: Number(d.volume || 0),
            color: d.close >= d.open
                ? "rgba(239, 68, 68, 0.5)"
                : "rgba(16, 185, 129, 0.5)",
        }));

        this.data = candles;
        this.candleSeries.setData(candles);
        this.volumeSeries.setData(volumes);

        const lastClose = candles[candles.length - 1]?.close || 0;
        const prevClose = candles.length > 1 ? candles[candles.length - 2]?.close : lastClose;
        const change = prevClose ? ((lastClose - prevClose) / prevClose * 100) : 0;
        document.getElementById("stockPrice").textContent = lastClose.toFixed(2);
        document.getElementById("stockChange").innerHTML =
            `<span style="color:${change >= 0 ? '#ef4444' : '#10b981'}">${change >= 0 ? '+' : ''}${change.toFixed(2)}%</span>`;
        document.getElementById("stockVolume").textContent =
            (data[data.length - 1]?.volume || 0).toLocaleString();
    },

    computeMA() {
        if (!this.data || this.data.length === 0) return;
        this.clearMA();

        function calcSMA(data, period) {
            const result = [];
            for (let i = period - 1; i < data.length; i++) {
                let sum = 0;
                for (let j = 0; j < period; j++) sum += data[i - j].close;
                result.push({ time: data[i].time, value: +(sum / period).toFixed(2) });
            }
            return result;
        }

        const colors = { ma5: "#3b82f6", ma20: "#f59e0b", ma60: "#a855f7", ma120: "#ec4899" };

        const createLine = (period, key) => {
            const data = calcSMA(this.data, period);
            const line = this.chart.addLineSeries({
                color: colors[key], lineWidth: 1, priceLineVisible: false,
                lastValueVisible: false, crosshairMarkerVisible: false,
            });
            line.setData(data);
            return line;
        };

        this.maSeries.ma5 = createLine(5, "ma5");
        this.maSeries.ma20 = createLine(20, "ma20");
        this.maSeries.ma60 = createLine(60, "ma60");
        this.maSeries.ma120 = createLine(120, "ma120");

        this.updateMAVisibility();
    },

    clearMA() {
        const keys = ["ma5", "ma20", "ma60", "ma120"];
        keys.forEach((k) => {
            if (this.maSeries[k]) {
                this.chart.removeSeries(this.maSeries[k]);
                this.maSeries[k] = null;
            }
        });
    },

    bindMAToggles() {
        ["ma5", "ma20", "ma60", "ma120"].forEach((ma) => {
            const cb = document.getElementById(ma + "Check");
            if (cb) {
                cb.addEventListener("change", () => this.updateMAVisibility());
            }
        });
    },

    updateMAVisibility() {
        const keys = ["ma5", "ma20", "ma60", "ma120"];
        keys.forEach((k) => {
            const line = this.maSeries[k];
            if (!line) return;
            const cb = document.getElementById(k + "Check");
            line.applyOptions({ visible: cb ? cb.checked : false });
        });
    },

    renderBrokers(brokers) {
        const tbody = document.getElementById("brokerTableBody");
        if (!tbody) return;
        if (!brokers || brokers.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" class="text-center text-muted">尚無資料</td></tr>';
            return;
        }
        tbody.innerHTML = brokers.slice(0, 10).map((b) => `
            <tr>
                <td>${b.broker_id} ${b.broker_name || ""}</td>
                <td>${(b.total_net || 0).toLocaleString()}</td>
                <td>${b.days_count || 0} 天</td>
            </tr>
        `).join("");
    },

    bindResize() {
        window.addEventListener("resize", () => {
            if (this.chart) {
                const container = document.getElementById("klineChart");
                if (container) this.chart.applyOptions({ width: container.clientWidth });
            }
        });
    },

    renderMockData() {
        const now = new Date();
        const candles = [];
        const volumes = [];
        let price = 35;

        for (let i = 119; i >= 0; i--) {
            const d = new Date(now);
            d.setDate(d.getDate() - i);
            if (d.getDay() === 0 || d.getDay() === 6) continue;

            const open = price + (Math.random() - 0.55) * 2;
            const close = open + (Math.random() - 0.5) * 3;
            const high = Math.max(open, close) + Math.random() * 1.5;
            const low = Math.min(open, close) - Math.random() * 1.5;
            const vol = Math.floor(500 + Math.random() * 5000);
            const time = d.toISOString().slice(0, 10);

            candles.push({ time, open: +open.toFixed(2), high: +high.toFixed(2), low: +low.toFixed(2), close: +close.toFixed(2) });
            volumes.push({ time, value: vol, color: close >= open ? "rgba(239, 68, 68, 0.5)" : "rgba(16, 185, 129, 0.5)" });
            price = close;
        }

        this.data = candles;
        this.candleSeries.setData(candles);
        this.volumeSeries.setData(volumes);
        this.computeMA();
    },
};

window.addEventListener("load", () => {
    const stockId = document.getElementById("stockSearchInput")?.value?.trim();
    if (stockId && stockId !== "0") KlineChart.init(stockId);
});

"use strict";

document.addEventListener("DOMContentLoaded", () => {
    const defaultList = [
        { code: "9200", name: "凱基台北" },
        { code: "9600", name: "富邦嘉義" },
        { code: "9868", name: "永豐金" },
    ];

    renderBlacklist(defaultList);

    document.getElementById("btnAddBlacklist")?.addEventListener("click", () => {
        const code = document.getElementById("blacklistCode").value.trim();
        const name = document.getElementById("blacklistName").value.trim();
        if (!code || !name) {
            Utils.showToast("請輸入券商代碼與名稱", "warning");
            return;
        }
        defaultList.push({ code, name });
        renderBlacklist(defaultList);
        document.getElementById("blacklistCode").value = "";
        document.getElementById("blacklistName").value = "";
        document.getElementById("blacklistCount").textContent = defaultList.length;
    });

    document.getElementById("btnTestApi")?.addEventListener("click", () => {
        const badge = document.getElementById("apiStatusBadge");
        Utils.updateStatusDot("warning");
        if (badge) { badge.className = "badge bg-warning"; badge.textContent = "測試中..."; }
        fetch("/api/status")
            .then((r) => r.json())
            .then(() => {
                if (badge) { badge.className = "badge bg-success"; badge.textContent = "連線成功"; }
                Utils.updateStatusDot("ok");
            })
            .catch(() => {
                if (badge) { badge.className = "badge bg-danger"; badge.textContent = "連線失敗"; }
                Utils.updateStatusDot("error");
            });
    });

    document.getElementById("btnSaveSettings")?.addEventListener("click", () => {
        Utils.showToast("設定已儲存 (後端待補)", "success");
    });

    document.getElementById("btnResetDefaults")?.addEventListener("click", () => {
        if (!confirm("確定要重設所有設定為預設值嗎？")) return;
        document.getElementById("settingsCapital").value = "1000000";
        document.getElementById("settingsTradeRatio").value = "0.2";
        document.getElementById("settingsCommission").value = "0.1425";
        document.getElementById("settingsTax").value = "0.3";
        document.getElementById("settingsKeyCandleLookback").value = "20";
        document.getElementById("settingsVolumeMA").value = "5";
        document.getElementById("settingsChipDays").value = "5";
        document.getElementById("settingsChipDumpRatio").value = "30";
        document.getElementById("settingsCapitalThreshold").value = "10";
        document.getElementById("settingsPriceThreshold").value = "50";
        Utils.showToast("已重設為預設值", "success");
    });

    function renderBlacklist(list) {
        const tbody = document.getElementById("blacklistTableBody");
        if (!tbody) return;
        document.getElementById("blacklistCount").textContent = list.length;
        tbody.innerHTML = list.map((item, idx) => `
            <tr>
                <td>${item.code}</td>
                <td>${item.name}</td>
                <td>
                    <button class="btn btn-sm btn-outline-danger remove-broker" data-idx="${idx}">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            </tr>
        `).join("");

        tbody.querySelectorAll(".remove-broker").forEach((btn) => {
            btn.addEventListener("click", () => {
                const idx = parseInt(btn.dataset.idx);
                defaultList.splice(idx, 1);
                renderBlacklist(defaultList);
            });
        });
    }
});

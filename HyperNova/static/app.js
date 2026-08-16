// HyperNova 1000:1 Live Trading Dashboard JavaScript
let socket;
let chart;
let chartData = {
    labels: [],
    equity: [],
    balance: []
};

// Initialize Dashboard
document.addEventListener('DOMContentLoaded', () => {
    initWebSocket();
    initChart();
    loadInitialData();

    // Auto refresh every 2 seconds for high-frequency live tracking
    setInterval(refreshData, 2000);
});

// WebSocket Connection
function initWebSocket() {
    socket = io();

    socket.on('connect', () => {
        console.log('Connected to server');
        addLog('🟢 Web Dashboard sunucuya bağlandı (1000:1 Aktif)', 'log-success');
    });

    socket.on('disconnect', () => {
        console.log('Disconnected from server');
        addLog('🔴 Sunucu bağlantısı kesildi', 'log-error');
    });

    socket.on('price_update', (data) => {
        updatePrice(data.symbol, data.price);
    });

    socket.on('status_update', (data) => {
        updateStatus(data.status);
    });

    socket.on('position_change', (data) => {
        refreshPositions();
        refreshStatus();
    });

    socket.on('log_message', (data) => {
        addLog(data.message);
    });
}

// Initialize Chart
function initChart() {
    const ctx = document.getElementById('pnlChart').getContext('2d');

    chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: chartData.labels,
            datasets: [
                {
                    label: 'Varlık (Equity)',
                    data: chartData.equity,
                    borderColor: '#4b55ff',
                    backgroundColor: 'rgba(75, 85, 255, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.3,
                    pointRadius: 0
                },
                {
                    label: 'Bakiye (Balance)',
                    data: chartData.balance,
                    borderColor: 'rgba(230, 232, 240, 0.4)',
                    borderWidth: 1,
                    borderDash: [5, 5],
                    fill: false,
                    pointRadius: 0
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            animation: false,
            plugins: {
                legend: {
                    display: true,
                    labels: { color: '#e6e8f0', font: { size: 12 } }
                },
                tooltip: {
                    backgroundColor: 'rgba(10, 14, 39, 0.9)',
                    titleColor: '#e6e8f0',
                    bodyColor: '#e6e8f0',
                    borderColor: '#4b55ff',
                    borderWidth: 1
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(75, 85, 255, 0.08)' },
                    ticks: { color: '#a0a4b8', maxTicksLimit: 8 }
                },
                y: {
                    grid: { color: 'rgba(75, 85, 255, 0.08)' },
                    ticks: {
                        color: '#a0a4b8',
                        callback: (v) => '$' + v.toLocaleString()
                    }
                }
            }
        }
    });
}

// Initial Data Load
async function loadInitialData() {
    await Promise.all([
        refreshStatus(),
        refreshPositions(),
        refreshHistory()
    ]);
}

// Refresh Data Loop
async function refreshData() {
    await Promise.all([
        refreshStatus(),
        refreshPositions(),
        refreshHistory()
    ]);
}

// API Calls
async function refreshStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();

        updatePrice(data.symbol, data.price);
        updateStatus(data.status);
        updateBalanceStats(data);
        updateMicrostructureUI(data.microstructure);

        // Update Chart
        const now = new Date().toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        chartData.labels.push(now);
        chartData.equity.push(data.equity);
        chartData.balance.push(data.balance);

        if (chartData.labels.length > 25) {
            chartData.labels.shift();
            chartData.equity.shift();
            chartData.balance.shift();
        }

        chart.update('none');
    } catch (error) {
        console.error('Status fetch error:', error);
    }
}

function updateMicrostructureUI(micro) {
    if (!micro) return;
    ['sol', 'hype', 'btc'].forEach(sym => {
        const key = sym.toUpperCase();
        const el = document.getElementById(`l2-${sym}`);
        if (el && micro[key]) {
            const d = micro[key];
            const oir = d.oir_pct || 0;
            const isBuy = oir >= 0;
            const color = isBuy ? '#10b981' : '#ef4444';
            const sign = isBuy ? '+' : '';
            const tag = isBuy ? 'ALICI BASKISI' : 'SATICISI BASKISI';
            el.innerHTML = `<strong>${key}:</strong> <span style="color:${color}; font-weight:800;">${sign}${oir.toFixed(1)}% ${tag}</span> <span style="color:#a0a4b8; font-size:11px;">(B:${d.bid_vol.toFixed(0)} | A:${d.ask_vol.toFixed(0)})</span>`;
            el.style.borderColor = isBuy ? 'rgba(16,185,129,0.35)' : 'rgba(239,68,68,0.35)';
        }
    });
}

// Render Rich Detailed Positions
async function refreshPositions() {
    try {
        const response = await fetch('/api/positions');
        const positions = await response.json();

        const container = document.getElementById('positions-list');
        const countBadge = document.getElementById('positions-count-badge');

        if (countBadge) {
            countBadge.textContent = `${positions.length} Aktif`;
        }

        if (positions.length === 0) {
            container.innerHTML = '<div class="empty-state">Henüz açık pozisyon yok (Sinyaller taranıyor...)</div>';
            return;
        }

        container.innerHTML = positions.map(pos => {
            const isPos = pos.pnl_usd >= 0;
            const pnlClass = isPos ? 'positive' : 'negative';
            const sideClass = pos.side.toLowerCase();
            const sign = isPos ? '+' : '';

            // Format TP / SL
            const tpStr = pos.tp_price ? `$${pos.tp_price.toFixed(4)}` : 'Dinamik';
            const slStr = pos.sl_price ? `$${pos.sl_price.toFixed(4)}` : 'Dinamik';

            return `
                <div class="position-card ${sideClass}">
                    <!-- Top Badge Row -->
                    <div class="position-top-row">
                        <div class="position-badges">
                            <span class="position-symbol">${pos.symbol}</span>
                            <span class="badge badge-side ${sideClass}">${pos.side}</span>
                            <span class="badge badge-leverage">${pos.leverage}x</span>
                        </div>
                        <span class="badge-time">⏱️ ${pos.duration_str}</span>
                    </div>

                    <!-- PnL Hero -->
                    <div class="position-pnl-hero">
                        <span class="pnl-amount ${pnlClass}">
                            ${sign}$${pos.pnl_usd.toFixed(2)}
                        </span>
                        <span class="roe-badge ${pnlClass}">
                            ${sign}${pos.roe_pct.toFixed(1)}% ROE (${sign}${pos.price_change_pct.toFixed(2)}%)
                        </span>
                    </div>

                    <!-- 6-Metric Details Grid -->
                    <div class="position-grid">
                        <div class="grid-item">
                            <span class="grid-label">🎯 Giriş Fiyatı</span>
                            <span class="grid-val">$${pos.entry_price.toFixed(4)}</span>
                        </div>
                        <div class="grid-item">
                            <span class="grid-label">💵 Anlık Fiyat</span>
                            <span class="grid-val cur">$${pos.current_price.toFixed(4)}</span>
                        </div>
                        <div class="grid-item">
                            <span class="grid-label">📦 Hacim (Notional)</span>
                            <span class="grid-val">$${pos.notional_usd.toFixed(0)} (${pos.size_coin.toFixed(3)})</span>
                        </div>
                        <div class="grid-item">
                            <span class="grid-label">🟢 Kâr Alma (TP)</span>
                            <span class="grid-val tp">${tpStr}</span>
                        </div>
                        <div class="grid-item">
                            <span class="grid-label">🛑 Zarar Kes (SL)</span>
                            <span class="grid-val sl">${slStr}</span>
                        </div>
                        <div class="grid-item">
                            <span class="grid-label">🛡️ Teminat (Margin)</span>
                            <span class="grid-val" style="color:#c084fc;">$${pos.required_margin.toFixed(2)}</span>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

    } catch (error) {
        console.error('Positions fetch error:', error);
    }
}

// Render Trade History
async function refreshHistory() {
    try {
        const response = await fetch('/api/history');
        const history = await response.json();

        const tbody = document.getElementById('history-body');

        if (history.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="empty-state">Henüz kapanan işlem yok</td></tr>';
            return;
        }

        tbody.innerHTML = history.map(trade => {
            const isPos = trade.pnl >= 0;
            const pnlClass = isPos ? 'pnl-positive' : 'pnl-negative';
            const sign = isPos ? '+' : '';
            const entryPx = trade.entry_price ? `$${trade.entry_price.toFixed(4)}` : '-';
            const exitPx = trade.exit_price ? `$${trade.exit_price.toFixed(4)}` : '-';

            const time = new Date(trade.time).toLocaleTimeString('tr-TR', {
                hour: '2-digit', minute: '2-digit', second: '2-digit'
            });

            return `
                <tr>
                    <td>${time}</td>
                    <td><span class="badge ${trade.side === 'LONG' ? 'badge-side long' : 'badge-side short'}">${trade.action || 'CLOSE'}</span></td>
                    <td><strong>${trade.symbol}</strong></td>
                    <td>${entryPx}</td>
                    <td>${exitPx}</td>
                    <td class="${pnlClass}">${sign}$${trade.pnl.toFixed(2)}</td>
                </tr>
            `;
        }).join('');

    } catch (error) {
        console.error('History fetch error:', error);
    }
}

// UI Updaters
function updatePrice(symbol, price) {
    const symbolEl = document.getElementById('symbol');
    const priceEl = document.getElementById('price');
    if (symbolEl) symbolEl.textContent = symbol;
    if (priceEl) priceEl.textContent = '$' + price.toFixed(4);
}

function updateStatus(status) {
    const statusEl = document.getElementById('status');
    if (statusEl) statusEl.textContent = status;
}

function updateBalanceStats(data) {
    const balanceEl = document.getElementById('balance');
    const equityEl = document.getElementById('equity');
    const equityChangeEl = document.getElementById('equity-change');
    const unrealizedEl = document.getElementById('unrealized-pnl');
    const unrealizedChangeEl = document.getElementById('unrealized-change');
    const usedMarginEl = document.getElementById('used-margin');
    const freeMarginEl = document.getElementById('free-margin');

    animateValue(balanceEl, data.balance, '$');
    animateValue(equityEl, data.equity, '$');
    animateValue(unrealizedEl, data.unrealized_pnl, '$', true);

    if (usedMarginEl) usedMarginEl.textContent = `$${data.used_margin.toFixed(2)}`;
    if (freeMarginEl) freeMarginEl.textContent = `Serbest: $${data.free_margin.toFixed(2)}`;

    const startBalance = 10000;
    const equityChange = ((data.equity - startBalance) / startBalance) * 100;
    if (equityChangeEl) {
        equityChangeEl.textContent = `${equityChange >= 0 ? '+' : ''}${equityChange.toFixed(2)}%`;
        equityChangeEl.style.color = equityChange >= 0 ? '#10b981' : '#ef4444';
    }

    if (unrealizedChangeEl) {
        unrealizedChangeEl.textContent = `${data.open_positions} Açık Pozisyon`;
    }

    if (equityEl) equityEl.style.color = data.equity >= startBalance ? '#10b981' : '#ef4444';
    if (unrealizedEl) unrealizedEl.style.color = data.unrealized_pnl >= 0 ? '#10b981' : '#ef4444';
}

function animateValue(element, targetValue, prefix = '', showSign = false) {
    if (!element) return;
    const formatted = targetValue.toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
    const sign = showSign && targetValue >= 0 ? '+' : '';
    element.textContent = `${sign}${prefix}${formatted}`;
}

function addLog(message, className = '') {
    const logContent = document.getElementById('log-content');
    if (!logContent) return;

    const logEntry = document.createElement('div');
    logEntry.className = `log-entry ${className}`;
    logEntry.textContent = message;
    logContent.appendChild(logEntry);

    while (logContent.children.length > 35) {
        logContent.removeChild(logContent.firstChild);
    }
    logContent.scrollTop = logContent.scrollHeight;
}

// Upload/Sync Telemetry to Central Training Hub
async function syncTelemetryToHub() {
    const btn = document.getElementById('btn-sync-telemetry');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span>⏳</span> Yükleniyor...';
    }

    try {
        const expRes = await fetch('/api/telemetry/export');
        const payload = await expRes.json();

        let hubUrl = localStorage.getItem('hypernova_hub_url') || window.location.origin;
        if (hubUrl.endsWith('/')) hubUrl = hubUrl.slice(0, -1);

        const uploadRes = await fetch(`${hubUrl}/api/telemetry/upload`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const res = await uploadRes.json();

        if (res.status === 'success' || res.status === 'skipped') {
            if (btn) {
                btn.innerHTML = '<span>✅</span> Merkeze İletildi!';
                btn.style.borderColor = '#10b981';
            }
            addLog(`📤 Telemetri Paketi Merkeze İletildi (${payload.trades_count || 0} işlem) -> ${hubUrl}`);
            setTimeout(() => {
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = '<span>📤</span> Veriyi Merkeze Yükle';
                }
            }, 3000);
        } else {
            throw new Error(res.message || 'Yükleme başarısız');
        }
    } catch (e) {
        if (btn) {
            btn.innerHTML = '<span>❌</span> Hata!';
            btn.style.borderColor = '#ef4444';
            setTimeout(() => {
                btn.disabled = false;
                btn.innerHTML = '<span>📤</span> Veriyi Merkeze Yükle';
            }, 3000);
        }
        addLog(`❌ Telemetri Yükleme Hatası: ${e.message}`);
    }
}

function configureHubServer() {
    const current = localStorage.getItem('hypernova_hub_url') || window.location.origin;
    const newUrl = prompt("💻 Merkezi Bilgisayar Eğitim İstasyonu Adresini Girin (Örn: http://192.168.0.17:5000):", current);
    if (newUrl && newUrl.trim() !== '') {
        localStorage.setItem('hypernova_hub_url', newUrl.trim());
        alert(`✅ Eğitim İstasyonu adresi kaydedildi: ${newUrl.trim()}`);
    }
}

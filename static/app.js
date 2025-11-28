// State
let currentSymbol = 'NVDA';
let currentType = 'line';
let currentPeriod = '5d';
let rawData = [];
let recsData = {};
let sortState = {};

// Chart setup
let chart = null;
let candleSeries = null;
let lineSeries = null;
const chartContainer = document.getElementById('chart');
const legend = document.getElementById('legend');

function createChart() {
    if (chart) {
        chart.remove();
    }
    
    chart = LightweightCharts.createChart(chartContainer, {
        width: chartContainer.clientWidth,
        height: 500,
        layout: {
            background: { color: '#1a1a1a' },
            textColor: '#d1d4dc',
        },
        grid: {
            vertLines: { color: '#2B2B43' },
            horzLines: { color: '#2B2B43' },
        },
        crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
        },
        timeScale: {
            borderColor: '#485c7b',
            timeVisible: true,
        },
    });
    
    chart.subscribeCrosshairMove(handleCrosshairMove);
    
    // Re-render data if we have it
    if (rawData.length) {
        renderData();
    }
}

function handleCrosshairMove(param) {
    if (!param.time || !param.seriesData.size) {
        legend.innerHTML = '';
        return;
    }
    
    if (currentType === 'candle' && candleSeries) {
        const data = param.seriesData.get(candleSeries);
        if (data) {
            const color = data.close >= data.open ? '#26a69a' : '#ef5350';
            legend.innerHTML = `
                <span style="color: ${color}">
                    O: ${data.open.toFixed(2)} 
                    H: ${data.high.toFixed(2)} 
                    L: ${data.low.toFixed(2)} 
                    C: ${data.close.toFixed(2)}
                </span>
            `;
        }
    } else if (currentType === 'line' && lineSeries) {
        const data = param.seriesData.get(lineSeries);
        if (data) {
            legend.innerHTML = `<span style="color: #2962FF">Price: $${data.value.toFixed(2)}</span>`;
        }
    }
}

// Smooth resize - just recreate chart with existing data
let resizeTimeout;
window.addEventListener('resize', () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
        candleSeries = null;
        lineSeries = null;
        createChart();
    }, 100);
});

// Render chart data
function renderData() {
    if (!rawData.length) return;
    
    // Clear existing series
    if (candleSeries) {
        chart.removeSeries(candleSeries);
        candleSeries = null;
    }
    if (lineSeries) {
        chart.removeSeries(lineSeries);
        lineSeries = null;
    }
    
    if (currentType === 'candle') {
        candleSeries = chart.addSeries(LightweightCharts.CandlestickSeries, {
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderVisible: false,
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350',
        });
        candleSeries.setData(rawData);
    } else {
        lineSeries = chart.addSeries(LightweightCharts.LineSeries, {
            color: '#2962FF',
            lineWidth: 2,
        });
        const lineData = rawData.map(c => ({ time: c.time, value: c.close }));
        lineSeries.setData(lineData);
    }
    chart.timeScale().fitContent();
}

// Chart type toggle
function setChartType(type) {
    currentType = type;
    document.getElementById('btn-candle').classList.toggle('active', type === 'candle');
    document.getElementById('btn-line').classList.toggle('active', type === 'line');
    renderData();
}

// Period toggle
function setPeriod(period) {
    currentPeriod = period;
    document.querySelectorAll('.time-period button').forEach(btn => btn.classList.remove('active'));
    document.getElementById('btn-' + period).classList.add('active');
    loadChart(currentSymbol);
}

// Load chart data
async function loadChart(symbol) {
    currentSymbol = symbol;
    document.querySelector('h1').textContent = symbol;
    
    document.querySelectorAll('.symbols button').forEach(btn => {
        btn.classList.toggle('active', btn.textContent === symbol);
    });
    
    // Show loading overlay
    document.getElementById('chart-loading').style.display = 'flex';
    
    const response = await fetch(`/api/candles/${symbol}?period=${currentPeriod}`);
    rawData = await response.json();
    
    // Hide loading
    document.getElementById('chart-loading').style.display = 'none';
    
    renderData();
    updateStats();
}

// Update stats
function updateStats() {
    if (!rawData.length) return;
    
    const firstPrice = rawData[0].open;
    const lastPrice = rawData[rawData.length - 1].close;
    const change = lastPrice - firstPrice;
    const changePercent = (change / firstPrice) * 100;
    
    const isPositive = change >= 0;
    const color = isPositive ? '#26a69a' : '#ef5350';
    const sign = isPositive ? '+' : '';
    
    const periodLabels = {
        '1d': 'today',
        '5d': 'past 5 days',
        '1m': 'past month',
        '6m': 'past 6 months',
        '1y': 'past year',
        '5y': 'past 5 years'
    };
    
    document.getElementById('stats').innerHTML = `
        <span id="current-price" style="font-size: 24px; font-weight: bold;">$${lastPrice.toFixed(2)}</span>
        <span id="price-change">
            <span style="color: ${color}; margin-left: 10px;">
                ${sign}${change.toFixed(2)} (${sign}${changePercent.toFixed(2)}%)
            </span>
            <span style="color: #888; font-size: 14px;"> ${periodLabels[currentPeriod]}</span>
        </span>
    `;
}

// Recommendations
async function loadRecommendations() {
    document.getElementById('recs-container').innerHTML = '<div class="loading"><div class="spinner"></div>Loading recommendations...</div>';
    
    const response = await fetch('/api/recommendations');
    recsData = await response.json();
    renderRecommendations();
}

function sortCandidates(ticker, column) {
    if (!sortState[ticker]) {
        sortState[ticker] = { column: column, ascending: true };
    } else if (sortState[ticker].column === column) {
        sortState[ticker].ascending = !sortState[ticker].ascending;
    } else {
        sortState[ticker] = { column: column, ascending: true };
    }
    renderRecommendations();
}

function renderRecommendations() {
    let html = '';
    
    for (const [ticker, rec] of Object.entries(recsData)) {
        const gainLossClass = rec.info.gainLoss >= 0 ? 'positive' : 'negative';
        const gainLossSign = rec.info.gainLoss >= 0 ? '+' : '';
        
        // Sort candidates
        let candidates = [...rec.candidates];
        if (sortState[ticker]) {
            const { column, ascending } = sortState[ticker];
            candidates.sort((a, b) => {
                const aVal = a[column];
                const bVal = b[column];
                return ascending ? aVal - bVal : bVal - aVal;
            });
        }
        
        const arrow = (col) => {
            if (sortState[ticker]?.column === col) {
                return sortState[ticker].ascending ? ' ▲' : ' ▼';
            }
            return ' ⠀';
        };
        
        html += `
            <div class="ticker-header">${ticker}</div>
            <div class="position-info">
                ${rec.info.shares} shares @ $${rec.info.avgPrice.toFixed(2)} | 
                Current: $${rec.price.toFixed(2)} | 
                P/L: <span class="${gainLossClass}">${gainLossSign}$${rec.info.gainLoss.toFixed(0)}</span> |
                ${rec.contracts} contracts available
                <button id="rec-btn-${ticker}" class="rec-button" onclick="getRecommendation('${ticker}')">Get Recommendation</button>
            </div>
            <div id="rec-result-${ticker}" class="rec-result"></div>
            <table>
                <thead>
                    <tr>
                        <th onclick="sortCandidates('${ticker}', 'strike')">Strike${arrow('strike')}</th>
                        <th onclick="sortCandidates('${ticker}', 'otmDollar')">OTM $${arrow('otmDollar')}</th>
                        <th onclick="sortCandidates('${ticker}', 'otmPct')">OTM %${arrow('otmPct')}</th>
                        <th onclick="sortCandidates('${ticker}', 'exp')">Expiry${arrow('exp')}</th>
                        <th onclick="sortCandidates('${ticker}', 'dte')">DTE${arrow('dte')}</th>
                        <th onclick="sortCandidates('${ticker}', 'delta')">Delta${arrow('delta')}</th>
                        <th onclick="sortCandidates('${ticker}', 'bid')">Bid${arrow('bid')}</th>
                        <th onclick="sortCandidates('${ticker}', 'weeklyPct')">Weekly %${arrow('weeklyPct')}</th>
                        <th onclick="sortCandidates('${ticker}', 'annualizedPct')">Annual %${arrow('annualizedPct')}</th>
                        <th onclick="sortCandidates('${ticker}', 'totalPremium')">Total Premium${arrow('totalPremium')}</th>
                    </tr>
                </thead>
                <tbody>
        `;
        
        for (const c of candidates) {
            html += `
                <tr>
                    <td>$${c.strike}</td>
                    <td>$${c.otmDollar}</td>
                    <td>${c.otmPct}%</td>
                    <td>${c.exp}</td>
                    <td>${c.dte}d</td>
                    <td>${c.delta}</td>
                    <td>$${c.bid.toFixed(2)}</td>
                    <td class="positive">${c.weeklyPct}%</td>
                    <td class="positive">${c.annualizedPct}%</td>
                    <td>$${c.totalPremium}</td>
                </tr>
            `;
        }
        
        html += '</tbody></table>';
    }
    
    document.getElementById('recs-container').innerHTML = html;
}

async function getRecommendation(ticker) {
    const button = document.getElementById(`rec-btn-${ticker}`);
    const container = document.getElementById(`rec-result-${ticker}`);

    button.disabled = true;
    button.textContent = 'Thinking...';
    container.innerHTML = '<div class="loading"><div class="spinner"></div>Getting recommendation...</div>';

    const response = await fetch(`/api/recommendation/${ticker}`);
    const data = await response.json();

    button.disabled = false;
    button.textContent = 'Get Recommendation';

    container.innerHTML = `<div class="recommendation">${data.recommendation.replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')}</div>`;
}

// Initialize
createChart();
loadChart('NVDA');
loadRecommendations();
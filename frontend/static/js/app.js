// Market status and data source
let currentDataSource = 'loading';

async function checkMarketStatus() {
    try {
        const res = await fetch('/api/market_status');
        const status = await res.json();
        
        const dot = document.getElementById('marketDot');
        const statusText = document.getElementById('marketStatus');
        const banner = document.getElementById('marketBanner');
        const bannerText = document.getElementById('marketBannerText');
        const sourceBadge = document.getElementById('dataSourceBadge');
        const sourceText = document.getElementById('dataSourceText');
        
        if (status.is_open) {
            dot.className = 'status-dot open';
            statusText.innerHTML = 'Market Open';
            banner.className = 'market-banner open';
            bannerText.innerHTML = '🟢 Market is OPEN - Showing live data from PSX';
            sourceBadge.className = 'data-source-badge live';
            sourceText.innerHTML = '📡 Live Data';
            currentDataSource = 'live';
        } else {
            dot.className = 'status-dot';
            statusText.innerHTML = 'Market Closed';
            banner.className = 'market-banner closed';
            bannerText.innerHTML = '🟡 Market is CLOSED - Showing last available data from storage';
            sourceBadge.className = 'data-source-badge stored';
            sourceText.innerHTML = '💾 Stored Data (Market Closed)';
            currentDataSource = 'stored';
        }
    } catch(e) { 
        console.error(e);
    }
}

// Load all stocks
async function loadAllStocks() {
    try {
        const res = await fetch('/api/all_stocks');
        const stocks = await res.json();
        
        const valid = stocks.filter(s => s.price !== 'N/A');
        document.getElementById('totalCompanies').innerHTML = stocks.length;
        document.getElementById('activeCompanies').innerHTML = valid.length;
        
        const allHtml = valid.map(s => `
            <div class="stock-row">
                <span class="symbol">${s.symbol}</span>
                <span>PKR ${s.price}</span>
                <span class="${s.change > 0 ? 'positive' : s.change < 0 ? 'negative' : ''}">
                    ${s.change > 0 ? '+' : ''}${s.change}%
                </span>
                <span class="status-badge ${s.change > 0 ? 'up' : s.change < 0 ? 'down' : 'same'}">
                    ${s.change > 0 ? 'Up' : s.change < 0 ? 'Down' : 'Same'}
                </span>
            </div>
        `).join('');
        
        document.getElementById('allStocksList').innerHTML = allHtml || '<div class="loading">No stocks available</div>';
        
        // Market sentiment
        const totalChange = valid.reduce((sum, s) => sum + s.change, 0);
        const avgChange = totalChange / (valid.length || 1);
        const sentiment = avgChange > 0.5 ? 'Bullish 📈' : avgChange < -0.5 ? 'Bearish 📉' : 'Neutral 📊';
        const sentimentColor = avgChange > 0.5 ? 'var(--success)' : avgChange < -0.5 ? 'var(--danger)' : 'var(--warning)';
        
        document.getElementById('marketSentiment').innerHTML = `
            <div class="sentiment-card">
                <div class="sentiment-value" style="color: ${sentimentColor}">${sentiment}</div>
                <div style="font-size: 0.8rem; margin-top: 10px;">Avg Change: ${avgChange > 0 ? '+' : ''}${avgChange.toFixed(2)}%</div>
                <div style="font-size: 0.7rem; margin-top: 5px; color: var(--text-muted);">Data source: ${currentDataSource === 'live' ? 'Live PSX' : 'Stored'}</div>
            </div>
        `;
        
    } catch(e) { 
        console.error(e);
        document.getElementById('allStocksList').innerHTML = '<div class="loading">Error loading stocks</div>';
    }
}

// Load gainers and losers
async function loadGainersLosers() {
    try {
        const [gainersRes, losersRes] = await Promise.all([
            fetch('/api/gainers'),
            fetch('/api/losers')
        ]);
        
        const gainers = await gainersRes.json();
        const losers = await losersRes.json();
        
        document.getElementById('gainersCount').innerHTML = gainers.length;
        document.getElementById('losersCount').innerHTML = losers.length;
        
        const gainersHtml = gainers.map(s => `
            <div class="stock-row">
                <span class="symbol">${s.symbol}</span>
                <span>PKR ${s.price}</span>
                <span class="positive">+${s.change}%</span>
                <span class="status-badge up">Up</span>
            </div>
        `).join('');
        
        document.getElementById('gainersList').innerHTML = gainersHtml || '<div class="loading">No gainers</div>';
        
    } catch(e) { 
        console.error(e);
        document.getElementById('gainersList').innerHTML = '<div class="loading">Error loading gainers</div>';
    }
}

// Load news
async function loadNews() {
    try {
        const res = await fetch('/api/news');
        const news = await res.json();
        
        const html = news.map(n => `
            <div class="news-item">
                <div class="news-title">📰 ${n.title}</div>
                <div class="news-meta">
                    <span>📰 ${n.source}</span>
                    <span class="${n.sentiment === 'positive' ? 'positive' : n.sentiment === 'negative' ? 'negative' : ''}">
                        ${n.sentiment === 'positive' ? '🟢 Positive' : n.sentiment === 'negative' ? '🔴 Negative' : '🟡 Neutral'}
                    </span>
                </div>
                <div class="news-summary">${n.summary}</div>
            </div>
        `).join('');
        
        document.getElementById('newsList').innerHTML = html || '<div class="loading">No news available</div>';
        document.getElementById('allNewsList').innerHTML = html || '<div class="loading">No news available</div>';
        
    } catch(e) { 
        console.error(e);
        document.getElementById('newsList').innerHTML = '<div class="loading">Error loading news</div>';
    }
}



async function searchStock() {
    const symbol = document.getElementById('searchSymbol').value.toUpperCase().trim();
    if (!symbol) {
        document.getElementById('searchResult').innerHTML = '<div class="result-card"><p>Please enter a symbol</p></div>';
        return;
    }
    
    // Client-side validation for invalid symbols like "00", "123"
    if (!/^[A-Z]+$/.test(symbol)) {
        document.getElementById('searchResult').innerHTML = `
            <div class="result-card">
                <p style="color: var(--danger);">❌ Invalid symbol: "${symbol}"</p>
                <p style="color: var(--text-muted);">Use only letters (A-Z). Example: UBL, MCB, SYS</p>
            </div>
        `;
        return;
    }
    
    if (symbol.length < 2 || symbol.length > 10) {
        document.getElementById('searchResult').innerHTML = `
            <div class="result-card">
                <p style="color: var(--danger);">❌ Invalid symbol: "${symbol}"</p>
                <p style="color: var(--text-muted);">Symbol should be 2-10 characters. Example: UBL, MCB, SYS</p>
            </div>
        `;
        return;
    }
    
    document.getElementById('searchResult').innerHTML = '<div class="result-card"><div class="loading">Fetching data...</div></div>';
    
    try {
        const res = await fetch(`/api/stock/${symbol}`);
        const d = await res.json();
        
        // Check for error from API
        if (d.error) {
            document.getElementById('searchResult').innerHTML = `
                <div class="result-card">
                    <p style="color: var(--danger);">${d.error}</p>
                    <p style="color: var(--text-muted); margin-top: 10px;">💡 Try: UBL, MCB, SYS, ENGRO, LUCK</p>
                </div>
            `;
            return;
        }
        
        if (d.price === 'N/A' || d.recommendation === 'NOT FOUND') {
            document.getElementById('searchResult').innerHTML = `
                <div class="result-card">
                    <p style="color: var(--danger);">❌ Symbol '${symbol}' not found on PSX</p>
                    <p style="color: var(--text-muted); margin-top: 10px;">💡 Try: UBL, MCB, SYS, ENGRO, LUCK</p>
                </div>
            `;
            return;
        }
        
        // Build result details HTML
        let resultDetailsHtml = `
            <div class="result-detail">
                <div class="result-detail-label">Sentiment</div>
                <div class="result-detail-value">${d.sentiment.toUpperCase()}</div>
            </div>
            <div class="result-detail">
                <div class="result-detail-label">RSI</div>
                <div class="result-detail-value">${d.rsi}</div>
            </div>
            <div class="result-detail">
                <div class="result-detail-label">Trend</div>
                <div class="result-detail-value">${d.trend}</div>
            </div>
            <div class="result-detail">
                <div class="result-detail-label">Confidence</div>
                <div class="result-detail-value">${d.confidence}%</div>
            </div>
        `;
        
        // Add ML Trend if available
        if (d.ml_trend && d.ml_trend.trend) {
            resultDetailsHtml += `
                <div class="result-detail">
                    <div class="result-detail-label">🤖 ML Trend</div>
                    <div class="result-detail-value ${d.ml_trend.trend === 'up' ? 'positive' : d.ml_trend.trend === 'down' ? 'negative' : ''}">
                        ${d.ml_trend.trend.toUpperCase()} (${d.ml_trend.confidence}%)
                    </div>
                </div>
            `;
        }
        
        document.getElementById('searchResult').innerHTML = `
            <div class="result-card">
                <div class="result-header">
                    <h2>${d.symbol}</h2>
                    <span class="recommendation-badge ${d.recommendation.toLowerCase()}">${d.recommendation}</span>
                </div>
                <div class="result-price">PKR ${d.price}</div>
                <div class="${d.change > 0 ? 'positive' : d.change < 0 ? 'negative' : ''}">
                    ${d.change > 0 ? '+' : ''}${d.change}%
                </div>
                <div class="result-details">
                    ${resultDetailsHtml}
                </div>
                ${d.data_source ? `<div class="data-note">📌 ${d.market_message || 'Data source: ' + d.data_source}</div>` : ''}
            </div>
        `;
        
    } catch(e) {
        console.error('Search error:', e);
        document.getElementById('searchResult').innerHTML = '<div class="result-card"><p style="color: var(--danger);">Error fetching data</p></div>';
    }
}

// ML Prediction
// ML Prediction
async function getMLPrediction() {
    const symbol = document.getElementById('predictSymbol').value.toUpperCase().trim();
    
    if (!symbol) {
        document.getElementById('predictionResult').innerHTML = '<div class="prediction-card"><p>Please enter a symbol</p></div>';
        return;
    }
    
    // Client-side validation
    if (!/^[A-Z]+$/.test(symbol)) {
        document.getElementById('predictionResult').innerHTML = `
            <div class="prediction-card">
                <p style="color: var(--danger);">❌ Invalid symbol: "${symbol}"</p>
                <p style="color: var(--text-muted);">Use only letters (A-Z). Example: UBL, MCB, SYS</p>
            </div>
        `;
        return;
    }
    
    if (symbol.length < 2 || symbol.length > 10) 
         {
        document.getElementById('predictionResult').innerHTML = `
            <div class="prediction-card">
                <p style="color: var(--danger);">❌ Invalid symbol: "${symbol}"</p>
                <p style="color: var(--text-muted);">Symbol should be 2-10 characters. Example: UBL, MCB, SYS</p>
            </div>
        `;
        return;
    }
    
    document.getElementById('predictionResult').innerHTML = '<div class="prediction-card"><div class="loading">Generating prediction...</div></div>';
    
    try {
        const res = await fetch(`/api/ml_predict/${symbol}`);
        const pred = await res.json();
        
        if (pred.error) {
            document.getElementById('predictionResult').innerHTML = `
                <div class="prediction-card">
                    <p style="color: var(--danger);">❌ ${pred.error}</p>
                </div>
            `;
            return;
        }
        
        const changeClass = pred.expected_return > 0 ? 'positive' : pred.expected_return < 0 ? 'negative' : '';
        const changeSign = pred.expected_return > 0 ? '+' : '';
        
        let predictionHtml = `
            <div class="prediction-card">
                <div class="result-header">
                    <h2>${pred.symbol}</h2>
                    <span class="recommendation-badge ${pred.action.toLowerCase()}">${pred.action}</span>
                </div>
                <div class="prediction-current">💰 Current Price: PKR ${pred.current_price}</div>
                <div class="prediction-next">📈 Predicted Price: PKR ${pred.predicted_price}</div>
                <div class="prediction-change ${changeClass}">
                    📊 Expected Return: ${changeSign}${pred.expected_return}%
                </div>
                <div style="margin-top: 10px;">🎯 Confidence: ${pred.confidence}%</div>
        `;
        
        // Add trend display in prediction result
        if (pred.ml_trend) {
            let trendColor = '';
            let confidence = pred.ml_trend_confidence || 50;
            
            if (pred.ml_trend === 'up') trendColor = 'positive';
            else if (pred.ml_trend === 'down') trendColor = 'negative';
            
            let confidenceLevel = '';
            if (confidence >= 70) confidenceLevel = '🔥 High';
            else if (confidence >= 55) confidenceLevel = '📊 Medium';
            else confidenceLevel = '⚡ Low';
            
            predictionHtml += `
                <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--border);">
                    🤖 ML Trend: <span class="${trendColor}">${pred.ml_trend.toUpperCase()} (${confidence}%)</span>
                    <span style="font-size: 0.7rem; margin-left: 8px; color: var(--text-muted);">${confidenceLevel} confidence</span>
                </div>
            `;
        }
        
        predictionHtml += `</div>`;
        
        document.getElementById('predictionResult').innerHTML = predictionHtml;
        
    } catch(e) {
        console.error('ML Prediction error:', e);
        document.getElementById('predictionResult').innerHTML = '<div class="prediction-card"><p style="color: var(--danger);">Error generating prediction</p></div>';
    }
}


// Filter stocks
document.getElementById('stockFilter')?.addEventListener('input', (e) => {
    const filter = e.target.value.toUpperCase();
    const rows = document.querySelectorAll('#allStocksList .stock-row');
    rows.forEach(row => {
        const symbol = row.querySelector('.symbol')?.innerText || '';
        row.style.display = symbol.includes(filter) ? 'flex' : 'none';
    });
});

// Refresh functions
function refreshData() { loadAllStocks(); loadGainersLosers(); }
function refreshNews() { loadNews(); }

// Navigation
document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
        link.classList.add('active');
        
        const page = link.dataset.page;
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        document.getElementById(page + 'Page').classList.add('active');
        
        document.getElementById('pageTitle').innerHTML = link.querySelector('span').innerHTML;
        
        if (page === 'dashboard') {
            document.getElementById('pageSubtitle').innerHTML = 'Real-time market overview';
            refreshData();
            refreshNews();
        } else if (page === 'search') {
            document.getElementById('pageSubtitle').innerHTML = 'Search and analyze any stock';
        } else if (page === 'predict') {
            document.getElementById('pageSubtitle').innerHTML = 'AI-powered price predictions';
        } else if (page === 'news') {
            document.getElementById('pageSubtitle').innerHTML = 'Latest market news';
            loadNews();
        }
    });
});

// Popular tags click
document.querySelectorAll('.popular-tags span').forEach(tag => {
    tag.addEventListener('click', () => {
        document.getElementById('searchSymbol').value = tag.innerText;
        searchStock();
    });
});

// Enter key search
document.getElementById('searchSymbol')?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') searchStock();
});

document.getElementById('predictSymbol')?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') getMLPrediction();
});

document.getElementById('searchSymbol')?.addEventListener('input', () => {
    clearTimeout(suggestionTimeout);
    suggestionTimeout = setTimeout(getSuggestions, 300);
});

// Initial loads
checkMarketStatus();
setInterval(checkMarketStatus, 60000);
loadAllStocks();
loadGainersLosers();
loadNews();


// Auto refresh every 30 seconds
setInterval(() => {
    if (document.getElementById('dashboardPage').classList.contains('active')) {
        refreshData();
        refreshNews();
    }
}, 30000);
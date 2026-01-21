const API_URL = 'http://localhost:5000/api';
let stocks = [];
let currentChart = null;
let currentSymbol = null;
let currentPeriod = '1mo';

// Load stocks from localStorage on page load
window.addEventListener('DOMContentLoaded', () => {
    const saved = localStorage.getItem('stocks');
    if (saved) {
        stocks = JSON.parse(saved);
        stocks.forEach(symbol => fetchStockData(symbol));
    }
});

function handleEnter(event) {
    if (event.key === 'Enter') {
        addStock();
    }
}

async function addStock() {
    const input = document.getElementById('stockSymbol');
    const symbol = input.value.trim().toUpperCase();
    
    if (!symbol) {
        alert('Please enter a stock symbol');
        return;
    }
    
    if (stocks.includes(symbol)) {
        alert('Stock already added');
        return;
    }
    
    stocks.push(symbol);
    localStorage.setItem('stocks', JSON.stringify(stocks));
    
    await fetchStockData(symbol);
    input.value = '';
}

async function fetchStockData(symbol) {
    const container = document.getElementById('stockCards');
    
    // Create loading card
    const cardId = `stock-${symbol}`;
    let card = document.getElementById(cardId);
    
    if (!card) {
        card = document.createElement('div');
        card.id = cardId;
        card.className = 'stock-card loading';
        card.innerHTML = '<p>Loading...</p>';
        container.appendChild(card);
    }
    
    try {
        const response = await fetch(`${API_URL}/stock/${symbol}`);
        const data = await response.json();
        
        if (response.ok) {
            displayStock(data);
        } else {
            card.innerHTML = `<p class="error-message">Error: ${data.error}</p>`;
            setTimeout(() => removeStock(symbol), 3000);
        }
    } catch (error) {
        card.innerHTML = `<p class="error-message">Failed to fetch data</p>`;
        setTimeout(() => removeStock(symbol), 3000);
    }
}

function displayStock(data) {
    const cardId = `stock-${data.symbol}`;
    const card = document.getElementById(cardId);
    
    const changeClass = data.change >= 0 ? 'positive' : 'negative';
    const changeSign = data.change >= 0 ? '+' : '';
    
    card.className = 'stock-card';
    card.innerHTML = `
        <div class="stock-header">
            <div class="stock-symbol">${data.symbol}</div>
        </div>
        <div class="stock-name">${data.name}</div>
        <div class="stock-price">$${data.price.toFixed(2)}</div>
        <div class="stock-change ${changeClass}">
            ${changeSign}${data.change.toFixed(2)} (${changeSign}${data.changePercent.toFixed(2)}%)
        </div>
        <button class="remove-btn" onclick="removeStock('${data.symbol}')">Remove</button>
    `;
    
    card.onclick = (e) => {
        if (!e.target.classList.contains('remove-btn')) {
            showChart(data.symbol);
        }
    };
}

function removeStock(symbol) {
    stocks = stocks.filter(s => s !== symbol);
    localStorage.setItem('stocks', JSON.stringify(stocks));
    
    const card = document.getElementById(`stock-${symbol}`);
    if (card) {
        card.remove();
    }
    
    if (currentSymbol === symbol) {
        document.getElementById('chartSection').style.display = 'none';
    }
}

async function showChart(symbol) {
    currentSymbol = symbol;
    document.getElementById('chartSection').style.display = 'block';
    document.getElementById('chartTitle').textContent = `${symbol} - Stock History`;
    
    // Reset button states
    document.querySelectorAll('.chart-controls button').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector('.chart-controls button').classList.add('active');
    
    currentPeriod = '1mo';
    await fetchHistory(symbol, currentPeriod);
}

async function showHistory(period) {
    if (!currentSymbol) return;
    
    currentPeriod = period;
    
    // Update active button
    document.querySelectorAll('.chart-controls button').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
    
    await fetchHistory(currentSymbol, period);
}

async function fetchHistory(symbol, period) {
    try {
        const response = await fetch(`${API_URL}/history/${symbol}?period=${period}`);
        const data = await response.json();
        
        if (response.ok) {
            drawChart(data.dates, data.prices, `${symbol} Price History`);
        }
    } catch (error) {
        console.error('Error fetching history:', error);
    }
}

async function showPrediction() {
    if (!currentSymbol) return;
    
    const btn = event.target;
    btn.disabled = true;
    btn.textContent = 'Loading prediction...';
    
    try {
        const response = await fetch(`${API_URL}/predict/${currentSymbol}?days=7`);
        const data = await response.json();
        
        if (response.ok) {
            // Fetch historical data first
            const histResponse = await fetch(`${API_URL}/history/${currentSymbol}?period=${currentPeriod}`);
            const histData = await histResponse.json();
            
            // Combine historical and prediction data
            const allDates = [...histData.dates, ...data.predictions.dates];
            const allPrices = [...histData.prices, ...data.predictions.prices];
            
            drawChart(
                allDates, 
                allPrices, 
                `${currentSymbol} - History + 7-Day Prediction`,
                histData.dates.length
            );
            
            // Show prediction info
            const changeClass = data.predicted_change >= 0 ? 'positive' : 'negative';
            const changeSign = data.predicted_change >= 0 ? '+' : '';
            
            alert(`Prediction for ${currentSymbol}:\n\n` +
                  `Current: $${data.current_price}\n` +
                  `Predicted (7 days): $${data.predictions.prices[data.predictions.prices.length - 1]}\n` +
                  `Change: ${changeSign}$${data.predicted_change.toFixed(2)} (${changeSign}${data.predicted_change_percent.toFixed(2)}%)`);
        } else {
            alert(`Error: ${data.error}`);
        }
    } catch (error) {
        alert('Failed to get prediction. Make sure the backend is running.');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Show Prediction';
    }
}

function drawChart(labels, data, title, splitIndex = null) {
    const ctx = document.getElementById('stockChart').getContext('2d');
    
    if (currentChart) {
        currentChart.destroy();
    }
    
    const datasets = [];
    
    if (splitIndex) {
        // Split data into historical and prediction
        datasets.push({
            label: 'Historical',
            data: data.slice(0, splitIndex),
            borderColor: 'rgb(75, 192, 192)',
            backgroundColor: 'rgba(75, 192, 192, 0.1)',
            tension: 0.1,
            fill: true
        });
        
        datasets.push({
            label: 'Prediction',
            data: [...Array(splitIndex - 1).fill(null), data[splitIndex - 1], ...data.slice(splitIndex)],
            borderColor: 'rgb(255, 152, 0)',
            backgroundColor: 'rgba(255, 152, 0, 0.1)',
            borderDash: [5, 5],
            tension: 0.1,
            fill: true
        });
    } else {
        datasets.push({
            label: 'Price',
            data: data,
            borderColor: 'rgb(75, 192, 192)',
            backgroundColor: 'rgba(75, 192, 192, 0.1)',
            tension: 0.1,
            fill: true
        });
    }
    
    currentChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true
                },
                title: {
                    display: true,
                    text: title
                }
            },
            scales: {
                y: {
                    beginAtZero: false
                }
            }
        }
    });
} 
from flask import Flask, jsonify, request
from flask_cors import CORS
import yfinance as yf
import pandas as pd
from neuralprophet import NeuralProphet
from datetime import datetime, timedelta
import warnings
from functools import lru_cache
import time

warnings.filterwarnings('ignore')

app = Flask(__name__)
CORS(app)

# Simple in-memory cache
cache = {}
CACHE_DURATION = 60  # Cache for 60 seconds

def get_cached_or_fetch(key, fetch_func, *args):
    """Simple caching mechanism"""
    current_time = time.time()
    
    if key in cache:
        data, timestamp = cache[key]
        if current_time - timestamp < CACHE_DURATION:
            return data
    
    # Fetch new data
    data = fetch_func(*args)
    cache[key] = (data, current_time)
    return data

@app.route('/api/stock/<symbol>', methods=['GET'])
def get_stock_data(symbol):
    """Get current stock data with caching"""
    try:
        def fetch_stock():
            # Add a small delay to avoid rate limits
            time.sleep(0.5)
            
            stock = yf.Ticker(symbol)
            info = stock.info
            hist = stock.history(period='1d')
            
            if hist.empty:
                return None
            
            current_price = hist['Close'].iloc[-1]
            
            return {
                'symbol': symbol.upper(),
                'name': info.get('longName', symbol),
                'price': round(current_price, 2),
                'currency': info.get('currency', 'USD'),
                'change': round(hist['Close'].iloc[-1] - hist['Open'].iloc[0], 2) if len(hist) > 0 else 0,
                'changePercent': round(((hist['Close'].iloc[-1] - hist['Open'].iloc[0]) / hist['Open'].iloc[0] * 100), 2) if len(hist) > 0 else 0
            }
        
        data = get_cached_or_fetch(f'stock_{symbol}', fetch_stock)
        
        if data is None:
            return jsonify({'error': 'Stock not found'}), 404
        
        return jsonify(data)
        
    except Exception as e:
        error_msg = str(e)
        if '429' in error_msg:
            return jsonify({'error': 'Rate limit exceeded. Please try again in a minute.'}), 429
        return jsonify({'error': error_msg}), 500

@app.route('/api/history/<symbol>', methods=['GET'])
def get_stock_history(symbol):
    """Get historical stock data with caching"""
    try:
        period = request.args.get('period', '1mo')
        cache_key = f'history_{symbol}_{period}'
        
        def fetch_history():
            time.sleep(0.5)
            stock = yf.Ticker(symbol)
            hist = stock.history(period=period)
            
            if hist.empty:
                return None
            
            return {
                'dates': hist.index.strftime('%Y-%m-%d').tolist(),
                'prices': hist['Close'].round(2).tolist(),
                'volumes': hist['Volume'].tolist()
            }
        
        data = get_cached_or_fetch(cache_key, fetch_history)
        
        if data is None:
            return jsonify({'error': 'No historical data found'}), 404
        
        return jsonify(data)
        
    except Exception as e:
        error_msg = str(e)
        if '429' in error_msg:
            return jsonify({'error': 'Rate limit exceeded. Please try again in a minute.'}), 429
        return jsonify({'error': error_msg}), 500

@app.route('/api/predict/<symbol>', methods=['GET'])
def predict_stock(symbol):
    """Predict future stock prices using NeuralProphet"""
    try:
        days = int(request.args.get('days', 7))
        
        # Get historical data
        time.sleep(0.5)
        stock = yf.Ticker(symbol)
        hist = stock.history(period='3mo')
        
        if hist.empty or len(hist) < 30:
            return jsonify({'error': 'Insufficient historical data'}), 400
        
        # Prepare data for NeuralProphet
        df = pd.DataFrame({
            'ds': hist.index,
            'y': hist['Close']
        })
        df['ds'] = pd.to_datetime(df['ds'])
        df = df.reset_index(drop=True)
        
        # Train model
        model = NeuralProphet(
            n_forecasts=days,
            n_lags=14,
            yearly_seasonality=False,
            weekly_seasonality=True,
            daily_seasonality=False,
            epochs=50,
            learning_rate=0.1
        )
        
        # Fit model
        model.fit(df, freq='D', validation_df=None, progress=None)
        
        # Make predictions
        future = model.make_future_dataframe(df, periods=days, n_historic_predictions=len(df))
        forecast = model.predict(future)
        
        # Get only future predictions
        predictions = forecast[forecast['ds'] > df['ds'].max()]
        
        result = {
            'symbol': symbol.upper(),
            'predictions': {
                'dates': predictions['ds'].dt.strftime('%Y-%m-%d').tolist(),
                'prices': predictions['yhat1'].round(2).tolist()
            },
            'current_price': round(hist['Close'].iloc[-1], 2),
            'predicted_change': round(predictions['yhat1'].iloc[-1] - hist['Close'].iloc[-1], 2),
            'predicted_change_percent': round(((predictions['yhat1'].iloc[-1] - hist['Close'].iloc[-1]) / hist['Close'].iloc[-1] * 100), 2)
        }
        
        return jsonify(result)
        
    except Exception as e:
        error_msg = str(e)
        if '429' in error_msg:
            return jsonify({'error': 'Rate limit exceeded. Please try again in a minute.'}), 429
        return jsonify({'error': error_msg}), 500

@app.route('/api/search/<query>', methods=['GET'])
def search_stocks(query):
    """Search for stock symbols"""
    try:
        time.sleep(0.5)
        ticker = yf.Ticker(query)
        info = ticker.info
        
        if 'symbol' not in info:
            return jsonify({'results': []})
        
        result = {
            'results': [{
                'symbol': info.get('symbol', query.upper()),
                'name': info.get('longName', query.upper()),
                'exchange': info.get('exchange', 'Unknown')
            }]
        }
        
        return jsonify(result)
    except:
        return jsonify({'results': []})

if __name__ == '__main__':
    print("Starting Flask server on http://localhost:5000")
    print("API Endpoints:")
    print("  GET /api/stock/<symbol> - Get current stock data")
    print("  GET /api/history/<symbol>?period=1mo - Get historical data")
    print("  GET /api/predict/<symbol>?days=7 - Get price predictions")
    print("  GET /api/search/<query> - Search for stocks")
    app.run(debug=True, port=5000)
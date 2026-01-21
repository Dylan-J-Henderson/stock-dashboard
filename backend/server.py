from flask import Flask, jsonify, request
from flask_cors import CORS
import yfinance as yf
import pandas as pd
from neuralprophet import NeuralProphet
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "http://localhost:*",
            "http://127.0.0.1:*",
            "https://dylan-j-henderson.github.io",
        ]
    }
})

@app.route('/api/stock/<symbol>', methods=['GET'])
def get_stock_data(symbol):
    """Get current stock data"""
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        hist = stock.history(period='1d')
        
        if hist.empty:
            return jsonify({'error': 'Stock not found'}), 404
        
        current_price = hist['Close'].iloc[-1]
        
        data = {
            'symbol': symbol.upper(),
            'name': info.get('longName', symbol),
            'price': round(current_price, 2),
            'currency': info.get('currency', 'USD'),
            'change': round(hist['Close'].iloc[-1] - hist['Open'].iloc[0], 2) if len(hist) > 0 else 0,
            'changePercent': round(((hist['Close'].iloc[-1] - hist['Open'].iloc[0]) / hist['Open'].iloc[0] * 100), 2) if len(hist) > 0 else 0
        }
        
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/history/<symbol>', methods=['GET'])
def get_stock_history(symbol):
    """Get historical stock data"""
    try:
        period = request.args.get('period', '1mo')
        stock = yf.Ticker(symbol)
        hist = stock.history(period=period)
        
        if hist.empty:
            return jsonify({'error': 'No historical data found'}), 404
        
        data = {
            'dates': hist.index.strftime('%Y-%m-%d').tolist(),
            'prices': hist['Close'].round(2).tolist(),
            'volumes': hist['Volume'].tolist()
        }
        
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/predict/<symbol>', methods=['GET'])
def predict_stock(symbol):
    """Predict future stock prices using NeuralProphet"""
    try:
        days = int(request.args.get('days', 7))
        
        # Get historical data
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
        return jsonify({'error': str(e)}), 500

@app.route('/api/search/<query>', methods=['GET'])
def search_stocks(query):
    """Search for stock symbols"""
    try:
        # Simple search using yfinance
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
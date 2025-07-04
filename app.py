#!/usr/bin/env python3
"""
TradingRoad - Plataforma de Trading Profesional
Flask Backend sin análisis AI
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
import sys
from datetime import datetime, timedelta
import json

# Añadir el directorio raíz al path para importar módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importar servicios
from config.config import ConfigService
from modules.market.marketService import MarketService
from modules.news.news import NewsService
from modules.calendar.calendar import CalendarService
from modules.volatility.volatility import VolatilityService

# Configurar la aplicación Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# Configurar CORS
CORS(app, origins=["*"])

# Inicializar servicios
config_service = ConfigService()
market_service = MarketService()
news_service = NewsService()
calendar_service = CalendarService()
volatility_service = VolatilityService()

print("🚀 TradingRoad Backend iniciado")
print("📊 Servicios disponibles: Market, News, Calendar, Volatility, Config")

# ==================== RUTAS PRINCIPALES ====================

@app.route('/')
def index():
    """Página principal del dashboard"""
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    """Dashboard principal - misma funcionalidad que index"""
    return render_template('index.html')

@app.route('/analysis')
def analysis():
    """Página de análisis básico"""
    return render_template('analysis.html')

@app.route('/trading')
def trading():
    """Página de trading"""
    return render_template('trading.html')

@app.route('/volatility')
def volatility():
    """Página de análisis de volatilidad y vencimientos"""
    return render_template('volatility.html')

@app.route('/news')
def news():
    """Página de noticias financieras"""
    return render_template('news.html')

@app.route('/calendar')
def calendar():
    """Página del calendario económico"""
    return render_template('calendar.html')

@app.route('/config')
def config():
    """Página de configuración"""
    return render_template('config.html')

# ==================== API ENDPOINTS ====================

# Market Data APIs
@app.route('/api/market/summary')
def get_market_summary():
    """Obtener resumen del mercado con múltiples símbolos"""
    try:
        symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']  # Principales criptos
        market_data = {}
        
        for symbol in symbols:
            try:
                data = market_service.get_current_price(symbol, 'binance')
                # Convertir el símbolo al formato esperado por el frontend
                symbol_key = symbol.replace('USDT', '').lower()  # BTCUSDT -> btc
                market_data[symbol_key] = {
                    'price': data.get('price', 0),
                    'change_24h': data.get('percentage', 0),
                    'change': data.get('change', 0),
                    'symbol': symbol
                }
            except Exception as e:
                print(f"Error obteniendo precio de {symbol}: {e}")
                # Datos mock si falla
                symbol_key = symbol.replace('USDT', '').lower()
                market_data[symbol_key] = {
                    'price': 50000 if 'BTC' in symbol else (3000 if 'ETH' in symbol else 150),
                    'change_24h': 0,
                    'change': 0,
                    'symbol': symbol
                }
        
        # Agregar SPY (simulado por ahora)
        market_data['spy'] = {
            'price': 580.45,
            'change_24h': 0.25,
            'change': 1.45,
            'symbol': 'SPY'
        }
        
        return jsonify({
            "status": "success",
            "data": market_data,
            "source": "binance",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/market/price/<symbol>')
def get_market_price(symbol):
    """Obtener precio actual de un símbolo"""
    try:
        source = request.args.get('source', 'binance')
        data = market_service.get_current_price(symbol, source)
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/market/historical/<symbol>')
def get_historical_data(symbol):
    """Obtener datos históricos de un símbolo"""
    try:
        source = request.args.get('source', 'binance')
        timeframe = request.args.get('timeframe', '1d')
        limit = int(request.args.get('limit', 100))
        
        data = market_service.get_historical_data(symbol, timeframe, limit, source)
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/market/symbols/<exchange>')
def get_symbols(exchange):
    """Obtener símbolos disponibles de un exchange"""
    try:
        symbols = market_service.get_available_symbols(exchange)
        return jsonify({"success": True, "data": symbols})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/market/search')
def search_symbols():
    """Buscar símbolos"""
    try:
        query = request.args.get('q', '')
        exchange = request.args.get('exchange', 'binance')
        
        if not query:
            return jsonify({"success": False, "error": "Query parameter required"}), 400
            
        results = market_service.search_symbols(query, exchange)
        return jsonify({"success": True, "data": results})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# News APIs
@app.route('/api/news')
def get_news():
    """Obtener noticias financieras"""
    try:
        category = request.args.get('category', 'markets')
        limit = int(request.args.get('limit', 10))
        
        news = news_service.get_news(category, limit)
        return jsonify({"success": True, "data": news})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/news/search')
def search_news():
    """Buscar noticias"""
    try:
        query = request.args.get('q', '')
        if not query:
            return jsonify({"success": False, "error": "Query parameter required"}), 400
            
        results = news_service.search_news(query)
        return jsonify({"success": True, "data": results})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Calendar APIs
@app.route('/api/calendar/events')
def get_calendar_events():
    """Obtener eventos del calendario económico"""
    try:
        date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        country = request.args.get('country', 'US')
        
        events = calendar_service.get_events(date, country)
        return jsonify({"success": True, "data": events})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/calendar/week')
def get_week_events():
    """Obtener eventos de la semana"""
    try:
        week_start = request.args.get('week_start', datetime.now().strftime('%Y-%m-%d'))
        country = request.args.get('country', 'US')
        
        events = calendar_service.get_week_events(week_start, country)
        return jsonify({"success": True, "data": events})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/calendar')
def get_calendar():
    """Obtener eventos del calendario económico con parámetros de fecha"""
    try:
        start_date = request.args.get('start_date', datetime.now().strftime('%Y-%m-%d'))
        end_date = request.args.get('end_date', (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'))
        country = request.args.get('country', 'US')
        
        events = calendar_service.get_week_events(start_date, country)
        return jsonify({"success": True, "data": events})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Volatility APIs
@app.route('/api/volatility/analysis/<symbol>')
def get_volatility_analysis(symbol):
    """Obtener análisis de volatilidad"""
    try:
        period = request.args.get('period', '30')
        
        analysis = volatility_service.get_volatility_analysis(symbol, period)
        return jsonify({"success": True, "data": analysis})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/volatility/expirations')
def get_expirations():
    """Obtener vencimientos de derivados"""
    try:
        date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        
        expirations = volatility_service.get_expirations(date)
        return jsonify({"success": True, "data": expirations})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== NUEVOS ENDPOINTS PARA VENCIMIENTOS AVANZADOS ====================

@app.route('/api/expirations/<currency>')
def get_expirations_by_currency(currency):
    """Obtener fechas de vencimiento disponibles para una moneda específica"""
    try:
        currency = currency.upper()
        dates = volatility_service.get_expiration_dates(currency)
        return jsonify(dates)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/derivatives/options/<currency>')
def get_options_data(currency):
    """Obtener datos de opciones de Deribit"""
    try:
        currency = currency.upper()
        data = volatility_service.get_deribit_options_data(currency)
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/derivatives/metrics/<currency>')
def get_derivatives_metrics(currency):
    """Obtener métricas de derivados"""
    try:
        currency = currency.upper()
        expiry_date = request.args.get('expiry_date')
        
        metrics = volatility_service.get_derivatives_metrics(currency, expiry_date)
        return jsonify({"success": True, "data": metrics})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/derivatives/orderbook/<currency>')
def get_derivatives_orderbook(currency):
    """Obtener libro de órdenes de derivados"""
    try:
        currency = currency.upper()
        level = int(request.args.get('level', 1))
        
        orderbook = volatility_service.get_orderbook_data(currency, level)
        return jsonify({"success": True, "data": orderbook})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/derivatives/volatility-history/<currency>')
def get_volatility_history(currency):
    """Obtener historial de volatilidad"""
    try:
        currency = currency.upper()
        days = int(request.args.get('days', 90))
        
        history = volatility_service.get_volatility_history(currency, days)
        return jsonify({"success": True, "data": history})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/derivatives/binance-metrics/<symbol>')
def get_binance_metrics(symbol):
    """Obtener métricas de Binance (Open Interest, Long/Short ratio, etc.)"""
    try:
        metrics = volatility_service.get_binance_metrics(symbol)
        return jsonify({"success": True, "data": metrics})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Config APIs
@app.route('/api/config', methods=['GET'])
def get_config():
    """Obtener configuración actual"""
    try:
        config = config_service.get_config()
        return jsonify({"success": True, "data": config})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/config', methods=['POST'])
def update_config():
    """Actualizar configuración"""
    try:
        new_config = request.get_json()
        if not new_config:
            return jsonify({"success": False, "error": "JSON data required"}), 400
            
        updated_config = config_service.update_config(new_config)
        return jsonify({"success": True, "data": updated_config})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== HEALTH CHECK ====================

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "market": True,
            "news": True,
            "calendar": True,
            "volatility": True,
            "config": True
        },
        "version": "1.0.0"
    })

@app.route('/api/status')
def status():
    """Status endpoint con información detallada"""
    try:
        # Test basic functionality of each service
        market_status = True
        news_status = True
        calendar_status = True
        volatility_status = True
        
        try:
            # Test market service
            market_service.get_available_symbols('binance')
        except:
            market_status = False
            
        try:
            # Test news service
            news_service.get_news('markets', 1)
        except:
            news_status = False
            
        return jsonify({
            "status": "running",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "market": market_status,
                "news": news_status,
                "calendar": calendar_status,
                "volatility": volatility_status,
                "config": True
            },
            "uptime": "N/A",
            "version": "1.0.0"
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    """Error handler para 404"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Error handler para 500"""
    return render_template('500.html'), 500

# ==================== MAIN ====================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print(f"🌐 Servidor corriendo en http://localhost:{port}")
    print(f"🔧 Debug mode: {debug}")
    print("📱 Endpoints disponibles:")
    print("   • / - Dashboard principal")
    print("   • /api/health - Health check")
    print("   • /api/market/* - APIs de mercado")
    print("   • /api/news/* - APIs de noticias")
    print("   • /api/calendar/* - APIs de calendario")
    print("   • /api/volatility/* - APIs de volatilidad")
    
    app.run(host='0.0.0.0', port=port, debug=debug)

# Servicio integrado de Volatilidad, Vencimientos y Sentimiento de Mercado
# Integra el módulo avanzado de Sentimiento-de-Mercado-y-Vencimientos

import os
import json
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from decimal import Decimal
import traceback

# ==============================================================================
# SECCIÓN 1: LÓGICA DE DERIBIT (OPCIONES Y DERIVADOS)
# ==============================================================================
def calculate_max_pain(df):
    """Calcula el punto de máximo dolor para opciones"""
    if df.empty or 'strike' not in df or df['strike'].nunique() == 0: 
        return 0
    
    strikes = sorted(df['strike'].unique())
    total_losses = []
    
    for expiry_strike in strikes:
        loss = 0
        
        # Pérdidas para calls
        calls_df = df[df['type'] == 'C'].copy()
        calls_df['loss'] = (expiry_strike - calls_df['strike']) * calls_df['open_interest']
        calls_df.loc[calls_df['loss'] < 0, 'loss'] = 0
        loss += calls_df['loss'].sum()
        
        # Pérdidas para puts
        puts_df = df[df['type'] == 'P'].copy()
        puts_df['loss'] = (puts_df['strike'] - expiry_strike) * puts_df['open_interest']
        puts_df.loc[puts_df['loss'] < 0, 'loss'] = 0
        loss += puts_df['loss'].sum()
        
        total_losses.append(loss)
    
    min_loss_index = total_losses.index(min(total_losses))
    return strikes[min_loss_index]

def get_deribit_option_data(currency='BTC'):
    """Obtiene datos de opciones de Deribit con manejo de errores mejorado"""
    url = f"https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency={currency}&kind=option"
    
    try:
        headers = {
            'User-Agent': 'TradingRoad/1.0 (contact@tradingroad.app)',
            'Accept': 'application/json'
        }
        response = requests.get(url, timeout=15, headers=headers)
        response.raise_for_status()
        result = response.json()
        
        if 'result' not in result:
            print(f"Warning: No 'result' key in Deribit response for {currency}")
            return pd.DataFrame()
            
        data = result['result']
        if not data:
            print(f"Warning: Empty data from Deribit for {currency}")
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        if df.empty:
            print(f"Warning: Empty DataFrame after processing Deribit data for {currency}")
            return df
        
        # Procesar datos griegos
        if 'greeks' not in df.columns:
            df['greeks'] = [{'delta': 0, 'gamma': 0, 'vega': 0, 'theta': 0} for _ in range(len(df))]
        else:
            df['greeks'] = df['greeks'].apply(lambda x: x if isinstance(x, dict) else {'delta': 0, 'gamma': 0, 'vega': 0, 'theta': 0})
        
        # Procesar fechas y strikes
        df['expiration_date'] = pd.to_datetime(df['instrument_name'].str.split('-').str[1], format='%d%b%y').dt.normalize()
        df['strike'] = df['instrument_name'].str.split('-').str[2]
        df['type'] = df['instrument_name'].str.split('-').str[3]
        
        # Convertir columnas numéricas
        numeric_cols = ['mark_iv', 'underlying_price', 'strike', 'open_interest', 'volume']
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
        
        df.dropna(subset=['strike'], inplace=True)
        df['strike'] = df['strike'].astype(int)
        
        # Convertir tipos numpy a tipos Python nativos para JSON
        for col in df.select_dtypes(include=[np.integer]).columns:
            df[col] = df[col].astype(int)
        for col in df.select_dtypes(include=[np.floating]).columns:
            df[col] = df[col].astype(float)
        
        return df
        
    except Exception as e:
        print(f"Error en get_deribit_option_data: {e}")
        traceback.print_exc()
        return None

def get_deribit_orderbook_data(currency='BTC', level=1000):
    """Obtiene datos del libro de órdenes de Deribit"""
    try:
        url = f"https://deribit.com/api/v2/public/get_order_book?instrument_name={currency}-PERPETUAL&depth=100"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()['result']
        
        # Procesar bids y asks
        bids = [[float(bid[0]), float(bid[1])] for bid in data.get('bids', [])]
        asks = [[float(ask[0]), float(ask[1])] for ask in data.get('asks', [])]
        
        # Agregar datos según el nivel especificado
        if level > 1:
            bids = aggregate_orderbook_level(bids, level, 'bid')
            asks = aggregate_orderbook_level(asks, level, 'ask')
        
        return {
            'bids': bids[:20],  # Limitar a top 20
            'asks': asks[:20],
            'timestamp': data.get('timestamp', datetime.now().timestamp() * 1000)
        }
        
    except Exception as e:
        print(f"Error en get_deribit_orderbook_data: {e}")
        return {'bids': [], 'asks': [], 'timestamp': datetime.now().timestamp() * 1000}

def aggregate_orderbook_level(orders, level, side):
    """Agrega órdenes por nivel de precio"""
    if not orders or level <= 1:
        return orders
    
    aggregated = defaultdict(float)
    
    for price, amount in orders:
        if side == 'bid':
            aggregated_price = int(price // level) * level
        else:  # ask
            aggregated_price = int(price // level + 1) * level
        aggregated[aggregated_price] += amount
    
    result = [[price, amount] for price, amount in aggregated.items()]
    result.sort(key=lambda x: x[0], reverse=(side == 'bid'))
    
    return result

def calculate_deribit_metrics(df):
    """Calcula métricas de Deribit"""
    if df is None or df.empty:
        return {}
    
    try:
        calls_df = df[df['type'] == 'C']
        puts_df = df[df['type'] == 'P']
        
        call_oi = calls_df['open_interest'].sum()
        put_oi = puts_df['open_interest'].sum()
        total_oi = call_oi + put_oi
        
        call_volume = calls_df['volume'].sum()
        put_volume = puts_df['volume'].sum()
        
        put_call_ratio_oi = put_oi / call_oi if call_oi > 0 else 0
        put_call_ratio_volume = put_volume / call_volume if call_volume > 0 else 0
        
        max_pain = calculate_max_pain(df)
        
        # Calcular valor nocional
        underlying_price = df['underlying_price'].iloc[0] if not df.empty else 0
        notional_value_usd = total_oi * underlying_price
        
        # Convertir a tipos Python nativos para serialización JSON
        return {
            'call_oi': int(call_oi) if not np.isnan(call_oi) else 0,
            'put_oi': int(put_oi) if not np.isnan(put_oi) else 0,
            'total_oi': int(total_oi) if not np.isnan(total_oi) else 0,
            'put_call_ratio_oi': float(put_call_ratio_oi) if not np.isnan(put_call_ratio_oi) else 0.0,
            'put_call_ratio_volume': float(put_call_ratio_volume) if not np.isnan(put_call_ratio_volume) else 0.0,
            'max_pain': int(max_pain) if not np.isnan(max_pain) else 0,
            'notional_value_usd': float(notional_value_usd) if not np.isnan(notional_value_usd) else 0.0,
            'underlying_price': float(underlying_price) if not np.isnan(underlying_price) else 0.0
        }
        
    except Exception as e:
        print(f"Error en calculate_deribit_metrics: {e}")
        return {}

def get_deribit_dvol_history(currency='BTC', days=90):
    """Obtiene historial de volatilidad de Deribit"""
    instrument = currency.upper()
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
    
    url = f"https://www.deribit.com/api/v2/public/get_volatility_index_data?currency={instrument}&start_timestamp={start_time}&end_timestamp={end_time}&resolution=D"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json().get('result', {}).get('data', [])
        
        if not data:
            return None
        
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['close'] = pd.to_numeric(df['close'])
        df['sma_7'] = df['close'].rolling(window=7).mean()
        df.dropna(subset=['sma_7'], inplace=True)
        
        return df
        
    except Exception as e:
        print(f"Error en get_deribit_dvol_history: {e}")
        return None

# ==============================================================================
# SECCIÓN 2: LÓGICA DE BINANCE Y OTRAS
# ==============================================================================
def get_binance_klines(symbol='BTC', interval='1d', days=7):
    """Obtiene datos de velas de Binance"""
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}USDT&interval={interval}&limit={days}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume', 'count', 'taker_buy_volume', 'taker_buy_quote_volume', 'ignore'])
        df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
        
        week_high_idx = df['high'].idxmax()
        week_low_idx = df['low'].idxmin()
        
        return {
            'week_high': df.loc[week_high_idx, 'high'],
            'week_high_timestamp': df.loc[week_high_idx, 'timestamp'],
            'week_low': df.loc[week_low_idx, 'low'],
            'week_low_timestamp': df.loc[week_low_idx, 'timestamp']
        }
        
    except Exception as e:
        print(f"Error en get_binance_klines: {e}")
        return None

def get_binance_sentiment_data(symbol='BTC', limit_oi=48, limit_ls=48):
    """Obtiene datos de sentimiento de Binance"""
    try:
        # Obtener OI actual
        oi_url = f"https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol}USDT"
        oi_response = requests.get(oi_url, timeout=10)
        oi_response.raise_for_status()
        current_oi = float(oi_response.json()['openInterest'])
        
        # Obtener historial de OI
        oi_hist_url = f"https://fapi.binance.com/futures/data/openInterestHist?symbol={symbol}USDT&period=5m&limit={limit_oi}"
        oi_hist_response = requests.get(oi_hist_url, timeout=10)
        oi_hist_response.raise_for_status()
        oi_hist_data = oi_hist_response.json()
        
        # Obtener ratio Long/Short
        ls_url = f"https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol={symbol}USDT&period=5m&limit={limit_ls}"
        ls_response = requests.get(ls_url, timeout=10)
        ls_response.raise_for_status()
        ls_data = ls_response.json()
        
        # Calcular cambio de OI en 4h
        oi_change_4h = 0
        if len(oi_hist_data) >= 48:  # 48 * 5min = 4h
            oi_4h_ago = float(oi_hist_data[-48]['sumOpenInterest'])
            oi_change_4h = ((current_oi - oi_4h_ago) / oi_4h_ago) * 100 if oi_4h_ago > 0 else 0
        
        return {
            'current_oi_binance': current_oi,
            'oi_change_4h_percent': oi_change_4h,
            'oi_history': oi_hist_data,
            'long_short_ratio': ls_data
        }
        
    except Exception as e:
        print(f"Error en get_binance_sentiment_data: {e}")
        return None

def get_binance_funding_info(symbol='BTC'):
    """Obtiene información de funding de Binance"""
    try:
        url = f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={symbol}USDT"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        return {
            'current_funding_rate': float(data['lastFundingRate']),
            'next_funding_time_ms': int(data['nextFundingTime']),
            'mark_price': float(data['markPrice'])
        }
        
    except Exception as e:
        print(f"Error en get_binance_funding_info: {e}")
        return None

def get_binance_funding_rate_history(symbol='BTC', limit=100):
    """Obtiene historial de funding rate de Binance"""
    try:
        url = f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol}USDT&limit={limit}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        return [{
            'timestamp': item['fundingTime'],
            'funding_rate': float(item['fundingRate'])
        } for item in data]
        
    except Exception as e:
        print(f"Error en get_binance_funding_rate_history: {e}")
        return None

def get_deribit_order_book(currency='BTC', depth=1000, step=0):
    """Obtiene libro de órdenes de Deribit"""
    instrument = f"{currency}-PERPETUAL"
    url = f"https://www.deribit.com/api/v2/public/get_order_book?instrument_name={instrument}&depth={depth}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()['result']
        
        # Procesar bids y asks
        bids = [[float(price), float(amount)] for price, amount in data['bids']]
        asks = [[float(price), float(amount)] for price, amount in data['asks']]
        
        # Aplicar agregación si se especifica step
        if step > 0:
            bids = aggregate_order_book_levels(bids, step, 'bid')
            asks = aggregate_order_book_levels(asks, step, 'ask')
        
        return {
            'bids': bids[:50],  # Limitar a 50 niveles
            'asks': asks[:50],
            'timestamp': data['timestamp']
        }
        
    except Exception as e:
        print(f"Error en get_deribit_order_book: {e}")
        return None

def aggregate_order_book_levels(levels, step, side):
    """Agrega niveles del libro de órdenes"""
    if not levels or step <= 0:
        return levels
    
    aggregated = {}
    
    for price, amount in levels:
        # Redondear precio al step más cercano
        if side == 'bid':
            rounded_price = int(price / step) * step
        else:  # ask
            rounded_price = (int(price / step) + 1) * step
        
        if rounded_price in aggregated:
            aggregated[rounded_price] += amount
        else:
            aggregated[rounded_price] = amount
    
    # Convertir de vuelta a lista ordenada
    result = [[price, amount] for price, amount in aggregated.items()]
    result.sort(key=lambda x: x[0], reverse=(side == 'bid'))
    
    return result


class VolatilityService:
    """
    Servicio para análisis de volatilidad y vencimientos
    """
    
    def __init__(self):
        pass
    
    def get_volatility_analysis(self, symbol='BTC', period='30'):
        """
        Obtiene análisis de volatilidad para un símbolo
        
        Args:
            symbol: Símbolo a analizar (ej: 'BTC', 'ETH')
            period: Período en días
            
        Returns:
            Dict con análisis de volatilidad
        """
        try:
            # Por ahora retornamos datos mock
            import random
            
            volatility_data = {
                'symbol': symbol,
                'period': period,
                'current_volatility': round(random.uniform(0.4, 1.2), 2),
                'avg_volatility': round(random.uniform(0.6, 1.0), 2),
                'volatility_percentile': round(random.uniform(0.3, 0.9), 2),
                'realized_volatility': round(random.uniform(0.5, 1.1), 2),
                'implied_volatility': round(random.uniform(0.6, 1.3), 2),
                'volatility_trend': random.choice(['increasing', 'decreasing', 'stable']),
                'last_updated': datetime.now().isoformat()
            }
            
            return volatility_data
            
        except Exception as e:
            print(f"Error en análisis de volatilidad: {e}")
            return {
                'error': str(e),
                'symbol': symbol,
                'period': period
            }
    
    def get_expirations(self, date=None):
        """
        Obtiene vencimientos de derivados para una fecha
        
        Args:
            date: Fecha en formato 'YYYY-MM-DD'
            
        Returns:
            List con vencimientos
        """
        try:
            if not date:
                date = datetime.now().strftime('%Y-%m-%d')
            
            # Obtener datos de Deribit usando llamadas directas a la API
            def get_raw_deribit_data(currency):
                url = f"https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency={currency}&kind=option"
                try:
                    response = requests.get(url, timeout=10)
                    response.raise_for_status()
                    return response.json()
                except Exception as e:
                    print(f"Error obtaining {currency} data: {e}")
                    return None
            
            btc_data = get_raw_deribit_data('BTC')
            eth_data = get_raw_deribit_data('ETH')
            
            expirations = []
            
            # Procesar datos BTC
            if btc_data and 'result' in btc_data:
                for option in btc_data['result'][:10]:  # Limitar a 10 resultados
                    if 'instrument_name' in option:
                        # Extraer información del nombre del instrumento
                        parts = option['instrument_name'].split('-')
                        if len(parts) >= 4:
                            exp_date = parts[1]  # e.g., "11JUL25"
                            strike = parts[2]    # e.g., "106000"
                            option_type = parts[3]  # e.g., "C" or "P"
                            
                            expirations.append({
                                'symbol': 'BTC',
                                'instrument': option.get('instrument_name', ''),
                                'expiration_date': exp_date,
                                'strike_price': float(strike) if strike.isdigit() else 0,
                                'option_type': 'call' if option_type == 'C' else 'put',
                                'open_interest': option.get('open_interest', 0),
                                'volume': option.get('volume', 0),
                                'last_price': option.get('last', 0),
                                'mark_price': option.get('mark_price', 0),
                                'underlying_price': option.get('underlying_price', 0),
                                'mark_iv': option.get('mark_iv', 0)
                            })
            
            # Procesar datos ETH
            if eth_data and 'result' in eth_data:
                for option in eth_data['result'][:10]:  # Limitar a 10 resultados
                    if 'instrument_name' in option:
                        # Extraer información del nombre del instrumento
                        parts = option['instrument_name'].split('-')
                        if len(parts) >= 4:
                            exp_date = parts[1]  # e.g., "11JUL25"
                            strike = parts[2]    # e.g., "106000"
                            option_type = parts[3]  # e.g., "C" or "P"
                            
                            expirations.append({
                                'symbol': 'ETH',
                                'instrument': option.get('instrument_name', ''),
                                'expiration_date': exp_date,
                                'strike_price': float(strike) if strike.isdigit() else 0,
                                'option_type': 'call' if option_type == 'C' else 'put',
                                'open_interest': option.get('open_interest', 0),
                                'volume': option.get('volume', 0),
                                'last_price': option.get('last', 0),
                                'mark_price': option.get('mark_price', 0),
                                'underlying_price': option.get('underlying_price', 0),
                                'mark_iv': option.get('mark_iv', 0)
                            })
            
            return expirations
            
        except Exception as e:
            print(f"Error obteniendo vencimientos: {e}")
            traceback.print_exc()
            return []
    
    def get_deribit_options_data(self, currency='BTC'):
        """
        Obtiene datos de opciones de Deribit con fechas de vencimiento
        """
        try:
            df = get_deribit_option_data(currency)
            if df is None or df.empty:
                return {}
            
            # Obtener fechas de vencimiento únicas
            expiry_dates = sorted(df['expiration_date'].unique())
            expiry_list = [date.strftime('%Y-%m-%d') for date in expiry_dates]
            
            # Agrupar datos por fecha de vencimiento
            expiry_data = {}
            for date in expiry_dates:
                date_str = date.strftime('%Y-%m-%d')
                date_df = df[df['expiration_date'] == date]
                
                expiry_data[date_str] = {
                    'strikes': sorted(date_df['strike'].unique().tolist()),
                    'options_count': len(date_df),
                    'total_oi': int(date_df['open_interest'].sum()),
                    'total_volume': int(date_df['volume'].sum())
                }
            print(expiry_data)
            return {
                'currency': currency,
                'expiry_dates': expiry_list,
                'expiry_data': expiry_data,
                'raw_data': df.to_dict('records') if len(df) < 1000 else [],
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error obteniendo datos de opciones: {e}")
            return {}
    
    def get_derivatives_metrics(self, currency='BTC', expiry_date=None):
        """
        Obtiene métricas de derivados para una fecha específica
        """
        try:
            df = get_deribit_option_data(currency)
            if df is None or df.empty:
                return {}
            
            # Filtrar por fecha de vencimiento si se especifica
            if expiry_date:
                try:
                    target_date = pd.to_datetime(expiry_date).normalize()
                    df = df[df['expiration_date'] == target_date]
                except:
                    pass
            
            # Calcular métricas usando la función existente
            metrics = calculate_deribit_metrics(df)
            
            # Agregar datos de Binance
            binance_data = get_binance_sentiment_data(currency)
            if binance_data:
                metrics.update({
                    'binance_oi': binance_data.get('current_oi_binance', 0),
                    'oi_change_4h': binance_data.get('oi_change_4h_percent', 0)
                })
            
            # Agregar datos de funding
            funding_data = get_binance_funding_info(currency)
            if funding_data:
                next_funding_time = datetime.fromtimestamp(funding_data['next_funding_time_ms'] / 1000)
                metrics.update({
                    'funding_rate': funding_data.get('current_funding_rate', 0) * 100,  # Convert to percentage
                    'next_funding_time': next_funding_time.strftime('%H:%M:%S'),
                    'mark_price': funding_data.get('mark_price', 0)
                })
            
            # Agregar datos de precio semanal
            weekly_data = get_binance_klines(currency, '1d', 7)
            if weekly_data:
                metrics.update({
                    'week_high': weekly_data.get('week_high', 0),
                    'week_low': weekly_data.get('week_low', 0)
                })
            
            metrics['timestamp'] = datetime.now().isoformat()
            return metrics
            
        except Exception as e:
            print(f"Error obteniendo métricas de derivados: {e}")
            return {}
    
    def get_orderbook_data(self, currency='BTC', level=1):
        """
        Obtiene datos del libro de órdenes
        """
        try:
            return get_deribit_orderbook_data(currency, level)
        except Exception as e:
            print(f"Error obteniendo libro de órdenes: {e}")
            return {'bids': [], 'asks': [], 'timestamp': datetime.now().timestamp() * 1000}
    
    def get_volatility_history(self, currency='BTC', days=90):
        """
        Obtiene historial de volatilidad
        """
        try:
            df = get_deribit_dvol_history(currency, days)
            if df is None or df.empty:
                return {}
            
            # Convertir DataFrame a formato JSON-serializable
            history_data = []
            for _, row in df.iterrows():
                history_data.append({
                    'timestamp': int(row['timestamp'].timestamp() * 1000),
                    'date': row['timestamp'].strftime('%Y-%m-%d'),
                    'volatility': float(row['close']),
                    'sma_7': float(row['sma_7']) if not pd.isna(row['sma_7']) else None
                })
            
            return {
                'currency': currency,
                'days': days,
                'data': history_data,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error obteniendo historial de volatilidad: {e}")
            return {}
    
    def get_binance_metrics(self, symbol='BTC'):
        """
        Obtiene métricas de Binance (OI, Long/Short ratio, etc.)
        """
        try:
            # Obtener datos de sentimiento
            sentiment_data = get_binance_sentiment_data(symbol)
            funding_history = get_binance_funding_rate_history(symbol, 100)
            
            result = {}
            
            if sentiment_data:
                # Procesar historial de OI para gráfico
                oi_history = []
                for item in sentiment_data.get('oi_history', []):
                    oi_history.append({
                        'timestamp': int(item['timestamp']),
                        'date': datetime.fromtimestamp(int(item['timestamp'])/1000).strftime('%Y-%m-%d %H:%M'),
                        'open_interest': float(item['sumOpenInterest'])
                    })
                
                # Procesar ratio Long/Short
                ls_history = []
                for item in sentiment_data.get('long_short_ratio', []):
                    ls_history.append({
                        'timestamp': int(item['timestamp']),
                        'date': datetime.fromtimestamp(int(item['timestamp'])/1000).strftime('%Y-%m-%d %H:%M'),
                        'long_short_ratio': float(item['longShortRatio'])
                    })
                
                result.update({
                    'current_oi': sentiment_data.get('current_oi_binance', 0),
                    'oi_change_4h': sentiment_data.get('oi_change_4h_percent', 0),
                    'oi_history': oi_history[-50:],  # Últimos 50 puntos
                    'long_short_history': ls_history[-50:]  # Últimos 50 puntos
                })
            
            if funding_history:
                # Procesar historial de funding rate
                funding_chart = []
                for item in funding_history:
                    funding_chart.append({
                        'timestamp': int(item['timestamp']),
                        'date': datetime.fromtimestamp(int(item['timestamp'])/1000).strftime('%Y-%m-%d %H:%M'),
                        'funding_rate': float(item['funding_rate']) * 100  # Convert to percentage
                    })
                
                result['funding_history'] = funding_chart
            
            result['timestamp'] = datetime.now().isoformat()
            return result
            
        except Exception as e:
            print(f"Error obteniendo métricas de Binance: {e}")
            return {}
    
    def get_expiration_dates(self, currency='BTC'):
        """
        Obtiene las fechas de vencimiento disponibles para una moneda específica
        
        Args:
            currency: Moneda (BTC, ETH)
            
        Returns:
            List de fechas de vencimiento únicas
        """
        try:
            currency = currency.upper()
            
            # Obtener datos de Deribit
            def get_raw_deribit_data(curr):
                url = f"https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency={curr}&kind=option"
                try:
                    response = requests.get(url, timeout=10)
                    response.raise_for_status()
                    return response.json()
                except Exception as e:
                    print(f"Error obtaining {curr} data: {e}")
                    return None
            
            data = get_raw_deribit_data(currency)
            
            if not data or 'result' not in data:
                return {"success": False, "data": []}
            
            # Extraer fechas de vencimiento únicas
            expiration_dates = set()
            
            for option in data['result']:
                if 'instrument_name' in option:
                    parts = option['instrument_name'].split('-')
                    if len(parts) >= 2:
                        exp_date = parts[1]  # e.g., "11JUL25"
                        expiration_dates.add(exp_date)
            
            # Convertir a lista y ordenar
            sorted_dates = sorted(list(expiration_dates))
            
            return {
                "success": True,
                "data": sorted_dates,
                "currency": currency,
                "count": len(sorted_dates)
            }
            
        except Exception as e:
            print(f"Error obteniendo fechas de vencimiento para {currency}: {e}")
            traceback.print_exc()
            return {"success": False, "data": [], "error": str(e)}

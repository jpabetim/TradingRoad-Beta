import pandas as pd
import requests
import os
from datetime import datetime, timedelta

class CalendarService:
    def __init__(self):
        self.fmp_api_key = os.getenv('FMP_API_KEY')
        self.base_url = 'https://financialmodelingprep.com/api/v3'
        if not self.fmp_api_key:
            print("Warning: FMP_API_KEY not found in environment variables")
    
    def get_economic_calendar(self, start_date=None, end_date=None, countries=None):
        """
        Obtiene los eventos del calendario económico y los devuelve en un DataFrame.
        
        Args:
            start_date: Fecha de inicio en formato 'YYYY-MM-DD'. Si es None, usa la fecha actual.
            end_date: Fecha fin en formato 'YYYY-MM-DD'. Si es None, usa una semana después de start_date.
            countries: Lista de países a incluir. Si es None, usa una lista predeterminada.
            
        Returns:
            DataFrame de pandas con los eventos económicos.
        """
        try:
            # Si no se proporcionan fechas, usar fechas predeterminadas
            if not start_date:
                start_date = datetime.now().strftime('%Y-%m-%d')
            if not end_date:
                end_date = (datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=7)).strftime('%Y-%m-%d')
                
            # Convertir fechas al formato requerido por investpy
            start_date_investpy = datetime.strptime(start_date, '%Y-%m-%d').strftime('%d/%m/%Y')
            end_date_investpy = datetime.strptime(end_date, '%Y-%m-%d').strftime('%d/%m/%Y')
            
            # Si no se proporcionan países, usar una lista predeterminada
            if not countries:
                countries = [
                    'united states', 'euro zone', 'japan', 'united kingdom', 
                    'germany', 'france', 'italy', 'spain',
                    'canada', 'australia', 'new zealand', 'switzerland', 'china'
                ]
            
            # Obtener datos del calendario económico
            df = investpy.economic_calendar(
                countries=countries,
                from_date=start_date_investpy,
                to_date=end_date_investpy
            )
            
            if df.empty:
                return pd.DataFrame()
            
            # Ordenar para asegurar consistencia
            df = df.sort_values(by=['date', 'time', 'zone', 'event']).reset_index(drop=True)
            
            # Convertir formato de tiempo
            df['time'] = df['time'].replace('All Day', '00:00')
            datetime_combined = df['date'] + ' ' + df['time']
            df['datetime'] = pd.to_datetime(datetime_combined, format='%d/%m/%Y %H:%M', errors='coerce')
            df.dropna(subset=['datetime'], inplace=True)
            
            # Mapear impacto
            impact_map = {'low': 'Bajo', 'medium': 'Medio', 'high': 'Alto'}
            df['impact'] = df['importance'].map(impact_map).fillna('Bajo')
            
            # Renombrar columnas
            columnas_map = {
                'zone': 'country', 
                'event': 'event_name',
                'datetime': 'event_datetime',
                'impact': 'impact',
                'actual': 'actual_value',
                'forecast': 'forecast_value',
                'previous': 'previous_value'
            }
            df.rename(columns=columnas_map, inplace=True)
            
            # Seleccionar y ordenar columnas
            columnas_finales = [
                'event_datetime', 'country', 'event_name', 'impact',
                'actual_value', 'forecast_value', 'previous_value'
            ]
            
            for col in columnas_finales:
                if col not in df.columns:
                    df[col] = ''
                    
            df = df[columnas_finales]
            df.fillna('', inplace=True)
            
            # Ordenar por fecha y hora
            df = df.sort_values(by='event_datetime', ascending=True)
            
            return df
            
        except Exception as e:
            print(f"Error al obtener datos del calendario económico: {e}")
            # En caso de error, devolver datos de ejemplo
            return self.get_mock_calendar_data(start_date, end_date)
    
    def get_mock_calendar_data(self, start_date=None, end_date=None):
        """
        Genera datos de ejemplo para el calendario económico cuando la API falla.
        """
        if not start_date:
            start_date = datetime.now().strftime('%Y-%m-%d')
        if not end_date:
            end_date = (datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=7)).strftime('%Y-%m-%d')
        
        # Crear fechas entre start_date y end_date
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        date_list = [start + timedelta(days=x) for x in range((end-start).days + 1)]
        
        # Datos de ejemplo
        mock_data = []
        events = [
            ("PIB (Trimestral)", "united states", "Alto"),
            ("Tasa de Desempleo", "united states", "Alto"),
            ("IPC (Mensual)", "euro zone", "Alto"),
            ("Decisión de Tipos de Interés", "united kingdom", "Alto"),
            ("Balanza Comercial", "japan", "Medio"),
            ("Ventas Minoristas", "germany", "Medio"),
            ("PMI Manufacturero", "france", "Medio"),
            ("PMI Servicios", "italy", "Bajo"),
            ("Producción Industrial", "spain", "Bajo"),
            ("Confianza del Consumidor", "canada", "Bajo")
        ]
        
        # Crear eventos para cada día
        for i, date in enumerate(date_list):
            # Generar entre 1 y 3 eventos por día
            num_events = min(3, len(events))
            for j in range(num_events):
                event_index = (i + j) % len(events)
                event_name, country, impact = events[event_index]
                
                # Generar hora aleatoria
                hour = (i * 4 + j * 2) % 24
                minute = (i * 10 + j * 5) % 60
                event_datetime = date.replace(hour=hour, minute=minute)
                
                # Generar valores aleatorios
                previous = format(3.5 + (i * 0.1) % 2, '.1f')
                forecast = format(3.7 + (i * 0.15) % 1.5, '.1f')
                actual = format(3.8 + (i * 0.2) % 1.8, '.1f')
                
                mock_data.append({
                    'event_datetime': event_datetime,
                    'country': country,
                    'event_name': event_name,
                    'impact': impact,
                    'actual_value': actual,
                    'forecast_value': forecast,
                    'previous_value': previous
                })
        
        return pd.DataFrame(mock_data)

    def get_events(self, date=None, country='US'):
        """
        Obtiene eventos del calendario económico para una fecha específica
        
        Args:
            date: Fecha en formato 'YYYY-MM-DD'
            country: País para filtrar eventos
            
        Returns:
            List de diccionarios con eventos
        """
        try:
            if not date:
                date = datetime.now().strftime('%Y-%m-%d')
            
            # Usar el método existente para obtener datos
            # Agregar un día para evitar el error de fecha
            start_date = datetime.strptime(date, '%Y-%m-%d')
            end_date = start_date + timedelta(days=1)
            end_date_str = end_date.strftime('%Y-%m-%d')
            
            df = self.get_economic_calendar(date, end_date_str, [country.lower()])
            
            if df.empty:
                # Devolver datos mock si no hay datos reales
                return self._get_mock_calendar_events(date, country)
            
            # Convertir DataFrame a lista de diccionarios
            events = []
            for _, row in df.iterrows():
                events.append({
                    'time': row.get('event_datetime', ''),
                    'country': row.get('country', ''),
                    'event': row.get('event_name', ''),
                    'impact': row.get('impact', ''),
                    'forecast': row.get('forecast_value', ''),
                    'previous': row.get('previous_value', ''),
                    'actual': row.get('actual_value', '')
                })
            
            return events
            
        except Exception as e:
            print(f"Error obteniendo eventos del calendario: {e}")
            return []
    
    def get_week_events(self, week_start=None, country='US'):
        """
        Obtiene eventos del calendario económico para una semana
        
        Args:
            week_start: Fecha de inicio de la semana en formato 'YYYY-MM-DD'
            country: País para filtrar eventos
            
        Returns:
            List de diccionarios con eventos
        """
        try:
            if not week_start:
                week_start = datetime.now().strftime('%Y-%m-%d')
            
            # Calcular fin de semana
            start_date = datetime.strptime(week_start, '%Y-%m-%d')
            end_date = start_date + timedelta(days=6)
            end_date_str = end_date.strftime('%Y-%m-%d')
            
            # Usar el método existente para obtener datos
            df = self.get_economic_calendar(week_start, end_date_str, [country.lower()])
            
            if df.empty:
                return []
            
            # Convertir DataFrame a lista de diccionarios
            events = []
            for _, row in df.iterrows():
                events.append({
                    'time': row.get('event_datetime', ''),
                    'country': row.get('country', ''),
                    'event': row.get('event_name', ''),
                    'impact': row.get('impact', ''),
                    'forecast': row.get('forecast_value', ''),
                    'previous': row.get('previous_value', ''),
                    'actual': row.get('actual_value', '')
                })
            
            return events
            
        except Exception as e:
            print(f"Error obteniendo eventos de la semana: {e}")
            return []
    
    def _get_mock_calendar_events(self, date, country):
        """
        Devuelve eventos mock del calendario económico
        """
        from datetime import datetime
        import random
        
        # Eventos mock basados en eventos reales típicos
        events_templates = [
            {
                'event': 'PIB (Trimestral)',
                'impact': 'Alto',
                'country': 'united states'
            },
            {
                'event': 'Tasa de Desempleo',
                'impact': 'Alto', 
                'country': 'united states'
            },
            {
                'event': 'IPC (Mensual)',
                'impact': 'Alto',
                'country': 'euro zone'
            },
            {
                'event': 'Decisión de Tasas de Interés',
                'impact': 'Alto',
                'country': 'united states'
            },
            {
                'event': 'Ventas al Menudeo',
                'impact': 'Medio',
                'country': 'united states'
            },
            {
                'event': 'Índice de Precios al Productor',
                'impact': 'Medio',
                'country': 'united states'
            }
        ]
        
        mock_events = []
        base_date = datetime.strptime(date, '%Y-%m-%d')
        
        for i, template in enumerate(events_templates[:3]):  # Limitar a 3 eventos
            event_time = base_date.replace(hour=8 + i*2, minute=5*i)
            
            mock_events.append({
                'time': event_time.strftime('%a, %d %b %Y %H:%M:%S GMT'),
                'country': template['country'],
                'event': template['event'],
                'impact': template['impact'],
                'forecast': str(round(random.uniform(3.5, 4.0), 1)),
                'previous': str(round(random.uniform(3.0, 3.8), 1)),
                'actual': str(round(random.uniform(3.5, 4.0), 1))
            })
        
        return mock_events

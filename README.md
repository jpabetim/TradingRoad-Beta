# TradingRoad Backend (Sin Análisis)

Backend Flask limpio para TradingRoad con solo los módulos esenciales de trading, sin funcionalidades de análisis AI.

## Características

### ✅ Módulos Incluidos
- **Trading** - Datos de mercado en tiempo real
- **Vencimientos** - Análisis de volatilidad y vencimientos
- **Noticias** - Noticias financieras
- **Calendario** - Calendario económico
- **Configuración** - Configuración de la aplicación

### ❌ Módulos Excluidos
- ~~Análisis AI~~ (eliminado completamente)
- ~~Gemini AI integration~~
- ~~Chat AI~~
- ~~Análisis técnico automático~~

## Instalación

1. **Crear entorno virtual:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # En macOS/Linux
   # o
   .venv\Scripts\activate     # En Windows
   ```

2. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configurar variables de entorno:**
   - Copia `.env.local.example` a `.env.local`
   - Configura tus claves API en `.env.local`

4. **Ejecutar el servidor:**
   ```bash
   python app.py
   ```

## Endpoints API

### Mercado
- `GET /api/market/data/<symbol>` - Datos de mercado
- `GET /api/market/ticker/<symbol>` - Datos de ticker
- `GET /api/volatility/<symbol>` - Datos de volatilidad

### Noticias
- `GET /api/news` - Noticias financieras

### Calendario
- `GET /api/calendar` - Eventos del calendario económico

### Configuración
- `GET /api/config` - Obtener configuración
- `POST /api/config` - Actualizar configuración

### Salud
- `GET /api/health` - Estado del servidor

## Exchanges Soportados

- Binance
- Coinbase
- Kraken
- KuCoin
- Bybit
- BingX

## Configuración

El servidor se ejecuta por defecto en:
- **Puerto:** 5007
- **URL Local:** http://localhost:5007
- **Debug:** Activado en desarrollo

## Estructura del Proyecto

```
TradingRoad-Recuperado/
├── app.py                 # Aplicación Flask principal
├── requirements.txt       # Dependencias Python
├── .env.local            # Variables de entorno
├── config/               # Configuración
├── modules/              # Módulos de negocio
│   ├── market/          # Servicios de mercado
│   ├── news/            # Servicios de noticias
│   └── calendar/        # Servicios de calendario
├── templates/           # Plantillas HTML
└── static/             # Archivos estáticos
```

## Desarrollo

Este backend está diseñado para ser usado independientemente, sin necesidad de frontend React. Incluye todas las funcionalidades esenciales de trading sin la complejidad del análisis AI.

Para desarrollo, el servidor se ejecuta en modo debug y recarga automáticamente los cambios.

#!/bin/bash

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Iniciando TradingRoad Backend (Sin Análisis)${NC}"
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "app.py" ]; then
    echo -e "${RED}❌ Error: No se encontró app.py. Asegúrate de estar en el directorio raíz del proyecto.${NC}"
    exit 1
fi

# Verificar que existe el archivo .env.local
if [ ! -f ".env.local" ]; then
    echo -e "${YELLOW}⚠️  Advertencia: No se encontró .env.local.${NC}"
    echo -e "${YELLOW}📝 Por favor, configura tus claves API en .env.local antes de continuar.${NC}"
    echo ""
fi

# Verificar que las dependencias están instaladas
echo -e "${BLUE}📦 Verificando dependencias...${NC}"

if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}🐍 Creando entorno virtual de Python...${NC}"
    python3 -m venv .venv
fi

echo -e "${YELLOW}🔧 Activando entorno virtual y instalando dependencias...${NC}"
source .venv/bin/activate
pip install -r requirements.txt

echo ""
echo -e "${GREEN}✅ Dependencias instaladas correctamente${NC}"
echo ""

# Iniciar el backend Flask
echo -e "${BLUE}🖥️  Iniciando backend Flask...${NC}"
python app.py

#!/bin/bash

# ═══════════════════════════════════════════════════════════════
# TETRA Nextion Display v4.1 - Instalador
# EA8DLF 2026 — https://github.com/EA8DLF/Tetra_JCT_Nextion_Display
# ═══════════════════════════════════════════════════════════════

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_NAME="tetra_nextion.py"
SERVICE_NAME="tetra-nextion"

clear

echo -e "${BLUE}${BOLD}"
echo " ╔══════════════════════════════════════════════════════════╗"
echo " ║     TETRA Nextion Display v4.1 - EA8DLF                 ║"
echo " ║     Instalador automático                                ║"
echo " ║     Compatible: 320×240 | 800×480                       ║"
echo " ╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# ── Verificar que no se ejecuta como root ─────────────────────
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}No ejecutar como root. Usar: bash install.sh${NC}"
    exit 1
fi

CURRENT_USER=$(whoami)
CURRENT_HOME=$(eval echo ~$CURRENT_USER)

echo -e "${CYAN}Usuario: ${BOLD}$CURRENT_USER${NC}"
echo -e "${CYAN}Home:    ${BOLD}$CURRENT_HOME${NC}"
echo ""

# ── Detectar modelo de Raspberry Pi ──────────────────────────
PI_MODEL=""
PI5=false

if [ -f /proc/device-tree/model ]; then
    PI_MODEL=$(cat /proc/device-tree/model 2>/dev/null | tr -d '\0')
    if echo "$PI_MODEL" | grep -q "Pi 5"; then
        PI5=true
        echo -e "${CYAN}Modelo: ${BOLD}$PI_MODEL${NC}"
        echo -e "${YELLOW}⚠️  Raspberry Pi 5 detectada — configuración UART especial${NC}"
    else
        echo -e "${CYAN}Modelo: ${BOLD}$PI_MODEL${NC}"
    fi
fi

echo ""

# ── Verificar dependencias ────────────────────────────────────
echo -e "${BOLD}[1/5] Verificando dependencias...${NC}"

if ! command -v python3 &>/dev/null; then
    echo -e "${RED}❌ Python3 no encontrado. Instalar con: sudo apt install python3${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python3: $(python3 --version)${NC}"

if ! command -v journalctl &>/dev/null; then
    echo -e "${YELLOW}⚠️  journalctl no disponible — lectura de SDS texto limitada${NC}"
else
    echo -e "${GREEN}✅ journalctl disponible${NC}"
fi

# ── Instalar librerías Python ─────────────────────────────────
echo ""
echo -e "${BOLD}[2/5] Instalando librerías Python...${NC}"

pip3 install pyserial requests --break-system-packages 2>/dev/null || \
pip install pyserial requests --break-system-packages 2>/dev/null || \
pip3 install pyserial requests 2>/dev/null || \
pip install pyserial requests 2>/dev/null || \
{ echo -e "${RED}❌ Error instalando librerías. Instalar manualmente: pip install pyserial requests${NC}"; exit 1; }

echo -e "${GREEN}✅ pyserial y requests instalados${NC}"

# ── Detectar y configurar UART ────────────────────────────────
echo ""
echo -e "${BOLD}[3/5] Configurando UART...${NC}"

SERIAL_PORT=""
CONFIG_FILE=""
REBOOT_NEEDED=false

# Detectar archivo de configuración del bootloader
if [ -f /boot/firmware/config.txt ]; then
    CONFIG_FILE="/boot/firmware/config.txt"
elif [ -f /boot/config.txt ]; then
    CONFIG_FILE="/boot/config.txt"
fi

if [ "$PI5" = true ]; then
    # ── Pi 5: ttyAMA0 + uart0-pi5 + quitar console=serial0 ──

    # 1. Configurar overlay UART
    if [ -n "$CONFIG_FILE" ]; then
        if ! grep -q "uart0-pi5" "$CONFIG_FILE" 2>/dev/null; then
            echo -e "${YELLOW}   Configurando UART en $CONFIG_FILE...${NC}"
            sudo bash -c "echo '' >> $CONFIG_FILE"
            sudo bash -c "echo '# TETRA Nextion Display - UART GPIO 14/15' >> $CONFIG_FILE"
            sudo bash -c "echo 'dtoverlay=uart0-pi5' >> $CONFIG_FILE"
            sudo bash -c "echo 'dtoverlay=disable-bt' >> $CONFIG_FILE"
            echo -e "${GREEN}✅ dtoverlay=uart0-pi5 configurado${NC}"
            REBOOT_NEEDED=true
        else
            echo -e "${GREEN}✅ dtoverlay=uart0-pi5 ya configurado${NC}"
        fi
    fi

    # 2. Eliminar console=serial0 de cmdline.txt (bloquea la pantalla)
    CMDLINE_FILE=""
    if [ -f /boot/firmware/cmdline.txt ]; then
        CMDLINE_FILE="/boot/firmware/cmdline.txt"
    elif [ -f /boot/cmdline.txt ]; then
        CMDLINE_FILE="/boot/cmdline.txt"
    fi

    if [ -n "$CMDLINE_FILE" ]; then
        if grep -q "console=serial0" "$CMDLINE_FILE" 2>/dev/null; then
            echo -e "${YELLOW}   Eliminando console=serial0 de $CMDLINE_FILE...${NC}"
            sudo sed -i 's/console=serial0,[0-9]* //g' "$CMDLINE_FILE"
            echo -e "${GREEN}✅ console=serial0 eliminado — la pantalla puede usar el UART${NC}"
            REBOOT_NEEDED=true
        else
            echo -e "${GREEN}✅ cmdline.txt ya correcto${NC}"
        fi
    fi

    # 3. Puerto serie Pi 5
    SERIAL_PORT="/dev/ttyAMA0"
    echo -e "${GREEN}✅ Puerto serie Pi 5: /dev/ttyAMA0${NC}"

else
    # ── Pi 3/4 ────────────────────────────────────────────────
    if [ -e /dev/serial0 ]; then
        SERIAL_PORT="/dev/serial0"
        echo -e "${GREEN}✅ Puerto detectado: /dev/serial0${NC}"
    elif [ -e /dev/ttyAMA0 ]; then
        SERIAL_PORT="/dev/ttyAMA0"
        echo -e "${GREEN}✅ Puerto detectado: /dev/ttyAMA0${NC}"
    elif [ -e /dev/ttyS0 ]; then
        SERIAL_PORT="/dev/ttyS0"
        echo -e "${YELLOW}⚠️  Puerto detectado: /dev/ttyS0${NC}"
    fi

    if [ -n "$CONFIG_FILE" ]; then
        if ! grep -q "enable_uart=1" "$CONFIG_FILE" 2>/dev/null; then
            echo -e "${YELLOW}   Configurando UART en $CONFIG_FILE...${NC}"
            sudo bash -c "echo '' >> $CONFIG_FILE"
            sudo bash -c "echo '# TETRA Nextion Display - UART GPIO 14/15' >> $CONFIG_FILE"
            sudo bash -c "echo 'enable_uart=1' >> $CONFIG_FILE"
            sudo bash -c "echo 'dtoverlay=disable-bt' >> $CONFIG_FILE"
            echo -e "${GREEN}✅ UART configurado${NC}"
            REBOOT_NEEDED=true
        else
            echo -e "${GREEN}✅ UART ya configurado${NC}"
        fi
    fi
fi

if [ -z "$SERIAL_PORT" ]; then
    SERIAL_PORT="/dev/serial0"
    echo -e "${YELLOW}⚠️  Puerto no detectado. Usando /dev/serial0 por defecto${NC}"
fi

# Añadir usuario al grupo dialout
if ! groups "$CURRENT_USER" | grep -q dialout; then
    sudo usermod -a -G dialout "$CURRENT_USER"
    echo -e "${GREEN}✅ Usuario añadido al grupo dialout${NC}"
else
    echo -e "${GREEN}✅ Usuario ya en grupo dialout${NC}"
fi

# ── Recopilar configuración TETRA ────────────────────────────
echo ""
echo -e "${BOLD}[4/5] Configuración de la red TETRA...${NC}"
echo -e "${CYAN}Pulsa ENTER para usar el valor por defecto [entre corchetes]${NC}"
echo ""

echo -e "${BOLD}¿Tienes TetraPack Monitor (bluestation-bs) instalado? [S/n]:${NC}"
read -p "  " INPUT_MONITOR_YN
INPUT_MONITOR_YN="${INPUT_MONITOR_YN:-S}"

if [[ "$INPUT_MONITOR_YN" =~ ^[Ss]$ ]]; then
    MONITOR_URL="http://localhost:5000"
    echo -e "${GREEN}  ✅ Monitor: $MONITOR_URL${NC}"
else
    MONITOR_URL=""
    echo -e "${YELLOW}  ⚠️  Sin monitor — el script leerá el journal directamente${NC}"
fi

echo ""
read -p "  Frecuencia TX [431.000MHz]: " INPUT_TX;  DEFAULT_TX="${INPUT_TX:-431.000MHz}"
read -p "  Frecuencia RX [438.600MHz]: " INPUT_RX;  DEFAULT_RX="${INPUT_RX:-438.600MHz}"
echo ""
read -p "  MCC de tu red TETRA [001]: " INPUT_MCC;  DEFAULT_MCC="${INPUT_MCC:-001}"
read -p "  MNC de tu red TETRA [001]: " INPUT_MNC;  DEFAULT_MNC="${INPUT_MNC:-001}"
echo ""
read -p "  ISSI del servidor de emergencias [214112]: " INPUT_EMERG
EMERGENCY_ISSI="${INPUT_EMERG:-214112}"

echo ""
echo -e "${BOLD}Tiempos de pantalla (segundos) — ENTER para valores por defecto:${NC}"
read -p "  Tiempo mostrando llamada de voz [20]: " INPUT_CALL;      CALL_MIN_DISPLAY="${INPUT_CALL:-20}"
read -p "  Tiempo mostrando SDS texto [15]: "      INPUT_SDS;       SDS_DISPLAY="${INPUT_SDS:-15}"
read -p "  Tiempo mostrando emergencia [25]: "     INPUT_EMERG_DISP; EMERGENCY_DISPLAY="${INPUT_EMERG_DISP:-25}"

# ── Instalar el script ────────────────────────────────────────
echo ""
echo -e "${BOLD}[5/5] Instalando script...${NC}"

DEST_SCRIPT="$CURRENT_HOME/$SCRIPT_NAME"
cp "$INSTALL_DIR/$SCRIPT_NAME" "$DEST_SCRIPT"

sed -i "s|MONITOR_URL    = \"http://localhost:5000\"|MONITOR_URL    = \"$MONITOR_URL\"|" "$DEST_SCRIPT"
sed -i "s|DEFAULT_TX     = \"431.000MHz\"|DEFAULT_TX     = \"$DEFAULT_TX\"|"             "$DEST_SCRIPT"
sed -i "s|DEFAULT_RX     = \"438.600MHz\"|DEFAULT_RX     = \"$DEFAULT_RX\"|"             "$DEST_SCRIPT"
sed -i "s|DEFAULT_MCC    = \"001\"|DEFAULT_MCC    = \"$DEFAULT_MCC\"|"                   "$DEST_SCRIPT"
sed -i "s|DEFAULT_MNC    = \"001\"|DEFAULT_MNC    = \"$DEFAULT_MNC\"|"                   "$DEST_SCRIPT"
sed -i "s|EMERGENCY_ISSI = \"214112\"|EMERGENCY_ISSI = \"$EMERGENCY_ISSI\"|"             "$DEST_SCRIPT"
sed -i "s|SERIAL_PORT    = \"/dev/serial0\"|SERIAL_PORT    = \"$SERIAL_PORT\"|"          "$DEST_SCRIPT"
sed -i "s|CALL_MIN_DISPLAY  = 20|CALL_MIN_DISPLAY  = $CALL_MIN_DISPLAY|"                 "$DEST_SCRIPT"
sed -i "s|SDS_DISPLAY       = 15|SDS_DISPLAY       = $SDS_DISPLAY|"                     "$DEST_SCRIPT"
sed -i "s|EMERGENCY_DISPLAY = 25|EMERGENCY_DISPLAY = $EMERGENCY_DISPLAY|"               "$DEST_SCRIPT"

echo -e "${GREEN}✅ Script instalado: $DEST_SCRIPT${NC}"
echo -e "${GREEN}✅ Puerto configurado: $SERIAL_PORT${NC}"

# ── Crear servicio systemd ────────────────────────────────────
echo ""
echo -e "${BOLD}¿Crear servicio systemd para arranque automático? [S/n]:${NC}"
read -p "  " INPUT_SERVICE
INPUT_SERVICE="${INPUT_SERVICE:-S}"

if [[ "$INPUT_SERVICE" =~ ^[Ss]$ ]]; then
    SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"

    sudo tee "$SERVICE_FILE" > /dev/null << SERVICEEOF
[Unit]
Description=TETRA Nextion Display v4.1 - EA8DLF
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$CURRENT_HOME
ExecStart=/usr/bin/python3 $DEST_SCRIPT
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICEEOF

    sudo systemctl daemon-reload
    sudo systemctl enable "$SERVICE_NAME.service"
    echo -e "${GREEN}✅ Servicio systemd creado y habilitado${NC}"

    if [ "$REBOOT_NEEDED" = false ]; then
        echo ""
        echo -e "${BOLD}¿Iniciar el servicio ahora? [S/n]:${NC}"
        read -p "  " INPUT_START
        INPUT_START="${INPUT_START:-S}"
        if [[ "$INPUT_START" =~ ^[Ss]$ ]]; then
            sudo systemctl start "$SERVICE_NAME.service"
            sleep 2
            if systemctl is-active --quiet "$SERVICE_NAME.service"; then
                echo -e "${GREEN}✅ Servicio iniciado correctamente${NC}"
            else
                echo -e "${YELLOW}⚠️  Revisar logs: journalctl -u $SERVICE_NAME -f${NC}"
            fi
        fi
    fi
fi

# ── Resumen final ─────────────────────────────────────────────
echo ""
echo -e "${BLUE}${BOLD}"
echo " ╔══════════════════════════════════════════════════════════╗"
echo " ║     Instalación completada ✅                            ║"
echo " ╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo -e "  Script:    ${BOLD}$DEST_SCRIPT${NC}"
echo -e "  Puerto:    ${BOLD}$SERIAL_PORT${NC}"
echo -e "  TX/RX:     ${BOLD}$DEFAULT_TX / $DEFAULT_RX${NC}"
echo -e "  MCC/MNC:   ${BOLD}$DEFAULT_MCC / $DEFAULT_MNC${NC}"
echo -e "  Monitor:   ${BOLD}${MONITOR_URL:-Sin monitor}${NC}"
echo ""

if [ "$REBOOT_NEEDED" = true ]; then
    echo -e "${YELLOW}  ⚠️  REINICIO NECESARIO para activar el UART${NC}"
    echo -e "${YELLOW}  Ejecutar: sudo reboot${NC}"
    echo -e "${YELLOW}  Tras el reinicio el servicio arrancará automáticamente.${NC}"
else
    echo -e "  Comandos útiles:"
    echo -e "  ${CYAN}sudo systemctl status $SERVICE_NAME${NC}"
    echo -e "  ${CYAN}journalctl -u $SERVICE_NAME -f${NC}"
    echo -e "  ${CYAN}python3 $DEST_SCRIPT${NC}  (manual)"
fi

echo ""

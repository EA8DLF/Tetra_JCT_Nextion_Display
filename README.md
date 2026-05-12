# TETRA Nextion Display v3.3

Monitor de red TETRA en tiempo real para pantalla TJC/Nextion conectada a Raspberry Pi mediante UART.

Desarrollado por **EA8DLF** · 2026

---

## Características

- 📻 **Voz** — Indicativo, nombre, bandera del país, TG activo e historial de llamadas
- 📨 **SDS texto** — Mensajes de texto recibidos por terminales locales en pantalla dedicada
- 🆘 **Emergencias** — Alerta SOS con GPS, geocodificación inversa (calle y ciudad via Nominatim)
- 📊 **Standby** — Terminales activos con RSSI, TG y estado Online/Offline en color
- 🌍 **Banderas** — Detecta el país automáticamente por prefijo de indicativo (30+ países)
- 🔄 **Compatible** con TetraPack Monitor (bluestation-bs) y modo sin monitor

## Hardware necesario

| Componente | Especificaciones |
|---|---|
| Raspberry Pi | 3B+ / 4B / **5** (cualquier modelo con GPIO 40 pines) |
| Pantalla UART | TJC o Nextion **320×240** px (ver lista de modelos) |
| Cables | 4× Dupont hembra-hembra |

## Pantallas compatibles

El HMI está diseñado para resolución **320×240 px**. Compatibles directamente sin rediseño:

| Fabricante | Modelos | Tamaño |
|---|---|---|
| **TJC** (China) | TJC3224T022, TJC3224T028 | 2.2" / 2.8" |
| **Nextion Basic** | NX3224T022, NX3224T024, NX3224T028 | 2.2" / 2.4" / 2.8" |
| **Nextion Enhanced** | NX3224K022, NX3224K024, NX3224K028 | 2.2" / 2.4" / 2.8" |

> ⚠️ Pantallas con otras resoluciones (3.2", 4.3", 5"...) requieren rediseñar el HMI.

## Conexionado GPIO

Mismos pines en todos los modelos de Raspberry Pi:

```
Pantalla TJC/Nextion    Raspberry Pi GPIO
────────────────────    ─────────────────────────
VCC (5V)           →   Pin 2  (5V)
GND                →   Pin 6  (GND)
TX (pantalla)      →   Pin 10 (GPIO15 / RX)
RX (pantalla)      →   Pin 8  (GPIO14 / TX)
```

## Instalación

```bash
git clone https://github.com/ea8dlf/tetra-nextion
cd tetra-nextion
bash install.sh
```

El instalador:
- Detecta automáticamente el modelo de Raspberry Pi (incluida Pi 5)
- Configura el UART en `/boot/firmware/config.txt` o `/boot/config.txt`
- Detecta el puerto serie disponible
- Pregunta los datos de tu red TETRA (TX/RX, MCC, MNC, ISSI emergencias)
- Instala el script y crea el servicio systemd

## Raspberry Pi 5 — Nota importante

En la Pi 5 el UART del GPIO no está activo por defecto. El instalador lo configura automáticamente añadiendo a `/boot/firmware/config.txt`:

```
dtoverlay=uart0-pi5
dtoverlay=disable-bt
```

Tras la instalación se pedirá **reiniciar** para activar el UART.

## Páginas de pantalla

| Página | Estado | Contenido |
|---|---|---|
| page0 | STANDBY | Reloj, fecha, IP, temperatura, terminales activos |
| page1 | VOZ | Indicativo, nombre, bandera, historial de llamadas |
| page3 | EMERGENCIA | SOS, GPS, dirección, ciudad (25 segundos) |
| page4 | SDS TEXTO | Mensaje de texto en hasta 5 líneas (15 segundos) |

## Requisitos

- Python 3.7+
- `pip install pyserial requests`
- systemd (para lectura de texto SDS del journal)
- TetraPack Monitor con bluestation-bs (opcional pero recomendado)

## Configuración

Todos los parámetros se configuran durante la instalación. Para cambiarlos después, editar la sección `─── AJUSTES ───` en `tetra_nextion.py`:

```python
MONITOR_URL    = "http://localhost:5000"  # Vacío si no hay monitor
SERIAL_PORT    = "/dev/serial0"           # /dev/ttyAMA0 en Pi 5
DEFAULT_TX     = "431.000MHz"
DEFAULT_RX     = "438.600MHz"
DEFAULT_MCC    = "001"
DEFAULT_MNC    = "001"
EMERGENCY_ISSI = "214112"
```

## Comandos útiles

```bash
# Estado del servicio
sudo systemctl status tetra-nextion

# Ver logs en tiempo real
journalctl -u tetra-nextion -f

# Reiniciar el servicio
sudo systemctl restart tetra-nextion

# Ejecutar manualmente (depuración)
python3 ~/tetra_nextion.py
```

## Estructura del repositorio

```
tetra-nextion/
├── tetra_nextion.py   # Script principal
├── install.sh         # Instalador interactivo
└── README.md          # Este archivo
```

## Licencia

Distribución libre para radioaficionados y operadores TETRA. Uso no comercial.

---

*73 de EA8DLF — Gran Canaria, España*

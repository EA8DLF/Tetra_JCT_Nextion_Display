# TETRA Nextion Display v4.0

Monitor de red TETRA en tiempo real para pantalla TJC/Nextion conectada a Raspberry Pi mediante UART.

Desarrollado por **EA8DLF** · 2026

---

## Novedades v4.0

- 🖥️ **Soporte pantalla 800×480** — compatible con TJC8048X543 (5") sin modificar el script
- 🚦 **Estado de terminales mejorado** — badge Online/Offline independiente con color verde/rojo
- 📋 **Último tráfico en standby** — muestra las 2 últimas llamadas de voz en page0
- 🏷️ **Labels incluidos en campos** — IP, temperatura y voltaje muestran su etiqueta
- 🔄 **Un solo script para ambas pantallas** — 320×240 y 800×480 comparten el mismo script

---

## Características

- 📻 **Voz** — Indicativo, nombre, bandera del país, TG activo e historial de llamadas
- 📨 **SDS texto** — Mensajes de texto recibidos por terminales locales en pantalla dedicada
- 🆘 **Emergencias** — Alerta SOS con sirenas animadas, GPS y geocodificación inversa (Nominatim)
- 📊 **Standby** — Terminales activos con TG, estado Online/Offline y último tráfico de voz
- 🌍 **Banderas** — Detecta el país automáticamente por prefijo de indicativo (30+ países)
- 🔄 **Compatible** con TetraPack Monitor (bluestation-bs) y modo sin monitor

---

## Hardware necesario

| Componente | Especificaciones |
|---|---|
| Raspberry Pi | 3B+ / 4B / **5** (cualquier modelo con GPIO 40 pines) |
| Pantalla UART | TJC/Nextion **320×240** px o **800×480** px (ver lista) |
| Cables | 4× Dupont hembra-hembra |

---

## Pantallas compatibles

### 320×240 px — HMI original (v1)

| Fabricante | Modelos | Tamaño |
|---|---|---|
| **TJC** (China) | TJC3224T022, TJC3224T028 | 2.2" / 2.8" |
| **Nextion Basic** | NX3224T022, NX3224T024, NX3224T028 | 2.2" / 2.4" / 2.8" |
| **Nextion Enhanced** | NX3224K022, NX3224K024, NX3224K028 | 2.2" / 2.4" / 2.8" |

### 800×480 px — HMI grande (v2)

| Fabricante | Modelos | Tamaño |
|---|---|---|
| **TJC Enhanced** | **TJC8048X543** | **5"** |

> Cada resolución requiere su propio archivo `.tft`. El script Python es el mismo para ambas.

---

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

---

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

---

## Raspberry Pi 5 — Nota importante

En la Pi 5 el UART del GPIO no está activo por defecto. El instalador lo configura automáticamente añadiendo a `/boot/firmware/config.txt`:

```
dtoverlay=uart0-pi5
dtoverlay=disable-bt
```

Tras la instalación se pedirá **reiniciar** para activar el UART.

---

## Páginas de pantalla

| Página | Estado | Contenido |
|---|---|---|
| page0 | STANDBY | Reloj, fecha, IP, temperatura, terminales con badge Online/Offline, último tráfico |
| page1 | VOZ | Indicativo, nombre, bandera, TG, historial de 4 llamadas, frecuencias |
| page3 | EMERGENCIA | SOS, sirenas animadas, GPS, dirección, ciudad (25 segundos) |
| page4 | SDS TEXTO | Mensaje de texto en hasta 5 líneas (15 segundos) |

---

## Componentes HMI — Nuevos en v4.0

### page0 — Standby

| Componente | Descripción |
|---|---|
| `t_st1` / `t_st2` / `t_st3` | Badge de estado Online/Offline con color para cada terminal |
| `t_hist1` / `t_hist2` | Último tráfico de voz: indicativo, TG y hora |

### page3 — Emergencia

| Componente | Descripción |
|---|---|
| `p_luz_i` / `p_luz_d` | Barras de luces policiales animadas que alternan |
| `tm0` | Timer interno que controla el destello de las luces |

---

## Requisitos

- Python 3.7+
- `pip install pyserial requests`
- systemd (para lectura de texto SDS del journal)
- TetraPack Monitor con bluestation-bs (opcional pero recomendado)

---

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

---

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

---

## Estructura del repositorio

```
tetra-nextion/
├── tetra_nextion.py              # Script principal (v4.0)
├── install.sh                    # Instalador interactivo
├── TETRA_V2.tft                  # HMI compilado 320×240 px
├── TETRA_V2_800x480.tft          # HMI compilado 800×480 px
└── README.md                     # Este archivo
```

---

## Licencia

Distribución libre para radioaficionados y operadores TETRA. Uso no comercial.

---

*73 de EA8DLF — Gran Canaria, España*

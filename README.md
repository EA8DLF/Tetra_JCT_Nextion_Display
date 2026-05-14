# TETRA Nextion Display v4.1

Monitor de red TETRA en tiempo real para pantalla TJC/Nextion conectada a Raspberry Pi mediante UART.

Desarrollado por **EA8DLF** · 2026

---

## Novedades v4.1

- 🔀 **Soporte dual-pantalla sin conflictos** — un solo script para 320×240 y 800×480 simultáneamente
- 🏷️ **Componentes 800×480 renombrados con sufijo `g`** — elimina colisiones de nombres entre HMIs
- 🍓 **Corrección Raspberry Pi 5** — puerto UART correcto (`/dev/ttyAMA0`) y eliminación automática de consola serie
- 🔗 **URL repositorio corregida** — `https://github.com/EA8DLF/Tetra_JCT_Nextion_Display`

## Novedades v4.0

- 🖥️ **Soporte pantalla 800×480** — compatible con TJC8048X543 (5")
- 🚦 **Estado de terminales mejorado** — badge Online/Offline con color verde/rojo
- 📋 **Último tráfico en standby** — 2 últimas llamadas de voz en page0
- 🏷️ **Labels incluidos en campos** — IP, temperatura y voltaje con etiqueta

---

## Características

- 📻 **Voz** — Indicativo, nombre, bandera del país, TG activo e historial de llamadas
- 📨 **SDS texto** — Mensajes de texto recibidos por terminales locales
- 🆘 **Emergencias** — Alerta SOS con sirenas animadas, GPS y geocodificación inversa (Nominatim)
- 📊 **Standby** — Terminales activos con TG, estado Online/Offline y último tráfico
- 🌍 **Banderas** — Detecta el país automáticamente por prefijo de indicativo (30+ países)
- 🔄 **Compatible** con TetraPack Monitor (bluestation-bs) y modo sin monitor

---

## Hardware necesario

| Componente | Especificaciones |
|---|---|
| Raspberry Pi | 3B+ / 4B / **5** (cualquier modelo con GPIO 40 pines) |
| Pantalla UART | TJC/Nextion **320×240** o **800×480** px (ver lista) |
| Cables | 4× Dupont hembra-hembra |

---

## Pantallas compatibles

### 320×240 px — HMI v2 (`TETRA V2.tft`)

| Fabricante | Modelos | Tamaño |
|---|---|---|
| **TJC** | TJC3224T022, TJC3224T028 | 2.2" / 2.8" |
| **Nextion Basic** | NX3224T022, NX3224T024, NX3224T028 | 2.2" / 2.4" / 2.8" |
| **Nextion Enhanced** | NX3224K022, NX3224K024, NX3224K028 | 2.2" / 2.4" / 2.8" |

### 800×480 px — HMI v4 (`TETRA TJC8048X543 (800×480).tft`)

| Fabricante | Modelos | Tamaño |
|---|---|---|
| **TJC Enhanced** | TJC8048X543 | 5" |

> Cada resolución requiere su propio archivo `.tft`. El script Python es el mismo para ambas.
> Los componentes del HMI 800×480 llevan sufijo `g` para evitar conflictos con el HMI 320×240.

---

## Conexionado GPIO

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
git clone https://github.com/EA8DLF/Tetra_JCT_Nextion_Display
cd Tetra_JCT_Nextion_Display
bash install.sh
```

El instalador:
- Detecta automáticamente el modelo de Raspberry Pi (incluida Pi 5)
- Configura el UART en `/boot/firmware/config.txt` o `/boot/config.txt`
- **Pi 5:** elimina `console=serial0` de `cmdline.txt` automáticamente
- Detecta el puerto serie disponible (`/dev/ttyAMA0` en Pi 5)
- Pregunta los datos de tu red TETRA (TX/RX, MCC, MNC, ISSI emergencias)
- Instala el script y crea el servicio systemd

---

## Raspberry Pi 5 — Notas importantes

### UART GPIO
En la Pi 5 el UART del GPIO no está activo por defecto. El instalador lo configura añadiendo a `/boot/firmware/config.txt`:

```
dtoverlay=uart0-pi5
dtoverlay=disable-bt
```

El puerto correcto en Pi 5 es `/dev/ttyAMA0` (no `/dev/serial0`).

### Consola serie
En Pi 5 la consola del sistema ocupa el UART por defecto, bloqueando la comunicación con la pantalla. El instalador elimina automáticamente `console=serial0,115200` de `/boot/firmware/cmdline.txt`.

Tras la instalación se pedirá **reiniciar** para aplicar todos los cambios.

---

## Páginas de pantalla

| Página | Estado | Contenido |
|---|---|---|
| page0 | STANDBY | Reloj, fecha, IP, temperatura, terminales con badge Online/Offline, último tráfico |
| page1 | VOZ | Indicativo, nombre, bandera, TG, historial de 4 llamadas, frecuencias |
| page3 | EMERGENCIA | SOS, sirenas animadas, GPS, dirección, ciudad (25 segundos) |
| page4 | SDS TEXTO | Mensaje de texto en hasta 5 líneas (15 segundos) |

---

## Componentes HMI

### Pantalla 320×240 — nombres originales

| Página | Componentes |
|---|---|
| page0 | `t_hora`, `t_fecha`, `t_ip`, `t_temp`, `t_volt`, `t_mcc`, `ter1`-`ter3`, `t_st1`-`t_st3`, `t_hist1`-`t_hist2` |
| page1 | `t_main`, `t_autor`, `t_tg`, `t_tipo`, `t_freq`, `t_log1`-`t_log4`, `p_flag`, `t_mcc_p1`, `t_provincia` |
| page3 | `t_emerg_call`, `t_emerg_issi`, `t_emerg_tg`, `t_emerg_gps`, `t_ecalle`, `t_epob`, `t_emerg_hora` |
| page4 | `t_sds`, `t_sfreq`, `t_smg`-`t_smg5` |

### Pantalla 800×480 — sufijo `g` en todos los nombres

Mismos componentes con `g` al final: `t_horag`, `ter1g`, `t_st1g`, `p_flagg`, `t_maingg`, etc.

---

## Requisitos

- Python 3.7+
- `pip install pyserial requests`
- systemd (para lectura de texto SDS del journal)
- TetraPack Monitor con bluestation-bs (opcional pero recomendado)

---

## Configuración manual

Editar la sección `─── AJUSTES ───` en `tetra_nextion.py`:

```python
SERIAL_PORT    = "/dev/serial0"    # Pi 5: /dev/ttyAMA0
MONITOR_URL    = "http://localhost:5000"
DEFAULT_TX     = "431.000MHz"
DEFAULT_RX     = "438.600MHz"
DEFAULT_MCC    = "001"
DEFAULT_MNC    = "001"
EMERGENCY_ISSI = "214112"
```

---

## Comandos útiles

```bash
sudo systemctl status tetra-nextion
journalctl -u tetra-nextion -f
sudo systemctl restart tetra-nextion
python3 ~/tetra_nextion.py        # ejecución manual
```

---

## Estructura del repositorio

```
Tetra_JCT_Nextion_Display/
├── tetra_nextion.py                       # Script principal (v4.1)
├── install.sh                             # Instalador interactivo
├── TETRA V2.tft                           # HMI compilado 320×240 px
├── TETRA TJC8048X543 (800×480).tft        # HMI compilado 800×480 px
├── Docs/
│   └── MANUAL.md                          # Manual de usuario completo
└── README.md
```

---

## Licencia

Distribución libre para radioaficionados y operadores TETRA. Uso no comercial.

---

*73 de EA8DLF — Gran Canaria, España*

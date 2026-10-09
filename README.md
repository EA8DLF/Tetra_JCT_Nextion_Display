# TETRA Nextion Display v4.2

Monitor de red TETRA en tiempo real para pantalla TJC/Nextion conectada a Raspberry Pi mediante UART.

Desarrollado por **EA8DLF** · 2026

---

## Novedades v4.2

- 🖥️🤝🖥️ **Un solo script para las dos pantallas** — selector `NEXTION_SIZE` (`320`/`800`) en el `.service`, mismo script instalado en ambas, sin ramas de código paralelas
- 🔴 **Online/Offline ya no se queda pegado en verde** — se detecta por timeout de inactividad en vez de por un evento de log de "baja" que estaciones base como nexus-bs nunca emiten
- 🏢 **Varias estaciones base** — reconoce `bluestation-bs`, FlowStation y Nexus-BS (comparten el mismo motor `tetra-bluestation`); si no hay monitor HTTP, lee el journal de la unidad systemd autodetectada o fijada con `JOURNAL_UNIT`
- ⚙️ **Todo configurable por variable de entorno** — `TETRA_*` para puerto, baudrate, monitor, journal, red TETRA y tiempos de pantalla, sin tocar el `.py`
- 🧯 **Sale limpio si no hay pantalla Nextion conectada** — evita quedarse corriendo a ciegas en una unidad con variante OLED

## Novedades v4.1

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
| **TJC** | TJC3224T022 ✅ probado, TJC3224T028 | 2.2" / 2.8" |

### 400×240 px — HMI compacto (`TETRA NX4024T032 (400x240).tft`)

| Fabricante | Modelos | Tamaño |
|---|---|---|
| **Nextion** (genuina) | NX4024T032 ⚠️ compilado, no probado en hardware real | 3.2" |

### 800×480 px — HMI v4 (`TETRA TJC8048X543 (800×480).tft`)

| Fabricante | Modelos | Tamaño |
|---|---|---|
| **TJC** | TJC8048X543 ✅ probado | 5" |

> Solo se han probado en hardware real TJC3224T022 (320×240) y TJC8048X543 (800×480);
> el resto de modelos TJC de la misma resolución deberían funcionar igual (mismo fabricante,
> mismo protocolo). La NX4024T032 (400×240) es una Nextion genuina, no TJC: su `.tft` se ha
> compilado específicamente para ese modelo exacto (no es un reciclado de otro), con los
> mismos nombres de componente que la pantalla de 320×240, pero **aún no se ha verificado en
> la pantalla física** — quita este aviso en cuanto se confirme en hardware real.

> Cada resolución requiere su propio archivo `.tft`, pero **el script Python es el mismo
> para las dos pantallas y usa los mismos nombres de componente en ambas** (`t_hora`,
> `ter1`-`ter3`, `t_st1`-`t_st3`, etc. — ver tabla de componentes más abajo). La variable
> de entorno `NEXTION_SIZE` (`320` o `800`, la pregunta el instalador) solo decide qué
> contenido extra se envía — p.ej. `t_hist1`/`t_hist2` (historial) y las etiquetas largas
> de temperatura/voltaje solo tienen sentido en la pantalla grande. Si el HMI 320×240 no
> tiene esos componentes, los comandos correspondientes simplemente se ignoran (Nextion
> descarta sin error los comandos a componentes inexistentes).

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
- Pregunta el tamaño de pantalla (320×240, 800×480, u otro ancho si tienes un HMI propio con esas mismas resoluciones) y lo deja fijado como `NEXTION_SIZE` en el servicio
- Detecta automáticamente el modelo de Raspberry Pi (incluida Pi 5)
- Configura el UART en `/boot/firmware/config.txt` o `/boot/config.txt`
- **Pi 5:** elimina `console=serial0` de `cmdline.txt` automáticamente
- Detecta el puerto serie disponible (`/dev/ttyAMA0` en Pi 5, o un adaptador USB-serie si no hay UART GPIO) y te deja confirmarlo o escribir otro
- Pregunta el baudrate de tu pantalla (9600 por defecto; algunas pantallas grandes usan otro)
- Pregunta si tienes un monitor HTTP (TetraPack/brew-server); si no, autodetecta o pregunta la unidad systemd de tu estación base (bluestation-bs/FlowStation/Nexus-BS) para leer su journal directamente
- Pregunta los datos de tu red TETRA (TX/RX, MCC, MNC, ISSI emergencias)
- Instala el script (con tu usuario y tu `$HOME`, sin rutas fijas) y crea el servicio systemd

No hace falta editar `tetra_nextion.py` a mano para usar otra pantalla, otro puerto o otra Raspberry: todo se pregunta en la instalación.

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

Mismos nombres de componente en las dos pantallas. `t_hist1`/`t_hist2` (historial de
standby) solo se envían con `NEXTION_SIZE=800`; el resto se envía siempre, y si el HMI
320×240 no tiene un componente, Nextion ignora ese comando sin problema.

| Página | Componentes |
|---|---|
| page0 | `t_hora`, `t_fecha`, `t_ip`, `t_temp`, `t_volt`, `t_mcc`, `ter1`-`ter3`, `t_st1`-`t_st3`, `t_hist1`-`t_hist2` (solo 800×480) |
| page1 | `t_main`, `t_tg`, `t_tipo`, `t_freq`, `t_log1`-`t_log4`, `p_flag`, `t_mcc_p1`, `t_provincia` |
| page3 | `t_emerg_call`, `t_emerg_issi`, `t_emerg_tg`, `t_emerg_gps`, `t_ecalle`, `t_epob`, `t_emerg_hora` |
| page4 | `t_sds`, `t_sfreq`, `t_smg`-`t_smg5` (solo 3 campos `t_smg`-`t_smg3` en 320×240) |

---

## Requisitos

- Python 3.7+
- Ninguna librería externa — solo la librería estándar (`termios`, `urllib`)
- systemd (para journalctl: lectura de texto SDS y, sin monitor, el stream de eventos)
- Monitor HTTP (TetraPack/brew-server) opcional — sin él, se lee el journal de la estación base directamente

---

## Configuración manual

### Opción A — variables de entorno (recomendado, sin tocar el código)

Cualquier ajuste se puede sobrescribir con una variable de entorno `TETRA_*`,
sin editar `tetra_nextion.py` ni reinstalar. Útil para cambiar de pantalla,
puerto o máquina. Ejemplo en el servicio systemd (`/etc/systemd/system/tetra-nextion.service`):

```ini
[Service]
Environment=TETRA_SERIAL_PORT=/dev/ttyUSB0
Environment=TETRA_BAUD_RATE=115200
```

Tras editar el `.service`: `sudo systemctl daemon-reload && sudo systemctl restart tetra-nextion`

| Variable | Ajuste que sobrescribe | Por defecto |
|---|---|---|
| `TETRA_SERIAL_PORT` | Puerto serie de la pantalla | `/dev/serial0` |
| `TETRA_BAUD_RATE` | Baudrate de la pantalla | `9600` |
| `TETRA_MONITOR_URL` | URL de TetraPack Monitor | `http://localhost:5000` |
| `TETRA_JOURNAL_UNIT` | Unidad systemd de la estación base (sin monitor) | autodetección |
| `TETRA_TERMINAL_OFFLINE_SEC` | Segundos sin noticias de un terminal → offline/rojo | `180` |
| `NEXTION_SIZE` | Ancho de pantalla: `800` = diseño grande; cualquier otro valor (`320`, `400`...) = diseño compacto, igual que la pequeña (sin prefijo `TETRA_`, va en el `.service`) | `320` |
| `TETRA_CONFIG_TOML` | Ruta al `config.toml` de bluestation-bs/FlowStation/Nexus-BS | autodetección |
| `TETRA_DEFAULT_TX` / `TETRA_DEFAULT_RX` | Frecuencias TX/RX por defecto | `431.000MHz` / `438.600MHz` |
| `TETRA_DEFAULT_MCC` / `TETRA_DEFAULT_MNC` | MCC/MNC por defecto | `001` / `001` |
| `TETRA_EMERGENCY_ISSI` | ISSI del servidor de emergencias | `214112` |
| `TETRA_STANDBY_TIMEOUT` | Segundos inactivo → standby | `20` |
| `TETRA_CALL_MIN_DISPLAY` | Segundos mínimos tras soltar PTT | `20` |
| `TETRA_SDS_DISPLAY` | Segundos mostrando SDS texto | `15` |
| `TETRA_SDS_BLOCK_TIME` | Segundos de bloqueo SDS tras voz | `30` |
| `TETRA_EMERGENCY_DISPLAY` | Segundos mostrando emergencia | `25` |

### Opción B — editar el script instalado

Editar la sección `─── AJUSTES ───` en `tetra_nextion.py` (son los valores
por defecto; una variable de entorno de la tabla anterior siempre tiene prioridad):

```python
SERIAL_PORT    = "/dev/serial0"    # Pi 5: /dev/ttyAMA0
BAUD_RATE      = 9600
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
├── tetra_nextion.py                       # Script principal (v4.2)
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

# Manual de Usuario — TETRA Nextion Display v4.1

**EA8DLF · 2026**
**Repositorio:** https://github.com/EA8DLF/Tetra_JCT_Nextion_Display

---

## Índice

1. [Introducción](#1-introducción)
2. [Hardware necesario](#2-hardware-necesario)
3. [Conexionado](#3-conexionado)
4. [Instalación](#4-instalación)
5. [Configuración](#5-configuración)
6. [Pantallas HMI](#6-pantallas-hmi)
7. [Funcionamiento](#7-funcionamiento)
8. [Raspberry Pi 5](#8-raspberry-pi-5)
9. [Solución de problemas](#9-solución-de-problemas)
10. [Comandos útiles](#10-comandos-útiles)

---

## 1. Introducción

TETRA Nextion Display es un sistema de monitorización en tiempo real de una red de radio TETRA. Muestra en una pequeña pantalla TJC/Nextion conectada a una Raspberry Pi la actividad de la red: llamadas de voz, mensajes SDS, emergencias y estado de los terminales.

Funciona en conjunto con **TetraPack Monitor (bluestation-bs)** o de forma autónoma leyendo directamente el journal del sistema.

### Características principales

- Pantalla de voz con indicativo, nombre, bandera del país e historial de llamadas
- Mensajes SDS de texto en pantalla dedicada
- Alerta de emergencia SOS con sirenas animadas y localización GPS
- Standby con terminales activos, estado Online/Offline y último tráfico
- Geocodificación inversa automática (Nominatim/OpenStreetMap)
- Base de datos de radioaficionados (RadioID.net) con 300.000+ entradas

---

## 2. Hardware necesario

| Componente | Especificaciones |
|---|---|
| Raspberry Pi | 3B+ / 4B / **5** |
| Pantalla TJC/Nextion | 320×240 px o 800×480 px (ver tabla de compatibilidad) |
| Cables Dupont | 4× hembra-hembra |
| MicroSD pantalla | ≥ 4 GB (para grabar el archivo `.tft`) |
| Alimentación Pi | 5V / 3A mínimo |

### Pantallas compatibles

**320×240 px** — archivo `TETRA V2.tft`:

| Fabricante | Modelos | Tamaño |
|---|---|---|
| TJC | TJC3224T022, TJC3224T028 | 2.2" / 2.8" |
| Nextion Basic | NX3224T022, NX3224T024, NX3224T028 | 2.2" / 2.4" / 2.8" |
| Nextion Enhanced | NX3224K022, NX3224K024, NX3224K028 | 2.2" / 2.4" / 2.8" |

**800×480 px** — archivo `TETRA TJC8048X543 (800×480).tft`:

| Fabricante | Modelos | Tamaño |
|---|---|---|
| TJC Enhanced | TJC8048X543 | 5" |

---

## 3. Conexionado

Conecta 4 cables Dupont hembra-hembra entre la pantalla y el GPIO de la Raspberry Pi:

```
Pantalla TJC/Nextion    Raspberry Pi GPIO
────────────────────    ──────────────────────────
VCC (5V)           →   Pin 2  (5V)
GND                →   Pin 6  (GND)
TX  (pantalla)     →   Pin 10 (GPIO15 / UART RX)
RX  (pantalla)     →   Pin 8  (GPIO14 / UART TX)
```

> **Importante:** TX de la pantalla va al RX de la Pi, y RX de la pantalla va al TX de la Pi. Si la pantalla no responde, intercambia los cables de datos.

---

## 4. Instalación

### Paso 1 — Grabar el HMI en la microSD de la pantalla

1. Descarga el archivo `.tft` correspondiente a tu pantalla desde el repositorio
2. Cópialo a la raíz de una microSD (FAT32, sin carpetas)
3. Inserta la microSD en la pantalla y enciéndela — cargará el HMI automáticamente
4. Cuando termine (barra de progreso completa) retira la microSD

### Paso 2 — Clonar e instalar en la Raspberry Pi

```bash
git clone https://github.com/EA8DLF/Tetra_JCT_Nextion_Display
cd Tetra_JCT_Nextion_Display
bash install.sh
```

El instalador realiza automáticamente:
- Instalación de dependencias Python (`pyserial`, `requests`)
- Detección del modelo de Raspberry Pi
- Configuración del UART en `/boot/firmware/config.txt`
- En **Pi 5**: eliminación de `console=serial0` de `cmdline.txt`
- Detección del puerto serie correcto
- Solicitud de parámetros de tu red TETRA
- Creación del servicio systemd

### Paso 3 — Reiniciar (si es necesario)

Si el instalador indica que se necesita reinicio (especialmente en Pi 5):

```bash
sudo reboot
```

Tras el reinicio el servicio arranca automáticamente.

---

## 5. Configuración

### Parámetros del instalador

| Parámetro | Descripción | Defecto |
|---|---|---|
| Monitor | URL de TetraPack Monitor | `http://localhost:5000` |
| TX | Frecuencia de transmisión | `431.000MHz` |
| RX | Frecuencia de recepción | `438.600MHz` |
| MCC | Mobile Country Code de tu red | `001` |
| MNC | Mobile Network Code de tu red | `001` |
| ISSI emergencias | ISSI del servidor de emergencias | `214112` |
| Tiempo voz | Segundos mostrando llamada tras PTT | `20` |
| Tiempo SDS | Segundos mostrando mensaje SDS | `15` |
| Tiempo emergencia | Segundos mostrando alerta SOS | `25` |

### Modificar configuración después de instalar

Edita directamente el script instalado:

```bash
nano ~/tetra_nextion.py
```

Localiza la sección `─── AJUSTES ───` y modifica los valores. Reinicia el servicio:

```bash
sudo systemctl restart tetra-nextion
```

---

## 6. Pantallas HMI

### page0 — Standby

Pantalla de reposo. Muestra:
- Reloj y fecha actuales
- IP de la Raspberry Pi
- Temperatura de la CPU
- Voltaje del sistema
- Hasta 3 terminales activos con su estado Online/Offline y TG
- Las 2 últimas llamadas de voz (historial)

### page1 — Voz

Se activa con cualquier llamada de voz. Muestra:
- Indicativo y nombre completo del operador
- Bandera del país (detectada por prefijo)
- Tipo de llamada y Talk Group activo
- MCC/MNC de la red
- Frecuencias TX/RX
- Historial de las 4 últimas llamadas
- Cronómetro de duración de la llamada

### page3 — Emergencia

Se activa con una señal de emergencia SOS. Máxima prioridad. Muestra:
- Indicativo e ISSI del terminal en emergencia
- Talk Group
- Coordenadas GPS
- Dirección postal (geocodificación inversa)
- Sirenas animadas de emergencia
- Hora de la alerta

### page4 — SDS Texto

Se activa al recibir un mensaje de texto SDS. Muestra:
- Indicativo del remitente
- Hasta 5 líneas del mensaje
- Frecuencias TX/RX

---

## 7. Funcionamiento

### Estados del sistema

```
STANDBY ←──────────────────────────────────┐
   │                                        │
   │ llamada voz         timeout (20s)      │
   ↓                          ↑             │
  VOZ ──── fin PTT ──→ POST_VOZ ────────────┤
                                            │
   │ SDS texto           timeout (15s)      │
   ↓                          ↑             │
  SDS ─────────────────────────────────────┤
                                            │
   │ emergencia SOS      timeout (25s)      │
   ↓                          ↑             │
EMERGENCIA ─────────────────────────────────┘
```

### Prioridades

1. **EMERGENCIA** — prioridad absoluta, interrumpe cualquier otro estado
2. **VOZ** — interrumpe SDS y standby
3. **SDS** — solo se muestra si no hay llamada activa o reciente (30s de bloqueo tras voz)
4. **STANDBY** — estado por defecto

### ISSIs de sistema

Los ISSIs `9999`, `200999` y `5000` son tratados como sistema y no generan eventos de voz ni SDS en pantalla (son ISSIs internos de la red).

---

## 8. Raspberry Pi 5

La Pi 5 tiene configuraciones específicas que el instalador gestiona automáticamente.

### Puerto UART

En Pi 5, el UART GPIO se activa con `dtoverlay=uart0-pi5` y el puerto es `/dev/ttyAMA0` (no `/dev/serial0`).

### Consola serie

Por defecto, Pi 5 usa el UART GPIO como consola del sistema (`console=serial0,115200` en `cmdline.txt`). Esto bloquea la comunicación con la pantalla. El instalador elimina esta entrada automáticamente.

### Verificación manual

Si la pantalla no responde en Pi 5:

```bash
# Verificar puerto
ls -la /dev/serial* /dev/ttyAMA*

# Verificar que no hay consola en el UART
cat /boot/firmware/cmdline.txt  # no debe contener console=serial0

# Verificar overlays
grep -E "uart0|disable-bt" /boot/firmware/config.txt

# Test directo
python3 -c "
import serial, time
s = serial.Serial('/dev/ttyAMA0', 9600, timeout=1)
time.sleep(0.5)
s.write(b't_hora.txt=\"TEST\"\xff\xff\xff')
time.sleep(0.5)
s.close()
print('Enviado — comprueba la pantalla')
"
```

---

## 9. Solución de problemas

### La pantalla no muestra nada / está en blanco

- Verificar alimentación VCC 5V
- Verificar que el archivo `.tft` está correctamente grabado en la microSD

### La pantalla enciende pero no se actualiza

1. Verificar cableado TX/RX (prueba intercambiando los cables de datos)
2. En Pi 5: verificar que `console=serial0` no está en `cmdline.txt`
3. Verificar el puerto configurado: `grep SERIAL_PORT ~/tetra_nextion.py`
4. Test directo con Python (ver sección Pi 5)

### El servicio arranca pero no hay logs

```bash
# Ver logs detallados
journalctl -u tetra-nextion -f

# Ejecutar manualmente para ver errores
sudo systemctl stop tetra-nextion
python3 ~/tetra_nextion.py
```

### Los campos aparecen en posiciones incorrectas

Asegúrate de que el archivo `.tft` en la microSD corresponde a la resolución de tu pantalla:
- **320×240** → `TETRA V2.tft`
- **800×480** → `TETRA TJC8048X543 (800×480).tft`

### No conecta con el monitor TetraPack

```bash
# Verificar que el monitor está activo
curl http://localhost:5000/api/system/stats

# Si no hay monitor, configurar MONITOR_URL vacío
sed -i 's|MONITOR_URL.*=.*"http://localhost:5000"|MONITOR_URL    = ""|' ~/tetra_nextion.py
sudo systemctl restart tetra-nextion
```

---

## 10. Comandos útiles

```bash
# Estado del servicio
sudo systemctl status tetra-nextion

# Logs en tiempo real
journalctl -u tetra-nextion -f

# Reiniciar servicio
sudo systemctl restart tetra-nextion

# Parar servicio
sudo systemctl stop tetra-nextion

# Ejecutar manualmente (para depuración)
python3 ~/tetra_nextion.py

# Verificar configuración
grep -E "SERIAL_PORT|MONITOR_URL|DEFAULT_TX|DEFAULT_MCC" ~/tetra_nextion.py

# Verificar puerto serie
ls -la /dev/serial* /dev/ttyAMA* 2>/dev/null
```

---

*73 de EA8DLF — Gran Canaria, España*
*https://github.com/EA8DLF/Tetra_JCT_Nextion_Display*

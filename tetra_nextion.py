#!/usr/bin/env python3
# TETRA Nextion Display v4.1
# Copyright (C) 2026 Jose Maria - EA8DLF
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# https://www.gnu.org/licenses/gpl-3.0.txt
# ═══════════════════════════════════════════════════════════════
#  TETRA Nextion/TJC Display v4.1 - EA8DLF 2026
#
#  Compatible con pantallas (simultáneo, un solo script):
#    · TJC3224T022 / TJC3224T028  (320×240 px) — componentes originales
#    · TJC8048X543                 (800×480 px) — componentes con sufijo "g"
#
#  El script envía a AMBAS pantallas a la vez.
#  Cada pantalla ignora los comandos de componentes que no existen en su HMI.
#
#  CAMBIOS v4.1 respecto a v4.0:
#    · Soporte dual-pantalla sin conflictos de nombres de componentes
#    · Componentes 800×480 renombrados con sufijo "g" en el HMI
#    · txts2() / send2() envían a las dos pantallas simultáneamente
#    · Puerto serie corregido para Raspberry Pi 5 (/dev/ttyAMA0)
#    · URL repositorio corregida
#
#  REQUISITOS: pip install pyserial requests
#  CONFIGURACIÓN: editar sección ─── AJUSTES ───
# ═══════════════════════════════════════════════════════════════
import re, json, time, requests, threading, os, csv, serial, socket, subprocess
from datetime import datetime, timedelta
from pathlib import Path

# ─── AJUSTES (editar según instalación) ───────────────────────
SERIAL_PORT    = "/dev/serial0"    # Pi 5: usar /dev/ttyAMA0
BAUD_RATE      = 9600
MONITOR_URL    = "http://localhost:5000"   # Vacío ("") si no hay monitor
CONFIG_TOML    = ""                # Vacío para autodetección
DEFAULT_TX     = "431.000MHz"
DEFAULT_RX     = "438.600MHz"
DEFAULT_MCC    = "001"
DEFAULT_MNC    = "001"
EMERGENCY_ISSI = "214112"

STANDBY_TIMEOUT   = 20
CALL_MIN_DISPLAY  = 20
SDS_DISPLAY       = 15
SDS_BLOCK_TIME    = 30
EMERGENCY_DISPLAY = 25

SYSTEM_ISSI  = {"9999", "200999", "5000"}
VOICE_FILTER = {"200999", "5000"}
CUSTOM_ISSI  = {
    "9999":   ("LORO",   "Eco TETRA",   "TETRA Net"),
    "200999": ("SERVER", "Server",      "TETRA Net"),
    "9998":   ("WX",     "Tiempo/Info", "TETRA Net"),
    "9990":   ("ECHO",   "Echo",        "TETRA Net"),
    "5000":   ("ADN",    "ADN System",  "TETRA Net"),
}

# ─── INICIALIZACIÓN ───────────────────────────────────────────
CACHE_FILE    = str(Path.home() / "radioid_cache.csv")
CACHE_MAX_AGE = timedelta(hours=24)
RADIOID_URL   = "https://radioid.net/static/user.csv"
API_URL       = f"{MONITOR_URL}/api/log-stream" if MONITOR_URL else ""
STATS_URL     = f"{MONITOR_URL}/api/system/stats" if MONITOR_URL else ""

# ─── CONFIG.TOML ──────────────────────────────────────────────
def read_config():
    paths = [CONFIG_TOML] if CONFIG_TOML else []
    if not CONFIG_TOML:
        for p in sorted(Path.home().rglob("config.toml")):
            if "bluestation" in str(p).lower():
                paths.append(str(p)); break
    for path in paths:
        try:
            with open(path) as f: txt = f.read()
            tx  = re.search(r"^tx_freq\s*=\s*(\d+)", txt, re.MULTILINE)
            rx  = re.search(r"^rx_freq\s*=\s*(\d+)", txt, re.MULTILINE)
            mcc = re.search(r"^mcc\s*=\s*(\d+)",     txt, re.MULTILINE)
            mnc = re.search(r"^mnc\s*=\s*(\d+)",     txt, re.MULTILINE)
            tx_mhz = f"{int(tx.group(1))/1e6:.3f}MHz" if tx else DEFAULT_TX
            rx_mhz = f"{int(rx.group(1))/1e6:.3f}MHz" if rx else DEFAULT_RX
            print(f"[config] Leído de {path}")
            return tx_mhz, rx_mhz, mcc.group(1) if mcc else DEFAULT_MCC, mnc.group(1) if mnc else DEFAULT_MNC
        except: pass
    print("[config] config.toml no encontrado — usando valores por defecto")
    return DEFAULT_TX, DEFAULT_RX, DEFAULT_MCC, DEFAULT_MNC

TX_FREQ, RX_FREQ, MCC, MNC = read_config()
print(f"[config] TX:{TX_FREQ} RX:{RX_FREQ} MCC:{MCC} MNC:{MNC}")

# ─── UART ─────────────────────────────────────────────────────
ser      = None
ser_lock = threading.Lock()

def init_serial():
    global ser
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"[uart] {SERIAL_PORT} {BAUD_RATE}bd OK")
    except Exception as e:
        print(f"[uart] Error: {e}")

def send(cmd):
    try:
        with ser_lock:
            if ser and ser.is_open:
                ser.write((cmd + "\xff\xff\xff").encode('latin-1', errors='replace'))
                time.sleep(0.02)
    except Exception as e:
        print(f"[uart] {e}")

def txts(comp, val, maxlen=40):
    """Envía texto a un componente de pantalla."""
    send(f'{comp}.txt="{str(val)[:maxlen]}"')

def txts2(comp, val, maxlen=40):
    """Envía texto a ambas pantallas:
       · comp        → pantalla 320×240 (nombre original)
       · comp + 'g'  → pantalla 800×480 (nombre con sufijo g)
    """
    txts(comp,        val, maxlen)
    txts(comp + "g",  val, maxlen)

def send2(cmd_320, cmd_800):
    """Envía comandos distintos para cada resolución de pantalla."""
    send(cmd_320)
    send(cmd_800)

# ─── RADIOID ──────────────────────────────────────────────────
radioid_db = {}

def load_radioid():
    global radioid_db
    fresh = os.path.exists(CACHE_FILE) and \
            datetime.now() - datetime.fromtimestamp(os.path.getmtime(CACHE_FILE)) < CACHE_MAX_AGE
    if not fresh:
        print("[radioid] Descargando base de datos...")
        try:
            r = requests.get(RADIOID_URL, timeout=120, stream=True)
            r.raise_for_status()
            with open(CACHE_FILE, "wb") as f:
                for chunk in r.iter_content(8192): f.write(chunk)
            print("[radioid] Descarga completada")
        except Exception as e:
            print(f"[radioid] Error descarga: {e}")
            if not os.path.exists(CACHE_FILE):
                print("[radioid] Sin caché — lookups desactivados"); return
    print("[radioid] Cargando...")
    tmp = {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8", errors="replace") as f:
            for row in csv.DictReader(f):
                rid = str(row.get("RADIO_ID","")).strip()
                if rid:
                    nombre = f"{row.get('FIRST_NAME','').strip()} {row.get('LAST_NAME','').strip()}".strip()
                    tmp[rid] = {
                        "callsign": row.get("CALLSIGN","???").strip(),
                        "name":     nombre or "Desconocido",
                        "city":     row.get("CITY","").strip(),
                        "state":    row.get("STATE","").strip(),
                    }
        radioid_db = tmp
        print(f"[radioid] {len(radioid_db)} entradas cargadas")
    except Exception as e:
        print(f"[radioid] Error carga: {e}")

def lookup(issi):
    if str(issi) in CUSTOM_ISSI: return CUSTOM_ISSI[str(issi)]
    e = radioid_db.get(str(issi))
    if e:
        prov = e.get("state","") or e.get("city","") or ""
        return e["callsign"], e["name"], prov
    return str(issi), "Desconocido", ""

# ─── BANDERAS ─────────────────────────────────────────────────
def get_flag(callsign):
    cs = callsign.upper().strip()
    if cs[:3] in ['EA8','EB8','EC8','ED8','EE8','EF8','EG8','EH8']: return 42,  "CANARY Isl"
    if cs[:3] in ['EA6','EB6','EC6','ED6','EE6','EF6','EG6','EH6']: return 23,  "BALEARIC Isl"
    if cs[:3] in ['EA9','EB9','EC9','ED9','EE9','EF9','EG9','EH9']: return 46,  "CEUTA/MELILLA"
    if cs[:2] in ['EA','EB','EC','ED','EE','EF','EG','EH']:          return 198, "SPAIN"
    if cs[:2] in ['CT','CS','CR','CQ','CU']:                         return 171, "PORTUGAL"
    if cs[:1] == 'F' or cs[:2] in ['FA','FB','FC','FD','FE','FF','TM']: return 78, "FRANCE"
    if cs[:2] in ['DA','DB','DC','DD','DE','DF','DG','DH','DI','DJ','DK','DL','DM','DO']: return 83, "GERMANY"
    if cs[:1] == 'I':                                                return 105, "ITALY"
    if cs[:2] in ['GM','GS','MM','MS','2M']:                         return 185, "SCOTLAND"
    if cs[:2] in ['GW','GC','MW','MC','2W']:                         return 236, "WALES"
    if cs[:2] in ['GI','MI','GN','MN']:                              return 69,  "N.IRELAND"
    if cs[:1] in ['G','M']:                                          return 69,  "ENGLAND"
    if cs[:2] in ['PA','PB','PD','PE','PH','PI']:                    return 213, "NETHERLANDS"
    if cs[:2] in ['ON','OO','OP','OQ','OR','OS','OT']:               return 27,  "BELGIUM"
    if cs[:2] in ['SA','SB','SC','SD','SE','SF','SG','SH','SI','SJ','SK','SL','SM']: return 205, "SWEDEN"
    if cs[:2] in ['LA','LB','LC','LN']:                              return 159, "NORWAY"
    if cs[:2] == 'OZ':                                               return 62,  "DENMARK"
    if cs[:2] in ['OH','OG','OI']:                                   return 77,  "FINLAND"
    if cs[:2] == 'HB':                                               return 206, "SWITZERLAND"
    if cs[:2] == 'OE':                                               return 18,  "AUSTRIA"
    if cs[:2] in ['EI','EJ']:                                        return 102, "IRELAND"
    if cs[:2] in ['SV','SZ','J4']:                                   return 57,  "GREECE"
    if cs[:2] in ['SP','SQ','SR','SN','SO']:                         return 169, "POLAND"
    if cs[:2] in ['OK','OL']:                                        return 61,  "CZECH Rep"
    if cs[:2] in ['HA','HG']:                                        return 96,  "HUNGARY"
    if cs[:2] in ['YO','YP','YQ','YR']:                              return 175, "ROMANIA"
    if cs[:2] == 'LZ':                                               return 37,  "BULGARIA"
    if cs[:2] == '9A':                                               return 58,  "CROATIA"
    if cs[:2] == 'OM':                                               return 191, "SLOVAKIA"
    if cs[:2] in ['UR','US','UT','UU','UV','UW','UX','UY','UZ','EM','EO']: return 224, "UKRAINE"
    if cs[:1] in ['W','K','N']:                                      return 228, "USA"
    if cs[:1] == 'R' or cs[:2] in ['UA','UB','UC']:                 return 176, "RUSSIA"
    if cs[:2] in ['JA','JB','JC','JD','JE','JF','JG','JH','JI','JJ','JK','JL','JM','JN','JO','JP','JQ','JR','JS']: return 108, "JAPAN"
    if cs[:2] == 'VK':                                               return 17,  "AUSTRALIA"
    if cs[:2] in ['ZL','ZM']:                                        return 153, "NEW ZEALAND"
    return 2, ""

# ─── STATS DEL SISTEMA ────────────────────────────────────────
stats = {"cpuTemp": 0, "voltage": 0, "localIp": "---"}

def fetch_stats():
    while True:
        updated = False
        if STATS_URL:
            try:
                r = requests.get(STATS_URL, timeout=5)
                data = r.json()
                stats["cpuTemp"] = float(data.get("cpuTemp") or 0)
                stats["voltage"] = float(data.get("voltage") or 0)
                stats["localIp"] = str(data.get("localIp") or "---")
                updated = True
            except: pass
        if not updated:
            try:
                with open("/sys/class/thermal/thermal_zone0/temp") as f:
                    stats["cpuTemp"] = int(f.read()) / 1000.0
            except: pass
            try:
                r2 = subprocess.run(["vcgencmd","measure_volts"],
                                    capture_output=True, text=True, timeout=2)
                v = re.search(r"volt=([\d.]+)", r2.stdout)
                if v: stats["voltage"] = float(v.group(1))
            except: pass
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                stats["localIp"] = s.getsockname()[0]
                s.close()
            except: pass
        time.sleep(10)

# ─── TERMINALES ───────────────────────────────────────────────
terminals = {}

def update_terminal(issi, rssi=None, tg=None):
    if str(issi) in SYSTEM_ISSI: return
    t = terminals.setdefault(str(issi), {
        "rssi": 0, "rssi_time": 0, "tg": "?", "callsign": "", "online": False
    })
    if rssi is not None:
        t["rssi"]      = rssi
        t["rssi_time"] = time.time()
        t["online"]    = True
        if not t["callsign"]: t["callsign"] = lookup(issi)[0]
    if tg is not None: t["tg"] = str(tg)

def terminal_line(issi):
    t = terminals.get(str(issi))
    if not t: return ""
    cs = t["callsign"] or lookup(issi)[0]
    return f"{issi} {cs} TG:{t['tg']}"

def refresh_terminals():
    if STATE[0] != "STANDBY": return
    sorted_t = [issi for issi, _ in sorted(
        terminals.items(), key=lambda x: x[1]["rssi_time"], reverse=True
    )]
    for i in range(1, 4):
        if i-1 < len(sorted_t):
            issi   = sorted_t[i-1]
            t      = terminals.get(str(issi), {})
            online = t.get("online", False)
            linea  = terminal_line(issi)

            # Texto terminal — ambas pantallas
            txts2(f"ter{i}", linea, 40)

            # Badge Online/Offline — ambas pantallas
            estado = "Online" if online else "Offline"
            color_txt = 2024   if online else 63488   # verde / rojo
            color_bg  = 384    if online else 6144

            txts2(f"t_st{i}", estado, 8)
            send2(f"t_st{i}.pco={color_txt}",  f"t_st{i}g.pco={color_txt}")
            send2(f"t_st{i}.bco={color_bg}",   f"t_st{i}g.bco={color_bg}")
        else:
            txts2(f"ter{i}",  "", 40)
            txts2(f"t_st{i}", "", 8)

def init_terminals_from_journal():
    time.sleep(5)
    try:
        result = subprocess.run(
            ["journalctl", "--since", "2 hours ago", "--no-pager", "-q"],
            capture_output=True, text=True, timeout=10
        )
        states = {}
        for line in result.stdout.splitlines():
            m = re.search(r"BrewEntity: subscriber register issi=(\d+)", line)
            if m: states[m.group(1)] = True
            m = re.search(r"BrewEntity: subscriber deregister issi=(\d+)", line)
            if m: states[m.group(1)] = False
        for issi, online in states.items():
            if str(issi) not in SYSTEM_ISSI:
                t = terminals.setdefault(str(issi), {
                    "rssi": 0, "rssi_time": 0, "tg": "?", "callsign": "", "online": False
                })
                t["online"] = online
                if not t["callsign"]: t["callsign"] = lookup(issi)[0]
                print(f"[terminal] init: {issi} = {'Online' if online else 'Offline'}")
    except Exception as e:
        print(f"[terminal] Error init: {e}")

# ─── SDS TEXTO ────────────────────────────────────────────────
def is_readable_text(byte_list):
    if len(byte_list) <= 4: return False
    text_bytes = [b for b in byte_list[4:] if 32 <= b < 128]
    return len(text_bytes) >= len(byte_list[4:]) * 0.7 and len(text_bytes) >= 3

def decode_sds_text(byte_list):
    return "".join(chr(b) for b in byte_list[4:] if 32 <= b < 128).strip()

def get_sds_text_from_journal(dst_issi, seconds=10):
    try:
        result = subprocess.run(
            ["journalctl", f"--since={seconds} seconds ago", "--no-pager", "-q"],
            capture_output=True, text=True, timeout=3
        )
        lines = list(reversed(result.stdout.splitlines()))
        p_local = re.compile(
            r"USdsData \{.*?called_party_ssi: Some\(" + str(dst_issi) + r"\).*?\[([\d,\s]+)\]"
        )
        p_net = re.compile(
            r"CmceSdsData \{ source_issi: \d+, dest_issi: " + str(dst_issi) + r".*?\[([\d,\s]+)\]"
        )
        for line in lines:
            for p in [p_local, p_net]:
                m = p.search(line)
                if m:
                    byte_list = [int(b.strip()) for b in m.group(1).split(",")]
                    if is_readable_text(byte_list):
                        text = decode_sds_text(byte_list)
                        print(f"[sds texto] {dst_issi}: {text}")
                        return text
    except Exception as e:
        print(f"[sds journal] Error: {e}")
    return None

# ─── TIEMPO ───────────────────────────────────────────────────
def hora():
    return datetime.now().astimezone().strftime("%H:%M:%S")

def fecha_hora():
    return datetime.now().astimezone().strftime("%d/%m/%Y %H:%M:%S")

def fecha_hora_sistema():
    temp     = stats.get("cpuTemp", 0)
    volt     = stats.get("voltage", 0)
    volt_str = f"{volt:.1f}V" if volt > 0 else "---V"
    return f"Fecha: {datetime.now().astimezone().strftime('%d/%m/%Y')} Hora: {hora()} Temp: {temp:.1f}\xb0C Voltaje: {volt_str}"

# ─── MÁQUINA DE ESTADOS ───────────────────────────────────────
STATE         = ["STANDBY"]
current_page  = [0]
call_log      = []
voice_hist    = []
active_calls  = {}
state_start   = [0]
call_start    = [0]
connected_at  = [0]
voice_end_time= [0]
emergency_issi= [None]
emergency_shown=[False]

def in_voice_protection():
    if STATE[0] in ("VOZ", "EMERGENCIA"): return True
    return time.time() - voice_end_time[0] < SDS_BLOCK_TIME

# ─── STANDBY (page0) ──────────────────────────────────────────
def show_standby():
    if current_page[0] != 0:
        send("page 0")
        current_page[0] = 0
        time.sleep(0.1)

    temp     = stats.get("cpuTemp", 0)
    volt     = stats.get("voltage", 0)
    ip       = stats.get("localIp", "---")
    volt_str = f"{volt:.1f}V" if volt > 0 else "---V"

    txts2("t_hora",  hora(), 10)
    txts2("t_fecha", datetime.now().astimezone().strftime("%d/%m/%Y"), 12)
    txts2("t_ip",    f"IP: {ip}", 22)
    txts2("t_temp",  f"Temp: {temp:.1f}\xb0C", 14)
    txts2("t_volt",  f"Voltaje: {volt_str}", 14)
    txts2("t_mcc",   f"MCC:{MCC} MNC:{MNC}", 20)

    # Último tráfico de voz (t_hist1/t_hist2 — ambas pantallas)
    for i, entry in enumerate(voice_hist[:2], 1):
        txts2(f"t_hist{i}", entry, 50)
    if len(voice_hist) < 1: txts2("t_hist1", "", 50)
    if len(voice_hist) < 2: txts2("t_hist2", "", 50)

    refresh_terminals()

# ─── VOZ (page1) ──────────────────────────────────────────────
def show_event(issi, tipo, tg="", issi_dst=""):
    callsign, name, provincia = lookup(issi)
    is_system = str(issi) in SYSTEM_ISSI
    pic, pais = (271, "TETRA Net") if is_system else get_flag(callsign)

    if current_page[0] != 1:
        send("page 1")
        current_page[0] = 1
        time.sleep(0.2)

    txts2("t_freq",    f"Frec. TX:{TX_FREQ} Frec. RX:{RX_FREQ}", 45)
    txts2("t_main",    f"{callsign} {name}", 35)
    txts2("t_autor",   f"{callsign}", 20)
    txts2("t_pais",    pais, 20)
    txts2("t_provincia", provincia[:25], 25)
    txts2("t_tipo",    f"Tipo de Llamada: {tipo}", 25)
    txts2("t_mcc_p1",  f"MCC:{MCC} MNC:{MNC}", 20)

    # Bandera — ambas pantallas
    send2(f"p_flag.pic={pic}", f"p_flagg.pic={pic}")

    if tg:
        txts2("t_tg", f"TG: {tg}", 15)
    elif issi_dst:
        txts2("t_tg", f"- {lookup(issi_dst)[0]}", 15)
    else:
        txts2("t_tg", "", 15)

    # Historial page1
    if time.time() - connected_at[0] > 3:
        tg_str    = tg or issi_dst or "?"
        log_entry = f"Indicativo: {callsign} - TG:{tg_str} - Hora: {hora()[:5]}"
        if not call_log or call_log[0] != log_entry:
            call_log.insert(0, log_entry)
            call_log[:] = call_log[:4]
        for i, log in enumerate(call_log, 1):
            txts2(f"t_log{i}", log, 50)

        # Historial para standby (t_hist1/t_hist2)
        hist_entry = f"Indicativo: {callsign} - TG:{tg_str} - Hora: {hora()[:5]}"
        if not voice_hist or voice_hist[0] != hist_entry:
            voice_hist.insert(0, hist_entry)
            voice_hist[:] = voice_hist[:2]

def update_event_clock():
    elapsed     = int(time.time() - call_start[0]) if call_start[0] > 0 else 0
    mins, secs  = divmod(elapsed, 60)
    linea       = fecha_hora_sistema() + f" [{mins:02d}:{secs:02d}]"
    txts2("t_hora", linea, 60)

# ─── SDS TEXTO (page4) ────────────────────────────────────────
def show_sds_text(issi_src, issi_dst, text):
    callsign, name, _ = lookup(issi_src)
    if current_page[0] != 4:
        send("page 4")
        current_page[0] = 4
        time.sleep(0.2)

    txts2("t_sfreq", f"Frec. TX:{TX_FREQ} Frec. RX:{RX_FREQ}", 45)
    txts2("t_sds",   f"{callsign} {name}", 35)
    txts2("t_hora",  fecha_hora_sistema(), 60)

    words = text.split()
    lines = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 <= 45:
            current = (current + " " + word).strip()
        else:
            if current: lines.append(current)
            current = word
    if current: lines.append(current)

    for i, field in enumerate(["t_smg","t_smg2","t_smg3","t_smg4","t_smg5"]):
        txts2(field, lines[i] if i < len(lines) else "", 45)

    print(f"[SDS texto] {callsign} → {issi_dst}: {text}")

# ─── EMERGENCIA (page3) ───────────────────────────────────────
def reverse_geocode(lat, lon):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
        r   = requests.get(url, timeout=5, headers={"User-Agent": "TETRA-Display/4.1 EA8DLF"})
        addr   = r.json().get("address", {})
        number = addr.get("house_number") or ""
        road   = addr.get("road") or addr.get("pedestrian") or addr.get("path") or ""
        city   = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("municipality") or ""
        street = f"{road} {number}".strip() if number else road
        return street, city
    except:
        return "", ""

def parse_emergency_text(text):
    result = {"issi":"","callsign":"","tg":"","gps":"Sin posicion","lat":None,"lon":None}
    m = re.search(r"ISSI\s+(\d+)", text);              result["issi"]     = m.group(1) if m else ""
    m = re.search(r"ISSI\s+\d+\s+(\w+)", text);        result["callsign"] = m.group(1) if m else ""
    m = re.search(r"TG\s+(\w+)", text);                result["tg"]       = m.group(1) if m else ""
    m = re.search(r"GPS:\s*\[?([0-9.-]+),([0-9.-]+)\]?", text)
    if m:
        result["lat"] = float(m.group(1))
        result["lon"] = float(m.group(2))
        result["gps"] = f"{m.group(1)}, {m.group(2)}"
    return result

def show_emergency(issi_src, text=""):
    parsed   = parse_emergency_text(text) if text else {}
    issi_real= parsed.get("issi") or issi_src
    cs_real  = parsed.get("callsign") or ""
    tg_real  = parsed.get("tg") or ""
    gps_txt  = parsed.get("gps") or "Sin posicion"
    lat, lon = parsed.get("lat"), parsed.get("lon")

    callsign, name, provincia = lookup(issi_real)
    if cs_real: callsign = cs_real

    calle, ciudad = reverse_geocode(lat, lon) if (lat and lon) else ("", provincia)

    if current_page[0] != 3:
        send("page 3")
        current_page[0] = 3
        time.sleep(0.2)

    txts2("t_emerg_call",  f"{callsign} {name}", 35)
    txts2("t_emerg_issi",  f"ISSI: {issi_real}", 22)
    txts2("t_emerg_tg",    f"TG: {tg_real}", 15)
    txts2("t_emerg_gps",   f"GPS: {gps_txt}", 35)
    txts2("t_ecalle",      calle[:40], 40)
    txts2("t_epob",        ciudad[:40], 40)
    txts2("t_emerg_hora",  fecha_hora(), 25)

    print(f"[EMERGENCIA] {callsign} ({issi_real}) TG:{tg_real} GPS:{gps_txt}")

# ─── PATRONES DE LOG ──────────────────────────────────────────
RE_RSSI       = re.compile(r"MsRssiUpdate \{ issi: (\d+), rssi_dbfs: ([-\d.]+) \}")
RE_REGISTER   = re.compile(r"BrewEntity: subscriber register issi=(\d+)")
RE_DEREGISTER = re.compile(r"BrewEntity: subscriber deregister issi=(\d+)")
RE_EMERG_TEXT = re.compile(r"CmceSdsData \{ source_issi: " + EMERGENCY_ISSI + r".*?\[(\d+(?:,\s*\d+)*)\]")
RE_EMERGENCY  = re.compile(r"SHORT_TRANSFER uuid=\S+ src=(\d+) dst=" + EMERGENCY_ISSI)
RE_SDS        = re.compile(r"SDS: U-SDS-DATA from ISSI (\d+) to ISSI (\d+), type=(\d+)")
RE_VOICE      = re.compile(r"rx_u_setup: call from ISSI (\d+) to (GSSI|ISSI) (\d+)")
RE_VOICE_P2P  = re.compile(r"rx_u_setup_p2p: call from ISSI (\d+) to ISSI (\d+)")
RE_NET_VOICE  = re.compile(r"BrewWorker: GROUP_TX uuid=(\S+) src=(\d+) dst=(\d+)")
RE_NET_SDS    = re.compile(r"BrewWorker: SHORT_TRANSFER uuid=\S+ src=(\d+) dst=(\d+)")
RE_NET_STALE  = re.compile(r"expiring stale pending SDS")
RE_NET_END    = re.compile(r"BrewWorker: GROUP_IDLE uuid=(\S+)|BrewEntity: group call ended uuid=(\S+)")
RE_LOCAL_END  = re.compile(r"DTxCeased|U-TX CEASED|release_group_call")

# ─── PROCESADO DE LOGS ────────────────────────────────────────
def process_line(line):
    if time.time() - connected_at[0] < 2: return

    m = RE_RSSI.search(line)
    if m: update_terminal(m.group(1), rssi=float(m.group(2))); return

    m = RE_REGISTER.search(line)
    if m:
        issi = m.group(1)
        if str(issi) not in SYSTEM_ISSI:
            t = terminals.setdefault(str(issi), {
                "rssi": 0, "rssi_time": 0, "tg": "?", "callsign": "", "online": False
            })
            t["online"] = True
            if not t["callsign"]: t["callsign"] = lookup(issi)[0]
            print(f"[terminal] ONLINE: {issi}")
            if STATE[0] == "STANDBY": refresh_terminals()
        return

    m = RE_DEREGISTER.search(line)
    if m:
        issi = m.group(1)
        if str(issi) in terminals:
            terminals[str(issi)]["online"] = False
            print(f"[terminal] OFFLINE: {issi}")
            if STATE[0] == "STANDBY": refresh_terminals()
        return

    m = RE_EMERG_TEXT.search(line)
    if m and not emergency_shown[0]:
        try:
            byte_list   = [int(b.strip()) for b in m.group(1).split(",")]
            text        = "".join(chr(b) for b in byte_list if 32 <= b < 128)
            mi          = re.search(r"ISSI\s+(\d+)", text)
            issi_emerg  = mi.group(1) if mi else (emergency_issi[0] or "?")
            emergency_shown[0] = True
            STATE[0]       = "EMERGENCIA"
            state_start[0] = time.time()
            call_start[0]  = time.time()
            show_emergency(issi_emerg, text)
        except Exception as e:
            print(f"[emerg] Error: {e}")
        return

    m = RE_EMERGENCY.search(line)
    if m:
        if str(m.group(1)) not in SYSTEM_ISSI:
            emergency_issi[0]  = m.group(1)
            emergency_shown[0] = False
        return

    if RE_NET_STALE.search(line): return

    m = RE_NET_END.search(line)
    if m:
        uuid = m.group(1) or m.group(2) or ""
        active_calls.pop(uuid, None)
        if STATE[0] == "VOZ":
            STATE[0]        = "POST_VOZ"
            state_start[0]  = time.time()
            voice_end_time[0]= time.time()
            print("[state] VOZ → POST_VOZ")
        return

    if RE_LOCAL_END.search(line):
        if STATE[0] == "VOZ":
            STATE[0]        = "POST_VOZ"
            state_start[0]  = time.time()
            voice_end_time[0]= time.time()
            print("[state] VOZ local → POST_VOZ")
        return

    m = RE_NET_VOICE.search(line)
    if m:
        uuid, issi_src, gssi_dst = m.group(1), m.group(2), m.group(3)
        if str(issi_src) in VOICE_FILTER: return
        active_calls[uuid] = (issi_src, gssi_dst)
        if STATE[0] == "VOZ": return
        STATE[0]       = "VOZ"
        call_start[0]  = time.time()
        state_start[0] = time.time()
        print(f"[state] → VOZ RED {issi_src} TG:{gssi_dst}")
        show_event(issi_src, "NET VOZ", tg=gssi_dst)
        return

    m = RE_NET_SDS.search(line)
    if m:
        issi_src, issi_dst = m.group(1), m.group(2)
        if str(issi_src) in SYSTEM_ISSI or issi_src == EMERGENCY_ISSI: return
        if str(issi_dst) in terminals:
            text = get_sds_text_from_journal(issi_dst)
            if text:
                STATE[0]       = "SDS"
                state_start[0] = time.time()
                call_start[0]  = time.time()
                show_sds_text(issi_src, issi_dst, text)
        return

    m = RE_VOICE_P2P.search(line)
    if m:
        issi_src, issi_dst = m.group(1), m.group(2)
        update_terminal(issi_src, tg=issi_dst)
        STATE[0]       = "VOZ"
        call_start[0]  = time.time()
        state_start[0] = time.time()
        print(f"[state] → VOZ PRIV {issi_src}")
        show_event(issi_src, "VOZ PRIV", issi_dst=issi_dst)
        return

    m = RE_VOICE.search(line)
    if m:
        issi_src, dst_type, dst_id = m.group(1), m.group(2), m.group(3)
        update_terminal(issi_src, tg=dst_id)
        STATE[0]       = "VOZ"
        call_start[0]  = time.time()
        state_start[0] = time.time()
        if dst_type == "GSSI":
            print(f"[state] → VOZ TG:{dst_id} desde {issi_src}")
            show_event(issi_src, "VOZ", tg=dst_id)
        else:
            print(f"[state] → VOZ PRIV {issi_src}")
            show_event(issi_src, "VOZ PRIV", issi_dst=dst_id)
        return

    m = RE_SDS.search(line)
    if m:
        issi_src, issi_dst, _ = m.group(1), m.group(2), m.group(3)
        if str(issi_dst) in terminals and str(issi_src) not in terminals:
            text = get_sds_text_from_journal(issi_dst)
            if text:
                STATE[0]       = "SDS"
                state_start[0] = time.time()
                call_start[0]  = time.time()
                show_sds_text(issi_src, issi_dst, text)

# ─── STREAM DE LOGS ───────────────────────────────────────────
def stream_logs():
    if not API_URL:
        print("[stream] Sin monitor configurado — modo sin stream")
        return
    while True:
        try:
            print("[stream] Conectando...")
            with requests.get(API_URL, stream=True, timeout=(10, None)) as r:
                r.raise_for_status()
                connected_at[0] = time.time()
                print("[stream] Conectado.")
                for raw in r.iter_lines():
                    if raw:
                        line = raw.decode("utf-8", errors="replace")
                        if line.startswith("data:"):
                            try:
                                process_line(json.loads(line[5:].strip()).get("line",""))
                            except json.JSONDecodeError:
                                pass
        except Exception as e:
            print(f"[stream] Error: {e}. Reconectando en 3s...")
            time.sleep(3)

# ─── BUCLE PRINCIPAL ──────────────────────────────────────────
def main_loop():
    while True:
        time.sleep(1)
        if STATE[0] == "STANDBY":
            pass
        elif STATE[0] == "VOZ":
            update_event_clock()
        elif STATE[0] == "POST_VOZ":
            if time.time() - state_start[0] >= CALL_MIN_DISPLAY:
                STATE[0] = "STANDBY"
                print("[state] POST_VOZ → STANDBY")
                show_standby()
            else:
                update_event_clock()
        elif STATE[0] == "SDS":
            if time.time() - state_start[0] >= SDS_DISPLAY:
                STATE[0] = "STANDBY"
                print("[state] SDS → STANDBY")
                show_standby()
            else:
                txts2("t_hora", fecha_hora_sistema(), 60)
        elif STATE[0] == "EMERGENCIA":
            if time.time() - state_start[0] >= EMERGENCY_DISPLAY:
                STATE[0]           = "STANDBY"
                emergency_issi[0]  = None
                emergency_shown[0] = False
                print("[state] EMERGENCIA → STANDBY")
                show_standby()
            else:
                txts2("t_emerg_hora", fecha_hora(), 25)

# ─── RELOJ STANDBY ────────────────────────────────────────────
def clock_standby():
    last = ""
    tick = 0
    while True:
        time.sleep(1)
        tick += 1
        if STATE[0] == "STANDBY" and current_page[0] == 0:
            h = hora()
            if h != last:
                last = h
                txts2("t_hora", h, 10)
            if tick % 10 == 0:
                refresh_terminals()

# ─── MAIN ─────────────────────────────────────────────────────
def main():
    print("[nextion] TETRA Nextion Display v4.1 - EA8DLF")
    print("[nextion] Compatible: TJC3224T028 (320×240) | TJC8048X543 (800×480)")
    print("[nextion] Repositorio: https://github.com/EA8DLF/Tetra_JCT_Nextion_Display")
    init_serial()
    time.sleep(1)
    send("page 0")
    current_page[0] = 0
    time.sleep(0.2)
    show_standby()
    threading.Thread(target=load_radioid,              daemon=True).start()
    threading.Thread(target=fetch_stats,               daemon=True).start()
    threading.Thread(target=stream_logs,               daemon=True).start()
    threading.Thread(target=clock_standby,             daemon=True).start()
    threading.Thread(target=init_terminals_from_journal, daemon=True).start()
    print("[nextion] En marcha. v4.1")
    main_loop()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        if ser: ser.close()
        print("\n[nextion] Saliendo.")

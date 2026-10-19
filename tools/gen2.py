# Erzeugt avarma.yaml (HA-Package). Aufruf: AVARMA_HOST=<gateway-ip> python3 gen2.py  (benötigt pyyaml + python-slugify bzw. HA-Python)
import json, yaml, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from params import P, addr
from homeassistant.util import slugify

REG = os.environ.get("AVARMA_REG", "/config/.storage/core.entity_registry")
HOST = os.environ.get("AVARMA_HOST", "192.168.0.101")   # IP des RS485-Ethernet-Gateways
U = {}
if os.path.exists(REG):
    for e in json.load(open(REG))["data"]["entities"]:
        if str(e.get("unique_id", "")).startswith("avarma_"):
            U[(e["entity_id"].split(".")[0], e["unique_id"])] = e["entity_id"]
def eid(domain, uid, name):
    return U.get((domain, uid)) or f"{domain}.{slugify(name)}"

HUB = "avarma"
# ---------- Live-Werte ----------
LIVE = [
 (4360,"aussen","Außentemperatur","int16",0.1,"°C",1,15,"temperature"),
 (4366,"vorlauf","Vorlauf TOut","int16",0.1,"°C",1,10,"temperature"),
 (4365,"ruecklauf","Rücklauf TIn","int16",0.1,"°C",1,10,"temperature"),
 (4358,"lamelle","Verdampfer Tc","int16",0.1,"°C",1,10,"temperature"),
 (4359,"heissgas","Heißgas Td","int16",0.1,"°C",1,10,"temperature"),
 (4361,"sauggas","Sauggas Ts","int16",0.1,"°C",1,10,"temperature"),
 (4362,"evi_ein","EVI Eintritt","int16",0.1,"°C",1,60,"temperature"),
 (4363,"evi_aus","EVI Austritt","int16",0.1,"°C",1,60,"temperature"),
 (4384,"raum_t2","Raumtemperatur T2","int16",0.1,"°C",1,60,"temperature"),
 (4380,"ipm","IPM Temperatur","int16",1,"°C",0,30,"temperature"),
 (4369,"diff_hk","Temperaturdifferenz Hauptkreis","int16",0.1,"K",1,30,None),
 (4373,"freq_ist","Kompressor Frequenz","uint16",1,"Hz",0,10,"frequency"),
 (4378,"freq_soll","Kompressor Frequenz Soll","uint16",1,"Hz",0,10,"frequency"),
 (4379,"strom","Kompressor Strom","uint16",0.1,"A",1,10,"current"),
 (4374,"luefter","Lüfter Drehzahl","uint16",1,"rpm",0,10,None),
 (4376,"eev","EEV Schritte","uint16",1,"P",0,10,None),
 (4368,"durchfluss","Durchfluss Q","uint16",0.1,"L/min",1,10,None),
 (4611,"pumpe","Pumpe C1 Leistung","uint16",1,"%",0,15,None),
 (4371,"hochdruck","Hochdruck Pd","uint16",0.01,"MPa",2,10,None),
 (4372,"niederdruck","Niederdruck Ps","uint16",0.01,"MPa",2,10,None),
 (4381,"netzspannung","Netzspannung","uint16",1,"V",0,30,"voltage"),
 (4367,"tdhw","Warmwasser TDHW","int16",0.1,"°C",1,30,"temperature"),
 (4364,"ty","Ty Kältemittel flüssig","int16",0.1,"°C",1,15,"temperature"),
 (4098,"vl_soll","Vorlauf Soll (P2)","uint16",1,"°C",0,60,"temperature"),
 (4099,"kuehl_soll","Kühlen Soll","uint16",1,"°C",0,300,"temperature"),
 (4100,"ww_soll","Warmwasser Soll","uint16",1,"°C",0,300,"temperature"),
 (4101,"raum_soll","Raum Soll","uint16",1,"°C",0,300,"temperature"),
 (4354,"status_roh","Betriebsstatus (roh)","uint16",1,None,0,15,None),
 (4390,"fehler0","Fehlerregister 0","uint16",1,None,0,10,None),
 (4391,"fehler1","Fehlerregister 1","uint16",1,None,0,10,None),
 (4387,"freqlimit","Frequenzbegrenzung (Bits)","uint16",1,None,0,30,None),
 (4609,"oelrueck","Ölrückführung (roh)","uint16",1,None,0,15,None),
 (4610,"betriebsstd","Kompressor Betriebsstunden","uint16",1,"h",0,600,"duration"),
 (4612,"modus_roh","Betriebsmodus (roh)","uint16",1,None,0,60,None),
 (4613,"abtau_anz","Abtauvorgänge","uint16",1,None,0,300,None),
 (6666,"abtau_gesperrt","Abtauung gesperrt (roh)","uint16",1,None,0,600,None),
 (4096,"ein_aus","Ein/Aus (roh)","uint16",1,None,0,15,None),
 (4097,"modus_wahl","Modus Wahl (roh)","uint16",1,None,0,60,None),
 (4103,"abtau_erzw","Abtauung erzwungen (roh)","uint16",1,None,0,60,None),
 # --- laut Hofman-Modbusliste (HE-AI-290 TDB 2025-11) ---
 (4370,"evi_diff","EVI Temperaturdifferenz","int16",0.1,"K",1,60,None),
 (4375,"luefter2","Lüfter 2 Drehzahl","uint16",1,"rpm",0,60,None),
 (4377,"evi_eev","EVI-EEV Schritte","uint16",1,"P",0,60,None),
 (4382,"dc_spannung","DC-Zwischenkreis Spannung","uint16",1,"V",0,30,"voltage"),
 (4383,"t6","T6 Fühler","int16",0.1,"°C",1,60,"temperature"),
 (4385,"verdampfer_temp","Verdampfungstemperatur","int16",0.1,"°C",1,15,"temperature"),
 (4386,"kondensator_temp","Kondensationstemperatur","int16",0.1,"°C",1,15,"temperature"),
 (4388,"soll_ww_calc","Berechnete Soll-Temp. 1","int16",0.1,"°C",1,30,"temperature"),
 (4389,"otc","Heizkurven-Soll OTC","int16",0.1,"°C",1,30,"temperature"),
 (4355,"ausgaenge","Ausgänge (Bits)","uint16",1,None,0,10,None),
 (4356,"eingaenge","Schalteingänge (Bits)","uint16",1,None,0,30,None),
 (4392,"fehler2","Fehlerregister 2","uint16",1,None,0,10,None),
 (4393,"fehler3","Fehlerregister 3","uint16",1,None,0,10,None),
 (4394,"fehler_drv0","Treiber-Fehler 0","uint16",1,None,0,15,None),
 (4395,"fehler_drv1","Treiber-Fehler 1","uint16",1,None,0,15,None),
 (4396,"fehler_drv2","Treiber-Fehler 2","uint16",1,None,0,15,None),
 (4397,"pumpe_pwm","Pumpe C1 PWM-Ausgang","uint16",1,None,0,30,None),
 (4398,"phasenstrom","Kompressor Phasenstrom","uint16",0.1,"A",1,15,"current"),
 (4608,"starts_wp","Kompressor-Starts gesamt","uint16",1,"Starts",0,30,None),
 (4614,"pumpe_c2","Pumpe C2 Leistung","uint16",1,"%",0,60,None),
 (4615,"sw_pcb","Software Platine","uint16",1,None,0,3600,None),
 (4616,"sw_hmi","Software Display","uint16",1,None,0,3600,None),
 (4617,"r290_konz","Kältemittel-Konzentration","uint16",0.1,"%",1,30,None),
 (4618,"r290_grenze","Kältemittel-Alarmgrenze","uint16",0.1,"%",1,3600,None),
 (4619,"r290_alarm","Kältemittel-Alarm (roh)","uint16",1,None,0,15,None),
 (4106,"uhr_datum","Uhr Monat/Tag (roh)","uint16",1,None,0,300,None),
 (4107,"uhr_zeit","Uhr Stunde/Minute (roh)","uint16",1,None,0,60,None),
] + [(4628+i,f"hist{i}",f"Fehlerspeicher {i+1}","uint16",1,None,0,120,None) for i in range(8)]
LIVE_P = {2: "vl_soll", 3: "kuehl_soll", 4: "ww_soll", 5: "raum_soll"}
sensors = []
for a,k,n,dt,sc,u,pr,scan,dc in LIVE:
    s = {"name": f"WP {n}", "unique_id": f"avarma_{k}", "slave": 1, "address": a, "input_type": "holding",
         "data_type": dt, "scale": sc, "precision": pr, "scan_interval": scan}
    if u: s["unit_of_measurement"] = u
    if dc: s["device_class"] = dc
    if a in (4362, 4363, 4364, 4367, 4384): s["nan_value"] = -32768
    if u and dc != "duration" and k not in LIVE_P.values(): s["state_class"] = "measurement"
    if k in ("betriebsstd", "starts_wp"): s["state_class"] = "total_increasing"
    sensors.append(s)
# ---------- Parameter lesen ----------
PSENS = {}
for p, sc, u, mn, mx, lvl, grp, name, desc in P:
    if p in LIVE_P:
        PSENS[p] = eid("sensor", f"avarma_{LIVE_P[p]}", f"WP {[l for l in LIVE if l[1]==LIVE_P[p]][0][2]}")
        continue
    n = f"WP P{p:02d} {name}"
    s = {"name": n, "unique_id": f"avarma_p{p:03d}", "slave": 1, "address": addr(p), "input_type": "holding",
         "data_type": "int16", "scale": sc, "precision": 2 if sc == 0.01 else (1 if sc == 0.1 else 0), "scan_interval": 900}
    if u: s["unit_of_measurement"] = u
    sensors.append(s)
    PSENS[p] = eid("sensor", f"avarma_p{p:03d}", n)
# ---------- Energie (Display-Zähler) ----------
EN = [(5120, 24, "e_prod_h", "Energie erzeugt Stunden (roh)"), (5254, 24, "e_verb_h", "Energie verbraucht Stunden (roh)"),
      (5144, 31, "e_prod_d", "Energie erzeugt Tage (roh)"), (5278, 31, "e_verb_d", "Energie verbraucht Tage (roh)"),
      (5175, 12, "e_prod_m", "Energie erzeugt Monate (roh)"), (5309, 12, "e_verb_m", "Energie verbraucht Monate (roh)"),
      (5187, 24, "e_ren_h", "Energie erneuerbar Stunden (roh)")]
for a, c, k, n in EN:
    sensors.append({"name": f"WP {n}", "unique_id": f"avarma_{k}", "slave": 1, "address": a, "input_type": "holding",
                    "data_type": "custom", "structure": f">{c}h", "count": c, "scan_interval": 300})
sensors.append({"name": "WP Energie erneuerbar Monat (roh)", "unique_id": "avarma_e_ren_m", "slave": 1, "address": 5251,
                "input_type": "holding", "data_type": "uint16", "scale": 0.1, "precision": 1, "unit_of_measurement": "kWh", "scan_interval": 300})
E = {k: eid("sensor", f"avarma_{k}", f"WP {n}") for a, c, k, n in EN}

S = lambda k, n: eid("sensor", f"avarma_{k}", n)
s_vl, s_rl, s_q = S("vorlauf","WP Vorlauf TOut"), S("ruecklauf","WP Rücklauf TIn"), S("durchfluss","WP Durchfluss Q")
s_f0, s_f1 = S("fehler0","WP Fehlerregister 0"), S("fehler1","WP Fehlerregister 1")
s_on, s_mode = S("ein_aus","WP Ein/Aus (roh)"), S("modus_wahl","WP Modus Wahl (roh)")
s_freq, s_oel, s_fl = S("freq_ist","WP Kompressor Frequenz"), S("oelrueck","WP Ölrückführung (roh)"), S("freqlimit","WP Frequenzbegrenzung (Bits)")
FREGS = [("fehler0","WP Fehlerregister 0"),("fehler1","WP Fehlerregister 1"),("fehler2","WP Fehlerregister 2"),("fehler3","WP Fehlerregister 3"),("fehler_drv0","WP Treiber-Fehler 0")]

pkg = {"modbus": [{"name": HUB, "type": "rtuovertcp", "host": HOST, "port": 502, "delay": 1, "timeout": 3,
                   "message_wait_milliseconds": 40, "sensors": sensors,
                   "switches": [{"name": "WP Ein/Aus", "unique_id": "avarma_switch_ein", "slave": 1, "address": 4096,
                                 "write_type": "holding", "command_on": 1, "command_off": 0, "scan_interval": 15,
                                 "verify": {"address": 4096, "input_type": "holding", "state_on": 1, "state_off": 0}}]}]}

# ---------- Freigabe (Codes wie am Display) ----------
pkg["input_text"] = {"wp_code": {"name": "WP Code eingeben", "mode": "password", "max": 8, "icon": "mdi:lock"}}
pkg["input_boolean"] = {"wp_benutzer_freigabe": {"name": "WP Benutzer-Freigabe", "icon": "mdi:lock-open-variant"},
                        "wp_techniker_freigabe": {"name": "WP Techniker-Freigabe", "icon": "mdi:account-hard-hat"}}

def lock_steps(lvl, p):
    flag = "input_boolean.wp_techniker_freigabe" if lvl == "T" else "input_boolean.wp_benutzer_freigabe"
    who = "Techniker-Code" if lvl == "T" else "Benutzer-Code (99) oder Techniker-Code"
    return [{"if": [{"condition": "state", "entity_id": flag, "state": "off"}],
             "then": [{"action": "persistent_notification.create",
                       "data": {"title": "Wärmepumpe: Parameter gesperrt",
                                "message": f"P{p:02d} wurde NICHT geändert. Zuerst {who} eingeben.",
                                "notification_id": "avarma_lock"}},
                      {"stop": "gesperrt"}]}]

numbers = []
for p, sc, u, mn, mx, lvl, grp, name, desc in P:
    if lvl == "X": continue
    se = PSENS[p]
    val = "{% set r = (value / " + str(sc) + ") | round(0) | int %}{{ r if r >= 0 else r + 65536 }}"
    n = {"name": f"WP Set P{p:02d} {name}", "unique_id": f"avarma_set_p{p:03d}",
         "state": "{{ states('" + se + "') | float(0) }}", "availability": "{{ has_value('" + se + "') }}",
         "min": mn, "max": mx, "step": sc,
         "set_value": lock_steps(lvl, p) + [
             {"action": "modbus.write_register", "data": {"hub": HUB, "slave": 1, "address": addr(p), "value": val}},
             {"delay": {"seconds": 2}},
             {"action": "homeassistant.update_entity", "target": {"entity_id": se}},
             {"action": "logbook.log", "data": {"name": "Wärmepumpe", "message": f"P{p:02d} {name} auf {{{{ value }}}} gesetzt", "entity_id": se}}]}
    if u: n["unit_of_measurement"] = u
    numbers.append(n)

nacht_sw = {"name": "WP Nachtmodus", "unique_id": "avarma_nachtmodus", "icon": "mdi:weather-night",
            "state": "{{ states('" + PSENS[17] + "') | int(0) == 1 }}", "availability": "{{ has_value('" + PSENS[17] + "') }}",
            "turn_on": [{"action": "modbus.write_register", "data": {"hub": HUB, "slave": 1, "address": addr(17), "value": 1}},
                        {"delay": {"seconds": 2}}, {"action": "homeassistant.update_entity", "target": {"entity_id": PSENS[17]}}],
            "turn_off": [{"action": "modbus.write_register", "data": {"hub": HUB, "slave": 1, "address": addr(17), "value": 0}},
                         {"delay": {"seconds": 2}}, {"action": "homeassistant.update_entity", "target": {"entity_id": PSENS[17]}}]}

def esum(e, div=10): return "{{ ((states('" + e + "').split(',') | map('int', 0) | sum) / " + str(div) + ") | round(1) }}"
def eavail(e): return "{{ has_value('" + e + "') and ',' in states('" + e + "') }}"
tpl_sensors = [
 {"name": "WP Spreizung VL-RL", "unique_id": "avarma_spreizung", "unit_of_measurement": "K", "state_class": "measurement",
  "state": "{{ (states('" + s_vl + "')|float(0) - states('" + s_rl + "')|float(0))|round(1) }}",
  "availability": "{{ has_value('" + s_vl + "') and has_value('" + s_rl + "') }}"},
 {"name": "WP Thermische Leistung", "unique_id": "avarma_waermeleistung", "unit_of_measurement": "kW", "device_class": "power", "state_class": "measurement",
  "state": "{% set q=states('" + s_q + "')|float(0) %}{% set dt=states('" + s_vl + "')|float(0)-states('" + s_rl + "')|float(0) %}{{ [q*dt*0.0698,0]|max|round(2) }}",
  "availability": "{{ has_value('" + s_q + "') }}"},
 {"name": "WP Modus", "unique_id": "avarma_modus_text",
  "state": "{{ {'2':'Heizen','4':'Kühlen','1':'Warmwasser','3':'Heizen+WW','5':'Kühlen+WW'}.get(states('" + s_mode + "'), states('" + s_mode + "')) }}",
  "availability": "{{ has_value('" + s_mode + "') }}"},
 {"name": "WP Ø Laufzeit pro Start heute", "unique_id": "avarma_avg_laufzeit", "unit_of_measurement": "min", "icon": "mdi:timer-outline",
  "state": "{% set h=states('sensor.wp_kompressor_laufzeit_heute')|float(0) %}{% set n=states('sensor.wp_kompressor_starts_heute')|int(0) %}{{ (h*60/n)|round(0) if n>0 else 0 }}"},
 {"name": "WP Wärme heute", "unique_id": "avarma_waerme_heute", "unit_of_measurement": "kWh", "device_class": "energy", "state_class": "total_increasing",
  "state": esum(E["e_prod_h"]), "availability": eavail(E["e_prod_h"])},
 {"name": "WP Strom heute", "unique_id": "avarma_strom_heute", "unit_of_measurement": "kWh", "device_class": "energy", "state_class": "total_increasing",
  "state": esum(E["e_verb_h"]), "availability": eavail(E["e_verb_h"])},
 {"name": "WP Wärme Monat (Display)", "unique_id": "avarma_waerme_monat_disp", "unit_of_measurement": "kWh", "device_class": "energy",
  "state": esum(E["e_prod_d"]), "availability": eavail(E["e_prod_d"])},
 {"name": "WP Strom Monat (Display)", "unique_id": "avarma_strom_monat_disp", "unit_of_measurement": "kWh", "device_class": "energy",
  "state": esum(E["e_verb_d"]), "availability": eavail(E["e_verb_d"])},
 {"name": "WP COP heute", "unique_id": "avarma_cop_heute", "icon": "mdi:approximately-equal",
  "state": "{% set w=states('sensor.wp_warme_heute')|float(0) %}{% set s=states('sensor.wp_strom_heute')|float(0) %}{{ (w/s)|round(2) if s>0 else 0 }}"},
]
tpl_bin = [
 {"name": "WP Ein", "unique_id": "avarma_ein", "state": "{{ states('" + s_on + "')|int(0) == 1 }}", "availability": "{{ has_value('" + s_on + "') }}"},
 {"name": "WP Kompressor läuft", "unique_id": "avarma_kompressor_laeuft", "device_class": "running", "delay_off": {"seconds": 45},
  "state": "{{ states('" + s_freq + "')|int(0) > 0 }}", "availability": "{{ has_value('" + s_freq + "') }}"},
 {"name": "WP Störung", "unique_id": "avarma_stoerung", "device_class": "problem",
  "state": "{{ " + " or ".join("states('" + S(k, n) + "')|int(0) > 0" for k, n in FREGS) + " }}", "availability": "{{ has_value('" + s_f0 + "') }}"},
 {"name": "WP Ölrückführung", "unique_id": "avarma_oelrueck", "state": "{{ states('" + s_oel + "')|int(0)|bitwise_and(1) > 0 }}", "availability": "{{ has_value('" + s_oel + "') }}"},
 {"name": "WP Modbus online", "unique_id": "avarma_modbus_online", "device_class": "connectivity", "state": "{{ has_value('" + s_vl + "') }}"},
] + [{"name": f"WP Frequenzbegrenzung {n}", "unique_id": f"avarma_flimit_{i}",
      "state": "{{ states('" + s_fl + "')|int(0)|bitwise_and(" + str(2**i) + ") > 0 }}"}
     for i, n in enumerate(["T3 Lamelle", "Hochdruck", "AC-Spannung", "Heißgas", "AC-Strom"])]
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "gen2_extra.py")).read())
pkg["template"] = [{"sensor": tpl_sensors, "binary_sensor": tpl_bin, "number": numbers, "switch": [nacht_sw], "select": [mode_sel], "button": buttons}]

KL = "binary_sensor.wp_kompressor_lauft"
pkg["sensor"] = [
 {"platform": "history_stats", "name": "WP Kompressor Laufzeit heute", "unique_id": "avarma_laufzeit_heute", "entity_id": KL,
  "state": "on", "type": "time", "start": "{{ today_at() }}", "end": "{{ now() }}"},
 {"platform": "history_stats", "name": "WP Kompressor Starts 24 h", "unique_id": "avarma_starts_24h", "entity_id": KL,
  "state": "on", "type": "count", "end": "{{ now() }}", "duration": {"hours": 24}},
]
um = {}
for k, n, c in [("tag", "heute", "daily"), ("woche", "Woche", "weekly"), ("monat", "Monat", "monthly"), ("jahr", "Jahr", "yearly")]:
    um[f"wp_kompressor_starts_{'heute' if k=='tag' else k}"] = {"name": f"WP Kompressor-Starts {n}", "unique_id": f"avarma_um_starts_{k}",
        "source": S("starts_wp", "WP Kompressor-Starts gesamt"), "cycle": c}
    if k != "tag":
        um[f"wp_warme_{k}"] = {"name": f"WP Wärme {n}", "unique_id": f"avarma_um_waerme_{k}", "source": "sensor.wp_warme_heute", "cycle": c}
        um[f"wp_strom_{k}"] = {"name": f"WP Strom {n}", "unique_id": f"avarma_um_strom_{k}", "source": "sensor.wp_strom_heute", "cycle": c}
pkg["utility_meter"] = um
pkg["automation"] = [
 {"id": "avarma_code", "alias": "WP: Code prüfen", "mode": "restart",
  "triggers": [{"trigger": "state", "entity_id": "input_text.wp_code"}],
  "conditions": [{"condition": "template", "value_template": "{{ trigger.to_state.state not in ['', 'unknown', 'unavailable'] }}"}],
  "actions": [
    {"choose": [
      {"conditions": [{"condition": "state", "entity_id": "input_text.wp_code", "state": "__TECH_SECRET__"}],
       "sequence": [{"action": "input_boolean.turn_on", "target": {"entity_id": ["input_boolean.wp_techniker_freigabe", "input_boolean.wp_benutzer_freigabe"]}}]},
      {"conditions": [{"condition": "state", "entity_id": "input_text.wp_code", "state": "99"}],
       "sequence": [{"action": "input_boolean.turn_on", "target": {"entity_id": "input_boolean.wp_benutzer_freigabe"}}]}],
     "default": [{"action": "persistent_notification.create", "data": {"title": "Wärmepumpe", "message": "Falscher Code.", "notification_id": "avarma_lock"}}]},
    {"action": "input_text.set_value", "target": {"entity_id": "input_text.wp_code"}, "data": {"value": ""}}]},
 {"id": "avarma_freigabe_timeout", "alias": "WP: Freigabe nach 15 min sperren", "mode": "parallel",
  "triggers": [{"trigger": "state", "entity_id": ["input_boolean.wp_benutzer_freigabe", "input_boolean.wp_techniker_freigabe"], "to": "on", "for": {"minutes": 15}}],
  "actions": [{"action": "input_boolean.turn_off", "target": {"entity_id": "{{ trigger.entity_id }}"}}]},
 {"id": "avarma_fehler_meldung", "alias": "WP: Fehler melden", "mode": "queued",
  "triggers": [{"trigger": "state", "entity_id": "sensor.wp_aktive_fehler"}],
  "conditions": [{"condition": "template", "value_template": "{{ trigger.to_state.state not in ['keine', 'unknown', 'unavailable'] and trigger.from_state is not none and trigger.from_state.state != trigger.to_state.state }}"}],
  "actions": [{"action": "persistent_notification.create", "data": {"title": "Wärmepumpe: Störung",
      "message": "Aktive Fehler: {{ state_attr('sensor.wp_aktive_fehler','details') | join(', ') }} ({{ now().strftime('%d.%m.%Y %H:%M') }})", "notification_id": "avarma_fehler"}},
     {"action": os.environ.get("AVARMA_NOTIFY", "notify.notify"), "continue_on_error": True, "data": {"title": "⚠️ Wärmepumpe: Störung",
      "message": "{{ state_attr('sensor.wp_aktive_fehler','details') | join(', ') }}",
      "data": {"push": {"interruption-level": "time-sensitive"}, "url": "/waermepumpe/fehler"}}}]},
]

pkg["automation"] += extra_autos
class D(yaml.SafeDumper): pass
D.add_representer(str, lambda d, s: d.represent_scalar('tag:yaml.org,2002:str', s, style="'" if any(c in s for c in "{}:#") else None))
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "avarma.yaml"), "w").write(
    "# Avarma (Hofman) R290 Wärmepumpe – Modbus RTU über RS485-Ethernet-Gateway (" + HOST + ":502).\n# Erzeugt von tools/gen2.py – https://github.com/ (siehe README).\n" +
    yaml.dump(pkg, Dumper=D, allow_unicode=True, sort_keys=False, width=4000).replace("'__TECH_SECRET__'", "!secret wp_code_techniker").replace("__TECH_SECRET__", "!secret wp_code_techniker"))
json.dump({"psens": PSENS}, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "psens.json"), "w"))
print("sensors", len(sensors), "numbers", len(numbers))

NOTIFY = os.environ.get("AVARMA_NOTIFY", "notify.notify")   # z. B. notify.mobile_app_mein_iphone
# --- Ergänzungen laut Hofman-Modbusliste (wird von gen2.py per exec geladen) ---
ERR = {1:"Außenfühler defekt",2:"Lamellenfühler defekt",3:"Sauggasfühler defekt",4:"EVI-Eintrittsfühler defekt",5:"EVI-Austrittsfühler defekt",
 6:"Heißgasfühler defekt",7:"Warmwasserfühler defekt",8:"Vorlauffühler defekt",9:"Rücklauffühler defekt",10:"Kältemittel-Flüssigkeitsfühler defekt",
 11:"Hochdrucksensor defekt",12:"Niederdrucksensor defekt",13:"Hochdruck-Schutz",14:"Niederdruck-Schutz",15:"Wasserdurchfluss zu gering",
 16:"Kommunikationsfehler",17:"Heißgastemperatur zu hoch",18:"EEPROM-Parameterfehler",99:"Kommunikation Treiberplatine",20:"IPM-Schutz",
 21:"Spannungsfehler",22:"Spreizung VL/RL zu groß",23:"Warmwasser-Frostschutz 2×",24:"Heizkreis-Frostschutz 2×",56:"Primärstrom-Schutz",
 26:"T6-Fühler defekt",27:"Außentemperatur über Grenze",28:"Rücklauf zu hoch (Kühlen)",29:"Raumfühler defekt",58:"Außentemperatur zu niedrig (T4)",
 32:"Vorlauf zu hoch (Heizen)",36:"Lüftertreiber Kommunikation",59:"VL/RL vertauscht oder 4-Wege-Ventil",40:"Vorlauf zu niedrig (Kühlen)",
 44:"DC-Lüftermotor 1",45:"DC-Lüftermotor 2",50:"Kondensator Überhitzung",51:"Kältemittel-Konzentration hoch (Leck!)"}
BITS = [(S("fehler0","WP Fehlerregister 0"), {b: b + 1 for b in range(16)}),
        (S("fehler1","WP Fehlerregister 1"), dict(enumerate([17,18,99,20,21,22,23,24,56,26,27,28,29,58,None,32]))),
        (S("fehler2","WP Fehlerregister 2"), {3:36,6:59,7:40,11:44,12:45}),
        (S("fehler3","WP Fehlerregister 3"), {1:50,2:51})]
DRV = {0:"IPM-Fehler",1:"Kompressor-Treiberfehler",2:"Kompressor-Überstrom",5:"IPM-Übertemperatur",6:"PFC-Fehler",7:"DC-Überspannung",
       8:"DC-Unterspannung",9:"AC-Spannung außerhalb",10:"AC-Überstrom",15:"Kommunikation Hauptplatine"}
s_drv = S("fehler_drv0","WP Treiber-Fehler 0")
jerr = "{" + ",".join(f"{k}:'{v}'" for k, v in ERR.items()) + "}"
def fault_list_jinja():
    j = "{% set ns = namespace(l=[]) %}"
    for ent, m in BITS:
        j += "{% set r = states('" + ent + "')|int(0) %}"
        for b, code in m.items():
            if code is None: continue
            j += "{% if r|bitwise_and(" + str(2**b) + ") %}{% set ns.l = ns.l + ['" + ("E%02d %s" % (code, ERR.get(code, ""))) + "'] %}{% endif %}"
    j += "{% set r = states('" + s_drv + "')|int(0) %}"
    for b, t in DRV.items():
        j += "{% if r|bitwise_and(" + str(2**b) + ") %}{% set ns.l = ns.l + ['E20 Treiber: " + t + "'] %}{% endif %}"
    return j
FL = fault_list_jinja()
HIST = [S(f"hist{i}", f"WP Fehlerspeicher {i+1}") for i in range(8)]
hist_j = "{% set m = " + jerr + " %}{% set ns = namespace(l=[]) %}" + "".join(
    "{% set c = states('" + h + "')|int(0) %}{% if c > 0 %}{% set ns.l = ns.l + ['E%02d %s'|format(c, m.get(c, 'unbekannt'))] %}{% endif %}" for h in HIST)
tpl_sensors += [
 {"name": "WP Aktive Fehler", "unique_id": "avarma_fehler_text",
  "state": FL + "{{ (ns.l | map('truncate', 3, True, '') | join(', ')) if ns.l else 'keine' }}",
  "attributes": {"details": FL + "{{ ns.l }}"}, "availability": "{{ has_value('" + S("fehler0","WP Fehlerregister 0") + "') }}"},
 {"name": "WP Fehlerspeicher", "unique_id": "avarma_fehlerspeicher", "icon": "mdi:history",
  "state": hist_j + "{{ ns.l | count }}", "attributes": {"liste": hist_j + "{{ ns.l }}"}},
 {"name": "WP Betrieb aktuell", "unique_id": "avarma_betrieb_text",
  "state": "{{ {'0':'Aus','1':'Warmwasser','2':'Heizen','4':'Kühlen'}.get(states('" + S("modus_roh","WP Betriebsmodus (roh)") + "'), 'unbekannt') }}"},
 {"name": "WP Uhr", "unique_id": "avarma_uhr", "icon": "mdi:clock-outline",
  "state": "{% set d = states('" + S("uhr_datum","WP Uhr Monat/Tag (roh)") + "')|int(0) %}{% set t = states('" + S("uhr_zeit","WP Uhr Stunde/Minute (roh)") + "')|int(0) %}"
           "{{ '%02d.%02d. %02d:%02d'|format(d % 256, d // 256, t // 256, t % 256) }}"},
 {"name": "WP Erneuerbar heute", "unique_id": "avarma_erneuerbar_heute", "unit_of_measurement": "kWh", "device_class": "energy",
  "state": esum(E["e_ren_h"]), "availability": eavail(E["e_ren_h"])},
 {"name": "WP Wärme Jahr (WP-Zähler)", "unique_id": "avarma_waerme_jahr_wp", "unit_of_measurement": "kWh", "device_class": "energy",
  "state": "{% set m = states('" + E["e_prod_m"] + "').split(',')|map('float',0)|list %}{% set d = states('" + E["e_prod_d"] + "').split(',')|map('float',0)|sum %}{% set c = m[now().month-1] %}{{ ((m|sum - c + [c, d]|max) / 10)|round(1) }}",
  "availability": eavail(E["e_prod_m"])},
 {"name": "WP Strom Jahr (WP-Zähler)", "unique_id": "avarma_strom_jahr_wp", "unit_of_measurement": "kWh", "device_class": "energy",
  "state": "{% set m = states('" + E["e_verb_m"] + "').split(',')|map('float',0)|list %}{% set d = states('" + E["e_verb_d"] + "').split(',')|map('float',0)|sum %}{% set c = m[now().month-1] %}{{ ((m|sum - c + [c, d]|max) / 10)|round(1) }}",
  "availability": eavail(E["e_verb_m"])},
 {"name": "WP JAZ Jahr", "unique_id": "avarma_jaz", "icon": "mdi:approximately-equal",
  "state": "{% set w=states('sensor.wp_warme_jahr_wp_zahler')|float(0) %}{% set s=states('sensor.wp_strom_jahr_wp_zahler')|float(0) %}{{ (w/s)|round(2) if s>0 else 0 }}"},
]
s_out, s_stat = S("ausgaenge","WP Ausgänge (Bits)"), S("status_roh","WP Betriebsstatus (roh)")
for b, n in [(0,"4-Wege-Ventil"),(1,"Öl-Heizung"),(3,"Pumpe C1"),(4,"Pumpe C2"),(5,"Pumpe C3"),(6,"E-Heizung E1"),(7,"E-Heizung E2"),(8,"Ventil G1"),(9,"Ventil G2")]:
    tpl_bin.append({"name": f"WP Ausgang {n}", "unique_id": f"avarma_out_{b}",
                    "state": "{{ states('" + s_out + "')|int(0)|bitwise_and(" + str(2**b) + ") > 0 }}", "availability": "{{ has_value('" + s_out + "') }}"})
for b, n in [(3,"Alarm"),(4,"Abtauung"),(8,"Legionellenschaltung"),(9,"Frostschutz"),(10,"Estrichtrocknung"),(11,"PV-Modus")]:
    tpl_bin.append({"name": f"WP {n} aktiv", "unique_id": f"avarma_stat_{b}",
                    "state": "{{ states('" + s_stat + "')|int(0)|bitwise_and(" + str(2**b) + ") > 0 }}", "availability": "{{ has_value('" + s_stat + "') }}"})
tpl_bin.append({"name": "WP Kältemittel-Alarm", "unique_id": "avarma_r290_alarm", "device_class": "gas",
                "state": "{{ states('" + S("r290_alarm","WP Kältemittel-Alarm (roh)") + "')|int(0) > 0 }}"})

MODES = {"Warmwasser": 1, "Heizen": 2, "Heizen + Warmwasser": 3, "Kühlen": 4, "Kühlen + Warmwasser": 5}
s_mw = S("modus_wahl","WP Modus Wahl (roh)")
mode_sel = {"name": "WP Betriebsart", "unique_id": "avarma_betriebsart", "icon": "mdi:hvac",
  "options": "{{ " + str(list(MODES)) + " }}",
  "state": "{{ " + str({str(v): k for k, v in MODES.items()}) + ".get(states('" + s_mw + "')) }}",
  "availability": "{{ has_value('" + s_mw + "') }}",
  "select_option": lock_steps("U", 1) + [
     {"action": "modbus.write_register", "data": {"hub": HUB, "slave": 1, "address": 4097, "value": "{{ " + str(MODES) + "[option] }}"}},
     {"delay": {"seconds": 2}}, {"action": "homeassistant.update_entity", "target": {"entity_id": s_mw}},
     {"action": "logbook.log", "data": {"name": "Wärmepumpe", "message": "Betriebsart auf {{ option }} gesetzt", "entity_id": s_mw}}]}
buttons = [
 {"name": "WP Fehler quittieren", "unique_id": "avarma_fehler_reset", "icon": "mdi:alert-remove",
  "press": [{"action": "modbus.write_register", "data": {"hub": HUB, "slave": 1, "address": 4104, "value": 1}},
            {"delay": {"seconds": 3}},
            {"action": "homeassistant.update_entity", "target": {"entity_id": [S(k, n) for k, n in FREGS]}},
            {"action": "logbook.log", "data": {"name": "Wärmepumpe", "message": "Fehler quittiert"}}]},
 {"name": "WP Uhr stellen", "unique_id": "avarma_uhr_stellen", "icon": "mdi:clock-edit",
  "press": [{"action": "modbus.write_register", "data": {"hub": HUB, "slave": 1, "address": 4106, "value": "{{ now().month * 256 + now().day }}"}},
            {"action": "modbus.write_register", "data": {"hub": HUB, "slave": 1, "address": 4107, "value": "{{ now().hour * 256 + now().minute }}"}},
            {"delay": {"seconds": 2}},
            {"action": "homeassistant.update_entity", "target": {"entity_id": [S("uhr_datum","WP Uhr Monat/Tag (roh)"), S("uhr_zeit","WP Uhr Stunde/Minute (roh)")]}}]},
]
extra_autos = [
 {"id": "avarma_uhr_sync", "alias": "WP: Uhr täglich stellen", "triggers": [{"trigger": "time", "at": "03:17:00"}],
  "actions": [{"action": "button.press", "target": {"entity_id": "button.wp_uhr_stellen"}}]},
 {"id": "avarma_r290_alarm", "alias": "WP: Kältemittel-ALARM (R290)", "mode": "single",
  "triggers": [{"trigger": "state", "entity_id": "binary_sensor.wp_kaltemittel_alarm", "to": "on"},
               {"trigger": "numeric_state", "entity_id": S("r290_konz","WP Kältemittel-Konzentration"), "above": 0},
               {"trigger": "template", "value_template": "{{ 'E51' in states('sensor.wp_aktive_fehler') }}"}],
  "actions": [
    {"action": "persistent_notification.create", "data": {"title": "⚠️ WÄRMEPUMPE: KÄLTEMITTEL-ALARM",
       "message": "Die Wärmepumpe meldet Kältemittel (R290/Propan) – Konzentration {{ states('sensor.wp_kaltemittel_konzentration') }} %, Fehler: {{ states('sensor.wp_aktive_fehler') }}. Keine Zündquellen, Bereich lüften, WP stromlos schalten, Fachbetrieb rufen.",
       "notification_id": "avarma_r290"}},
    {"action": NOTIFY, "continue_on_error": True, "data": {"title": "⚠️ Wärmepumpe: Kältemittel-ALARM",
       "message": "R290-Leck gemeldet ({{ states('sensor.wp_kaltemittel_konzentration') }} %). Keine Zündquellen, lüften, WP stromlos, Fachbetrieb rufen.",
       "data": {"push": {"sound": {"name": "default", "critical": 1, "volume": 1.0}, "interruption-level": "critical"}}}}]}]

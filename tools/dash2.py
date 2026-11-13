# Erzeugt das Dashboard für die Avarma-Integration.
#   python3 tools/dash2.py                      -> homeassistant/dashboards/waermepumpe.yaml
#   AVARMA_STORAGE=/config/.storage/ python3 tools/dash2.py  -> schreibt direkt lovelace.waermepumpe (Dashboard-URL "waermepumpe")
import json, shutil, time, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "custom_components", "avarma"))
from params import P
C = os.environ.get("AVARMA_STORAGE")
MAP = json.load(open(os.path.join(HERE, "entity_map.json")))  # Schlüssel -> Entity-ID der Integration
U = {"avarma_" + k: v for k, v in MAP.items()}
def E(k): return U["avarma_" + k]
FULL = {"columns": "full"}
def half(c): c = dict(c); c["grid_options"] = {"columns": 6}; return c
def full(c): c = dict(c); c["grid_options"] = FULL; return c

# ---------- Schema ----------
W, H = 1230, 670
def lbl(k, x, y, size=26, color="#ffffff", prefix=None, weight=700):
    el = {"type": "state-label", "entity": E(k), "style": {"left": f"{x/W*100:.2f}%", "top": f"{y/H*100:.2f}%", "color": color,
          "font-size": f"{size/W*100:.2f}cqw", "font-weight": str(weight), "white-space": "nowrap", "line-height": "1"}}
    if prefix: el["prefix"] = prefix
    return el
els = [lbl("aussen",250,80), lbl("luefter",72,150), *[dict(e, style=dict(e["style"], transform="translate(-100%,-50%)")) for e in (lbl("niederdruck",565,100), lbl("sauggas",565,165), lbl("hochdruck",830,100),
       lbl("heissgas",830,165))], lbl("lamelle",274,335), lbl("strom",650,292), lbl("freq_ist",650,342), lbl("eev",767,290,22),
       lbl("vorlauf",1140,145), lbl("durchfluss",1140,258), lbl("ruecklauf",1140,355), lbl("ty",886,452),
       lbl("kondensator_temp",1162,468,20), lbl("verdampfer_temp",1162,501,20), lbl("vl_soll",1162,534,20), lbl("pumpe",1162,567,20), lbl("tdhw",1162,600,20), lbl("ipm",1162,633,20)]
for i, (k, p) in enumerate([("modus_text","Modus: "),("fehler_text","Fehler: "),("waermeleistung","Wärmeleistung: "),("spreizung","Spreizung: ")]):
    e = lbl(k, 30, 545+i*30, 20, "#cfe3ff", p, 600); e["style"]["transform"] = "translate(0,-50%)"; els.append(e)
OUT_LABELS = [[("out_3","Heizpumpe"),("out_4","Zusatzpumpe"),("out_5","WW-Pumpe")],
              [("out_8","Ventil WW"),("out_9","Ventil 2"),("out_0","Abtauventil")],
              [("out_6","Heizstab 1"),("out_7","Heizstab 2"),("out_1","Öl-Heizung")]]
# Namen stehen fest im SVG (schema.svg), hier nur der Zustand: Ein = grün, Aus = rot
for col, items in enumerate(OUT_LABELS):
    for row, (k, p) in enumerate(items):
        for st, colr in (("on", "#4cd964"), ("off", "#ff5a4f")):
            e = lbl(k, 310 + col*175 + 155, 545 + row*30, 15, colr, None, 700); e["style"]["transform"] = "translate(-100%,-50%)"
            els.append({"type": "conditional", "conditions": [{"entity": E(k), "state": st}], "elements": [e]})

# --- drehende Symbole: Lüfter, Kompressor-Motor, Heizpumpe ---
def spin_icon(icon, x, y, size, on_conds, off_conds, dur):
    half = size / W * 100 / 2
    st = {"left": f"calc({x/W*100:.2f}% - {half:.2f}cqw)", "top": f"calc({y/H*100:.2f}% - {half:.2f}cqw)", "transform": "none",
          "--mdc-icon-size": f"{size/W*100:.2f}cqw", "width": f"{size/W*100:.2f}cqw", "height": f"{size/W*100:.2f}cqw",
          "color": "#e8eef5", "line-height": "0"}
    run = dict(st, animation=f"wpspin {dur}s linear infinite", color="#7cf03c")
    return [{"type": "conditional", "conditions": on_conds, "elements": [{"type": "icon", "icon": icon, "style": run, "tap_action": {"action": "none"}}]},
            {"type": "conditional", "conditions": off_conds, "elements": [{"type": "icon", "icon": icon, "style": st, "tap_action": {"action": "none"}}]}]
_fan, _komp, _pumpe = E("luefter"), E("kompressor_laeuft"), E("out_3")
els += spin_icon("mdi:fan", 70, 285, 80, [{"entity": _fan, "state_not": "0"}, {"entity": _fan, "state_not": "unavailable"}, {"entity": _fan, "state_not": "unknown"}],
                 [{"entity": _fan, "state": "0"}], 1.2)
els += spin_icon("mdi:cog", 650, 381, 30, [{"entity": _komp, "state": "on"}], [{"entity": _komp, "state": "off"}], 1.5)
els += spin_icon("mdi:pump", 1150, 300, 38, [{"entity": _pumpe, "state": "on"}], [{"entity": _pumpe, "state": "off"}], 2.0)
schema = {"type": "custom:avarma-schema-card", "image": "/avarma_static/schema.svg?v=11", "elements": els}

ein_btn = {"type": "button", "entity": E("switch_ein"), "name": "Wärmepumpe EIN / AUS", "show_state": True, "icon_height": "56px",
           "tap_action": {"action": "toggle", "confirmation": {"text": "Wärmepumpe wirklich ein- bzw. ausschalten?"}},
           "hold_action": {"action": "more-info"}}
bedienung = {"type": "entities", "title": "Bedienung", "show_header_toggle": False, "entities": [
    {"entity": E("switch_ein"), "name": "Wärmepumpe Ein/Aus"},
    {"entity": E("betriebsart"), "name": "Betriebsart"},
    {"entity": E("nachtmodus"), "name": "Nachtmodus"},
    {"entity": E("set_p002"), "name": "Vorlauf-Soll (P02)"},
    {"entity": E("set_p004"), "name": "Warmwasser-Soll (P04)"},
    {"type": "section", "label": "Zum Ändern: Benutzer-Freigabe einschalten bzw. Techniker-Code eingeben"},
    {"entity": "text.wp_code_eingeben", "name": "Code"},
    {"entity": "switch.wp_benutzer_freigabe", "name": "Benutzer-Freigabe (15 min)"},
    {"entity": "switch.wp_techniker_freigabe", "name": "Techniker-Freigabe (15 min)"},
    {"type": "section", "label": "Uhr der Wärmepumpe (wird täglich 03:17 gestellt)"},
    {"entity": E("uhr"), "name": "Uhr WP"},
    {"entity": E("uhr_stellen"), "name": "Uhr jetzt stellen"}]}
status = {"type": "entities", "title": "Status", "entities": [E(k) for k in ["ein","modus_text","betrieb_text","kompressor_laeuft","freq_soll","stoerung","fehler_text","stat_4","stat_8","stat_9","oelrueck","modbus_online","otc","ueberhitzung","unterkuehlung","temphub","raum_soll","netzspannung","dc_spannung","betriebsstd","starts_wp","abtau_anz","r290_konz","r290_alarm","raum_t2"]]}
def tile(k, name, icon=None):
    t = {"type": "tile", "entity": k if "." in k else E(k), "name": name, "vertical": True, "grid_options": {"columns": 4}}
    if icon: t["icon"] = icon
    return t
takt_tiles = [tile("sensor.wp_kompressor_starts_heute","Starts heute","mdi:counter"), tile("avg_laufzeit","Ø pro Start"),
              tile("laufzeit_heute","Laufzeit heute"),
              tile("sensor.wp_kompressor_starts_woche","Woche","mdi:counter"), tile("sensor.wp_kompressor_starts_monat","Monat","mdi:counter"),
              tile("sensor.wp_kompressor_starts_jahr","Jahr","mdi:counter"),
              half(tile("starts_24h","letzte 24 h","mdi:counter")), half(tile("starts_wp","Gesamt","mdi:counter"))]
limits = {"type": "entities", "title": "Frequenzbegrenzung aktiv", "entities": [E(f"flimit_{i}") for i in range(5)]}
hist = {"type": "history-graph", "title": "Temperaturen 24 h", "hours_to_show": 24, "entities": [E(k) for k in ["vorlauf","ruecklauf","aussen","lamelle"]]}
hist2 = {"type": "history-graph", "title": "Kompressor 24 h", "hours_to_show": 24, "entities": [E(k) for k in ["kompressor_laeuft","freq_ist","strom","leistung_el"]]}
hist3 = {"type": "history-graph", "title": "Drücke 24 h", "hours_to_show": 24, "entities": [E(k) for k in ["hochdruck","niederdruck"]]}
H2 = lambda t: {"type": "heading", "heading": t}

# Elektrische Leistung: U × I der WP, laufend am WP-Stromzähler abgeglichen (Faktor), dazu Herkunft jetzt
power_table = {"type": "markdown", "title": "Leistung jetzt", "grid_options": {"columns": 12}, "content":
  "{% set e = '" + E("leistung_el") + "' %}{% set p = states(e)|float(-1) %}{% set th = states('" + E("waermeleistung") + "')|float(0) %}"
  "{% set f = state_attr(e, 'faktor') %}{% set cop = states('" + E("cop_aktuell") + "') %}"
  "| | |\n|:--|--:|\n"
  "| ⚡ Leistung elektrisch | **{{ p | round(0) | int if p >= 0 else '–' }} W** |\n"
  "| Scheinleistung U × I | {{ state_attr(e, 'scheinleistung_va') or '–' }} VA |\n"
  "| Abgleich mit WP-Zähler | {{ ('%.3f' | format(f)) | replace('.', ',') if f else 'läuft noch' }} |\n"
  "| 🔥 Leistung thermisch | {{ ('%.2f' | format(th)) | replace('.', ',') }} kW |\n"
  "| COP aktuell | {{ cop | replace('.', ',') if cop not in ['unknown', 'unavailable', 'None'] else '–' }} |\n"
  "{% if state_attr(e, 'jetzt_netz_w') is not none %}"
  "| ☀️ davon PV | {{ state_attr(e, 'jetzt_pv_w') }} W |\n"
  "{% if states('sensor.wp_strom_aus_akku_heute') not in ['unknown', 'unavailable'] %}| 🔋 davon Akku | {{ state_attr(e, 'jetzt_akku_w') }} W |\n{% endif %}"
  "| 🔌 davon Netz | {{ state_attr(e, 'jetzt_netz_w') }} W |\n{% endif %}"
  "\n<small>Die WP meldet Spannung und Strom; U × I ist die Scheinleistung. Der Faktor gleicht sie laufend mit dem "
  "Stromzähler der WP ab, damit Watt und kWh zusammenpassen. Herkunft wie bei den kWh: Netz zuerst, dann Akku, Rest PV.</small>"}
r290 = [half({"type": "tile", "entity": E("r290_alarm"), "name": "Kältemittel-Leck (R290)", "vertical": True, "icon": "mdi:gas-cylinder"}),
        half({"type": "tile", "entity": E("r290_konz"), "name": "R290-Konzentration", "vertical": True, "icon": "mdi:molecule"})]
v_status = {"title": "Arbeitsstatus", "path": "arbeitsstatus", "icon": "mdi:heat-pump", "type": "sections", "max_columns": 3, "dense_section_placement": True, "sections": [
    {"type": "grid", "column_span": 2, "cards": [full(schema),
        full({"type": "statistics-graph", "title": "Energie pro Tag", "entities": [E("waerme_heute"), E("strom_heute")],
              "stat_types": ["change"], "period": "day", "days_to_show": 30, "chart_type": "bar"}),
        H2("Takte (Kompressor-Starts)")] + takt_tiles + [full(hist2), full(hist3), full(hist)]},
    {"type": "grid", "cards": [H2("Hauptbild"),
        {"type": "gauge", "entity": E("vorlauf"), "name": "TOut", "min": 10, "max": 60, "needle": True, "grid_options": {"columns": 6},
         "segments": [{"from": 10, "color": "#3fa9f5"}, {"from": 35, "color": "#43a047"}, {"from": 50, "color": "#ff9800"}]},
        {"type": "gauge", "entity": E("otc"), "name": "OTC (Heizkurve)", "min": 10, "max": 60, "grid_options": {"columns": 6}},
        tile("aussen", "Außen"), tile("sensor.wp_kompressor_starts_heute", "Starts heute", "mdi:counter"), tile("spreizung", "Spreizung VL–RL", "mdi:arrow-expand-vertical"),
        tile("cop_heute", "COP heute"), tile("modus_text", "Modus"), tile("kompressor_laeuft", "Kompressor"),
        tile("waerme_heute", "Wärme heute", "mdi:fire"), tile("strom_heute", "Strom heute", "mdi:flash"),
        tile("erneuerbar_heute", "Erneuerbar heute", "mdi:leaf"),
        tile("leistung_el", "Leistung elektrisch", "mdi:flash"), tile("waermeleistung", "Leistung thermisch", "mdi:fire"),
        tile("cop_aktuell", "COP aktuell"), power_table] + r290 + [
        full(ein_btn), full(bedienung), full(status), full(limits)]}]}

# ---------- Takte & Energie ----------
starts_bar = {"type": "statistics-graph", "title": "Kompressor-Starts pro Tag (30 Tage)", "entities": [E("starts_wp")],
              "stat_types": ["change"], "period": "day", "days_to_show": 30, "chart_type": "bar"}
starts_week = {"type": "statistics-graph", "title": "Kompressor-Starts pro Woche", "entities": [E("starts_wp")],
               "stat_types": ["change"], "period": "week", "days_to_show": 180, "chart_type": "bar"}
log_k = {"type": "logbook", "title": "Aufzeichnung Start/Stopp (48 h)", "hours_to_show": 48, "target": {"entity_id": [E("kompressor_laeuft"), E("switch_ein")]}}
def q(k, name, icon=None):  # Viertel-Kachel (4 pro Reihe)
    t = tile(k, name, icon); t["grid_options"] = {"columns": 3}; return t
def sub(text): return {"type": "heading", "heading": text, "heading_style": "subtitle"}
def w(t, cols): t = dict(t); t["grid_options"] = {"columns": cols}; return t
# Jetzt: gleiche Reihenfolge wie darunter (Wärme, Strom … COP), COP rechtsbündig unter den anderen COP-Kacheln
en_tiles = [sub("Jetzt"), w(q("waermeleistung","Wärmeleistung","mdi:fire"), 5), w(q("leistung_el","Stromaufnahme","mdi:flash"), 4),
            q("cop_aktuell","COP jetzt"),
            sub("Heute"), q("waerme_heute","Wärme","mdi:fire"), q("strom_heute","Strom","mdi:flash"),
            q("erneuerbar_heute","Erneuerbar","mdi:leaf"), q("cop_heute","COP"),
            sub("Woche"), q("sensor.wp_warme_woche","Wärme","mdi:fire"), q("sensor.wp_strom_woche","Strom","mdi:flash"),
            q("um_ren_week","Erneuerbar","mdi:leaf"), q("cop_woche","COP"),
            sub("Monat"), q("waerme_monat_disp","Wärme","mdi:fire"), q("strom_monat_disp","Strom","mdi:flash"),
            q("ren_monat_disp","Erneuerbar","mdi:leaf"), q("cop_monat","COP"),
            sub("Jahr"), q("waerme_jahr_wp","Wärme","mdi:fire"), q("strom_jahr_wp","Strom","mdi:flash"),
            q("ren_jahr_wp","Erneuerbar","mdi:leaf"), q("jaz","JAZ")]
en_bar = {"type": "statistics-graph", "title": "Energie pro Tag (Display-Zähler)", "entities": [E("waerme_heute"), E("strom_heute")],
          "stat_types": ["change"], "period": "day", "days_to_show": 30, "chart_type": "bar"}
en_hours = {"type": "markdown", "title": "Heute je Stunde (wie Display)", "content":
  "{% set p = states('" + E("e_prod_h") + "').split(',') %}{% set v = states('" + E("e_verb_h") + "').split(',') %}"
  "| Std | erzeugt | verbraucht |\n|---|---:|---:|\n{% for i in range(24) %}{% set a = (p[i]|float(0))/10 %}{% set b = (v[i]|float(0))/10 %}"
  "{% if a > 0 or b > 0 %}| {{ '%02d' % i }} | {{ a }} kWh | {{ b }} kWh |\n{% endif %}{% endfor %}"}
v_takte = {"title": "Takte & Energie", "path": "takte", "icon": "mdi:counter", "type": "sections", "max_columns": 3, "sections": [
    {"type": "grid", "cards": [H2("Kompressor-Starts")] + takt_tiles + [full(starts_bar), full(starts_week)]},
    {"type": "grid", "cards": [H2("Energie (Zähler der Wärmepumpe)")] + en_tiles + [full(en_bar)]},
    {"type": "grid", "cards": [H2("Verlauf heute"), full(log_k), full(en_hours)]}]}

# ---------- PV (optional, mit Netz-Sensor) und Einsparungen ----------
SAV = "sensor.wp_heizkosten_wp_jahr"
MON = "['Jänner','Februar','März','April','Mai','Juni','Juli','August','September','Oktober','November','Dezember']"
J_FMT = ("{% macro n(v, d=0) %}{{ '–' if v is none else ('%.*f' | format(d, v)) | replace('.', ',') }}{% endmacro %}"
         "{% set M = " + MON + " %}")
FUEL = [("oel", "Heizöl"), ("gas", "Gas"), ("pellets", "Pellets"), ("holz", "Stückholz")]
SRC_SER = [{"key": "pv", "name": "PV", "color": "#fbc02d"}, {"key": "akku", "name": "Akku", "color": "#26a69a"},
           {"key": "netz", "name": "Netz", "color": "#ef5350"}]
pv_source = {"type": "custom:avarma-source-card", "grid_options": FULL}
pv_days = {"type": "custom:avarma-bar-card", "entity": SAV, "title": "Je Tag (letzte 30 Tage)", "period": "tage", "field": "",
           "stacked": True, "decimals": 1, "unit": "kWh Strom der WP je Tag", "series": SRC_SER, "grid_options": FULL}
pv_month = {"type": "custom:avarma-bar-card", "entity": SAV, "title": "Je Monat", "period": "monate", "field": "",
            "stacked": True, "decimals": 0, "unit": "kWh Strom der WP je Monat", "series": SRC_SER, "grid_options": FULL,
            "note": "Monate vor der ersten Messung der Herkunft sind mit dem Jahresanteil geschätzt."}
PV_ON = [{"condition": "state", "entity": "sensor.wp_netzanteil_strom_heute", "state_not": "unavailable"}]
PV_OFF = [{"condition": "state", "entity": "sensor.wp_netzanteil_strom_heute", "state": "unavailable"}]
pv_hint = {"type": "markdown", "title": "PV-Anteil einrichten", "visibility": PV_OFF, "grid_options": FULL, "content":
    "Diese Seite zeigt, wie viel Strom der Wärmepumpe aus **PV**, **Akku** und **Netz** kommt. Dafür braucht die Integration "
    "die Netzleistung deines Hauses:\n\n**Einstellungen → Geräte & Dienste → Avarma → Konfigurieren**\n\n"
    "- **Netzleistung des Hauses**: Sensor in W, **+ = Bezug** aus dem Netz, − = Einspeisung (z. B. Smart Meter, Shelly 3EM, Wechselrichter)\n"
    "- **Akkuleistung** (optional): Sensor in W, **+ = Laden, − = Entladen**; zählt dein Sensor umgekehrt, den Schalter darunter einschalten\n\n"
    "Danach rechnet die Integration rückwirkend ab Jahresbeginn nach (soweit Home Assistant Statistiken hat). Details im README."}
for crd in (pv_source, pv_days, pv_month):
    crd["visibility"] = PV_ON
# breiter Bildschirm: Herkunft links, Diagramme rechts doppelt breit; am Handy alles untereinander
v_pv = {"title": "PV", "path": "pv", "icon": "mdi:solar-power-variant", "type": "sections", "max_columns": 3, "sections": [
    {"type": "grid", "cards": [pv_hint, pv_source]},
    {"type": "grid", "column_span": 2, "cards": [pv_days, pv_month]}]}

COL = {"wp": "#43a047", "oel": "#8d6e63", "gas": "#42a5f5", "pellets": "#ffb300", "holz": "#ef6c00"}
SER_ALL = [{"key": "wp", "name": "Wärmepumpe", "color": COL["wp"]}] + [{"key": k, "name": n, "color": COL[k]} for k, n in FUEL]
SER_KOST = SER_ALL[:1] + [{"key": "wp_ohne_pv", "name": "WP ohne PV", "color": "#a5d6a7"}] + SER_ALL[1:]  # nur mit PV sichtbar
def bars(title, field, unit, series, note=None, period="monate", **kw):
    c = {"type": "custom:avarma-bar-card", "entity": SAV, "title": title, "field": field, "unit": unit,
         "series": series, "period": period, "grid_options": FULL, **kw}
    if note: c["note"] = note
    return c
# Jahresübersicht: eine Zeile je Heizung, Einheit in jeder Zelle
sav_year = {"type": "markdown", "title": "Jahresübersicht", "grid_options": FULL, "content":
    J_FMT + "{% set ja = state_attr('" + SAV + "', 'jahre') or {} %}"
    "{% for y in ja.keys() | sort | reverse %}{% set r = ja[y] %}\n### {{ y }}\n"
    "Wärme von der WP: **{{ n(r.waerme) }} kWh** · Strom der WP: **{{ n(r.strom) }} kWh** (davon Netz {{ n(r.netz) }} kWh)\n\n"
    "| Heizung | Heizkosten | Ersparnis durch die WP | CO₂ gespart |\n|:--|--:|--:|--:|\n"
    "{% if r.kosten.wp_ohne_pv is defined and r.kosten.wp_ohne_pv is not none %}"
    "| **Wärmepumpe (mit PV)** | **{{ n(r.kosten.wp) }} €** | – | – |\n"
    "| Wärmepumpe ohne PV | {{ n(r.kosten.wp_ohne_pv) }} € | PV spart **{{ n(r.ersparnis.pv) }} €** | – |\n"
    "{% else %}| **Wärmepumpe** | **{{ n(r.kosten.wp) }} €** | – | – |\n{% endif %}"
    + "".join("| " + nm + " | {{ n(r.kosten." + k + ") }} € | **{{ n(r.ersparnis." + k + ") }} €** | {{ n(r.co2." + k + ") }} kg |\n" for k, nm in FUEL) +
    "{% endfor %}\n<small>Heizkosten = was dieselbe Wärme mit dieser Heizung gekostet hätte (inkl. Grundgebühr und Wartung). "
    "Ersparnis = Heizkosten der Heizung minus Heizkosten der WP. – = kein Preis eingetragen.</small>"}
sav_charts = [
    bars("Heizkosten je Monat", "kosten", "Euro je Monat", SER_KOST, hide_empty=True,
         note="So viel hätte die Wärme des Monats mit der jeweiligen Heizung gekostet (inkl. Grundgebühr und Wartung). Mit PV: „WP ohne PV“ = aller WP-Strom zum Netzpreis."),
    bars("Ersparnis durch die Wärmepumpe je Monat", "ersparnis", "Euro je Monat", SER_ALL[1:],
         "Heizkosten der jeweiligen Heizung minus Heizkosten der WP. Unter der Nulllinie = die WP war teurer."),
    bars("CO₂ gespart je Monat", "co2", "kg CO₂ je Monat", SER_ALL[1:],
         "CO₂ der jeweiligen Heizung für dieselbe Wärme minus CO₂ des Netzstroms der WP (Klimabilanz)."),
    bars("Ersparnis je Jahr", "ersparnis", "Euro je Jahr", SER_ALL[1:], period="jahre"),
]
# WP über die volle Breite, darunter die vier Alternativen nebeneinander (breiter Abschnitt = 24 Spalten)
def vis(t, v): t = dict(t); t["visibility"] = v; return t
sav_kpi = [vis(dict(tile(SAV, "Heizkosten Wärmepumpe", "mdi:heat-pump"), grid_options=FULL), PV_OFF)] + [
    vis(dict(tile(e, n, i), grid_options={"columns": 8}), PV_ON) for e, n, i in (
        (SAV, "Heizkosten WP (mit PV)", "mdi:heat-pump"),
        ("sensor.wp_heizkosten_wp_ohne_pv_jahr", "WP ohne PV", "mdi:transmission-tower"),
        ("sensor.wp_ersparnis_jahr_pv", "Ersparnis durch PV", "mdi:solar-power"))] + [
    dict(tile(f"sensor.wp_ersparnis_jahr_{k}", f"Ersparnis zu {n}", "mdi:piggy-bank-outline"), grid_options={"columns": 6})
    for k, n in FUEL]
# Heizwärmebedarf aus Tageswärme der WP und Außentemperatur
HWB = "sensor.wp_heizwaermebedarf_jahr"
sav_hwb = {"type": "markdown", "title": "Heizwärmebedarf (von der WP gedeckter Teil)", "grid_options": FULL, "content":
    J_FMT + "{% set h = states.sensor.wp_heizwaermebedarf_jahr.attributes if states.sensor.wp_heizwaermebedarf_jahr else {} %}"
    "{% if (h.tage or 0) < 7 %}Noch zu wenig Heiztage (unter 15 °C): {{ h.tage or 0 }} von mindestens 7. Die Werte erscheinen, sobald genug Daten da sind.\n"
    "{% else %}| Kennwert | Wert |\n|:--|--:|\n"
    "| **Heizlast** bei {{ n(h.nat, 1) }} °C Norm-Außentemperatur | **{{ n(h.heizlast_kw, 1) }} kW** |\n"
    "| **Heizwärmebedarf** pro Jahr (hochgerechnet) | **{{ n(h.jahr_kwh) }} kWh** |\n"
    "{% if h.kwh_m2 is not none %}| je m² Wohnfläche ({{ n(h.flaeche) }} m²) | **{{ n(h.kwh_m2) }} kWh/m²·Jahr** |\n{% endif %}"
    "| Heizgrenze (berechnet) | {{ n(h.heizgrenze, 1) }} °C |\n"
    "| Wärme je Heizgradtag | {{ n(h.kwh_je_kd, 1) }} kWh/Kd |\n"
    "| Datenbasis | {{ h.tage }} Heiztage, {{ n(h.q_gemessen) }} kWh, {{ n(h.hgt_gemessen) }} Kd |\n"
    "| Güte der Geraden (R²) | {{ n(h.r2, 2) }} |\n{% endif %}"
    "\n<small>Nur die Wärme laut Zähler der WP – heizen auch Ofen, Solar o. Ä. mit, ist der echte Bedarf des Hauses höher. "
    "<b>Heizlast</b>: Gerade aus Tageswärme und mittlerer Außentemperatur der Heiztage, abgelesen bei der Norm-Außentemperatur. "
    "<b>Jahresbedarf</b>: gemessene Wärme ÷ gemessene Heizgradtage (20/12) × Heizgradtage eines normalen Jahres am Standort. "
    "Werte rechts unter „Haus“ anpassen. Außentemperatur vom Fühler der WP (kann in der Sonne zu hoch sein). "
    "Je mehr kalte Tage, desto genauer; R² nahe 1 = Punkte liegen gut auf der Geraden.</small>"}
def prices(title, keys):
    return {"type": "entities", "title": title, "state_color": False, "grid_options": FULL,
            "entities": [f"number.wp_preis_{k}" for k in keys]}
sav_hint = {"type": "markdown", "title": "So wird gerechnet", "grid_options": FULL, "content":
    "<small>Grundlage ist die <b>Wärme</b>, die die WP laut eigenem Zähler geliefert hat, je Monat.<br>"
    "<b>WP</b>: Netzstrom × (Arbeitspreis + Netzkosten) + Strom aus PV/Akku × Einspeisevergütung (entgangener Ertrag) + Grundgebühr/12 + Wartung/12.<br>"
    "<b>Alternativen</b>: Brennstoff = Wärme ÷ Nutzungsgrad (Öl 92 %, Gas 95 %, Pellets 90 %, Holz 75 %); "
    "Heizwerte: Öl 10 kWh/l, Pellets 4,9 kWh/kg, Stückholz 1.900 kWh/Raummeter (Hartholz), Gas lt. Umrechnung von der Rechnung. "
    "Dazu Grundgebühr (Gas) und Wartung inkl. Rauchfangkehrer je 1/12 pro Monat.<br>"
    "<b>Gas und Pellets</b>: Es genügt einer der beiden Preise (€/kWh oder €/m³ bzw. €/kg oder €/t), der andere wird umgerechnet.<br>"
    "<b>CO₂</b>: Klimabilanz Öl 0,310 · Gas 0,247 · Pellets 0,036 · Holz 0,020 kg je kWh Brennstoff, WP nur der Netzstrom mit 0,227 kg/kWh.<br>"
    "Gerechnet wird immer mit den aktuell eingetragenen Preisen, auch für vergangene Monate. Monate vor der ersten Messung der Herkunft (*) gelten als Netzstrom. "
    "Ohne Netz-Sensor in den Optionen (siehe Seite PV) zählt der gesamte WP-Strom als Netzstrom, die Einspeisevergütung spielt dann keine Rolle.</small>"}
v_spar = {"title": "Einsparungen", "path": "einsparungen", "icon": "mdi:piggy-bank", "type": "sections", "max_columns": 3, "sections": [
    {"type": "grid", "column_span": 2, "cards": [H2("Laufendes Jahr")] + sav_kpi + [sav_year, sav_hwb] + sav_charts},
    {"type": "grid", "cards": [H2("Preise und Fixkosten"),
        prices("Strom (Wärmepumpe)", ["strom_preis", "strom_netz", "strom_grund", "strom_einspeis", "wp_wartung"]),
        prices("Heizöl", ["oel_l", "oel_wartung"]),
        prices("Gas", ["gas_kwh", "gas_m3", "gas_hs", "gas_grund", "gas_wartung"]),
        prices("Pellets", ["pellet_kg", "pellet_t", "pellet_wartung"]),
        prices("Stückholz", ["holz_rm", "holz_wartung"]),
        {"type": "entities", "title": "Haus (für HWB)", "state_color": False, "grid_options": FULL,
         "entities": ["number.wp_haus_flaeche", "number.wp_haus_nat", "number.wp_haus_hgt"]}, sav_hint]}]}

# ---------- Fehler ----------
fehler_info = {"type": "markdown", "content":
  "## Aktive Fehler\n{% set l = state_attr('" + E("fehler_text") + "','details') or [] %}"
  "{% if l %}{% for f in l %}- **{{ f }}**\n{% endfor %}{% else %}✅ Keine aktive Störung.{% endif %}\n\n"
  "## Fehlerspeicher der Wärmepumpe\n{% set h = state_attr('" + E("fehlerspeicher") + "','liste') or [] %}"
  "{% if h %}{% for f in h %}{{ loop.index }}. {{ f }}\n{% endfor %}{% else %}leer{% endif %}"}
quit_btn = {"type": "button", "entity": E("fehler_reset"), "name": "Fehler quittieren", "icon": "mdi:alert-remove", "icon_height": "48px",
            "show_state": False, "tap_action": {"action": "perform-action", "perform_action": "button.press", "target": {"entity_id": E("fehler_reset")}, "confirmation": {"text": "Fehler an der Wärmepumpe quittieren?"}}}
log_f = {"type": "logbook", "title": "Fehlerprotokoll Home Assistant (30 Tage)", "hours_to_show": 720, "target": {"entity_id": [E("fehler_text"), E("stoerung")]}}
v_fehler = {"title": "Fehler", "path": "fehler", "icon": "mdi:alert", "type": "sections", "max_columns": 2, "sections": [
    {"type": "grid", "cards": [full(fehler_info), full(quit_btn), full({"type": "entities", "entities": [E("stoerung"), E("fehler_text"), E("stat_3"), E("r290_alarm")]})]},
    {"type": "grid", "cards": [full(log_f)]}]}

# ---------- Parameter ----------
ORDER = ["Heizen & Heizkurve", "Warmwasser & Legionellen", "Nachtmodus", "Pumpen & Durchfluss", "E-Heizung & 2. Wärmeerzeuger",
         "Estrichtrocknung", "System & Funktionen", "Kompressor", "Abtauung", "Lüfter", "Expansionsventil / EVI / Überhitzung", "Schutzfunktionen", "Sonstige"]
freigabe = {"type": "entities", "title": "Freigabe", "show_header_toggle": False, "entities": [
    {"entity": "text.wp_code_eingeben", "name": "Code eingeben"},
    {"entity": "switch.wp_benutzer_freigabe", "name": "Benutzer-Freigabe (Schalter oder Code 99)"},
    {"entity": "switch.wp_techniker_freigabe", "name": "Techniker-Freigabe"}],
    "footer": None}
freigabe.pop("footer")
def param_view(level, title, path, note):
    secs = [{"type": "grid", "cards": [full({"type": "markdown", "content": note}), full(freigabe),
             full({"type": "button", "name": "← zurück", "icon": "mdi:arrow-left", "tap_action": {"action": "navigate", "navigation_path": "/waermepumpe/parameter"}})]}]
    for g in ORDER:
        rows = [p for p in P if p[6] == g and p[5] == level and ("avarma_set_p%03d" % p[0]) in U]
        if not rows: continue
        ents = [{"entity": U["avarma_set_p%03d" % p[0]], "name": f"P{p[0]:02d} · {p[7]}"} for p in rows]
        md = "\n".join(f"**P{p[0]:02d} {p[7]}** – {p[8]}" for p in rows if p[8])
        cards = [full({"type": "entities", "title": g, "entities": ents})]
        if md: cards.append(full({"type": "markdown", "content": md}))
        secs.append({"type": "grid", "cards": cards})
    return {"title": title, "path": path, "subview": True, "back_path": "/waermepumpe/parameter", "type": "sections", "max_columns": 3, "sections": secs}
v_user = param_view("U", "Benutzer-Parameter", "benutzer",
    "### Benutzer-Parameter (Code 99)\nEntspricht den **blauen** Feldern am Display. Zum Ändern zuerst die Benutzer-Freigabe einschalten (oder Code 99 eingeben) – sie gilt 15 Minuten. "
    "Jede Änderung wird direkt in die Wärmepumpe geschrieben und im Logbuch vermerkt.")
v_tech = param_view("T", "Techniker-Parameter", "techniker",
    "### Techniker-Parameter\nEntspricht den **weißen** Feldern am Display.\n\n⚠️ **ACHTUNG – GEFÄHRLICH:** Diese Parameter steuern Kältekreis, Verdichter, Schutz- und Abtaufunktionen. Falsche Werte können die Wärmepumpe in Dauerstörung bringen, den Verdichter beschädigen oder Schutzfunktionen aushebeln. **Nur ändern, wenn du genau weißt, was der Parameter bewirkt** – im Zweifel Hersteller oder Fachbetrieb fragen. Werksreset (P87), RS485-Adresse (P108) und Kompressormodell (P39) sind bewusst gesperrt.")
def navbtn(name, icon, path):
    return full({"type": "button", "name": name, "icon": icon, "icon_height": "64px", "tap_action": {"action": "navigate", "navigation_path": path}})
nacht = {"type": "entities", "title": "Nachtmodus", "entities": [
    {"entity": E("betriebsart"), "name": "Betriebsart"},
    {"entity": E("nachtmodus"), "name": "Nachtmodus"},
    {"entity": E("set_p015"), "name": "Start (Uhr)"}, {"entity": E("set_p016"), "name": "Ende (Uhr)"}]}
v_param = {"title": "Parameter", "path": "parameter", "icon": "mdi:tune", "type": "sections", "max_columns": 3, "sections": [
    {"type": "grid", "cards": [navbtn("Benutzer-Parameter", "mdi:account", "/waermepumpe/benutzer")]},
    {"type": "grid", "cards": [navbtn("Techniker-Parameter", "mdi:account-hard-hat", "/waermepumpe/techniker")]},
    {"type": "grid", "cards": [full(nacht), full(freigabe)]}]}

def _amp(v, rules):
    # rules: Liste (grenze_bis, ampel, text) aufsteigend; letzte Regel ohne Grenze
    return rules
KK_MD = (
 "{% set run = is_state('" + E("kompressor_laeuft") + "','on') %}"
 "{% set ts = states('" + E("sauggas") + "')|float(0) %}{% set ty = states('" + E("ty") + "')|float(0) %}"
 "{% set tl = states('" + E("verdampfer_temp") + "')|float(0) %}{% set th = states('" + E("kondensator_temp") + "')|float(0) %}"
 "{% set ta = states('" + E("aussen") + "')|float(0) %}{% set vl = states('" + E("vorlauf") + "')|float(0) %}{% set rl = states('" + E("ruecklauf") + "')|float(0) %}"
 "{% macro amp(v, g1, y1, y2, r2) %}{% if v < g1 %}🔴{% elif v < y1 %}🟡{% elif v <= y2 %}🟢{% elif v <= r2 %}🟡{% else %}🔴{% endif %}{% endmacro %}"
 "## Kältekreis-Ampel\n"
 "{% if not run %}> ℹ️ **Der Kompressor steht.** Die Kennwerte sind nur im Betrieb aussagekräftig – im Stillstand gleichen sich die Drücke an. Die Tabelle zeigt deshalb nur Werte, wenn der Kompressor läuft.\n\n{% endif %}"
 "| Kennwert | Formel | aktuell | Richtwert | |\n|---|---|---:|---|:-:|\n"
 "{% if run %}"
 "| **Überhitzung** | Ts − TL | {{ (ts-tl)|round(1) }} K | 2 … 8 K | {{ amp(ts-tl, 1, 2, 8, 12) }} |\n"
 "| **Unterkühlung** | TH − Ty | {{ (th-ty)|round(1) }} K | 1 … 8 K | {{ amp(th-ty, 0, 1, 8, 12) }} |\n"
 "| **Temperaturhub** | TH − TL | {{ (th-tl)|round(1) }} K | ≤ 40 K | {{ amp(th-tl, -99, -99, 40, 50) }} |\n"
 "| **Abstand Luft → Verdampfung** | Außen − TL | {{ (ta-tl)|round(1) }} K | 3 … 10 K | {{ amp(ta-tl, 1, 3, 10, 14) }} |\n"
 "| **Abstand Kondensation → Vorlauf** | TH − TOut | {{ (th-vl)|round(1) }} K | 1 … 6 K | {{ amp(th-vl, -1, 1, 6, 10) }} |\n"
 "| **Spreizung Heizwasser** | TOut − TIn | {{ (vl-rl)|round(1) }} K | 3 … 7 K | {{ amp(vl-rl, 1, 3, 7, 10) }} |\n"
 "{% else %}| alle Kennwerte | – | – | – | ⚪ |\n{% endif %}"
 "\n🟢 im Richtwert · 🟡 auffällig, beobachten · 🔴 deutlich daneben\n\n"
 "_Richtwerte sind allgemeine Erfahrungswerte für Luft/Wasser-Wärmepumpen mit R290, keine Herstellerangaben. Kurz nach dem Start, beim Abtauen und während der Ölrückführung sind Ausreißer normal – entscheidend ist der stabile Betrieb über einige Minuten._"
)
KK_TXT = """## So hängt alles zusammen

Der Kältekreis „pumpt“ Wärme von der Außenluft ins Heizwasser – auf zwei Temperaturniveaus:

```
Außenluft  ──(Verdampfer, Lüfter)──▶  TL  Verdampfungstemperatur  (niedriger Druck Ps)
                                        │  Verdichter hebt die Temperatur an
Heizwasser ◀──(Plattenwärmetauscher)──  TH  Kondensationstemperatur (hoher Druck Pd)
```

**TL – Verdampfungstemperatur.** Bei dieser Temperatur verdampft das Kältemittel im Außenregister. Sie liegt **einige Grad unter der Außenluft** – nur so kann die Luft Wärme abgeben. Berechnet aus dem Niederdruck **Ps**.

**TH – Kondensationstemperatur.** Bei dieser Temperatur wird das Kältemittel im Plattenwärmetauscher wieder flüssig und gibt dabei die Wärme ans Heizwasser ab. Sie liegt **etwas über dem Vorlauf (TOut)**. Berechnet aus dem Hochdruck **Pd**.

**Überhitzung (Ts − TL).** Um so viel ist das Sauggas wärmer als der Siedepunkt, bevor es in den Verdichter geht. Das Expansionsventil (EEV) regelt darauf.
- **zu niedrig (< 2 K):** Gefahr, dass flüssiges Kältemittel in den Verdichter gelangt („Nasslaufen“) – schädlich für den Verdichter.
- **zu hoch (> 10 K):** Verdampfer wird schlecht genutzt, Heißgas wird sehr heiß. Hinweise auf zu wenig Kältemittel (Leck!) oder ein zu weit geschlossenes EEV.

**Unterkühlung (TH − Ty).** Um so viel ist das flüssige Kältemittel nach dem Wärmetauscher kälter als der Kondensationspunkt.
- **sehr klein (< 1 K):** eher zu wenig Kältemittel – zusammen mit hoher Überhitzung ein typisches Zeichen für einen Kältemittelverlust.
- **sehr groß (> 10 K):** eher zu viel Kältemittel oder Probleme im Wärmetauscher.

**Temperaturhub (TH − TL).** So viel „Höhe“ muss der Verdichter überwinden. **Je kleiner, desto effizienter** (höherer COP). Ein niedriger Vorlauf (Fußbodenheizung, flache Heizkurve) hält den Hub klein.

**Abstand Außen → TL.** Wird der Abstand immer größer (> 12 K), ist der Verdampfer vereist oder der Lüfter fördert zu wenig Luft → Abtauung fällig.

**Abstand TH → Vorlauf.** Wird er groß (> 8 K), kommt die Wärme schlecht ins Wasser: zu wenig Durchfluss (Filter, Ventile, Luft im System) oder verschmutzter Plattenwärmetauscher.

**Spreizung TOut − TIn.** Die Pumpe regelt laut P58 auf etwa 5 K. Viel größere Spreizung = zu wenig Durchfluss.

### Typische Muster
| Beobachtung | mögliche Ursache |
|---|---|
| Überhitzung hoch **und** Unterkühlung niedrig | Kältemittelmangel / Leck → Fachbetrieb |
| Überhitzung sehr niedrig, Td niedrig | EEV zu weit offen, Gefahr Nasslaufen |
| Außen − TL wächst stetig | Verdampfer vereist, Lüfter |
| TH − TOut groß, Spreizung groß | zu wenig Wasserdurchfluss |
| Hub sehr groß | Vorlauf zu hoch → Heizkurve senken spart Strom |

> ⚠️ Diese Ampel ist eine Orientierungshilfe, keine Diagnose. Arbeiten am Kältekreis (R290!) nur durch einen zertifizierten Fachbetrieb.
"""
kk_hist = {"type": "history-graph", "title": "Kennwerte 24 h (nur bei laufendem Kompressor)", "hours_to_show": 24,
           "entities": [E("ueberhitzung"), E("unterkuehlung"), E("temphub")]}
kk_temps = {"type": "history-graph", "title": "TH / TL / Außen / Vorlauf 24 h", "hours_to_show": 24,
            "entities": [E("kondensator_temp"), E("verdampfer_temp"), E("aussen"), E("vorlauf")]}
kk_tiles = [tile("kondensator_temp","TH Kondensation","mdi:thermometer-high"), tile("verdampfer_temp","TL Verdampfung","mdi:thermometer-low"),
            tile("ueberhitzung","Überhitzung"), tile("unterkuehlung","Unterkühlung"), tile("temphub","Temperaturhub"), tile("kompressor_laeuft","Kompressor")]
v_kk = {"title": "Kältekreis", "path": "kaeltekreis", "icon": "mdi:snowflake-thermometer", "type": "sections", "max_columns": 3, "sections": [
    {"type": "grid", "cards": [H2("Live-Werte")] + kk_tiles + [full({"type": "markdown", "content": KK_MD}), full(kk_hist), full(kk_temps)]},
    {"type": "grid", "column_span": 2, "cards": [full({"type": "markdown", "content": KK_TXT})]}]}
diag = {"type": "entities", "title": "Rohwerte / noch nicht zugeordnet", "entities": [E(k) for k in
        ["status_roh","ausgaenge","eingaenge","modus_roh","ein_aus","modus_wahl","fehler0","fehler1","fehler2","fehler3","fehler_drv0","fehler_drv1","fehler_drv2","freqlimit","abtau_gesperrt","abtau_erzw","evi_ein","evi_aus","evi_diff","evi_eev","diff_hk","luefter2","t6","verdampfer_temp","kondensator_temp","soll_ww_calc","otc","pumpe_pwm","pumpe_c2","phasenstrom","sw_pcb","sw_hmi","r290_grenze","uhr_datum","uhr_zeit"] + [f"hist{i}" for i in range(8)] + ["out_%d" % b for b in (0,1,3,4,5,6,7,8,9)] + ["stat_%d" % b for b in (3,4,8,9,10,11)]]}
v_diag = {"title": "Diagnose", "path": "diagnose", "icon": "mdi:stethoscope", "type": "masonry", "cards": [diag]}

cfg = {"views": [v_status, v_takte, v_pv, v_spar, v_kk, v_fehler, v_param, v_user, v_tech, v_diag]}
if C:
    ts = time.strftime("%Y%m%d_%H%M%S")
    if os.path.exists(C + "lovelace.waermepumpe"): shutil.copy(C + "lovelace.waermepumpe", C + "lovelace.waermepumpe.bak_" + ts)
    json.dump({"version": 1, "minor_version": 1, "key": "lovelace.waermepumpe", "data": {"config": cfg}}, open(C + "lovelace.waermepumpe", "w"), ensure_ascii=False, indent=1)
else:
    import yaml
    class D(yaml.SafeDumper):
        def ignore_aliases(self, data): return True
    D.add_representer(str, lambda d, v: d.represent_scalar('tag:yaml.org,2002:str', v, style='|' if '\n' in v else None))
    txt = yaml.dump(cfg, Dumper=D, allow_unicode=True, sort_keys=False, width=4000)
    open(os.path.join(HERE, "..", "custom_components", "avarma", "dashboard.yaml"), "w").write(
        "# Wird von tools/dash2.py erzeugt und von der Integration als Dashboard /waermepumpe bereitgestellt.\n" + txt)
    out = os.path.join(HERE, "..", "homeassistant", "dashboards", "waermepumpe.yaml")
    open(out, "w").write("# Dashboard „Wärmepumpe“ – in HA: Einstellungen → Dashboards → Neu → (leer) → ⋮ → Raw-Konfigurationseditor → Inhalt ersetzen\n"
                         + yaml.dump(cfg, Dumper=D, allow_unicode=True, sort_keys=False, width=4000))
print("ok")

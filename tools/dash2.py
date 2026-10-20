import json, shutil, time, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from params import P
C = os.environ.get("AVARMA_STORAGE", "/config/.storage/")
reg = json.load(open(C + "core.entity_registry"))["data"]["entities"]
U = {}
for e in reg:  # Automationen ignorieren; bei gleicher unique_id gewinnt binary_sensor (z. B. avarma_r290_alarm)
    uid, ent = str(e.get("unique_id", "")), e["entity_id"]
    if not uid.startswith("avarma_") or ent.startswith("automation."): continue
    if uid not in U or ent.startswith("binary_sensor."): U[uid] = ent
def E(k): return U["avarma_" + k]
FULL = {"columns": "full"}
def full(c): c = dict(c); c["grid_options"] = FULL; return c

# ---------- Schema ----------
W, H = 1230, 670
def lbl(k, x, y, size=26, color="#ffffff", prefix=None, weight=700):
    el = {"type": "state-label", "entity": E(k), "style": {"left": f"{x/W*100:.2f}%", "top": f"{y/H*100:.2f}%", "color": color,
          "font-size": f"{size/W*100:.2f}cqw", "font-weight": str(weight), "white-space": "nowrap", "line-height": "1"}}
    if prefix: el["prefix"] = prefix
    return el
els = [lbl("aussen",250,80), lbl("luefter",72,150), lbl("niederdruck",535,100), lbl("sauggas",535,165), lbl("hochdruck",737,100),
       lbl("heissgas",737,165), lbl("lamelle",274,335), lbl("strom",650,292), lbl("freq_ist",650,342), lbl("eev",767,290,22),
       lbl("vorlauf",1140,145), lbl("durchfluss",1140,258), lbl("ruecklauf",1140,355), lbl("ty",886,452),
       lbl("vl_soll",1162,534,20), lbl("pumpe",1162,567,20), lbl("tdhw",1162,600,20), lbl("ipm",1162,633,20)]
for i, (k, p) in enumerate([("modus_text","Modus: "),("fehler_text","Fehler: "),("waermeleistung","Wärmeleistung: "),("spreizung","Spreizung: ")]):
    e = lbl(k, 30, 545+i*30, 20, "#cfe3ff", p, 600); e["style"]["transform"] = "translate(0,-50%)"; els.append(e)
OUT_LABELS = [[("out_3","Heizpumpe"),("out_4","Zusatzpumpe"),("out_5","WW-Pumpe")],
              [("out_8","Ventil WW"),("out_9","Ventil 2"),("out_0","Abtauventil")],
              [("out_6","Heizstab 1"),("out_7","Heizstab 2"),("out_1","Öl-Heizung")]]
# Namen stehen fest im SVG (schema.svg), hier nur der Zustand: Ein = grün, Aus = rot
for col, items in enumerate(OUT_LABELS):
    for row, (k, p) in enumerate(items):
        for st, colr in (("on", "#4cd964"), ("off", "#ff5a4f")):
            e = lbl(k, 320 + col*180 + 118, 545 + row*30, 16, colr, None, 700); e["style"]["transform"] = "translate(0,-50%)"
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
schema = {"type": "picture-elements", "image": "/local/avarma/schema.svg?v=7", "elements": els,
          "card_mod": {"style": "ha-card{background:#06090d;border-radius:16px;overflow:hidden;container-type:inline-size} @keyframes wpspin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}"}}

ein_btn = {"type": "button", "entity": E("switch_ein"), "name": "Wärmepumpe EIN / AUS", "show_state": True, "icon_height": "56px",
           "tap_action": {"action": "toggle", "confirmation": {"text": "Wärmepumpe wirklich ein- bzw. ausschalten?"}},
           "hold_action": {"action": "more-info"}}
bedienung = {"type": "entities", "title": "Bedienung", "entities": [
    {"entity": E("switch_ein"), "name": "Wärmepumpe Ein/Aus"},
    {"entity": E("betriebsart"), "name": "Betriebsart"},
    {"entity": E("nachtmodus"), "name": "Nachtmodus"},
    {"entity": E("set_p002"), "name": "Vorlauf-Soll (P02)"},
    {"entity": E("set_p004"), "name": "Warmwasser-Soll (P04)"},
    {"type": "section", "label": "Zum Ändern: Code eingeben (Benutzer- oder Techniker-Code)"},
    {"entity": "input_text.wp_code", "name": "Code"},
    {"entity": "input_boolean.wp_benutzer_freigabe", "name": "Benutzer-Freigabe (15 min)"},
    {"entity": "input_boolean.wp_techniker_freigabe", "name": "Techniker-Freigabe (15 min)"},
    {"type": "section", "label": "Uhr der Wärmepumpe (wird täglich 03:17 gestellt)"},
    {"entity": E("uhr"), "name": "Uhr WP"},
    {"entity": E("uhr_stellen"), "name": "Uhr jetzt stellen"}]}
status = {"type": "entities", "title": "Status", "entities": [E(k) for k in ["ein","modus_text","betrieb_text","kompressor_laeuft","freq_soll","stoerung","fehler_text","stat_4","stat_8","stat_9","oelrueck","modbus_online","otc","raum_soll","netzspannung","dc_spannung","betriebsstd","starts_wp","abtau_anz","r290_konz","r290_alarm","raum_t2"]]}
def tile(k, name, icon=None):
    t = {"type": "tile", "entity": k if "." in k else E(k), "name": name, "vertical": True, "grid_options": {"columns": 4}}
    if icon: t["icon"] = icon
    return t
takt_tiles = [tile("sensor.wp_kompressor_starts_heute","Starts heute","mdi:counter"), tile("sensor.wp_kompressor_starts_woche","Woche","mdi:counter"),
              tile("sensor.wp_kompressor_starts_monat","Monat","mdi:counter"), tile("sensor.wp_kompressor_starts_jahr","Jahr","mdi:counter"),
              tile("starts_wp","Gesamt"), tile("starts_24h","letzte 24 h"), tile("laufzeit_heute","Laufzeit heute"), tile("avg_laufzeit","Ø pro Start")]
limits = {"type": "entities", "title": "Frequenzbegrenzung aktiv", "entities": [E(f"flimit_{i}") for i in range(5)]}
hist = {"type": "history-graph", "title": "Temperaturen 24 h", "hours_to_show": 24, "entities": [E(k) for k in ["vorlauf","ruecklauf","aussen","lamelle"]]}
hist2 = {"type": "history-graph", "title": "Kompressor 24 h", "hours_to_show": 24, "entities": [E(k) for k in ["kompressor_laeuft","freq_ist","strom"]]}
hist3 = {"type": "history-graph", "title": "Drücke 24 h", "hours_to_show": 24, "entities": [E(k) for k in ["hochdruck","niederdruck"]]}
H2 = lambda t: {"type": "heading", "heading": t}

def half(c): c = dict(c); c["grid_options"] = {"columns": 6}; return c
r290 = [half({"type": "tile", "entity": E("r290_alarm"), "name": "Kältemittel-Leck (R290)", "vertical": True, "icon": "mdi:gas-cylinder"}),
        half({"type": "tile", "entity": E("r290_konz"), "name": "R290-Konzentration", "vertical": True, "icon": "mdi:molecule"})]
v_status = {"title": "Arbeitsstatus", "path": "arbeitsstatus", "icon": "mdi:heat-pump", "type": "sections", "max_columns": 3, "dense_section_placement": True, "sections": [
    {"type": "grid", "column_span": 2, "cards": [full(schema), H2("Takte (Kompressor-Starts)")] + takt_tiles + [full(hist2), full(hist), full(hist3)]},
    {"type": "grid", "cards": [H2("Hauptbild"),
        {"type": "gauge", "entity": E("vorlauf"), "name": "TOut", "min": 10, "max": 60, "needle": True, "grid_options": {"columns": 6},
         "segments": [{"from": 10, "color": "#3fa9f5"}, {"from": 35, "color": "#43a047"}, {"from": 50, "color": "#ff9800"}]},
        {"type": "gauge", "entity": E("otc"), "name": "OTC (Heizkurve)", "min": 10, "max": 60, "grid_options": {"columns": 6}},
        tile("aussen", "Außen"), tile("modus_text", "Modus"), tile("kompressor_laeuft", "Kompressor")] + r290 + [
        full(ein_btn), full(bedienung), full(status), full(limits)]}]}

# ---------- Takte & Energie ----------
starts_bar = {"type": "statistics-graph", "title": "Kompressor-Starts pro Tag (30 Tage)", "entities": [E("starts_wp")],
              "stat_types": ["change"], "period": "day", "days_to_show": 30, "chart_type": "bar"}
starts_week = {"type": "statistics-graph", "title": "Kompressor-Starts pro Woche", "entities": [E("starts_wp")],
               "stat_types": ["change"], "period": "week", "days_to_show": 180, "chart_type": "bar"}
log_k = {"type": "logbook", "title": "Aufzeichnung Start/Stopp (48 h)", "hours_to_show": 48, "target": {"entity_id": [E("kompressor_laeuft"), E("switch_ein")]}}
en_tiles = [tile("waerme_heute","Wärme heute","mdi:fire"), tile("strom_heute","Strom heute","mdi:flash"), tile("cop_heute","COP heute"),
            tile("waerme_monat_disp","Wärme Monat","mdi:fire"), tile("strom_monat_disp","Strom Monat","mdi:flash"),
            tile("sensor.wp_warme_woche","Wärme Woche","mdi:fire"), tile("sensor.wp_strom_woche","Strom Woche","mdi:flash"),
            tile("erneuerbar_heute","Erneuerbar heute","mdi:leaf"), tile("waerme_jahr_wp","Wärme Jahr","mdi:fire"),
            tile("strom_jahr_wp","Strom Jahr","mdi:flash"), tile("jaz","JAZ Jahr")]
en_bar = {"type": "statistics-graph", "title": "Energie pro Tag (Display-Zähler)", "entities": [E("waerme_heute"), E("strom_heute")],
          "stat_types": ["max"], "period": "day", "days_to_show": 30, "chart_type": "bar"}
en_hours = {"type": "markdown", "title": "Heute je Stunde (wie Display)", "content":
  "{% set p = states('" + E("e_prod_h") + "').split(',') %}{% set v = states('" + E("e_verb_h") + "').split(',') %}"
  "| Std | erzeugt | verbraucht |\n|---|---:|---:|\n{% for i in range(24) %}{% set a = (p[i]|float(0))/10 %}{% set b = (v[i]|float(0))/10 %}"
  "{% if a > 0 or b > 0 %}| {{ '%02d' % i }} | {{ a }} kWh | {{ b }} kWh |\n{% endif %}{% endfor %}"}
v_takte = {"title": "Takte & Energie", "path": "takte", "icon": "mdi:counter", "type": "sections", "max_columns": 3, "sections": [
    {"type": "grid", "cards": [H2("Kompressor-Starts")] + takt_tiles + [full(starts_bar), full(starts_week)]},
    {"type": "grid", "cards": [full(log_k)]},
    {"type": "grid", "cards": [H2("Energie (Zähler der Wärmepumpe)")] + en_tiles + [full(en_bar), full(en_hours)]}]}

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
freigabe = {"type": "entities", "title": "Freigabe", "entities": [
    {"entity": "input_text.wp_code", "name": "Code eingeben"},
    {"entity": "input_boolean.wp_benutzer_freigabe", "name": "Benutzer-Freigabe (Code 99)"},
    {"entity": "input_boolean.wp_techniker_freigabe", "name": "Techniker-Freigabe"}],
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
        if md: cards.append(full({"type": "markdown", "content": md, "card_mod": {"style": "ha-card{font-size:0.85em;opacity:0.85}"}}))
        secs.append({"type": "grid", "cards": cards})
    return {"title": title, "path": path, "subview": True, "back_path": "/waermepumpe/parameter", "type": "sections", "max_columns": 3, "sections": secs}
v_user = param_view("U", "Benutzer-Parameter", "benutzer",
    "### Benutzer-Parameter (Code 99)\nEntspricht den **blauen** Feldern am Display. Zum Ändern zuerst oben den Code eingeben – die Freigabe gilt 15 Minuten. "
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

diag = {"type": "entities", "title": "Rohwerte / noch nicht zugeordnet", "entities": [E(k) for k in
        ["status_roh","ausgaenge","eingaenge","modus_roh","ein_aus","modus_wahl","fehler0","fehler1","fehler2","fehler3","fehler_drv0","fehler_drv1","fehler_drv2","freqlimit","abtau_gesperrt","abtau_erzw","evi_ein","evi_aus","evi_diff","evi_eev","diff_hk","luefter2","t6","verdampfer_temp","kondensator_temp","soll_ww_calc","otc","pumpe_pwm","pumpe_c2","phasenstrom","sw_pcb","sw_hmi","r290_grenze","uhr_datum","uhr_zeit"] + [f"hist{i}" for i in range(8)] + ["out_%d" % b for b in (0,1,3,4,5,6,7,8,9)] + ["stat_%d" % b for b in (3,4,8,9,10,11)]]}
v_diag = {"title": "Diagnose", "path": "diagnose", "icon": "mdi:stethoscope", "type": "masonry", "cards": [diag]}

cfg = {"views": [v_status, v_takte, v_fehler, v_param, v_user, v_tech, v_diag]}
ts = time.strftime("%Y%m%d_%H%M%S")
if os.path.exists(C + "lovelace.waermepumpe"): shutil.copy(C + "lovelace.waermepumpe", C + "lovelace.waermepumpe.bak_" + ts)
json.dump({"version": 1, "minor_version": 1, "key": "lovelace.waermepumpe", "data": {"config": cfg}}, open(C + "lovelace.waermepumpe", "w"), ensure_ascii=False, indent=1)
print("ok")

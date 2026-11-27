"""Konstanten der Avarma-Integration."""

DOMAIN = "avarma"
MANUFACTURER = "Hofman Energy / Avarma"

CONF_SLAVE = "slave"
CONF_PROTOCOL = "protocol"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_TECH_CODE = "tech_code"
CONF_NOTIFY = "notify_service"
CONF_CLOCK_SYNC = "clock_sync"
CONF_TECH_SWITCH = "tech_switch"
CONF_DASHBOARD = "dashboard"
CONF_GRID_SENSOR = "grid_sensor"  # Netzleistung des Hauses in W (+ = Bezug), für den Netzanteil des WP-Stroms
CONF_BATTERY_SENSOR = "battery_sensor"  # Akkuleistung in W (+ = Laden, − = Entladen, wie Victron), für den Akkuanteil
CONF_BATTERY_INVERT = "battery_invert"  # Akku-Sensor zählt umgekehrt (+ = Entladen)
CONF_OUTDOOR_SENSOR = "outdoor_sensor"  # eigener Außenfühler (Regelung, Heizwärmebedarf)
CONF_ROOM_SENSORS = "room_sensors"  # Raumfühler für die eigene Regelung (Mittelwert)
CONF_WEATHER = "weather_entity"  # Wetter mit Stundenprognose (Vorladen vor Frost)
CONF_MODELL = "modell"  # Modell der WP (Werkseinstellungen in der Parameter-Spalte „Werk“)
CONF_PAGES = "pages"  # wählbare Seiten im Dashboard (Pfad der Ansicht → Name)
PAGES = {"pv": "PV", "einsparungen": "Einsparungen", "regelung": "Regelung", "uebergang": "Übergangszeit", "kaeltekreis": "Kältekreis",
         "diagnose": "Diagnose"}
CONF_PAGES_KNOWN = "pages_known"  # Seiten, die es beim Speichern der Optionen gab – später neue Seiten sind zunächst sichtbar
PAGES_V1 = ["pv", "einsparungen", "regelung", "kaeltekreis", "diagnose"]  # Seiten vor CONF_PAGES_KNOWN

DEFAULT_PORT = 502
DEFAULT_SLAVE = 1
DEFAULT_SCAN = 10
USER_CODE = "99"          # Benutzer-Code wie am Display (steht auch in der Anleitung)
UNLOCK_MINUTES = 15

STATIC_URL = "/avarma_static"

PLATFORMS = ["sensor", "binary_sensor", "number", "select", "switch", "button", "text"]

# Register (Spalte "Decimal" der Hofman-Liste)
REG_ON = 4096
REG_MODE = 4097
REG_FORCE_DEFROST = 4103
REG_FAULT_RESET = 4104
REG_CLOCK_DATE = 4106
REG_CLOCK_TIME = 4107
REG_STATUS = 4354
REG_OUTPUTS = 4355
REG_INPUTS = 4356
REG_FREQ = 4373
REG_FREQLIMIT = 4387
REG_FAULTS = (4390, 4391, 4392, 4393)
REG_DRV = (4394, 4395, 4396)
REG_STARTS = 4608
REG_DEFROSTS = 4613
REG_OIL = 4609
REG_R290_KONZ = 4617
REG_R290_ALARM = 4619
REG_HIST = 4628

MODES = {1: "Warmwasser", 2: "Heizen", 3: "Heizen + Warmwasser", 4: "Kühlen", 5: "Kühlen + Warmwasser"}
MODES_SHORT = {1: "Warmwasser", 2: "Heizen", 3: "Heizen+WW", 4: "Kühlen", 5: "Kühlen+WW"}
BETRIEB = {0: "Aus", 1: "Warmwasser", 2: "Heizen", 4: "Kühlen"}

# Fehlercodes nach Originalbetriebsanleitung AVARMA V06 (S. 64–67, 9 kW). E18/E21/E51/E56/E59 sind dort „reserviert“,
# werden laut Modbus-Protokoll (TDB 24.11.2025) aber als Fehlerbit gemeldet – Name dann aus dem Protokoll.
ERR = {1: "Sensorfehler Außenlufttemperatur", 2: "Sensorfehler Verdampfertemperatur", 3: "Sensorfehler Ansaugtemperatur",
       4: "Sensorfehler EVI-Einlasstemperatur", 5: "Sensorfehler EVI-Auslasstemperatur", 6: "Sensorfehler Verdichtungstemperatur",
       7: "Sensorfehler Trinkwassertemperatur", 8: "Sensorfehler Austrittstemperatur", 9: "Sensorfehler Eintrittstemperatur",
       10: "Sensorfehler Kältemitteltemperatur", 11: "Sensorfehler Hochdruck", 12: "Sensorfehler Niederdruck",
       13: "Hochdruckschutz", 14: "Niederdruckschutz", 15: "Störung Wasserdurchfluss", 16: "Kommunikationsfehler",
       17: "Schutz gegen zu hohe Verdichtungstemperatur", 18: "EEPROM-Parameterfehler", 20: "Schutz IPM", 21: "Spannungsfehler",
       22: "Wassertemperaturdifferenz zu hoch", 23: "Trinkwasser-Frostschutz 2×", 24: "AC-Frostschutz 2×",
       26: "Sensorfehler Temperatur T6", 27: "Umgebungstemperatur über Obergrenze", 28: "Wassereintrittstemperatur zu hoch (Kühlen)",
       29: "Sensorfehler Raumtemperatur", 32: "Wasseraustrittstemperatur zu hoch (Heizen)", 36: "Kommunikationsfehler DC-Lüfterplatine",
       40: "Wasseraustrittstemperatur zu niedrig (Kühlen)", 44: "Störung DC-Lüftermotor 1", 45: "Störung DC-Lüftermotor 2",
       50: "Schutz gegen hohe Verdampfertemperatur", 51: "Kältemittel-Konzentration hoch (Leck!)", 56: "Primärstrom-Schutz",
       58: "Umgebungstemperatur unter unterer Grenze", 59: "VL/RL vertauscht oder 4-Wege-Ventil", 99: "Kommunikationsstörung Inverter"}
_SENSOR = "Fühler: Unterbrechung oder Kurzschluss."
_PROT = "In der Betriebsanleitung V06 als „reserviert“ geführt; Bedeutung laut Modbus-Protokoll."
# Bemerkung (mögliche Ursache / was prüfen) nach Betriebsanleitung V06
ERR_INFO = {**{k: _SENSOR for k in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 26, 29)},
       11: "Sensor defekt, Unterbrechung oder Kurzschluss, Platine (PCB) defekt.",
       12: "Sensor defekt, Unterbrechung oder Kurzschluss, Platine (PCB) defekt.",
       13: "Zu viel Kältemittel, Fehler am Drosselorgan (EEV) oder Drucksensorfehler.",
       14: "Zu wenig Kältemittel, Fehler am Drosselorgan (EEV) oder Drucksensorfehler.",
       15: "Zu geringe Wasserdurchflussmenge oder Störung des Durchflussschalters.",
       16: "Kommunikationsfehler zwischen Hauptplatine und Regler.",
       17: "Zu wenig Kältemittel oder Fehler am Drosselorgan (EEV).",
       18: _PROT, 21: _PROT, 51: _PROT + " Keine Zündquellen, lüften, WP stromlos schalten, Fachbetrieb rufen.", 56: _PROT, 59: _PROT,
       20: "IPM-Modul (Leistungsteil des Verdichterantriebs) hat abgeschaltet – Unternummer E20-x am Display beachten.",
       22: "Umwälzpumpe und Wasserfilter (Schmutzfänger) prüfen.",
       23: "Die Frostschutzfunktion im Trinkwasserbetrieb wurde 2× binnen 60 Minuten aktiviert.",
       24: "Die Frostschutzfunktion im Heiz-/Kühlbetrieb wurde 2× binnen 90 Minuten aktiviert.",
       27: "Umgebungstemperatur über 45 °C.",
       28: "Kühlen: Wassereintritt über 40 °C. Ausschalten und Wasser vor dem Einschalten unter 40 °C abkühlen lassen.",
       32: "Austrittstemperatur über 75 °C. Umwälzpumpe und Wasserfilter prüfen.",
       36: "Kommunikationskabel zur Lüfterplatine prüfen.",
       40: "Austrittstemperatur unter 5 °C. Umwälzpumpe und Wasserfilter prüfen.",
       44: "Motorleitung prüfen oder Motor defekt.", 45: "Motorleitung prüfen oder Motor defekt.",
       50: "Zu wenig Kältemittel, Störung am Drosselorgan (EEV) oder Verdampferfühler defekt.",
       58: "Außentemperatur unter der Grenze aus P82.",
       99: "Kommunikationsstörung zwischen Hauptplatine und Inverterplatine."}
# Bit -> Fehlercode je Fehlerregister 4390..4393
FAULT_BITS = (
    {b: b + 1 for b in range(16)},
    dict(enumerate([17, 18, 99, 20, 21, 22, 23, 24, 56, 26, 27, 28, 29, 58, None, 32])),
    {3: 36, 6: 59, 7: 40, 11: 44, 12: 45},
    {1: 50, 2: 51},
)
DRV = {0: "IPM-Fehler", 1: "Kompressor-Treiberfehler", 2: "Kompressor-Überstrom", 5: "IPM-Übertemperatur", 6: "PFC-Fehler",
       7: "DC-Überspannung", 8: "DC-Unterspannung", 9: "AC-Spannung außerhalb", 10: "AC-Überstrom",
       15: "Kommunikation Hauptplatine"}

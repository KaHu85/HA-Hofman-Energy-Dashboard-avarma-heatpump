<img src="custom_components/avarma/brand/icon@2x.png" width="96" align="right">

# Avarma R290 Wärmepumpe in Home Assistant

Komplette Einbindung einer **Avarma (Hofman Energy) R290 Monoblock-Wärmepumpe** in Home Assistant über Modbus/RS485. Es braucht kein ESPHome und keine Cloud: Ein RS485-Ethernet-Gateway hängt an der Wärmepumpe, Home Assistant liest und schreibt direkt.

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/D6C72A89GR)

### Getestete Anlage

| | |
|---|---|
| Wärmepumpe | **Avarma (Hofman Energy) R290 Monoblock, 9 kW, Version 3 (HE-AI-290-00-000V-V03)** |
| Hauptplatine, Modell (Register 4352) | 23557 (0x5C05) |
| Hauptplatine, Software (Register 4353 / 4615) | 1518 |
| Display-Software (Register 4616) | wird nicht über Modbus gemeldet (0) |
| Modbus | RTU, 9600 8N1, Slave 1, über COMM3 |
| Home Assistant | Core 2026.2 auf Raspberry Pi 5 |

> ⚠️ **Getestet nur an meiner Avarma 9 kW, Version 3 (V03).** Ältere Modelle (V01/V02) und andere Leistungsgrößen können leicht abweichen – bei den Wertebereichen einzelner Parameter (z. B. Raum-Soll, Heizkurve, Druckwerte bar statt MPa, E-Heizung, Estrichtrocknung, Heizgrenze) sind Unterschiede zur Anleitung von 2024 belegt, und höhere Parameter (ab P116) sowie Zusatzregister gibt es bei älteren Ständen eventuell nicht. **Vergleiche vor dem ersten Ändern alle Parameter mit dem Original-Display deiner Wärmepumpe** (Nummer, Bedeutung, Wert und Bereich). Stimmt etwas nicht überein, dort nichts schreiben – falsche Werte können die Wärmepumpe beschädigen.
>
> Andere Leistungsgrößen und Softwarestände sollten mit demselben Regler ähnlich funktionieren, sind aber **nicht getestet**. Deine Werte siehst du nach der Installation im Dashboard unter **Diagnose** („WP Software Platine“). Über Rückmeldungen mit Modell und Softwarestand freue ich mich.

> 🤖 **Komplett mit [Claude](https://claude.ai) (Anthropic) erstellt.** Registeranalyse, Home-Assistant-Integration, Dashboard, Display-Nachbau, Parameterliste und diese Anleitung sind im Dialog mit Claude entstanden. Getestet und abgeglichen an der echten Anlage.

### Neu in 1.3.0

- **Eigene Regelung verbessert:** Raum-Nachführung reagiert schneller, wenn es deutlich zu kalt ist, und gedämpft, wenn es zu warm ist (kurze Fremdwärme von Ofen/Kochen zählt nicht, kein Aufschaukeln mehr). Raum-Soll in 0,1-K-Schritten. **Gebäude / Heizsystem** (Heizkörper, Fußbodenheizung, Benutzerdefiniert) mit **Feineinstellung**.
- **Prognose-Baustein:** reagiert vorab auf die Stundenprognose der Wetter-Entität; stündliche Vorhersage und 24-h-Temperaturkurve auf der Seite „Regelung“. Wetter-Entität wird in den Optionen vorgeschlagen.
- **Heizkurve P08:** Ändert sich P08, gleicht die Regelung das aus (kein doppeltes Korrigieren). Optional: **Heizkurve lernen** passt P08 einmal am Tag langsam an.
- **Wärmste Stunden** *(experimentell)*: heizt bevorzugt in den wärmeren Stunden des Tages, mit Tagesauswertung.
- **Übergangszeit** *(Technikerzugang, auf eigene Gefahr)*: begrenzt bei milder Außentemperatur Lüfter (P60), Höchstfrequenz (P45) und Frequenzreduktion (P114) gegen Takten. Dazu optional **Kompressor-Stufen**: P45 nach Außentemperatur, für einen gleichmäßigeren Kompressor.
- **Abtauungen** im Dashboard (heute, 24 h, je Tag) und **Zähler der Schreibvorgänge** in die WP (je Parameter und Herkunft).
- **Parameter** nach der Hofman-Werksliste 9 kW benannt und beschrieben; auf den Parameterseiten eine Spalte **„Werk (9 kW)“** mit dem Werkswert.
- **Sicherheit:** Seite „Regelung“/„Übergangszeit“ in den Optionen abgewählt → die Regelung schaltet sich sauber aus und schreibt die Grundwerte zurück; ohne Raumfühler geht P09 auf den Grundwert; nie zwei Schreibvorgänge gleichzeitig.
- **Dashboard:** Namen ohne „WP“ davor (HA 2026.10), Einstellungen rechts, Erklärtexte aufklappbar.

Alle neuen Regelungen sind nach dem Update **aus** und müssen bewusst eingeschaltet werden. Entity-IDs sind unverändert, bestehende Automationen laufen weiter.

![Dashboard: Arbeitsstatus](docs/images/ha-arbeitsstatus.jpg)

| Smartphone | Original-Display „Arbeitsstatus“ |
|---|---|
| <img src="docs/images/dashboard-smartphone.jpg" width="300"> | <img src="docs/images/display-arbeitsstatus.jpg" width="450"> |

### Dashboard nach deinen Wünschen
Welche Seiten das Dashboard zeigt, entscheidest du selbst – **jederzeit**, nicht nur bei der Installation:
**Einstellungen → Geräte & Dienste → Avarma Wärmepumpe → ⚙️ Konfigurieren → „Seiten im Dashboard“**. Häkchen setzen oder entfernen, **OK** – fertig (danach die Seite neu laden).
**PV**, **Einsparungen**, **Regelung**, **Übergangszeit**, **Kältekreis** und **Diagnose** sind wählbar; Arbeitsstatus, Takte & Energie, Fehler und Parameter sind immer dabei. Abgewählte Seiten verschwinden nur aus dem Dashboard, die Funktionen dahinter laufen weiter.

| Seiten wählen | PV (optional) | Einsparungen (optional) |
|---|---|---|
| <img src="docs/images/ha-optionen-seiten.jpg" width="320" alt="Seiten im Dashboard wählen"> | <img src="docs/images/ha-pv.jpg" width="320" alt="Seite PV"> | <img src="docs/images/ha-einsparungen.jpg" width="320" alt="Seite Einsparungen"> |

---

## Was du bekommst

- **Nachgebautes Display „Arbeitsstatus“**: Kältekreis mit allen Live-Werten (Ps/Pd, Ts/Td/Tc, TOut/TIn, Q, Ty, Kompressor A/Hz, EEV, Lüfter) und den Ausgängen C1–C3, G1/G2, E1/E2, 4-Wege-Ventil und Öl-Heizung (Verdichter-Heizband).
- **Hauptbild** mit TOut und OTC (Heizkurven-Soll), **EIN/AUS-Knopf** mit Sicherheitsabfrage, **Betriebsart** (Heizen / WW / Kühlen …) und **Nachtmodus** samt Uhrzeiten.
- **Takt-Zählung**: Kompressor-Starts heute, Woche, Monat, Jahr und gesamt (aus dem internen Zähler der WP), dazu Laufzeit, Ø Laufzeit pro Start, Balkendiagramme und eine Aufzeichnung jedes Starts und Stopps.
- **Kältekreis-Ampel**: Kondensations- und Verdampfungstemperatur (TH/TL wie am Display), Überhitzung, Unterkühlung und Temperaturhub mit Richtwerten und verständlicher Erklärung.
- **Energie** aus den Zählern der Wärmepumpe (wie am Display): Wärme, Strom, erneuerbar, COP heute, JAZ.
- **Leistung jetzt**: elektrische Leistung in Watt (aus Spannung × Strom der WP, laufend am Stromzähler der WP abgeglichen), Wärmeleistung und **COP jetzt**.
- **Seite „Einsparungen“**: Heizkosten der WP im Vergleich zu **Heizöl, Gas, Pellets und Stückholz** – eigene Preise, Grundgebühren und Wartung eintragbar, Ersparnis und CO₂ je Monat und Jahr als Balkendiagramm. Mit PV zusätzlich **Heizkosten der WP mit und ohne PV** und die **Ersparnis durch die PV**.
- **Heizwärmebedarf**: **Heizlast** in kW bei Norm-Außentemperatur und hochgerechneter **Jahres-Heizwärmebedarf** in kWh und kWh/m²·Jahr – berechnet aus der Tageswärme der WP und der Außentemperatur.
- **Seite „PV“ (optional)**: wie viel Strom der WP aus **PV, Akku und Netz** kommt – jetzt, heute, Woche, Monat, Jahr, je Tag und je Monat. Braucht einen Sensor für die Netzleistung des Hauses (siehe 4.3).
- **Eigene Regelung (optional)**: verschiebt die eingebaute Heizkurve der WP sanft nach deiner **Raumtemperatur** (eigene Raumfühler), gleicht einen **in der Sonne zu warm messenden Außenfühler** aus (eigener Außenfühler) und **lädt vor Frost vor** (Wetterprognose) – mit Schutz gegen Takten. Ein-/ausschaltbar, ausfallsicher.
- **Seiten wählbar**: PV, Einsparungen, Regelung, Kältekreis und Diagnose lassen sich in den Optionen jederzeit ein- und ausblenden.
- **Fehler**:
  - aktive Fehler im Klartext (E01–E59, Treiberfehler)
  - Fehlerspeicher der WP
  - Fehler quittieren per Knopf
  - Benachrichtigung bei Störung in Home Assistant und als Push aufs Handy (mit Fehlertext)
- **R290-Kältemittel-Alarm**: kritische Push-Nachricht, falls die WP Kältemittel meldet (sofern ein Sensor verbaut ist, siehe unten).
- **Alle Parameter P00–P150 und P201–P208 lesen UND ändern**:
  - aufgeteilt in **Benutzer-Parameter** (blau am Display, Benutzer-Code) und **Techniker-Parameter** (weiß am Display, Techniker-Code)
  - jeweils mit deutscher Erklärung und erlaubtem Bereich
  - Änderungen landen im Logbuch
  - Werksreset, RS485-Adresse und Kompressormodell sind gesperrt
- **Uhr der Wärmepumpe** wird täglich geprüft (und gestellt, wo die Steuerung das zulässt). Geht sie falsch, kommt ein Hinweis, die Uhr am Display zu stellen – bei der getesteten Anlage gibt das Original-Display die Uhrzeit vor.


### Screenshots

| Arbeitsstatus | Energie pro Tag & Takte |
|---|---|
| ![Arbeitsstatus](docs/images/ha-arbeitsstatus.jpg) | ![Energie pro Tag und Takte](docs/images/ha-energie-takte.jpg) |
| **Takte & Energie** (mit Leistung jetzt) | **Takte & Energie (Verläufe)** |
| ![Takte & Energie](docs/images/ha-takte-energie.jpg) | ![Takte & Energie, Verläufe](docs/images/ha-takte-energie-2.jpg) |
| **PV: Woher kommt der Strom der WP?** | **Einsparungen: Jahresübersicht und Preise** |
| ![PV](docs/images/ha-pv.jpg) | ![Einsparungen](docs/images/ha-einsparungen.jpg) |
| **Einsparungen: Heizkosten und Ersparnis je Monat** | **Einsparungen: CO₂ und Ersparnis je Jahr** |
| ![Einsparungen je Monat](docs/images/ha-einsparungen-2.jpg) | ![Einsparungen CO₂ und Jahr](docs/images/ha-einsparungen-3.jpg) |
| **Drücke, Temperaturen & Status** | **Kältekreis** |
| ![Verläufe und Status](docs/images/ha-verlaeufe-status.jpg) | ![Kältekreis](docs/images/ha-kaeltekreis.jpg) |
| **Fehler** | **Parameter** |
| ![Fehler](docs/images/ha-fehler.jpg) | ![Parameter](docs/images/ha-parameter.jpg) |
| **Benutzer-Parameter** | **Diagnose** |
| ![Benutzer-Parameter](docs/images/ha-benutzer-parameter.jpg) | ![Diagnose](docs/images/ha-diagnose.jpg) |

#### Am Smartphone

| | | | |
|---|---|---|---|
| <img src="docs/images/dashboard-smartphone.jpg" width="200" alt="Display"> | <img src="docs/images/phone-hauptbild.jpg" width="200" alt="Hauptbild"> | <img src="docs/images/phone-takte.jpg" width="200" alt="Takte"> | <img src="docs/images/phone-kompressor.jpg" width="200" alt="Kompressor 24 h"> |
| <img src="docs/images/phone-verlaeufe.jpg" width="200" alt="Drücke und Temperaturen"> | <img src="docs/images/phone-starts.jpg" width="200" alt="Kompressor-Starts"> | <img src="docs/images/phone-energie.jpg" width="200" alt="Energie"> | |

---

## 1. Hardware

| Teil | Hinweis |
|---|---|
| Avarma / Hofman R290 Monoblock | getestet: 9 kW |
| **RS485 ↔ Ethernet-Gateway** | getestet: **USR-TCP232-304**. Möglich sind auch Elfin EW11/EW11A (WLAN) oder Waveshare RS485 TO ETH |
| 2-adrige Leitung (verdrillt) | A/B, optional GND |

> **USB-RS485-Stick:** Die Integration spricht nur über das Netzwerk (Modbus TCP / RTU over TCP). Ein USB-Stick geht nur mit einem Umweg wie `ser2net`, deshalb ist ein Gateway die einfachere Lösung.
> ⚠️ **Nicht** geeignet: USB-RS232-Adapter mit passivem RS232→RS485-Wandler (z. B. „STM485S“) und reine USB-TTL-Adapter. Die liefern kein Signal.

## 2. Anschluss an der Wärmepumpe

> ⚠️ **Wärmepumpe vorher allpolig stromlos schalten.** Im Gerät liegen 230 V an, und es enthält R290 (Propan).

### 2.1 Klemmleiste: Klemmen 11 (A) und 12 (B)
Die RS485-Leitung zum Gateway kommt an die Kundenklemmen **11 = A** und **12 = B** („RS485 – User wiring“).

![Klemmleiste mit RS485 an 11/12](docs/images/klemmleiste-11-12.jpg)

### 2.2 Hauptplatine: grünen Stecker von COMM2 auf COMM3 umstecken
**Ab Werk geht von 11/12 noch keine Kommunikation aus.** Intern führen die Klemmen 11/12 über einen grünen 4-poligen Stecker (`+12V G A B`) auf **COMM2**, und COMM2 ist für Modbus nicht aktiv.

**Lösung:** Die beiden grünen Stecker auf der Hauptplatine **tauschen**. Der Stecker mit der Leitung von 11/12 kommt auf **COMM3** (`+12V G A3 B3`), der andere auf COMM2. An der Klemmleiste ändert sich nichts.

![Hauptplatine: Leitung von 11/12 jetzt auf COMM3](docs/images/platine-comm3.jpg)

| Anschluss | Funktion |
|---|---|
| COMM1 (`+5V G A1 B1`) | **Original-Display**, nicht anfassen |
| COMM2 (grün) | ab Werk mit 11/12 verbunden, für Modbus inaktiv |
| **COMM3 (grün, `A3 B3`)** | **Modbus für Home Assistant** ✅ (Slave 1) |
| COMM4 (`+12V G A4 B4`) | ab Werk belegt, nicht anfassen |

### 2.3 Gateway anschließen
<img src="docs/images/gateway-usr-tcp232-304.jpg" width="260" align="right">

Am USR-TCP232-304:
- **A** ← Klemme 11
- **B** ← Klemme 12
- **G** optional an Masse
- Versorgung **5 V DC**, Netzwerk an den Switch bzw. Router.

Kommt keine Antwort, tausch A und B einmal (manche Hersteller beschriften verkehrt herum). Laufen Display und Home Assistant gleichzeitig, ist das kein Problem, weil sie an getrennten Ports hängen (Display an COMM1, Home Assistant an COMM3).

<br clear="right">

## 3. Gateway einrichten (USR-TCP232-304)

In der Weboberfläche des Gateways (Zugangsdaten laut Handbuch; **ändere das Standard-Passwort**):

| Einstellung | Wert |
|---|---|
| Baudrate | **9600** |
| Data / Parity / Stop | **8 / None / 1** |
| Work Mode | **TCP Server** |
| Local Port | **502** |
| Modbus-TCP-Umwandlung | **aus** (transparent) |

Gib dem Gateway im Router eine **feste IP** (DHCP-Reservierung).

## 4. Home Assistant einrichten

Voraussetzungen: Home Assistant ab 2025.1 und [HACS](https://hacs.xyz/docs/use/).

### 4.1 Integration über HACS installieren

[![In HACS öffnen](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=KaHu85&repository=HA-Hofman-Energy-Dashboard-avarma-heatpump&category=integration)

1. Auf den Button klicken, die eigene Home-Assistant-Instanz bestätigen und in HACS **Herunterladen** wählen.
   Ohne Button: HACS → ⋮ → *Benutzerdefinierte Repositories* → `https://github.com/KaHu85/HA-Hofman-Energy-Dashboard-avarma-heatpump`, Typ *Integration* → hinzufügen, dann „Avarma Wärmepumpe“ suchen und herunterladen.
2. Home Assistant **neu starten**.

<details><summary>Manuell ohne HACS</summary>

Den Ordner `custom_components/avarma` aus diesem Repository nach `<config>/custom_components/avarma` kopieren (z. B. per Samba- oder File-Editor-Add-on) und Home Assistant neu starten. Updates kommen dann nicht automatisch.
</details>

### 4.2 Wärmepumpe hinzufügen

[![Integration hinzufügen](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=avarma)

1. Auf den Button klicken oder: Einstellungen → Geräte & Dienste → **Integration hinzufügen** → „Avarma Wärmepumpe“.
2. Eintragen:
   - **IP-Adresse** des Gateways
   - **Port:** `502`
   - **Slave-ID:** `1`
   - **Protokoll:** *RTU over TCP* (Gateway transparent, wie in Abschnitt 3) bzw. *Modbus TCP*, wenn dein Gateway selbst umsetzt
3. Beim Speichern wird die Verbindung geprüft. Klappt das nicht: Protokoll, A/B-Verdrahtung und 9600 8N1 am Gateway kontrollieren.

> Es darf **nur ein** System gleichzeitig die Wärmepumpe über das Gateway abfragen. Zwei Abfragen auf demselben Bus stören sich gegenseitig.

> **IP oder Port später ändern:** Einstellungen → Geräte & Dienste → Avarma Wärmepumpe → beim Eintrag ⋮ → **Neu konfigurieren**. Die aktuellen Werte sind vorausgefüllt und lassen sich anpassen. Optionen, Zähler und Verläufe bleiben erhalten.

| ⋮ → Neu konfigurieren | Verbindung ändern |
|---|---|
| <img src="docs/images/ha-integration-menue.jpg" width="420"> | <img src="docs/images/ha-neu-konfigurieren.jpg" width="380"> |

### 4.3 Optionen (Gerät → ⚙️ **Konfigurieren**)

| Option | Bedeutung |
|---|---|
| **Techniker-Code** | Derselbe Code wie am Display deiner Anlage (vom Installateur bzw. Hersteller). Er wird nur lokal in Home Assistant gespeichert. Leer = Techniker-Parameter bleiben gesperrt. Solange die **Übergangszeit** eingeschaltet ist (oder ihre Normalwerte noch nicht zurückgeschrieben hat), lässt sich der Code nicht löschen – ohne Code könnte sie die Normalwerte nicht mehr zurückschreiben. |
| **Techniker-Freigabe per Schalter erlauben** | Aus = Techniker-Parameter nur nach Eintippen des Codes. Ein = der gespeicherte Code genügt, der Schalter „Techniker-Freigabe“ gibt die Parameter für 15 Minuten frei. Nur einschalten, wenn niemand Unbefugtes Zugriff auf dein Home Assistant hat. |
| **Push-Benachrichtigung an** | z. B. `notify.mobile_app_mein_iphone` für Störungen und den R290-Alarm. Den Namen findest du unter Entwicklerwerkzeuge → Aktionen → „notify.“. |
| **Uhr täglich stellen** | stellt bzw. prüft die Uhr der Wärmepumpe täglich um 03:17 und beim Start (Hinweis, falls sie am Display gestellt werden muss) |
| **Dashboard bereitstellen** | legt das Dashboard „Wärmepumpe“ an (Standard: ein), siehe 4.4 |
| **Seiten im Dashboard** | PV, Einsparungen, Regelung, Übergangszeit, Kältekreis, Diagnose einzeln an/aus (Standard: alle; später neu hinzugekommene Seiten sind zuerst eingeschaltet). Arbeitsstatus, Takte & Energie, Fehler und Parameter sind immer dabei. Jederzeit änderbar; nach **OK** lädt die Integration neu, dann die Seite neu laden. **Wichtig:** Wird „Regelung“ bzw. „Übergangszeit“ abgewählt, **schaltet sich die jeweilige Regelung aus** (P09 zurück auf den Grundwert bzw. P60/P45/P114 auf die Normalwerte) – sie läuft nicht unsichtbar weiter. |
| **Abfrageintervall** | Standard 10 s (Parameter alle 15 min, Energiezähler alle 5 min) |
| **Netzleistung des Hauses** | *Optional, für die Seite „PV“.* Ein Sensor in **W** (oder kW) mit dem Netzbezug des ganzen Hauses: **+ = Bezug** aus dem Netz, − = Einspeisung. Typisch: Smart Meter (z. B. über P1-/IR-Lesekopf), Shelly 3EM/Pro 3EM („Total Power“), Netz-Sensor des Wechselrichters bzw. Energiezählers (Fronius, SMA, Victron „Grid“ …). Zählt dein Sensor umgekehrt (+ = Einspeisung), vorher einen Template-Sensor mit umgekehrtem Vorzeichen anlegen. Leer = keine PV-Auswertung. |
| **Akkuleistung** | *Optional, nur mit Hausakku.* Sensor in **W** mit der Lade-/Entladeleistung des Akkus: Standard **+ = Laden, − = Entladen** (wie Victron „Battery power“). Ohne Akku-Sensor wird PV und Akku gemeinsam als „PV“ gezählt. |
| **Eigener Außenfühler** | *Optional.* Temperatursensor im Schatten (z. B. Shelly, Wetterstation). Wird für die **eigene Regelung** (Sonnenkorrektur), die **Übergangszeit** (wählbar) und den **Heizwärmebedarf** statt des WP-Fühlers verwendet – der sitzt oft in der Sonne und misst dann deutlich zu warm. |
| **Raumfühler für die eigene Regelung** | *Optional.* Ein oder mehrere Raumthermometer, gerechnet wird mit dem **Mittelwert**. Am besten Räume, die typisch für das Haus sind (z. B. Wohnzimmer, Gang) – nicht Bad, Sauna oder einen Raum mit Ofen. |
| **Wetter mit Stundenprognose** | *Optional.* Wetter-Entität für den **Prognose-Baustein** der eigenen Regelung, das **Vorladen vor Frost** und die Vorhersage auf der Seite „Regelung“. Vorgeschlagen wird **Open-Meteo**, falls vorhanden (für Österreich/Deutschland empfohlen), sonst **Met.no** (`weather.forecast_home`, richtet Home Assistant meist bei der Ersteinrichtung ein). Siehe [Wetterprognose einrichten](#wetterprognose-einrichten). |
| **Akku-Sensor zählt umgekehrt** | Einschalten, wenn dein Akku-Sensor beim **Entladen positiv** ist (bei manchen Hybrid-Wechselrichtern so). Prüfen: abends ohne Sonne, wenn der Akku das Haus versorgt, muss der Sensor ohne Schalter **negativ** sein. |

| Optionen (Teil 1: Code, Push, Uhr, Dashboard, Seiten) | Optionen (Teil 2: Netz, Akku, Fühler, Wetter) |
|---|---|
| <img src="docs/images/ha-optionen.jpg" width="380" alt="Optionen der Integration"> | <img src="docs/images/ha-optionen-regelung.jpg" width="380" alt="Optionen: Fühler und Wetter"> |

### 4.4 Dashboard
Das Dashboard **„Wärmepumpe“** legt die Integration selbst an. Es erscheint nach dem Einrichten automatisch in der Seitenleiste, mit allen Unterseiten und dem Display-Nachbau. **card-mod oder andere Zusatzkarten sind nicht nötig** – auch die Diagramme der Seiten „PV“ und „Einsparungen“ bringt die Integration selbst mit. Mit jedem Update der Integration wird auch das Dashboard aktualisiert. Nach einem Update die Seite einmal neu laden (Cmd/Strg + Shift + R, in der App: Frontend-Cache zurücksetzen), sonst zeigen neue Karten „Konfigurationsfehler“.

<details><summary>Eigenes, veränderbares Dashboard statt des mitgelieferten</summary>

Das mitgelieferte Dashboard lässt sich in der Oberfläche nicht bearbeiten, dafür bleibt es immer aktuell. Wer es selbst anpassen will:
1. In den Optionen der Integration „Dashboard bereitstellen“ ausschalten.
2. Einstellungen → Dashboards → **Dashboard hinzufügen** → „Neues Dashboard von Grund auf“ → URL z. B. `waermepumpe`.
3. Dashboard öffnen → ✏️ → ⋮ → **Raw-Konfigurationseditor** → Inhalt von [`homeassistant/dashboards/waermepumpe.yaml`](homeassistant/dashboards/waermepumpe.yaml) einfügen → Speichern.
</details>

### 4.5 Umstieg vom früheren YAML-Paket
Wer die ältere Version mit `packages/avarma.yaml` nutzt (Stand: Branch [`yaml-paket`](https://github.com/KaHu85/HA-Hofman-Energy-Dashboard-avarma-heatpump/tree/yaml-paket)):
1. `packages/avarma.yaml` löschen (und `www/avarma/schema.svg`, wird nicht mehr gebraucht). Wird die Datei in der `configuration.yaml` einzeln eingebunden (z. B. `avarma: !include packages/avarma.yaml`), diese Zeile ebenfalls entfernen, sonst startet Home Assistant im Wiederherstellungsmodus. Dann neu starten.
2. Integration installieren und einrichten wie oben. Solange das alte Paket noch aktiv ist, startet die Integration absichtlich nicht.
3. Die Entitäten heißen wie vorher (z. B. `sensor.wp_vorlauf_tout`), dadurch laufen **Verläufe und Statistiken weiter**. Die Zähler (Starts, Wärme/Strom Woche/Monat/Jahr, Laufzeit) werden beim ersten Start aus der Historie übernommen.
4. Ein früher angelegtes Dashboard mit der URL `waermepumpe` löschen. Die Integration stellt ihres dann selbst bereit (Abschnitt 4.4). Geändert haben sich nur Code-Feld und Freigaben: `text.wp_code_eingeben`, `switch.wp_benutzer_freigabe`, `switch.wp_techniker_freigabe`.

---

## 5. Bedienung

| Reiter | Inhalt |
|---|---|
| **Arbeitsstatus** | Display-Nachbau, Hauptbild, EIN/AUS, Betriebsart, Nachtmodus, **Leistung jetzt** (W, kW, COP jetzt), Takte, Status, Verläufe |
| **Takte & Energie** | Leistung jetzt, Starts Tag/Woche/Monat/Jahr/gesamt, Ø Laufzeit, Start/Stopp-Aufzeichnung, Energie, COP, JAZ |
| **PV** | *optional*: Woher kommt der Strom der WP – PV, Akku, Netz; jetzt, Heute/Woche/Monat/Jahr, je Tag und je Monat (ohne Netz-Sensor nur ein Einrichtungshinweis) |
| **Einsparungen** | Heizkosten der WP (mit PV: mit/ohne PV und Ersparnis durch PV) und Ersparnis gegenüber Heizöl, Gas, Pellets, Stückholz; Jahresübersicht, **Heizwärmebedarf**, Diagramme je Monat und Jahr, CO₂; Preise und Angaben zum Haus eintragen |
| **Regelung** | *optional*: eigene Regelung ein/aus, Raum-Soll, max. Verschiebung, was die Regelung gerade macht, Verlauf 48 h mit den gewählten Fühlern |
| **Kältekreis** | TH/TL, Überhitzung, Unterkühlung, Temperaturhub mit Ampel und ausführlicher Erklärung, was gut und was schlecht ist |
| **Fehler** | aktive Fehler im Klartext, Fehlerspeicher, **Fehler quittieren**, Protokoll |
| **Parameter** | → **Benutzer-Parameter** / **Techniker-Parameter**, Nachtmodus, Freigabe |
| **Diagnose** | alle Rohwerte und Bits |

<img src="docs/images/display-parameter.jpg" width="420" align="right">

### Parameter ändern
1. **Benutzer-Freigabe** einschalten (oder im Feld **Code** `99` eingeben und Enter drücken). Techniker-Parameter: Techniker-Code eingeben bzw. – falls in den Optionen erlaubt – den Schalter **Techniker-Freigabe** umlegen. Die Freigabe gilt **15 Minuten**.
2. Wert ändern. Er wird sofort per Modbus in die Wärmepumpe geschrieben, zurückgelesen und im **Logbuch** vermerkt.
3. Ohne Freigabe wird **nichts** geschrieben, und Home Assistant zeigt einen Hinweis.

> ℹ️ **Änderungen am Display oder in der Smart-Life-App erscheinen in Home Assistant erst nach bis zu 15 Minuten.** Die Integration liest die Parameterliste (P06–P150, P201–P208) nur alle 15 Minuten, um den Modbus zu schonen. Nur P02–P05 (Vorlauf-, Kühl-, Warmwasser- und Raum-Soll) und Ein/Aus/Betriebsart kommen alle 10 Sekunden. Steht ein in der App geänderter Wert (z. B. R2 = P148) noch auf dem alten Stand, ist das kein Fehler: einfach etwas warten. Was du in Home Assistant änderst, wird sofort zurückgelesen.

> ⚠️ **Techniker-Parameter sind gefährlich!** Sie steuern Kältekreis, Verdichter, Expansionsventil, Schutz- und Abtaufunktionen. Falsche Werte können die Wärmepumpe in Dauerstörung bringen, den Verdichter beschädigen oder Schutzabschaltungen aushebeln, und eventuell geht die Garantie verloren. **Ändere dort nur etwas, wenn du genau weißt, was der Parameter bewirkt.** Notiere vorher den alten Wert und frag im Zweifel den Hersteller oder Fachbetrieb.

Neben jedem Eingabefeld steht in der Spalte **„Werk (9 kW)“** der Werkswert laut Hofman-Werksliste. ⚠️ Er gilt für die 9-kW-Anlage; andere Leistungsgrößen können andere Werkswerte haben.

Die komplette Liste mit Adressen, Bereichen und Erklärungen steht in **[docs/parameter.md](docs/parameter.md)**, alle Register in **[docs/register.md](docs/register.md)**.

<br clear="right">

### Takte (Kompressor-Starts)
Grundlage ist der **interne Startzähler der Wärmepumpe** (Register 4608). Er zählt also auch Starts, bevor Home Assistant lief. Viele Starts mit kurzer Ø-Laufzeit heißt: Die Anlage taktet. Stellschrauben dafür sind z. B. **P06** (Hysterese), **P46** (Mindestfrequenz) und **P114** (Frequenzreduktion) – oder die Regelung [Übergangszeit](#übergangszeit-optional-technikerzugang-auf-eigene-gefahr).

**Abtauungen:** Grundlage ist der Abtau-Zähler der WP (Register 4613). Angezeigt werden *Abtauungen heute*, *Abtauungen 24 h* und *Abtauungen pro Tag (30 Tage)*; im Start/Stopp-Verlauf sind die Abtauphasen markiert. **Abtauen ist kein Start:** Beim Abtauen meldet der Binärsensor „Kompressor läuft“ kurz aus und wieder ein – für Starts deshalb immer den Startzähler (*Kompressor-Starts heute*) nehmen, nicht den Binärsensor. Beim ersten Start holt die Integration die Ausgangswerte aus dem HA-Verlauf von `sensor.wp_abtauvorgange`.

### Energie
<img src="docs/images/display-energie.jpg" width="380" align="right">

Die Werte kommen direkt aus den Energiezählern der Wärmepumpe (dieselben wie am Display unter „Tägliche/Monatliche Energie“). Die Zähler für Woche, Monat und Jahr können auch im **Energie-Dashboard** verwendet werden.

<br clear="right">

### Leistung jetzt (W) und COP jetzt
Ein eigenes Register für die Leistung hat die Wärmepumpe nicht. Die Integration rechnet **Netzspannung × Strom** (Register 4381 und 4379) – das ist die Scheinleistung und liegt typisch 10–20 % über dem tatsächlichen Verbrauch. Deshalb wird sie **laufend mit dem Stromzähler der WP abgeglichen** (Faktor als Attribut `faktor` von `sensor.wp_leistung_elektrisch`, bei der getesteten Anlage ≈ 0,88). Der Abgleich startet nach rund 2 kWh Heizbetrieb, bis dahin wird die ungekürzte Scheinleistung angezeigt. **COP jetzt** = Wärmeleistung ÷ elektrische Leistung, nur bei laufendem Kompressor.

### PV: Woher kommt der Strom der Wärmepumpe? (optional)
Voraussetzung: in den Optionen (4.3) die **Netzleistung des Hauses** eintragen, bei einem Hausakku zusätzlich die **Akkuleistung**. Ohne diese Angaben zeigt die Seite „PV“ nur einen Hinweis, was einzutragen ist.

So wird gerechnet: Die WP zählt ihren Strom in 0,1-kWh-Schritten. Jeder Schritt wird mit dem gleichzeitig gemessenen Netzbezug und der Akku-Entladung verglichen. **Netz zuerst** (so viel, wie das Haus in der Zeit bezogen hat), **dann Akku** (so viel, wie der Akku abgegeben hat), **der Rest ist PV**. Laufen gleichzeitig andere Verbraucher, wird der Netzanteil der WP dadurch eher zu hoch angesetzt – die PV-Ersparnis ist also eher vorsichtig gerechnet. Akkuladung aus dem Netz wird nicht erkannt. Beim ersten Eintragen rechnet die Integration rückwirkend ab Jahresbeginn nach, soweit Home Assistant Statistiken der Sensoren hat.

![Seite PV](docs/images/ha-pv.jpg)

Die Seite zeigt die Leistung jetzt sowie Heute, Woche, Monat und Jahr als Anteilsbalken, dazu Balkendiagramme je Tag (letzte 30 Tage) und je Monat. Zusätzlich gibt es die Sensoren `sensor.wp_strom_aus_netz_…`, `…_akku_…`, `…_pv_…` (heute/woche/monat/jahr) und `sensor.wp_netzanteil_strom_…`.

### Einsparungen: Was spart die Wärmepumpe?
![Seite Einsparungen](docs/images/ha-einsparungen.jpg)

Auf der Seite **„Einsparungen“** rechts die eigenen Preise eintragen (Felder mit Beispielwerten vorbelegt):

| Bereich | Felder | Hinweise |
|---|---|---|
| **Strom (Wärmepumpe)** | Arbeitspreis und Netzkosten in **€/kWh**, Grundgebühr WP in **€/Jahr**, PV-Einspeisevergütung in **€/kWh**, Wartung WP in **€/Jahr** | Grundgebühr nur eintragen, wenn die WP einen eigenen Zähler/Tarif hat. Die Einspeisevergütung zählt nur mit PV (Seite „PV“): Strom aus PV/Akku kostet so viel, wie man beim Einspeisen bekommen hätte. |
| **Heizöl** | Preis in **€/Liter**, Wartung in **€/Jahr** | Wartung inkl. Rauchfangkehrer/Kaminkehrer. |
| **Gas** | Preis in **€/kWh oder €/m³** (einer genügt, der andere wird umgerechnet), Umrechnung kWh/m³ **laut Gasrechnung**, Grundgebühr/Zähler und Wartung in **€/Jahr** | |
| **Pellets** | Preis in **€/kg oder €/Tonne** (einer genügt), Wartung in **€/Jahr** | |
| **Stückholz** | Preis in **€/Raummeter**, Wartung in **€/Jahr** | Hartholz, 1.900 kWh/Raummeter. |
| **Haus (für HWB)** | beheizte Wohnfläche in **m²**, Norm-Außentemperatur in **°C**, Heizgradtage pro Jahr (20/12) in **Kd** | Für den Heizwärmebedarf (siehe unten). Vorbelegt mit Werten für Bregenz (−10 °C, 3.456 Kd, 130 m²) – **bitte an den eigenen Standort anpassen**. |

**Mit PV** (Netz-Sensor in den Optionen eingetragen) zeigt die Seite zusätzlich die **Heizkosten der WP ohne PV** – also wenn der gesamte WP-Strom zum Netzpreis gekauft worden wäre – und die **Ersparnis durch die PV** (Kacheln, eigene Zeilen in der Jahresübersicht und ein eigener Balken im Diagramm). Ohne PV entfällt das automatisch.

Grundlage ist die **Wärme laut Zähler der Wärmepumpe**, je Monat. Für jede Alternative wird gerechnet, was dieselbe Wärme gekostet hätte: Brennstoff = Wärme ÷ Nutzungsgrad (Öl 92 %, Gas 95 %, Pellets 90 %, Holz 75 %; Heizwerte Öl 10 kWh/l, Pellets 4,9 kWh/kg) plus Grundgebühr und Wartung je 1/12 pro Monat. Die WP kostet Netzstrom × (Arbeitspreis + Netzkosten) + PV/Akku-Strom × Einspeisevergütung + Grundgebühr/Wartung. **Ersparnis = Kosten der Alternative − Kosten der WP.** CO₂ nach Klimabilanz (Öl 0,310 · Gas 0,247 · Pellets 0,036 · Holz 0,020 kg je kWh Brennstoff, Netzstrom 0,227 kg/kWh, Österreich).

Gerechnet wird immer mit den **aktuell eingetragenen Preisen**, auch für vergangene Monate. Die Monate beginnen mit dem ersten Monat, in dem die WP Wärme geliefert hat; die WP selbst kennt nur das laufende Jahr, die Integration hebt die Monate für die Vorjahre auf. Ohne Netz-Sensor zählt der gesamte WP-Strom als Netzstrom.

### Heizwärmebedarf
Die Integration merkt sich je Tag die **Wärme der WP** (Tageszähler) und die **mittlere Außentemperatur** (eigener Außenfühler, falls eingetragen, sonst Fühler der WP); vorhandene Tage werden beim ersten Start aus den Home-Assistant-Statistiken übernommen. Daraus berechnet die Seite „Einsparungen“:

| Kennwert | Rechenweg |
|---|---|
| **Heizlast** (kW) | Gerade durch die Tageswärme über der mittleren Außentemperatur (Heiztage unter 15 °C), abgelesen bei der **Norm-Außentemperatur** ÷ 24 h |
| **Heizwärmebedarf pro Jahr** (kWh) | gemessene Wärme ÷ gemessene **Heizgradtage (20/12)** × Heizgradtage eines normalen Jahres am Standort |
| **je m²** (kWh/m²·Jahr) | Jahresbedarf ÷ beheizte Wohnfläche – vergleichbar mit dem Energieausweis |
| Heizgrenze, Wärme je Heizgradtag, Datenbasis, R² | zur Einordnung, wie gut die Werte schon sind |

Werte erscheinen ab 7 Heiztagen; je mehr kalte Tage, desto genauer.

#### Wo finde ich Heizgradtage (Kd) und Norm-Außentemperatur für meinen Standort?

**Was die Werte bedeuten:**
- **Heizgradtage HGT 20/12** (Einheit Kd = Kelvin·Tage): Für jeden Tag mit einer mittleren Außentemperatur **unter 12 °C** wird der Abstand zu **20 °C** Raumtemperatur gezählt und über ein ganzes, durchschnittliches Jahr aufsummiert. Beispiel: Ein Tag mit 2 °C Tagesmittel zählt 20 − 2 = 18 Kd, ein Tag mit 13 °C zählt gar nicht. Je kälter und länger der Winter am Standort, desto höher der Wert.
- **Norm-Außentemperatur** (°C): die tiefe Außentemperatur, für die eine Heizung am Standort ausgelegt wird (Heizlastberechnung). Sie hängt von Region und Seehöhe ab.

**Wo nachschauen (in dieser Reihenfolge):**
1. **Eigener Energieausweis** (Österreich): Im Anhang bzw. auf der Seite **„Klimadaten“ / „Standortklima“** stehen *Heizgradtage (12/20) in Kd*, *Heiztage* und *Norm-Außentemperatur* – nach ÖNORM B 8110-5 genau für Ort und Seehöhe des Hauses gerechnet. Das ist die beste Quelle.
2. **Kein eigener Energieausweis?** Energieausweise anderer Gebäude **im selben Ort** (z. B. in Immobilienanzeigen als PDF) nennen dieselben Klimadaten für den Ort. So stammen die vorbelegten Werte für Bregenz (3.456 Kd, −10 °C).
3. **Heizlastberechnung** des Installateurs (ÖNORM EN 12831): Dort steht immer die **Norm-Außentemperatur**.
4. **Österreich, Wetterdaten:** [GeoSphere Austria (Data Hub)](https://data.hub.geosphere.at/) liefert Tagesmitteltemperaturen der nächsten Messstation – daraus lassen sich die Heizgradtage selbst rechnen (siehe unten). Für Niederösterreich gibt es fertige Tabellen der [Energie- und Umweltagentur NÖ](https://www.energie-noe.at/download/NOE_HGT_Heizsaisonsummen_2012-2024_Kunze.pdf).
5. **Deutschland:** Das Tool [„Gradtagzahlen-Deutschland.xlsx“ des IWU](https://www.iwu.de/fileadmin/publikationen/energie/mobasy/2020_IWU_LogaGrossklosLandgraf_MOBASYTeilberichtKlimadatenRealbilanzierung.pdf) (Daten des DWD, nach Postleitzahl). ⚠️ In Deutschland sind oft andere Bezugswerte üblich (z. B. Gradtagzahl 20/15 oder Heizgrenze 15 °C) – für diese Integration den Wert **20/12** verwenden oder selbst rechnen.
6. **Schweiz:** Heizgradtage nach SIA (ebenfalls **20/12**) von MeteoSchweiz, z. B. über [opendata.swiss](https://ckan.opendata.swiss/en/perma/ogd105%40bundesamt-fur-energie-bfe).

**Selbst rechnen:** Tagesmittel der Außentemperatur für mehrere ganze Jahre besorgen (Wetterstation in der Nähe), je Jahr `Summe über alle Tage mit Tmittel < 12 °C von (20 − Tmittel)` bilden und den **Mittelwert über mehrere Jahre** nehmen – ein einzelnes Jahr kann deutlich wärmer oder kälter sein.

**Faustwerte zur Kontrolle:** Tallagen in Österreich liegen meist bei rund **3.000–3.700 Kd** und einer Norm-Außentemperatur um **−10 bis −14 °C**; höher gelegene Orte haben deutlich mehr Heizgradtage und tiefere Norm-Außentemperaturen. Weicht dein Wert stark davon ab, lieber nochmals prüfen.

> ⚠️ Gerechnet wird **nur mit der Wärme laut Zähler der WP**. Heizen Ofen, Solarthermie oder eine andere Heizung mit, ist der echte Bedarf des Hauses höher. Bereitet die WP auch Warmwasser, ist es in der Wärme enthalten. Der Außenfühler der WP kann in der Sonne zu hoch messen.

### Eigene Regelung (optional)
Idee nach [holle74/avarma-eigenbau-regelung](https://github.com/holle74/avarma-eigenbau-regelung) – aber bewusst **sanft und ausfallsicher**: Die **eingebaute Heizkurve der WP bleibt aktiv**, die Integration verschiebt sie nur über **P09 (Heizkurven-Verschiebung)**. Fällt Home Assistant aus, heizt die WP mit ihrer Kurve und der zuletzt gesetzten Verschiebung einfach weiter. Es wird **nichts anderes** geschrieben (kein Vorlauf-Soll, keine Kompressor- oder Lüftervorgaben).

**Einrichten:** In den Optionen (4.3) Raumfühler wählen, optional eigenen Außenfühler und Wetter. Dann auf der Seite **„Regelung“** (Einstellungen rechts) das **Raum-Soll** (Standard 22 °C, in 0,1-K-Schritten) und die **max. Verschiebung** (Standard 5 K, 2–10 K) einstellen, unter **„Gebäude / Heizsystem“** Heizkörper oder Fußbodenheizung wählen und mit dem Schalter **„Eigene Regelung“** einschalten. Die Tabelle „Was die Regelung gerade macht“ zeigt auch bei ausgeschalteter Regelung, was sie tun *würde* – erst ein paar Stunden zuschauen, dann einschalten.

| Baustein | Was er tut |
|---|---|
| **Raum-Nachführung** | Raumfühler gegen das Raum-Soll (lernend, Grenze = max. Verschiebung), Verhalten einstellbar über **Gebäude / Heizsystem** (Heizkörper, Fußbodenheizung, Benutzerdefiniert) und die **Feineinstellung** (Werte für Heizkörper): mehr als 0,5 K zu kalt (Mittel 1 h) → je K 1 K hoch (0,5–1,5 K), höchstens alle 90 min; sonst mehr als 0,3 K zu kalt (Mittel 3 h) → +0,5 K, höchstens alle 3 h; seit ≥ 50 min durchgehend mehr als 0,3 K zu warm → je K 1 K zurück (0,5–1 K), höchstens jede Stunde (kurze Fremdwärme von Ofen/Kochen zählt nicht). Fußbodenheizung: vorsichtiger und mit längeren Abständen. Lernt nur so weit, wie der Baustein zusammen mit den anderen unter der Grenze noch wirkt (kein Aufschaukeln). Andere Raumfühler gewählt → beginnt neu bei 0 K |
| **Prognose** | Stundenprognose der Wetter-Entität (z. B. Open-Meteo): mittlere Temperatur der nächsten *Vorausschau* h (Heizkörper 3 h, FBH 8 h) gegen die Prognose für jetzt. Kälter angesagt → Kurve vorab hoch, wärmer → runter (Steigung der Heizkurve × Differenz × Gewichtung 50 % / 70 %, höchstens ± 3 K; Gewichtung 0 % = aus). Da beides aus derselben Prognose kommt, stört ein Versatz zum eigenen Fühler nicht |
| **Sonnenkorrektur** | nur mit eigenem Außenfühler: misst der WP-Fühler wärmer als dein Fühler, rechnet die WP zu wenig Vorlauf – ausgeglichen mit der gemessenen Steigung ihrer Heizkurve, über 60 min gemittelt |
| **Vorladen vor Frost** | nur mit Wetter: Minimum der nächsten 24 h unter 3 °C → tagsüber (7–22 Uhr) bis +2 K |
| **Wärmste Stunden** *(experimentell, eigener Schalter)* | nur mit Wetter: ist es jetzt wärmer als im Mittel der nächsten 24 h, etwas hoch, ist es kälter, etwas runter (siehe unten) |

#### Feineinstellung (jedes Haus reagiert anders)

Die Karte **„Feineinstellung“** auf der Seite „Regelung“ (rechts) legt fest, wie schnell die Raum-Nachführung reagiert. Oben steht **„Gebäude / Heizsystem“**:

- **Heizkörper** – reagiert schneller (Startwerte unten, Spalte HK)
- **Fußbodenheizung** – träger und vorsichtiger, längere Abstände (Spalte FBH, *Startwerte geschätzt, noch nicht erprobt*)
- **Benutzerdefiniert** – entsteht automatisch, sobald ein Wert von Hand geändert wird

Ein Profil wählen setzt alle Werte auf dessen Startwerte. Jede Änderung steht im Logbuch. Im Namen jedes Werts stehen die Startwerte beider Profile und der erlaubte Bereich; der Wert selbst wird rechts eingetippt.

| Wert | HK | FBH | erlaubt | Bedeutung |
|---|---|---|---|---|
| Deutlich zu kalt ab | 0,5 K | 0,7 K | 0,3–2 K | ab dieser Abweichung (Mittel 1 h) schneller Schritt nach oben |
| Hoch je K zu kalt | 1,0 K | 0,7 K | 0,2–3 K | so viel K Verschiebung je K zu kalt |
| Hoch höchstens je Schritt | 1,5 K | 1,0 K | 0,3–3 K | Obergrenze eines schnellen Schritts |
| Hoch frühestens alle | 90 min | 180 min | 30–360 min | Abstand zwischen zwei Schritten nach oben |
| Totband | 0,3 K | 0,3 K | 0,1–1 K | darunter keine Reaktion |
| Kleine Abweichung: Schritt | 0,5 K | 0,3 K | 0,1–1 K | Schritt bei kleiner Abweichung (Mittel 3 h), zugleich kleinster Schritt |
| Kleine Abweichung: alle | 180 min | 360 min | 60–720 min | Abstand bei kleiner Abweichung |
| Zu warm mindestens | 50 min | 120 min | 10–180 min | so lange muss es **durchgehend** zu warm sein (kurze Fremdwärme von Ofen/Kochen zählt nicht) |
| Runter je K zu warm | 1,0 K | 0,7 K | 0,2–3 K | so viel K zurück je K zu warm |
| Runter höchstens je Schritt | 1,0 K | 1,0 K | 0,3–3 K | Obergrenze eines Schritts nach unten |
| Runter frühestens alle | 60 min | 180 min | 30–360 min | Abstand zwischen zwei Schritten nach unten |
| Prognose: Vorausschau | 3 h | 8 h | 0–12 h | so weit schaut der Prognose-Baustein voraus (0 = aus) |
| Prognose: Gewichtung | 50 % | 70 % | 0–100 % | Stärke des Prognose-Bausteins (0 % = aus) |

Entitäten: `select.wp_regelung_profil`, `number.wp_rg_*` (z. B. `number.wp_rg_kalt_abstand`), `number.wp_regelung_raum_soll`, `number.wp_regelung_max_verschiebung`, `switch.wp_heizkurve_lernen_p08`, `switch.wp_warmste_stunden_nutzen`.

#### Heizkurve P08: Ausgleich und Lernen

Die Regelung kennt die Form der eingebauten Heizkurve (aus Messwerten abgeleitet: 25 °C Vorlauf ab 17 °C außen, P08 bei −3 °C außen, dazwischen eine Gerade).

- **Ausgleich (immer):** Ändert sich P08 – von Hand, am Display oder gelernt –, verschiebt die Regelung ihre Raum-Nachführung um genau die Wirkung bei der aktuellen Außentemperatur. Es wird also nicht doppelt korrigiert.
- **Heizkurve lernen** (Schalter `switch.wp_heizkurve_lernen_p08`, Standard aus): Einmal am Tag ab 14 Uhr wertet die Regelung die letzten 3 Tage aus. Zieht sie umso mehr ab, je kälter es ist, ist die Kurve zu steil → P08 runter; umgekehrt rauf. Höchstens 1 °C am Tag, Bereich 40–55 °C, nur mit ≥ 24 h Daten, ≥ 3 K Temperaturspanne und klarem Zusammenhang. Ergebnis im Logbuch und auf der Seite „Regelung“.

P08 regelt so vor allem die **Steigung**; ob es insgesamt wärmer oder kühler sein soll, stellst du über das Raum-Soll ein.

#### Wärmste Stunden (experimentell)

Eine Wärmepumpe arbeitet effizienter, je wärmer die Außenluft ist (grob 2–3 % COP je K). Mit dem Schalter `switch.wp_warmste_stunden_nutzen` (Standard aus) hebt die Regelung die Kurve etwas an, wenn es laut Stundenprognose jetzt wärmer ist als im Mittel der nächsten 24 h, und senkt sie ab, wenn es kälter ist. Stärke und Grenze stehen in der Feineinstellung (Heizkörper 50 % / ± 1,5 K, FBH 70 % / ± 2 K).

- **Komfort:** angehoben wird nur bis Raum = Soll + 0,5 K, abgesenkt nur bis Soll − 0,5 K.
- **Schutz:** Solange er an ist, sind Totband und „deutlich zu kalt“ der Raum-Nachführung 0,3 K weiter; Stunden mit mehr als ± 1 K zählen nicht für das Heizkurven-Lernen.
- **Auswertung:** Die Karte „Wärmste Stunden – Auswertung je Tag“ zeigt Außen Ø, Außen je erzeugter kWh („Vorteil“), Starts, Laufzeit, Wärme, Strom und COP – auch mit Schalter aus, damit man Tage vergleichen kann.

> ℹ️ **Erwartung realistisch halten:** Läuft die WP fast durchgehend und ist der Unterschied zwischen Tag und Nacht klein, lässt sich kaum etwas verschieben – erwartet sind dann eher 0–1 %. Mehr bringt es an Tagen mit großem Tag/Nacht-Unterschied (Frühjahr, Herbst). Gemessen ist der Nutzen noch nicht.

#### Wetterprognose einrichten

Für den Prognose-Baustein, das Vorladen und die Vorhersage auf der Seite braucht es eine **Wetter-Entität mit Stundenprognose**. Installiert wird dafür nichts extra:

1. **Open-Meteo** (empfohlen für Österreich/Deutschland, rechnet mit dem DWD-Modell ICON-D2, kein Konto, kein API-Schlüssel): **Einstellungen → Geräte & Dienste → Integration hinzufügen → „Open-Meteo“**. Alternativ **Met.no** („Forecast Home“, `weather.forecast_home`) – das richtet Home Assistant meist schon bei der Ersteinrichtung ein.
2. In den Optionen der Avarma-Integration **„Wetter mit Stundenprognose“** wählen – vorgeschlagen ist Open-Meteo, sonst Met.no – und speichern.
3. Bei Met.no unter **Einstellungen → System → Allgemein** die richtige **Höhe** eintragen. Mit 0 m rechnet Met.no die Temperatur auf Meereshöhe um und sagt sie zu warm vorher.

Ohne Wetter-Entität läuft die Regelung trotzdem; Prognose und Vorladen bleiben dann bei 0, und auf der Seite „Regelung“ erscheint statt der Vorhersage ein Hinweis zum Einrichten.

#### Was die Seite „Regelung“ zeigt

Links: **„Was die Regelung gerade macht“** (alle Bausteine mit Wert, Ziel-P09, Status; die ausführliche Erklärung ist unter „So rechnet die Regelung“ aufklappbar), **Verlauf 48 h** (Raum, Raum-Soll, P09, Außen), die **stündliche Wettervorhersage** und die **Temperaturprognose 24 h als Kurve** (schattiert: das Fenster, das die Regelung als Vorausschau nutzt). Rechts: Schalter, Raum-Soll, max. Verschiebung und die Feineinstellung. Die Seite bleibt sichtbar, solange die Regelung eingeschaltet ist – auch wenn ein Raumfühler kurz ausfällt.

**Grenzen und Schutz gegen Takten:**
- gesamt höchstens ± max. Verschiebung um den Wert, den P09 beim Einschalten hatte; P09-Bereich −10…+10 K
- geschrieben wird erst ab 0,5 K Änderung, **höchstens alle 30 min**, je Schritt höchstens +2 K / −1 K
- **Absenkbremse:** bei laufendem Kompressor wird erst abgesenkt, wenn der Vorlauf schon unter dem neuen Soll liegt (sonst stoppt die WP) – höchstens 60 min warten
- **Takt-Schutz:** nach 3 Kompressorstarts in 2 h werden 2 h lang keine Änderungen gemacht
- pausiert, wenn die Heizkurve der WP aus ist (P19 = 0), die WP aus ist oder nicht heizt
- jede Änderung steht im **Logbuch**; **Ausschalten** stellt den ursprünglichen P09 wieder her
- **Seite „Regelung“ in den Optionen abgewählt** → Regelung schaltet sich aus, P09 zurück auf den Grundwert
- **keine Raumfühler mehr gewählt** → P09 zurück auf den Grundwert, Regelung pausiert
- Takt und Einstellungsänderung laufen nie gleichzeitig (kein doppeltes Schreiben)

Im Verlauf erscheinen die gewählten Fühler mit ihrem Namen. Den Namen legst du in Home Assistant an der Entität fest (⚙️ → **Name**) – die **Entitäts-ID nicht ändern**, sonst müssen die Fühler in den Optionen neu gewählt werden.

### Übergangszeit (optional, Technikerzugang, auf eigene Gefahr)

> ⚠️ **Achtung – auf eigene Gefahr!** Diese Regelung schreibt mit dem Technikerzugang selbstständig **Techniker-Parameter** in die Wärmepumpe. Falsche Werte können zu Störungen, Vereisung, zu wenig Leistung oder Schäden führen; eventuell geht die Garantie verloren.

**Wozu:** In der Übergangszeit braucht das Haus wenig Wärme. Die WP läuft mit voller Leistung an, erreicht das Soll schnell und schaltet ab – sie **taktet**. Mit weniger Lüfter, niedrigerer Höchstfrequenz und mehr Frequenzreduktion moduliert sie weiter herunter und läuft länger durch.

**Voraussetzungen:** Techniker-Code in den Optionen (4.3) hinterlegt – eine Code-Eingabe oder 15-min-Freigabe ist dafür **nicht** nötig. Auf der Seite **„Übergangszeit“** den Warnhinweis mit **„Ich bestätige“** quittieren (blendet ihn aus, „wieder anzeigen“ holt ihn zurück). Ohne beides lässt sie sich nicht einschalten und nicht einstellen. **Ausschalten geht immer** und schreibt sofort die Normalwerte zurück.

**Wann:** Übergangszeit, sobald die Außentemperatur (Mittel 30 min) **≥ „ab“** ist; zurück zu den Normalwerten erst **unter „ab − Hysterese“**. Umgeschaltet wird **höchstens einmal pro Stunde**. Beispiel 13 °C / 2 K: ab 13,0 °C Übergangszeit, unter 11,0 °C wieder normal, dazwischen bleibt der aktuelle Zustand.

**Außenfühler (wählbar):**

| Auswahl | Verwendet | Fehlt er … |
|---|---|---|
| Eigener Außenfühler (Standard) | Fühler aus den Optionen; ist keiner eingetragen, der Fühler der WP | … wird der andere genommen |
| Außenfühler der WP | interner Fühler der WP (misst in der Sonne oft viel zu warm) | … wird der eigene genommen |
| Kleinerer Wert von beiden | der kühlere der beiden (am vorsichtigsten) | … wird der vorhandene genommen |

Welcher Fühler gerade zählt, steht im Status.

| Einstellung | Grundwert | erlaubt |
|---|---|---|
| Ab Außentemperatur | 13 °C | 5–20 °C |
| Hysterese | 2 K | 0,5–4 K |
| **P60** Lüfter max. in der Übergangszeit | 400 U/min | 400–1500 U/min |
| **P45** Kompressor max. in der Übergangszeit | 50 Hz | 50–85 Hz |
| **P114** Frequenzreduktion in der Übergangszeit | 15 % | 0–60 % |
| Normalwerte P60 / P45 / P114 | aus der WP übernommen | wie oben |

**Normalwerte:** Solange die Übergangszeit nicht gilt, übernimmt die Regelung, was in der WP steht (am Display oder auf der Parameterseite geändert → neuer Normalwert, steht im Verlauf). Normalwerte lassen sich auch direkt auf der Seite ändern und werden dann sofort geschrieben. **Während** der Übergangszeit setzt die Regelung ihre Werte – Änderungen dann auf ihrer Seite machen.

**Nachverfolgung:** Jeder Wert wird nach dem Schreiben **zurückgelesen**; nimmt die WP ihn nicht an, steht „nicht übernommen“ im Verlauf und es wird erst nach 1 h erneut versucht. Alles steht in der scrollbaren Liste **„Verlauf der Änderungen“** (100 Einträge), im **Logbuch** (30 Tage) und im Verlauf von Außentemperatur, P60, P45, P114 und Starts (7 Tage). Mehrere Klicks auf eine Einstellung ergeben **einen** Eintrag (20 s nach dem letzten Klick). Takt und Einstellungsänderung laufen nie gleichzeitig, jeder Schreibvorgang steht also genau einmal im Verlauf. Die Tabelle „Was die Übergangszeit gerade macht“ zeigt je Parameter: jetzt in der WP, Übergangszeit, Normalwert, dazu beide Außenfühler.

**Seite „Übergangszeit“** (3 Spalten, am Handy untereinander): oben Schalter und Status · wann gilt sie · Werte in der Übergangszeit; darunter der **Verlauf der Änderungen** (so hoch wie die Reihe, sonst 10 Einträge, Rest scrollen) · was sie gerade macht (Erklärung aufklappbar) · Normalwerte; dann je drei Graphen (7 Tage): Außentemperatur, Kompressor-Starts, Vorlauf/Heizkurven-Soll, Lüfter P60 und Drehzahl, Kompressor P45 und Frequenz, P114; unten das Logbuch.

**Abschalten über die Optionen:** Seite „Übergangszeit“ abgewählt → die Übergangszeit schaltet sich aus und schreibt die Normalwerte zurück (wird sie trotzdem wieder eingeschaltet, schaltet die Integration sie beim nächsten Durchlauf erneut aus). Den Techniker-Code kann man erst löschen, wenn sie aus ist und alle Normalwerte zurückgeschrieben sind.

**Kompressor-Stufen** (Schalter `switch.wp_uz_kompressor_stufen`, Standard aus, Technikerzugang): Auch **unterhalb** der Übergangszeit begrenzt die Regelung dann P45 nach der Außentemperatur (Mittel 30 min). Zweck: Nach dem Abtauen fährt die WP sonst auf die volle Höchstfrequenz hoch und regelt danach wieder herunter – mit Stufen läuft der Kompressor gleichmäßiger.

| Stufe | Grundwert ab | Grundwert P45 | erlaubt |
|---|---|---|---|
| Stufe 1 | 5 °C | 52 Hz | −15…15 °C / 40–85 Hz |
| Stufe 2 | 0 °C | 56 Hz | wie oben |
| Stufe 3 | −5 °C | 60 Hz | wie oben |
| Stufe 4 | −10 °C | 72 Hz | wie oben |
| Darunter | – | 85 Hz (Werkswert, volle Leistung) | 40–85 Hz |

- In eine **kältere** Stufe geht es, sobald es 1 K unter der Grenze der aktuellen Stufe ist; in eine **wärmere** höchstens einmal pro Stunde.
- Solange Stufen gelten, wird P45 nicht als Normalwert übernommen; der Normalwert gilt nur bei ausgeschalteten Stufen.
- Jeder Wechsel steht im Verlauf und im Logbuch.
- Erfahrung an der 9-kW-Anlage bei ~0 °C (Stufe 2): Frequenz deutlich gleichmäßiger, keine Spitzen über 60 Hz, kein messbarer Unterschied beim COP, Raum unverändert. Nach dem Abtauen braucht der Vorlauf etwas länger, bis er wieder oben ist. **Die Grundwerte gelten für 9 kW** – bei kleineren Anlagen vorher prüfen, ob die Leistung bei Frost reicht.

**Bewusst nicht dabei:** Pumpe (P58/P59/P20) – mehr Durchfluss hilft nur wenig, weniger Durchfluss schadet eher; **P46** (Mindestfrequenz) – Hofman nennt 35 Hz, darunter steigt das Risiko für Ölrückführung und Schmierung.

Entitäten: `switch.wp_ubergangszeit`, `switch.wp_uz_hinweis_bestatigt`, `select.wp_uz_aussenfuehler`, `number.wp_uz_ab`, `number.wp_uz_hyst`, `number.wp_uz_p60|p45|p114`, `number.wp_uz_normal_p60|p45|p114`, `switch.wp_uz_kompressor_stufen`, `number.wp_uz_s1_ab…s4_ab`, `number.wp_uz_s1_hz…s4_hz`, `number.wp_uz_kalt_hz`, `sensor.wp_ubergangszeit_status` (Attribute: Außentemperatur, Quelle, Ist-/Übergangs-/Normalwerte, `verlauf` – nicht im Recorder gespeichert).

### Uhr der Wärmepumpe – nur am Display stellbar
Die Uhr der Wärmepumpe lässt sich **nur direkt am Display** stellen. Über Modbus bestätigt die Steuerung zwar das Schreiben der Uhrzeit (Register 4106/4107), übernimmt sie aber nicht. Getestet an Platine 23557 / Software 1518 mit Funktion 0x06 und 0x10.

- Nach jeder **Zeitumstellung** (Ende März und Ende Oktober) die Uhr am Display neu stellen und dabei auch das **Datum** prüfen.
- Am Tag der Zeitumstellung erinnert die Integration um 09:00 mit einer Meldung in Home Assistant und, falls eingerichtet, mit einer Push-Nachricht.
- Weicht die Uhr mehr als 10 Minuten ab, erscheint zusätzlich der Hinweis „Wärmepumpe: Uhr am Display stellen“. Geprüft wird beim Start und täglich um 03:17.
- Warum das wichtig ist: Die Wärmepumpe beginnt „heute“ nach ihrer eigenen Uhr. Geht sie falsch, stimmen Wärme, Strom und COP heute nicht, und die Tageswerte werden dem falschen Tag zugeordnet.

### R290-Kältemittel-Alarm
Der Alarm wird ausgelöst bei Alarm-Flag, Konzentration > 0 **oder** Fehler **E51**. Dann gibt es eine Meldung in Home Assistant und eine kritische Push-Nachricht.
> ⚠️ **Ob bei meiner Anlage überhaupt ein R290-Konzentrationssensor verbaut ist, weiß ich selbst nicht sicher.** Meine 9 kW meldet als Konzentration 0 und als **Alarmgrenze 0**. Das spricht eher dafür, dass kein Sensor aktiv ist. Ob ein Sensor verbaut ist, hängt vom Modell ab, bitte beim Hersteller erfragen.
> **Diese Funktion ersetzt keinen Gaswarnmelder.** Den Sensor bitte **nicht** selbst mit Feuerzeuggas testen (brennbares Gas im Gerät mit Elektrik).

---

## 6. Für Bastler

| Datei | Zweck |
|---|---|
| `custom_components/avarma/params.py` | Parameterliste: Display-Nummer → Adresse, Skalierung, Bereich, Ebene, Erklärung |
| `custom_components/avarma/` | die Integration (eigener schlanker Modbus-Client, keine Zusatzpakete) |
| `custom_components/avarma/einsparung.py` | Preise, Brennstoffe, Rechenweg der Seite „Einsparungen“ |
| `custom_components/avarma/regelung.py` | Rechenregeln der eigenen Regelung (Bausteine, Grenzen, Absenkbremse, Takt-Schutz) |
| `custom_components/avarma/uebergang.py` | Übergangszeit: Werte mit Grundwert und Grenzen, Fühlerwahl, Umschaltregel mit Hysterese |
| `custom_components/avarma/www/avarma-cards.js` | eigene Karten: `avarma-schema-card` (Display-Nachbau), `avarma-bar-card` (Balken je Monat/Tag/Jahr, gruppiert oder gestapelt), `avarma-source-card` (Herkunft PV/Akku/Netz), `avarma-history-card` (Verlauf mit den in den Optionen gewählten Fühlern), `avarma-list-card` (Liste aus einem Attribut, scrollbar) |
| `tools/dash2.py` | erzeugt das Dashboard (`homeassistant/dashboards/waermepumpe.yaml`) |
| `tools/entity_map.json` | Zuordnung Schlüssel → Entity-ID für den Dashboard-Generator |

Ereignis für eigene Automationen: `avarma_stoerung` (Daten: `fehler` = neue Fehler, `alle` = alle aktiven).

Für eigene Auswertungen: `sensor.wp_heizkosten_wp_jahr` trägt die Monats- und Jahrestabellen als Attribute `monate` und `jahre` (Wärme, Strom, Herkunft, Kosten inkl. `wp_ohne_pv`, Ersparnis inkl. `pv`, CO₂), dazu `preise` und `tage` (Herkunft je Tag). `sensor.wp_heizwaermebedarf_jahr` trägt alle Kennwerte des Heizwärmebedarfs als Attribute, `sensor.wp_heizlast` die Heizlast. Die Tabellen-Attribute werden nicht im Verlauf gespeichert.

## 7. Hinweise und offene Punkte

- **Adress-Falle:** Die Hofman-Liste hat zwei Spalten. Immer **„Decimal“** verwenden, nicht „Decimal+1“.
- Parameter-Register **nicht im Dauertakt schreiben**. Ob jeder Schreibvorgang ins EEPROM geht, ist unbekannt. Die Integration zählt deshalb jeden Schreibvorgang (`sensor.wp_schreibvorgange_heute` / `_gesamt`, Aufteilung je Parameter und Herkunft: Regelung, Übergangszeit, Hand, Uhr; Karte auf der Seite „Diagnose“). Mit eigener Regelung sind es typisch 10–25 am Tag, fast nur P09.
- Die Integration liest Parameter nur alle 15 Minuten (und direkt nach dem Schreiben), Live-Werte und P02–P05 alle 10 Sekunden. In der App oder am Display geänderte Parameter erscheinen deshalb mit bis zu 15 Minuten Verzögerung.
- Bekannte Abweichungen Display ↔ Register: **P34** (Display 0 / Register 400), **P116** (0 / 1).
- Unklar ist noch die Bedeutung von **P137–P147, P149 und P150**. Beobachtung zu **P144** (unsicher): nach dem Start auf 60 Hz senkte P144 = 3 die Frequenz um 3 Hz auf 57 Hz; ob er dauerhaft die Höchstfrequenz mindert, ist offen. **P148** ist in der Smart-Life-App „R2_setting“ (vermutlich Raum-Soll Kühlen), **P05** ist „R1_setting“.
- **Raumfühler** (Klemmen 13/14) und **Warmwasserfühler** werden nur ausgewertet, wenn die zugehörige Funktion aktiv ist (P67 bzw. P63). Sonst zeigen die Register fest 27,0 °C bzw. 70,0 °C – auch mit angeschlossenem Fühler.

## 8. Dashboard oder Integration entfernen

### Nur das Dashboard entfernen (Integration bleibt)
1. **Einstellungen → Geräte & Dienste → Avarma Wärmepumpe → ⚙️ Konfigurieren**
2. Haken bei **„Dashboard ‚Wärmepumpe‘ bereitstellen“** entfernen → **OK**.

Das Dashboard `/waermepumpe` verschwindet sofort aus der Seitenleiste; Sensoren, Zähler und Verläufe bleiben. Eine **eigene Kopie** des Dashboards (siehe 4.4) separat unter **Einstellungen → Dashboards** → Dashboard anklicken → **Löschen** entfernen.

### Alles komplett entfernen (Integration, Dashboard, Diagramm-Karten)
1. **Integration löschen:** Einstellungen → Geräte & Dienste → **Avarma Wärmepumpe** → ⋮ → **Löschen**. Damit sind Gerät, alle Entitäten, das Dashboard und die Lovelace-Ressource der Karten (`/avarma_static/avarma-cards.js`) weg.
2. **Dateien entfernen:**
   - mit HACS: HACS → „Avarma Wärmepumpe“ → ⋮ → **Entfernen** (löscht `custom_components/avarma`)
   - ohne HACS: Ordner `<config>/custom_components/avarma` von Hand löschen (z. B. Samba- oder File-Editor-Add-on)
3. **Home Assistant neu starten.**
4. **Browser bzw. App neu laden** (Cmd/Strg + Shift + R, in der App: Frontend-Cache zurücksetzen), sonst hängen die alten Karten noch im Zwischenspeicher.

<details><summary>Optional aufräumen, falls etwas übrig bleibt</summary>

- **Ressource:** Einstellungen → Dashboards → ⋮ → **Ressourcen** – ein Eintrag `/avarma_static/avarma-cards.js` sollte weg sein, sonst von Hand löschen.
- **Gespeicherte Zähler und Preise:** Die Datei `<config>/.storage/avarma.<Eintrag-ID>` bleibt liegen. Bei gestopptem Home Assistant löschen, wenn bei einer späteren Neueinrichtung sauber von vorn begonnen werden soll.
- **Alte Statistiken:** Entwicklerwerkzeuge → **Statistiken** → verwaiste `sensor.wp_…`-Einträge über „Beheben“ bzw. „Entfernen“ löschen. Der normale Verlauf läuft nach der eingestellten Aufbewahrungszeit von selbst ab.
- **Eigene Verweise:** Automationen auf das Ereignis `avarma_stoerung`, Einträge im **Energie-Dashboard** mit den WP-Zählern, eigene Karten mit `sensor.wp_…`.
</details>

## 9. Haftung

Alles auf eigene Gefahr. Falsche Parameter können die Wärmepumpe in Störung bringen oder beschädigen, und Garantiefragen klärt jeder selbst. Arbeiten im Gerät nur stromlos. Es enthält brennbares Kältemittel (R290).

## Danke

- [holle74/avarma-eigenbau-regelung](https://github.com/holle74/avarma-eigenbau-regelung): ESPHome-Konfiguration, viel Vorarbeit zu den Registern und die Idee zur eigenen Regelung (Raum-Nachführung, Absenkbremse)
- Hinweise aus der Community, z. B. zur Zuordnung R1/R2 der Smart-Life-App
- [Akkudoktor-Forum: Wiki Avarma R290](https://akkudoktor.net/t/wiki-avarma-290-waermepumpe-monoblock/41521) und [Thread AVARMA WP Monoblock](https://akkudoktor.net/t/avarma-wp-monoblock-r290/16194): u. a. der Hinweis auf RS485-3 / COMM3
- Erstellt mit [Claude](https://claude.ai) von Anthropic
- Hofman Energy: Modbus-Protokoll *HE-AI-290-00-000V-V03 TDB* (nicht enthalten, beim Hersteller bzw. Händler erhältlich)

## Unterstützen

Wenn dir das Projekt hilft, freue ich mich über einen Uhudler:

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/D6C72A89GR)

## Lizenz

[![CC BY-NC-SA 4.0](https://img.shields.io/badge/Lizenz-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.de)

**CC BY-NC-SA 4.0**: Frei für private, nicht kommerzielle Nutzung mit Namensnennung. Bearbeitungen müssen unter derselben Lizenz weitergegeben werden. Kommerzielle Nutzung nur mit Erlaubnis. Details siehe [LICENSE](LICENSE).

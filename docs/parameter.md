# Parameterliste Avarma / Hofman (Display P00–P208)

Display-Nummer, Modbus-Adresse (Spalte **Decimal** der Hofman-Liste), Darstellung wie am Display, erlaubter Bereich in Home Assistant und Erklärung.

Skalierung: Der Wert im Register ist *Anzeigewert ÷ Faktor* (z. B. Faktor 0,1 → 42,0 °C steht als 420 im Register).

> Namen, Bedeutung, Bereiche und Werkswerte nach der Hofman-Werksliste für die 9-kW-Anlage (PCB V15.18, Controller V2.18). Wo die Werksliste nichts Genaues sagt, steht ein ⚠️. Ändern auf eigene Gefahr.

> ℹ️ Home Assistant liest diese Liste nur **alle 15 Minuten** neu ein (P02–P05 alle 10 Sekunden). Am Display oder in der Smart-Life-App geänderte Werte erscheinen daher mit bis zu 15 Minuten Verzögerung.






## System & Funktionen

| P | Adresse | Name | Faktor | Einheit | Bereich | Werk 9 kW | Ebene | Erklärung |
|---|---|---|---|---|---|---|---|---|
| P00 | 8192 | Ein/Aus (Parameterspiegel) | 1 |  | 0 … 10 | 0 | nur lesen | Spiegel von Ein/Aus (0 = aus, 1 = ein). Schalten über den EIN/AUS-Knopf. |
| P01 | 8193 | Betriebsart (Parameterspiegel) | 1 |  | 0 … 10 | 2 | nur lesen | 0 Aus, 1 Warmwasser, 2 Heizen, 3 Heizen+WW, 4 Kühlen, 5 Kühlen+WW. Umschalten über „Betriebsart“. |
| P62 | 8252 | Heizen/Kühlen-Auswahl | 1 |  | 0 … 2 | 0 | Benutzer (Code 99) | 0 = Heizen und Kühlen, 1 = nur Kühlen, 2 = nur Heizen. |
| P66 | 8256 | Wärmequelle (Auswahl) | 1 |  | 0 … 1 | 0 | Techniker | Werksliste: „Selected heat source“, 0–1. Modbus-Protokoll (TDB 24.11.2025): „Water source air cooling option“. |
| P67 | 8257 | Raumthermostat | 1 |  | 0 … 1 | 0 | Benutzer (Code 99) | 0 = kein Raumthermostat, 1 = Thermostat-Eingang aktiv. |
| P70 | 8260 | Wiederanlauf nach Stromausfall | 1 |  | 0 … 1 | 1 | Techniker | 0 = aus, 1 = WP läuft nach Stromausfall im letzten Zustand weiter. |
| P87 | 8277 | Werksreset | 1 |  | 0 … 0 | 0 | nur lesen | Gesperrt – nur am Display auslösen. |
| P98 | 8288 | Ventil G1 invertieren | 1 |  | 0 … 1 | 0 | Benutzer (Code 99) | Schaltsignal des Ventils G1 umkehren. |
| P99 | 8289 | Ventil G2 invertieren | 1 |  | 0 … 1 | 0 | Benutzer (Code 99) | Schaltsignal des Ventils G2 umkehren. |
| P100 | 8290 | Ventil G3 invertieren | 1 |  | 0 … 1 | 0 | Benutzer (Code 99) | Schaltsignal des Ventils G3 umkehren. |
| P108 | 8296 | RS485-Adresse | 1 |  | 1 … 1 | 1 | nur lesen | RS485-Adresse (1–16). Gesperrt – eine Änderung würde die HA-Verbindung trennen. |
| P121 | 8311 | PV-Aktivierung | 1 |  | 0 … 1 | 0 | Benutzer (Code 99) | PV-Funktion aktivieren (0/1). |
| P150 | 8340 | Vierwegeventil: Startverzögerung | 1 | s | 0 … 100 | 0 | Benutzer (Code 99) | Werksliste: „Four-way valve delayed start time“. |
| P201 | 4864 | SG-Ready aktiv | 1 |  | 0 … 1 | 0 | Benutzer (Code 99) | 0 = aus, 1 = ein. |
| P202 | 4865 | SG-Ready Heizen: Soll bei Einschaltempfehlung | 1 | °C | 0 … 75 | aus | Benutzer (Code 99) | Heiz-Soll bei SG-Ready-Einschaltempfehlung, 25–75 °C (0 = aus). |
| P203 | 4866 | SG-Ready Heizen: Soll bei Einschaltbefehl | 1 | °C | 0 … 75 | aus | Benutzer (Code 99) | Heiz-Soll bei SG-Ready-Einschaltbefehl, 25–75 °C (0 = aus). |
| P204 | 4867 | SG-Ready Kühlen: Soll bei Einschaltempfehlung | 1 | °C | 0 … 25 | aus | Benutzer (Code 99) | Kühl-Soll bei Einschaltempfehlung, 7–25 °C (0 = aus). |
| P205 | 4868 | SG-Ready Kühlen: Soll bei Einschaltbefehl | 1 | °C | 0 … 25 | aus | Benutzer (Code 99) | Kühl-Soll bei Einschaltbefehl, 7–25 °C (0 = aus). |
| P206 | 4869 | SG-Ready Warmwasser: Soll bei Einschaltempfehlung | 1 | °C | 0 … 70 | aus | Benutzer (Code 99) | WW-Soll bei Einschaltempfehlung, 25–70 °C (0 = aus). |
| P207 | 4870 | SG-Ready Warmwasser: Soll bei Einschaltbefehl | 1 | °C | 0 … 70 | aus | Benutzer (Code 99) | WW-Soll bei Einschaltbefehl, 25–70 °C (0 = aus). |
| P208 | 4871 | SG-Ready Wärmeerzeuger | 1 |  | 0 … 2 | 0 | Benutzer (Code 99) | Wärmeerzeuger für Heizen/WW bei SG-Ready: 0 = WP + E1/E2, 1 = nur E1/E2, 2 = nur WP. |

## Heizen & Heizkurve

| P | Adresse | Name | Faktor | Einheit | Bereich | Werk 9 kW | Ebene | Erklärung |
|---|---|---|---|---|---|---|---|---|
| P02 | 4098 | Vorlauf-Soll Heizen | 1 | °C | 25 … 75 | 45 | Benutzer (Code 99) | Ziel-Vorlauftemperatur im Heizbetrieb (ohne Heizkurve). Nach einem Neustart der WP evtl. wieder 45 °C. |
| P03 | 4099 | Soll Kühlen | 1 | °C | 7 … 25 | 12 | Benutzer (Code 99) | Ziel-Vorlauftemperatur im Kühlbetrieb. |
| P05 | 4101 | Raum-Soll | 1 | °C | 18 … 35 | 21 | Benutzer (Code 99) | Raum-Solltemperatur, in der Smart-Life-App „R1_setting“ (steht dort bei Nachtmodus Ein/Aus, hat aber nichts mit dem Nachtmodus zu tun). Nur mit Raumfühler/Thermostat (P67) wirksam. |
| P06 | 8196 | Hysterese Heizen/Kühlen | 0,1 | K | 1 … 15 | 5 | Benutzer (Code 99) | Um so viel muss der Vorlauf unter den Sollwert fallen, bis die WP wieder startet. Größer = weniger Takte, aber größere Schwankung. |
| P08 | 8198 | Heizkurve: max. Vorlauf | 0,1 | °C | 15 … 70 | 45 | Benutzer (Code 99) | Höchster Vorlauf der Heizkurve (AU) am kalten Ende, bestimmt damit die Steigung. Untergrenze der Kurve ist P146. |
| P09 | 8199 | Heizkurve: Verschiebung | 0,1 | K | -10 … 10 | 0 | Benutzer (Code 99) | Parallelverschiebung der Heizkurve (+ = wärmer, − = kühler). |
| P19 | 8209 | Heizkurve (AU) aktiv | 1 |  | 0 … 1 | 0 | Benutzer (Code 99) | 1 = Vorlauf wird nach Außentemperatur geführt (Heizkurve), 0 = fester Vorlauf-Soll P02. |
| P135 | 8325 | Heizgrenze (Heizkurve) | 0,1 | °C | 15 … 25 | 17 | Benutzer (Code 99) | Werksliste: „AU heating limiting temperature“. Über dieser Außentemperatur heizt die WP nach Heizkurve nicht (Sommerabschaltung). |
| P136 | 8326 | Heizkurve: Wiedereinschalten | 0,1 | °C | 3 … 13 | 5 | Benutzer (Code 99) | Werksliste: „AU heating recovery temperature“, 3–13 °C. ⚠️ Ungeklärt, ob absolute Außentemperatur oder Abstand zu P135. |
| P146 | 8336 | Heizkurve: Mindest-Vorlauf (OTC-Minimum) | 0,1 | °C | 10 … 25 | 25 | Benutzer (Code 99) | Untergrenze der Heizkurve, wirkt bei P08 ≤ 50 (Werksliste: „OTC minimum setting value“). |
| P148 | 8338 | Zweite Temperaturzone: Soll | 0,1 | °C | 18 … 35 | 25 | Benutzer (Code 99) | Werksliste: „Dual temperature zone setting temperature“. In der Smart-Life-App „R2_setting“. |

## Warmwasser & Legionellen

| P | Adresse | Name | Faktor | Einheit | Bereich | Werk 9 kW | Ebene | Erklärung |
|---|---|---|---|---|---|---|---|---|
| P04 | 4100 | Warmwasser-Soll | 1 | °C | 25 … 70 | 45 | Benutzer (Code 99) | Zieltemperatur des Warmwasserspeichers. Der Kompressor heizt höchstens bis P35, darüber nur die E-Heizung. |
| P07 | 8197 | Hysterese Warmwasser | 0,1 | K | 1 … 15 | 5 | Benutzer (Code 99) | Einschalt-Differenz für die Warmwasserbereitung. |
| P10 | 8200 | Legionellen: Intervall | 1 | d | 1 … 99 | 7 | Benutzer (Code 99) | Alle wie viele Tage die Legionellenschaltung läuft. |
| P11 | 8201 | Legionellen: Startzeit | 1 | h | 0 … 23 | 23 | Benutzer (Code 99) | Uhrzeit (Stunde) des Legionellenprogramms. |
| P12 | 8202 | Legionellen: Dauer | 1 | min | 5 … 99 | 10 | Benutzer (Code 99) | Haltezeit auf Legionellentemperatur. |
| P13 | 8203 | Legionellen: Temperatur | 0,1 | °C | 50 … 70 | 70 | Benutzer (Code 99) | Zieltemperatur der Legionellenschaltung. |
| P14 | 8204 | Legionellen: Modus | 1 |  | 0 … 2 | 2 | Benutzer (Code 99) | 0 = automatisch, 1 = manuell, 2 = ungültig (aus). |
| P18 | 8208 | Reserve | 1 |  | 0 … 1 | 0 | Benutzer (Code 99) | Laut Werksliste Reserve ohne Funktion (0 = ungültig, 1 = gültig). ⚠️ Modbus-Protokoll (TDB 24.11.2025) nennt hier „DHW AU function“ (Warmwasser nach Heizkurve); beim Nutzer steht 1. |
| P35 | 8225 | WW: Kompressor-Obergrenze | 0,1 | °C | 0 … 70 | 70 | Techniker | Im Warmwasserbetrieb höchste Wassertemperatur, bis zu der der Kompressor läuft; darüber nur E-Heizung. |
| P63 | 8253 | Warmwasserfunktion | 1 |  | 0 … 1 | 1 | Benutzer (Code 99) | 0 = kein Warmwasserspeicher, 1 = WW-Bereitung aktiv. |
| P83 | 8273 | WW-Zirkulationspumpe Betrieb | 1 |  | 0 … 3 | 3 | Techniker | 0 = nein, 1 = Zeit, 2 = Temperaturdifferenz, 3 = Zeit + Temperaturdifferenz (nur bei P88 = 1). |
| P84 | 8274 | WW-Zirkulation Differenz | 0,1 | K | 4 … 20 | 5 | Techniker | Einschaltdifferenz der Zirkulationspumpe. |

## Nachtmodus

| P | Adresse | Name | Faktor | Einheit | Bereich | Werk 9 kW | Ebene | Erklärung |
|---|---|---|---|---|---|---|---|---|
| P15 | 8205 | Nachtmodus Start | 1 | h | 0 … 23 | 22 | Benutzer (Code 99) | Stunde, ab der der leise Nachtmodus gilt. |
| P16 | 8206 | Nachtmodus Ende | 1 | h | 0 … 23 | 6 | Benutzer (Code 99) | Stunde, bis zu der der Nachtmodus gilt. |
| P17 | 8207 | Nachtmodus aktiv | 1 |  | 0 … 1 | 0 | Benutzer (Code 99) | 0 = aus, 1 = ein. Im Nachtmodus reduziert die WP Kompressor- und Lüfterleistung (leiser). |

## Pumpen & Durchfluss

| P | Adresse | Name | Faktor | Einheit | Bereich | Werk 9 kW | Ebene | Erklärung |
|---|---|---|---|---|---|---|---|---|
| P20 | 8210 | Umwälzpumpe Betriebsart | 1 |  | 0 … 2 | 0 | Benutzer (Code 99) | 0 = Pumpe läuft durch, 1 = Pumpe stoppt bei erreichter Temperatur, 2 = 15 min aus / 1 min an. |
| P21 | 8211 | Pumpe Frostschutz-Intervall | 1 | min | 5 … 50 | 30 | Benutzer (Code 99) | Intervall, in dem die Pumpe bei Stillstand zum Frostschutz läuft. |
| P26 | 8216 | Durchflussmesser-Modell | 1 |  | 0 … 5 | 2 | Techniker | Typ des eingebauten Durchflussmessers (Werksliste: „Water Flow Meter Model“). Nicht ändern. ⚠️ Modbus-Protokoll (TDB 24.11.2025) nennt hier „Defrost Interval Multiplier“ (0 = keine Abtauung, 1–4 = Intervall ×4). Welche Bedeutung für diese Firmware gilt, ist offen – nicht ändern. |
| P58 | 8248 | Pumpe Regel-Spreizung | 0,1 | K | 3 … 8 | 5 | Techniker | Auf diese Spreizung VL–RL regelt die drehzahlgeregelte Pumpe C1. |
| P59 | 8249 | Pumpe Mindestdrehzahl | 1 | ×10 % | 2 … 8 | 8 | Techniker | Untere Drehzahl der PWM-Pumpe, 2–8 (8 = 80 %). |
| P61 | 8251 | Mindestdurchfluss | 1 | L/min | 3 … 80 | 8 | Techniker | Unter diesem Durchfluss → Fehler E15. Nicht ohne Grund absenken. |
| P65 | 8255 | Pumpe C2 Funktion | 1 |  | 0 … 1 | 0 | Benutzer (Code 99) | 0 = Zusatzpumpe, 1 = Heizkreis-Umwälzpumpe. |
| P68 | 8258 | Durchflussschalter-Auswahl | 1 |  | 0 … 5 | 1 | Techniker | Werksliste: „Flow switch selection“, 0–5. Nur mit Hersteller-Freigabe ändern. |
| P88 | 8278 | Pumpe C3 Funktion | 1 |  | 0 … 1 | 0 | Benutzer (Code 99) | 0 = WW-Zusatzpumpe, 1 = WW-Zirkulationspumpe. |
| P149 | 8339 | Pumpe C2: Taktverzögerung | 1 | min | 1 … 60 | 15 | Benutzer (Code 99) | Werksliste: „C2 pump jog delay time“. |

## E-Heizung & 2. Wärmeerzeuger

| P | Adresse | Name | Faktor | Einheit | Bereich | Werk 9 kW | Ebene | Erklärung |
|---|---|---|---|---|---|---|---|---|
| P22 | 8212 | E-Heizung Heizen: Start unter | 0,1 | °C | -30 … 20 | 0 | Benutzer (Code 99) | Unter dieser Außentemperatur darf die Zusatzheizung (E2) beim Heizen zuschalten. |
| P23 | 8213 | E-Heizung WW: Start unter | 0,1 | °C | -30 … 20 | 0 | Benutzer (Code 99) | Unter dieser Außentemperatur darf die Zusatzheizung (E1) beim Warmwasser zuschalten. |
| P24 | 8214 | E-Heizung: Zuschalt-Offset | 0,1 | K | 1 … 15 | 5 | Benutzer (Code 99) | Temperatur-Offset, ab dem der Heizstab zugeschaltet wird (Werksliste: „Electrical heater active temp offset value“). |
| P36 | 8226 | Verzögerung Kompressor → E1 | 1 | min | 0 … 999 | 5 | Techniker | Wartezeit zwischen Kompressorstart und Heizstab E1 (laut Werksliste reserviert). |
| P81 | 8271 | E1/E2 Funktion | 1 |  | 0 … 3 | 0 | Techniker | 0 = E-Zusatzheizung, 1 = zweiter Wärmeerzeuger, 2 = mit E-Heizer, 3 = mit Kessel. |
| P82 | 8272 | 2. Wärmeerzeuger (Hilfsmodus): Start unter | 0,1 | °C | -30 … 20 | -25 | Techniker | Unter dieser Außentemperatur wird im Hilfsmodus die Zusatzquelle (E2, E1) freigegeben. |
| P116 | 8304 | E-Heizung Leistungsberechnung | 1 |  | 0 … 1 | 0 | Benutzer (Code 99) | Heizstab-Leistung in die Energieberechnung einrechnen (0/1). |
| P117 | 8305 | E0 Leistung | 0,1 | kW | 0 … 20 | 0 | Benutzer (Code 99) | Leistung Heizstab E0 (für die Energiebilanz). |
| P118 | 8306 | E1 Leistung | 0,1 | kW | 0 … 20 | 0 | Benutzer (Code 99) | Leistung Heizstab E1. |
| P119 | 8307 | E2 Leistung | 0,1 | kW | 0 … 20 | 0 | Benutzer (Code 99) | Leistung Heizstab E2. |

## Schutzfunktionen

| P | Adresse | Name | Faktor | Einheit | Bereich | Werk 9 kW | Ebene | Erklärung |
|---|---|---|---|---|---|---|---|---|
| P25 | 8215 | Frostschutz-Temperatur | 0,1 | °C | -15 … 5 | 3 | Techniker | Frostschutz-Temperatur für Heizen/Kühlen: darunter startet der Frostschutz. |
| P42 | 8232 | Strom: Frequenzbegrenzung ab | 0,1 | A | 1 … 50 | 14 | Techniker | Ab diesem Kompressorstrom wird die Frequenz begrenzt (nicht weiter erhöht). |
| P43 | 8233 | Strom: Frequenzabsenkung ab | 0,1 | A | 1 … 50 | 16 | Techniker | Ab diesem Strom wird die Frequenz reduziert. |
| P44 | 8234 | Strom: Abschaltung ab | 0,1 | A | 1 … 50 | 18 | Techniker | Ab diesem Strom schaltet der Kompressor ab. |
| P51 | 8241 | Hochdruck: keine Frequenzerhöhung ab | 0,1 | bar | 20 … 45 | 29,5 | Techniker | Ab diesem Hochdruck keine Frequenzerhöhung mehr. |
| P52 | 8242 | Hochdruck: Sperre aufheben ab | 0,1 | bar | 20 … 45 | 26 | Techniker | Unter diesem Hochdruck darf die Frequenz wieder steigen. |
| P53 | 8243 | Hochdruck-Abschaltung | 0,1 | bar | 20 … 45 | 32 | Techniker | Schutzabschaltung bei zu hohem Druck. |
| P54 | 8244 | Niederdruck-Abschaltung | 0,1 | bar | 0,1 … 1 | 0,3 | Techniker | Schutzabschaltung bei zu niedrigem Druck. |
| P55 | 8245 | Hochdruck-Schutz Hysterese | 0,1 | bar | 1 … 10 | 5 | Techniker | Rückschaltdifferenz Hochdruckschutz. |
| P56 | 8246 | Niederdruck-Schutz Hysterese | 0,01 | bar | 0,1 … 5 | 0,15 | Techniker | Rückschaltdifferenz Niederdruckschutz. |
| P57 | 8247 | Heißgas-Schutztemperatur | 1 | °C | 100 … 125 | 105 | Techniker | Abschaltung bei zu hoher Druckgastemperatur (Td). |
| P73 | 8263 | Drucksensor/Druckschalter | 1 |  | 0 … 1 | 0 | Techniker | 0 = Drucksensor, 1 = Druckschalter. |
| P102 | 8292 | Schutzgrenze Spreizung VL/RL | 0,1 | K | 8 … 20 | 12 | Techniker | Maximal zulässige Spreizung, sonst Schutz. |
| P109 | 8297 | Heißgas-Grenze 1 | 1 | °C | 80 … 125 | 100 | Techniker | Frequenzbegrenzung ab dieser Druckgastemperatur (Stufe 1). |
| P110 | 8298 | Heißgas-Grenze 2 | 1 | °C | 80 … 125 | 97 | Techniker | Stufe 2. |
| P111 | 8299 | Heißgas-Grenze 3 | 1 | °C | 80 … 125 | 95 | Techniker | Stufe 3. |
| P115 | 8303 | Vorlauf-Übertemperaturschutz | 1 | °C | 70 … 90 | 83 | Techniker | Schutzabschaltung bei zu hohem Vorlauf. |
| P145 | 8335 | Kältemittel-Konzentrationserkennung | 1 |  | 0 … 1 | 0 | Techniker | Erkennung der Kältemittelkonzentration: 0 = aus, 1 = ein. |

## Abtauung

| P | Adresse | Name | Faktor | Einheit | Bereich | Werk 9 kW | Ebene | Erklärung |
|---|---|---|---|---|---|---|---|---|
| P27 | 8217 | Abtau: erstes Intervall | 1 | min | 15 … 99 | 50 | Techniker | Werksliste: „First Defrost Interval“ – Zeit bis zur ersten Abtauung. Beobachtet: wirkt wohl auch als Mindestabstand zwischen weiteren Abtauungen. Modbus-Protokoll (TDB 24.11.2025): „defrost cycle“, 15–99 min. |
| P28 | 8218 | Abtaumodus | 1 |  | 0 … 1 | 0 | Techniker | 0 = automatisch. 1 = Abtauung manuell auslösen (springt danach auf 0). |
| P29 | 8219 | Abtau-Start Lamellentemp. | 0,1 | °C | -8 … 5 | -3 | Techniker | Lamelle (Tc) muss unter diesen Wert fallen, damit abgetaut wird. |
| P30 | 8220 | Abtau-Ende Lamellentemp. | 0,1 | °C | 5 … 30 | 20 | Techniker | Abtauung endet, wenn die Lamelle diese Temperatur erreicht. |
| P31 | 8221 | Abtau: max. Dauer | 1 | min | 2 … 20 | 12 | Techniker | Abtauung wird spätestens nach dieser Zeit beendet. |
| P47 | 8237 | Abtau-Frequenz | 1 | Hz | 30 … 90 | 65 | Techniker | Kompressorfrequenz während der Abtauung. |
| P85 | 8275 | Abtau: Außentemperatur-Grenze | 0,1 | °C | 0 … 20 | 8 | Techniker | Werksliste: „Defrost ambient temperature“. Über dieser Außentemperatur taut die WP nicht selbst ab (Community-Tipp: 15 °C). |
| P86 | 8276 | Abtau ΔT Außen–Lamelle (≥ −7 °C) | 0,1 | K | 0 … 20 | 8 | Techniker | Geforderte Differenz Außenluft–Lamelle (ΔT1) für den Abtaustart bei Außentemperatur ≥ −7 °C. |
| P91 | 8281 | Abtau ΔT Außen–Lamelle (< −7 °C) | 0,1 | K | 0 … 20 | 8 | Techniker | Geforderte Differenz Außenluft–Lamelle (ΔT2) für den Abtaustart bei Außentemperatur < −7 °C. |
| P101 | 8291 | EEV-Schritte beim Abtauen | 1 | P | 0 … 480 | 480 | Techniker | Ventilöffnung während der Abtauung. |

## Expansionsventil / EVI / Überhitzung

| P | Adresse | Name | Faktor | Einheit | Bereich | Werk 9 kW | Ebene | Erklärung |
|---|---|---|---|---|---|---|---|---|
| P32 | 8222 | EEV Regelart | 1 |  | 0 … 4 | 3 | Techniker | 0 keine, 1 Prüfung (Check), 2 manuell, 3 Sauggas-Überhitzung, 4 Heißgas-Überhitzung. |
| P33 | 8223 | EEV manuell Heizen | 1 | P | 50 … 480 | 400 | Techniker | Feste Ventilöffnung im manuellen Modus (Heizen). |
| P34 | 8224 | EEV manuell Kühlen | 1 | P | 50 … 480 | 400 | Techniker | Feste Ventilöffnung im manuellen Modus (Kühlen). Achtung: Display zeigt 0, Register liest 400. |
| P49 | 8239 | Heißgas-Überhitzung P-Faktor | 1 |  | 0 … 10 | 2 | Techniker | Proportional-Koeffizient der Heißgas-Überhitzungsregelung. |
| P50 | 8240 | Heißgas-Überhitzung D-Faktor | 1 |  | 0 … 20 | 1 | Techniker | Differential-Koeffizient der Heißgas-Überhitzungsregelung. |
| P64 | 8254 | EEV Mindestöffnung | 1 | P | 0 … 480 | 90 | Techniker | Kleinste Öffnung des Expansionsventils. |
| P74 | 8264 | EVI: zuschalten ab Heißgastemperatur | 0,1 | °C | 50 … 125 | 55 | Techniker | Ab dieser Heißgas-(Druckgas-)Temperatur wird die Zwischeneinspritzung (EVI) aktiv. ⚠️ Modbus-Protokoll (TDB 24.11.2025) nennt hier „Enthalpy injection valve control mode“ (0–3); der Wert 55 passt nur zur Werksliste. |
| P75 | 8265 | Unterkühlungs-EEV Heizen aktiv | 1 |  | 0 … 1 | 0 | Techniker | Regelung des Unterkühlungs-Expansionsventils im Heizbetrieb: 0 = aus, 1 = ein. ⚠️ Modbus-Protokoll (TDB 24.11.2025): „EVI valve initial opening heating“ (40–480). |
| P76 | 8266 | Heißgas-Überhitzung Soll | 0,1 |  | 12 … 50 | 17 | Techniker | Ziel-Überhitzung des Heißgases (Werksliste: „Discharge superheat“). ⚠️ Modbus-Protokoll (TDB 24.11.2025): „EVI valve initial opening cooling“ (40–480); der Wert 17 passt nur zur Werksliste. |
| P77 | 8267 | Unterkühlung max. Öffnung (Heißgas > 100 °C) | 1 | P | 60 … 480 | 200 | Techniker | Größte Öffnung des Unterkühlungsventils, wenn die Heißgastemperatur über 100 °C liegt. ⚠️ Modbus-Protokoll (TDB 24.11.2025): „Spray enthalpy valve superheat (heating)“ (−5…10 °C); der Wert 200 passt nur zur Werksliste. |
| P78 | 8268 | Unterkühlung max. Öffnung (Heißgas 90–100 °C) | 1 | P | 60 … 480 | 180 | Techniker | Größte Öffnung des Unterkühlungsventils bei Heißgastemperatur über 90 bis 100 °C. ⚠️ Modbus-Protokoll (TDB 24.11.2025): „Spray enthalpy valve superheat (cooling)“; der Wert 180 passt nur zur Werksliste. |
| P79 | 8269 | Unterkühlung max. Öffnung (Heißgas ≤ 90 °C) | 1 | P | 60 … 480 | 150 | Techniker | Größte Öffnung des Unterkühlungsventils bei Heißgastemperatur bis 90 °C. Früher hier fälschlich als WLAN-Upload-Intervall gedeutet. ⚠️ Modbus-Protokoll (TDB 24.11.2025): „WIFI data upload cycle“ (s); der Wert 150 = Werkswert der Werksliste. |
| P89 | 8279 | Sauggas-Überhitzung P-Faktor | 1 |  | 0 … 20 | 3 | Techniker | Proportional-Koeffizient der Sauggas-Überhitzungsregelung. |
| P90 | 8280 | Sauggas-Überhitzung D-Faktor | 1 |  | 0 … 20 | 1 | Techniker | Differential-Koeffizient der Sauggas-Überhitzungsregelung. |
| P92 | 8282 | Soll-Überhitzung Heizen (Außen ≤ −5 °C) | 0,1 | K | -5 … 10 | 2,5 | Techniker | Ziel-Überhitzung Sauggas (Außentemperatur-Bereich 1). |
| P93 | 8283 | Soll-Überhitzung Heizen (−5…5 °C) | 0,1 | K | -5 … 10 | 2,5 | Techniker | Ziel-Überhitzung Sauggas (Bereich 2). |
| P94 | 8284 | Soll-Überhitzung Heizen (5…25 °C) | 0,1 | K | -5 … 10 | 2 | Techniker | Ziel-Überhitzung Sauggas bei Außentemperatur +5 bis +25 °C. |
| P95 | 8285 | Soll-Überhitzung Kühlen | 0,1 | K | -5 … 10 | 3 | Techniker | Ziel-Überhitzung im Kühlbetrieb. |
| P96 | 8286 | Soll-Überhitzung Heizen (Außen ≥ 25 °C) | 0,1 | K | -5 … 10 | 0,5 | Techniker | Ziel-Überhitzung Sauggas bei Außentemperatur ab 25 °C. |
| P103 | 8293 | EEV Anfangsöffnung Haltezeit | 1 | s | 0 … 300 | 60 | Techniker | So lange bleibt das EEV nach dem Start auf Anfangsöffnung. |
| P112 | 8300 | EEV-Korrektur ab Heißgas | 1 | °C | 80 … 125 | 100 | Techniker | Ab dieser Heißgastemperatur passt das EEV die Öffnung an. |
| P113 | 8301 | EEV-Korrektur Intervall | 1 | s | 1 … 120 | 30 | Techniker | Zeitintervall der EEV-Anpassung bei zu hoher Heißgastemperatur. |

## Lüfter

| P | Adresse | Name | Faktor | Einheit | Bereich | Werk 9 kW | Ebene | Erklärung |
|---|---|---|---|---|---|---|---|---|
| P37 | 8227 | Lüfter: Temperaturdifferenz Heizen | 0,1 | K | 2 … 15 | 6 | Techniker | Temperaturdifferenz für die Drehzahlregelung des DC-Lüfters im Heizbetrieb. |
| P38 | 8228 | Lüfter: Temperaturdifferenz Kühlen | 0,1 | K | 3 … 18 | 8 | Techniker | Temperaturdifferenz für die Drehzahlregelung des DC-Lüfters im Kühlbetrieb. |
| P60 | 8250 | Lüfter max. Drehzahl | 1 | ×10 U/min | 40 … 150 | 63 | Techniker | Höchste Drehzahl des DC-Lüfters in 10 U/min (63 = 630 U/min, Bereich 400–1500). |
| P69 | 8259 | Lüftertyp | 1 |  | 0 … 3 | 1 | Techniker | 0 = AC, 1 = erster DC, 2 = zweiter DC, 3 = zwei DC-Lüfter. |
| P71 | 8261 | Lüftersteuerung | 1 |  | 0 … 1 | 1 | Techniker | 1 = automatisch, 0 = manuell mit P72 (Vereisungsgefahr!). |
| P72 | 8262 | Lüfter manuelle Drehzahl | 1 | ×10 U/min | 40 … 150 | 40 | Techniker | Nur bei P71 = 0. Feste Lüfterdrehzahl in 10 U/min (40 = 400 U/min). |

## Kompressor

| P | Adresse | Name | Faktor | Einheit | Bereich | Werk 9 kW | Ebene | Erklärung |
|---|---|---|---|---|---|---|---|---|
| P39 | 8229 | Kompressormodell | 1 |  | 0 … 999 | 59 | nur lesen | Kompressormodell (Werksliste: Reserve). NICHT ändern. |
| P40 | 8230 | Kompressorfrequenz: Automatik | 1 |  | 0 … 1 | 1 | Techniker | 0 = manuell (feste Frequenz P97), 1 = automatisch. |
| P41 | 8231 | Ölrückführung Frequenz | 1 | Hz | 10 … 100 | 50 | Techniker | Frequenz für die periodische Ölrückführung. |
| P45 | 8235 | Kompressor max. Frequenz | 1 | Hz | 50 … 120 | 85 | Techniker | Höchste Kompressorfrequenz (Leistungsgrenze, auch beim Abtauen wirksam). |
| P46 | 8236 | Kompressor min. Frequenz | 1 | Hz | 0 … 90 | 35 | Techniker | Niedrigste Frequenz. Kleiner = weiter herunter modulieren = weniger Takten. |
| P48 | 8238 | Warmwasser max. Frequenz | 1 | % | 2 … 10 | 10 | Techniker | Höchste Frequenz im Warmwasserbetrieb (Werksliste: „DHW maximum frequency“, 2–10, Einheit dort Hz – Bedeutung als Stufe/Faktor unklar). Modbus-Protokoll (TDB 24.11.2025): 2–10 = Prozentsatz der höchsten eingestellten Frequenz. |
| P80 | 8270 | Mindestfrequenz-Berechnung | 0,1 |  | 0 … 10 | 1 | Techniker | Koeffizient zur Berechnung der niedrigsten Kompressorfrequenz (Werksliste: Reserve). |
| P104 | 8294 | Frequenz für Leistungsberechnung | 1 | Hz | 20 … 60 | 50 | Techniker | Anfangsfrequenz des Kompressors für die Berechnung der Heiz-/Kühlleistung. |
| P105 | 8194 | Startfrequenz A | 1 | Hz | 20 … 60 | 30 | Techniker | Startfrequenz des Kompressors (Anlaufplateau A). |
| P106 | 8195 | Startfrequenz A Dauer | 1 | s | 0 … 300 | 60 | Techniker | So lange läuft der Kompressor nach dem Start auf Startfrequenz A. |
| P114 | 8302 | Frequenzreduktion bei VL-Soll | 1 | % | 0 … 60 | 2 | Techniker | Wie weit der Kompressor nach erreichtem Soll die Frequenz absenkt. Größer = weniger Takten (Community: 3 % → 15 % bei Takten). |
| P137 | 8327 | Resonanzfrequenz 1 | 1 | Hz | 0 … 120 | 0 | Techniker | Frequenz, die der Kompressor überspringt, um Resonanzen (Brummen, Vibrationen) zu vermeiden. 0 = keine. |
| P138 | 8328 | Resonanzfrequenz 2 | 1 | Hz | 0 … 120 | 0 | Techniker | Frequenz, die der Kompressor überspringt, um Resonanzen (Brummen, Vibrationen) zu vermeiden. 0 = keine. |
| P139 | 8329 | Resonanzfrequenz 3 | 1 | Hz | 0 … 120 | 0 | Techniker | Frequenz, die der Kompressor überspringt, um Resonanzen (Brummen, Vibrationen) zu vermeiden. 0 = keine. |
| P140 | 8330 | Resonanzfrequenz 4 | 1 | Hz | 0 … 120 | 0 | Techniker | Frequenz, die der Kompressor überspringt, um Resonanzen (Brummen, Vibrationen) zu vermeiden. 0 = keine. |
| P141 | 8331 | Resonanzfrequenz 5 | 1 | Hz | 0 … 120 | 0 | Techniker | Frequenz, die der Kompressor überspringt, um Resonanzen (Brummen, Vibrationen) zu vermeiden. 0 = keine. |
| P142 | 8332 | Resonanzfrequenz 6 | 1 | Hz | 0 … 120 | 0 | Techniker | Frequenz, die der Kompressor überspringt, um Resonanzen (Brummen, Vibrationen) zu vermeiden. 0 = keine. |
| P143 | 8333 | Resonanzfrequenz 7 | 1 | Hz | 0 … 120 | 0 | Techniker | Frequenz, die der Kompressor überspringt, um Resonanzen (Brummen, Vibrationen) zu vermeiden. 0 = keine. |
| P144 | 8334 | Resonanzfrequenz 8 | 1 | Hz | 0 … 120 | 0 | Techniker | Frequenz, die der Kompressor überspringt, um Resonanzen (Brummen, Vibrationen) zu vermeiden. 0 = keine. |
| P147 | 8337 | Hochfrequenz bei tiefer Außentemperatur | 1 |  | 0 … 1 | 0 | Benutzer (Code 99) | Werksliste: „Low temperature high frequency switch“, 0 = aus, 1 = ein. |

## Sonstige

| P | Adresse | Name | Faktor | Einheit | Bereich | Werk 9 kW | Ebene | Erklärung |
|---|---|---|---|---|---|---|---|---|
| P97 | 8287 | Festfrequenz (bei P40 = 0) | 1 | Hz | 10 … 100 | 50 | Techniker | Kompressorfrequenz, wenn P40 = 0 (manuell). |
| P107 | 8295 | PRT-Berechnungswert | 1 |  | 1 … 100 | 3 | Techniker | Hersteller-Parameter (Werksliste: „PRT calculation value“). |

## Estrichtrocknung

| P | Adresse | Name | Faktor | Einheit | Bereich | Werk 9 kW | Ebene | Erklärung |
|---|---|---|---|---|---|---|---|---|
| P122 | 8312 | Estrichtrocknung aktiv | 1 |  | 0 … 1 | 0 | Benutzer (Code 99) | Startet das Estrich-Aufheizprogramm (Perioden P123–P134). |
| P123 | 8313 | Periode 1 Dauer | 1 | d | 1 … 15 | 10 | Benutzer (Code 99) | Dauer Periode 1. |
| P124 | 8314 | Periode 1 Start | 0,1 | °C | 10 … 60 | 20 | Benutzer (Code 99) | Vorlauf zu Beginn von Periode 1. |
| P125 | 8315 | Periode 1 Ende | 0,1 | °C | 10 … 60 | 20 | Benutzer (Code 99) | Vorlauf am Ende von Periode 1. |
| P126 | 8316 | Periode 2 Dauer | 1 | d | 1 … 15 | 5 | Benutzer (Code 99) | Dauer Periode 2. |
| P127 | 8317 | Periode 2 Start | 0,1 | °C | 10 … 60 | 20 | Benutzer (Code 99) |  |
| P128 | 8318 | Periode 2 Ende | 0,1 | °C | 10 … 60 | 50 | Benutzer (Code 99) |  |
| P129 | 8319 | Periode 3 Dauer | 1 | d | 1 … 15 | 10 | Benutzer (Code 99) |  |
| P130 | 8320 | Periode 3 Start | 0,1 | °C | 10 … 60 | 50 | Benutzer (Code 99) |  |
| P131 | 8321 | Periode 3 Ende | 0,1 | °C | 10 … 60 | 50 | Benutzer (Code 99) |  |
| P132 | 8322 | Periode 4 Dauer | 1 | d | 1 … 15 | 5 | Benutzer (Code 99) |  |
| P133 | 8323 | Periode 4 Start | 0,1 | °C | 10 … 60 | 50 | Benutzer (Code 99) |  |
| P134 | 8324 | Periode 4 Ende | 0,1 | °C | 10 … 60 | 20 | Benutzer (Code 99) |  |

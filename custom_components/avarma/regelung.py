"""Eigene Regelung (optional): die eingebaute Heizkurve der WP über P09 sanft verschieben.

Idee nach holle74/avarma-eigenbau-regelung, aber ausfallsicher: Die WP heizt immer mit ihrer eigenen Heizkurve,
die Integration verschiebt sie nur in engen Grenzen. Fällt Home Assistant aus, bleibt die zuletzt gesetzte
Verschiebung stehen.
"""

from __future__ import annotations

from typing import Any

MAX_STANDARD = 5.0      # K Grenze (einstellbar 2–10 K): gesamt um den Grundwert, ebenso je Raum und Sonne
VORLADEN_AB = 3.0       # °C Prognose-Minimum, ab dem vorgeladen wird
VORLADEN_FAKTOR = 0.3   # K je K unter VORLADEN_AB
VORLADEN_MAX = 2.0      # K
STEIGUNG_BIS = 14.0     # °C: darüber hängt die Heizkurve der WP am Minimum, Punkte verfälschen die Steigung
P09_MIN, P09_MAX = -10.0, 10.0
SCHREIB_MIN = 0.5       # K Mindeständerung zum Schreiben
SCHREIB_ABSTAND = 1800  # s zwischen zwei Schreibvorgängen
SCHRITT_HOCH, SCHRITT_RUNTER = 2.0, 1.0  # K je Schreibvorgang (sanft, gegen Takten)
ABSENK_WARTEN = 3600    # s: so lange höchstens auf die Absenkbremse warten
SONNE_MITTEL = 3600     # s: Sonnenkorrektur über 60 min mitteln (Wolken)
TAKT_FENSTER, TAKT_STARTS, TAKT_SPERRE = 2 * 3600, 3, 2 * 3600  # ≥ 3 Starts in 2 h → 2 h nichts ändern
STEIGUNG_STANDARD = 1.2  # K Vorlauf je K Außentemperatur (gemessen an einer Avarma 9 kW)
PROG_MAX = 3.0          # K: Prognose-Baustein höchstens ±
# Form der eingebauten Heizkurve (aus Messwerten einer Avarma 9 kW abgeleitet, nicht dokumentiert):
# 25 °C ab 17 °C außen, P08 bei −3 °C außen, dazwischen eine Gerade
KURVE_MIN, KURVE_OBEN, KURVE_UNTEN = 25.0, 17.0, -3.0
P08_MIN, P08_MAX = 40.0, 55.0  # °C: in diesem Bereich darf das Lernen P08 verstellen
P08_SCHRITT = 1.0       # °C: höchstens so viel je Lernschritt (einmal am Tag)
KURVE_TAGE = 3          # Tage, über die das Lernen auswertet
KURVE_STUNDE = 14       # ab dieser Uhrzeit wird einmal am Tag ausgewertet
KURVE_TAG_MAX = 1.0     # K: Lernpunkte mit stärkerem Wärmste-Stunden-Baustein zählen nicht (absichtliche Schwankung)
TAG_KOMFORT = 0.5       # K: Wärmste Stunden hebt bis Soll + 0,5 an bzw. senkt bis Soll − 0,5 ab
TAG_RAMPE = 0.3         # K: davor sanft auslaufen
TAG_TOTBAND = 0.3       # K: so viel weiter sind Totband und „deutlich zu kalt“ der Raum-Nachführung, solange er an ist

# Feineinstellung (jedes Haus reagiert anders). Schlüssel: Name, Einheit, min, max, Schritt, Heizkörper, Fußbodenheizung
FEIN = {
    "totband": ("Totband (darunter keine Reaktion)", "K", 0.1, 1.0, 0.1, 0.3, 0.3),
    "kalt_ab": ("Deutlich zu kalt ab", "K", 0.3, 2.0, 0.1, 0.5, 0.7),
    "kalt_faktor": ("Hoch je K zu kalt", "K", 0.2, 3.0, 0.1, 1.0, 0.7),
    "kalt_max": ("Hoch höchstens je Schritt", "K", 0.3, 3.0, 0.1, 1.5, 1.0),
    "kalt_abstand": ("Hoch frühestens alle", "min", 30, 360, 10, 90, 180),
    "langsam_schritt": ("Kleine Abweichung: Schritt", "K", 0.1, 1.0, 0.1, 0.5, 0.3),
    "langsam_abstand": ("Kleine Abweichung: alle", "min", 60, 720, 10, 180, 360),
    "warm_dauer": ("Zu warm mindestens", "min", 10, 180, 5, 50, 120),
    "warm_faktor": ("Runter je K zu warm", "K", 0.2, 3.0, 0.1, 1.0, 0.7),
    "warm_max": ("Runter höchstens je Schritt", "K", 0.3, 3.0, 0.1, 1.0, 1.0),
    "warm_abstand": ("Runter frühestens alle", "min", 30, 360, 10, 60, 180),
    "vorschau": ("Prognose: Vorausschau", "h", 0, 12, 1, 3, 8),
    "prog_gewicht": ("Prognose: Gewichtung", "%", 0, 100, 10, 50, 70),
    "tag_staerke": ("Wärmste Stunden: Stärke", "%", 0, 100, 10, 50, 70),
    "tag_max": ("Wärmste Stunden: höchstens ±", "K", 0.5, 3.0, 0.1, 1.5, 2.0),
}
PROFILE = {"hk": "Heizkörper", "fbh": "Fußbodenheizung", "frei": "Benutzerdefiniert"}


def fein_standard(profil: str = "hk") -> dict[str, float]:
    spalte = 6 if profil == "fbh" else 5
    return {k: v[spalte] for k, v in FEIN.items()}


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def mean(values: list[float | None]) -> float | None:
    vals = [v for v in values if v is not None]
    return round(sum(vals) / len(vals), 2) if vals else None


def lern_schritt(lern: float, raum: float | None, raum_kurz: float | None, soll: float, now: float, zuletzt: float,
                 grenze: float = MAX_STANDARD, rest: float = 0.0, raum_min: float | None = None,
                 f: dict[str, float] | None = None) -> tuple[float, float]:
    """Raum-Nachführung nach Feineinstellung f (Werte für Heizkörper in Klammern).

    Deutlich zu kalt (Mittel 1 h mehr als kalt_ab 0,5 K unter Soll) → je K kalt_faktor (1 K) hoch, langsam_schritt–kalt_max
    (0,5–1,5 K), höchstens alle kalt_abstand (90 min). Sonst Mittel 3 h mehr als totband (0,3 K) darunter → +langsam_schritt
    (0,5 K) alle langsam_abstand (3 h).
    Zu warm: erst wenn der Raum seit warm_dauer (50 min) durchgehend mehr als totband über Soll ist (raum_min = Minimum
    dieser Zeit; kurze Fremdwärme von Ofen/Kochen zählt nicht) → je K warm_faktor (1 K) zurück, langsam_schritt–warm_max
    (0,5–1 K), höchstens alle warm_abstand (60 min).
    Gegen Aufschaukeln: rest = übrige Bausteine. Der Raum-Baustein lernt nur so weit, wie er in der Summe
    (Grenze ± max. Verschiebung) noch wirkt; was darüber liegt, wird vor dem Absenken gekappt, damit jeder
    Schritt sofort bei der WP ankommt.
    """
    f = f or fein_standard()
    oben, unten = grenze - rest, -grenze - rest
    kurz = raum_kurz if raum_kurz is not None else raum
    if raum_min is not None and kurz is not None and raum_min > soll + f["totband"] and now - zuletzt >= f["warm_abstand"] * 60:
        schritt = clamp(round((kurz - soll) * f["warm_faktor"], 1), f["langsam_schritt"], f["warm_max"])
        return round(clamp(min(lern, oben) - schritt, -grenze, grenze), 1), now
    if kurz is not None and kurz < soll - f["kalt_ab"] and now - zuletzt >= f["kalt_abstand"] * 60:
        if lern >= oben:  # Summe hängt schon an der Grenze: weiter hochlernen bringt nichts
            return lern, zuletzt
        schritt = clamp(round((soll - kurz) * f["kalt_faktor"], 1), f["langsam_schritt"], f["kalt_max"])
        return round(clamp(max(lern, unten) + schritt, -grenze, grenze), 1), now
    if raum is not None and raum < soll - f["totband"] and now - zuletzt >= f["langsam_abstand"] * 60:
        if lern >= oben:
            return lern, zuletzt
        return round(clamp(max(lern, unten) + f["langsam_schritt"], -grenze, grenze), 1), now
    return lern, zuletzt


def prognose(fc: list[list[float]], now: float, stunden: float, steigung: float, gewicht: float) -> tuple[float, float | None, float | None]:
    """Vorausschau: mittlere Prognose der nächsten `stunden` h gegen die Prognose für jetzt (beides aus derselben
    Wetter-Entität, ein Versatz zum eigenen Fühler kürzt sich so weg). Kälter angesagt → Kurve vorab hoch, wärmer → runter.

    fc = [[Zeit, Temperatur], …] stündlich. Liefert (Verschiebung K, Prognose jetzt, Mittel der Vorausschau).
    """
    if stunden <= 0 or gewicht <= 0 or not fc:
        return 0.0, None, None
    vor = [p for p in fc if p[0] <= now]
    nach = [p for p in fc if p[0] > now]
    if vor and nach:
        (t0, v0), (t1, v1) = vor[-1], nach[0]
        jetzt = v0 + (v1 - v0) * (now - t0) / (t1 - t0)
    elif vor and now - vor[-1][0] <= 3600:
        jetzt = vor[-1][1]
    elif nach and nach[0][0] - now <= 3600:  # manche Dienste liefern erst ab der nächsten vollen Stunde
        jetzt = nach[0][1]
    else:
        return 0.0, None, None
    werte = [p[1] for p in nach if p[0] <= now + stunden * 3600]
    if not werte:
        return 0.0, round(jetzt, 1), None
    mittel = sum(werte) / len(werte)
    return round(clamp(-steigung * (mittel - jetzt) * gewicht / 100, -PROG_MAX, PROG_MAX), 1), round(jetzt, 1), round(mittel, 1)


def tagesgang(fc: list[list[float]], now: float, staerke: float, maxk: float, steigung: float,
              raum: float | None, soll: float) -> tuple[float, float | None, float | None]:
    """Wärmste Stunden: Ist es laut Prognose jetzt wärmer als im Mittel der nächsten 24 h, Kurve anheben (die WP
    arbeitet dann mit besserem COP), ist es kälter, absenken. Über den Tag gleicht sich das aus.

    Komfort: Anheben nur bis Raum = Soll + 0,5 K, Absenken nur bis Soll − 0,5 K (davor sanft auslaufend).
    Liefert (Verschiebung K, Prognose jetzt, Mittel 24 h).
    """
    if staerke <= 0:
        return 0.0, None, None
    _v, jetzt, mittel = prognose(fc, now, 24, 1.0, 100)
    if jetzt is None or mittel is None:
        return 0.0, jetzt, mittel
    v = clamp(staerke / 100 * (jetzt - mittel) * steigung, -maxk, maxk)
    if raum is not None:
        if v > 0:
            v *= clamp((soll + TAG_KOMFORT - raum) / TAG_RAMPE, 0.0, 1.0)
        elif v < 0:
            v *= clamp((raum - (soll - TAG_KOMFORT)) / TAG_RAMPE, 0.0, 1.0)
    return round(v, 1), jetzt, mittel


def tag_fein(f: dict[str, float]) -> dict[str, float]:
    """Raum-Nachführung, solange „Wärmste Stunden“ an ist: Totband und „deutlich zu kalt“ etwas weiter, damit sie
    die absichtliche Schwankung von ± 0,5 K nicht wegregelt."""
    return dict(f, totband=f["totband"] + TAG_TOTBAND, kalt_ab=f["kalt_ab"] + TAG_TOTBAND)


def sonnenkorrektur(t_wp: float | None, t_ext: float | None, steigung: float, grenze: float = MAX_STANDARD) -> float:
    """Misst der WP-Fühler (Sonne) wärmer als der eigene Fühler, rechnet die Heizkurve zu wenig – ausgleichen."""
    if t_wp is None or t_ext is None:
        return 0.0
    return round(clamp(steigung * (t_wp - t_ext), -grenze, grenze), 1)


def vorladen(t_min: float | None, stunde: int) -> float:
    """Frost angesagt (Minimum der nächsten 24 h unter 3 °C): tagsüber etwas mehr Wärme einlagern."""
    if t_min is None or t_min >= VORLADEN_AB or not 7 <= stunde < 22:
        return 0.0
    return round(min((VORLADEN_AB - t_min) * VORLADEN_FAKTOR, VORLADEN_MAX), 1)


def ziel(grund: float, teile: list[float], grenze: float = MAX_STANDARD) -> float:
    """P09-Ziel = Grundwert + Summe der Bausteine, gesamt höchstens ± max. Verschiebung um den Grundwert."""
    return round(clamp(grund + clamp(sum(teile), -grenze, grenze), P09_MIN, P09_MAX), 1)


def schreiben(zielwert: float, ist: float | None, now: float, zuletzt: float) -> bool:
    """Parameter nicht im Dauertakt schreiben: erst ab 0,5 K Änderung und höchstens alle 30 min."""
    return ist is None or (abs(zielwert - ist) >= SCHREIB_MIN and now - zuletzt >= SCHREIB_ABSTAND)


def steigung(punkte: list[list[float]]) -> float:
    """Steigung der WP-Heizkurve (K Vorlauf je K außen) aus Punkten [Außen, Heizkurven-Soll ohne P09]."""
    punkte = [p for p in punkte if p[0] < STEIGUNG_BIS]
    if len(punkte) < 20:
        return STEIGUNG_STANDARD
    xs, ys = [p[0] for p in punkte], [p[1] for p in punkte]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx < 4 * len(xs):  # zu wenig Temperaturspreizung
        return STEIGUNG_STANDARD
    b = sum((x - mx) * (y - my) for x, y in punkte) / sxx
    return round(clamp(-b, 0.3, 3.0), 2)


def schritt(zielwert: float, ist: float) -> float:
    """Höchstens +2 K bzw. −1 K je Schreibvorgang."""
    return round(clamp(zielwert, ist - SCHRITT_RUNTER, ist + SCHRITT_HOCH), 1)


def absenkbremse(neu: float, ist: float, laeuft: bool | None, vorlauf: float | None, otc: float | None,
                 wartet_seit: float | None, now: float) -> tuple[bool, float | None]:
    """Absenken bei laufendem Kompressor nur, wenn der Vorlauf schon unter dem neuen Soll liegt (sonst stoppt die WP).

    Liefert (darf schreiben, wartet_seit). Nach 60 min Warten wird trotzdem abgesenkt (in kleinen Schritten).
    """
    if neu >= ist or not laeuft or vorlauf is None or otc is None:
        return True, None
    if vorlauf <= otc + (neu - ist):
        return True, None
    seit = wartet_seit or now
    return now - seit >= ABSENK_WARTEN, seit


def kurve(p08: float, aussen: float) -> float:
    """Heizkurven-Soll der WP ohne P09 bei dieser Außentemperatur."""
    t = clamp(aussen, KURVE_UNTEN, KURVE_OBEN)
    return KURVE_MIN + (p08 - KURVE_MIN) * (KURVE_OBEN - t) / (KURVE_OBEN - KURVE_UNTEN)


def kurve_wirkung(alt: float, neu: float, aussen: float) -> float:
    """So viel K ändert sich das Soll bei dieser Außentemperatur, wenn P08 von alt auf neu geht."""
    return round(kurve(neu, aussen) - kurve(alt, aussen), 2)


def p08_lernen(punkte: list[list[float]], p08: float) -> dict[str, Any]:
    """Aus stündlichen Punkten [Zeit, Außen, Raum-Nachführung] ablesen, ob die Heizkurve zu steil oder zu flach ist.

    Raum-Nachführung ≈ c + d · x mit x = Anteil der Kurve (0 bei 17 °C, 1 bei −3 °C). Wird der Abzug umso größer,
    je kälter es ist (d < 0), ist die Kurve zu steil: P08 um d tiefer würde ihn ausgleichen. Gestellt wird gedämpft
    (halber Wert, höchstens 1 °C, in 0,5er-Schritten) und nur bei klarem Zusammenhang.
    """
    punkte = [p for p in punkte if len(p) < 4 or abs(p[3]) <= KURVE_TAG_MAX]  # starke Wärmste-Stunden-Phasen auslassen
    xs = [(KURVE_OBEN - clamp(p[1], KURVE_UNTEN, KURVE_OBEN)) / (KURVE_OBEN - KURVE_UNTEN) for p in punkte]
    ys = [p[2] for p in punkte]
    erg: dict[str, Any] = {"punkte": len(xs), "schritt": 0.0, "d": None, "r": None}
    if len(xs) < 24:
        erg["text"] = f"zu wenig Daten ({len(xs)} von 24 Stunden)"
        return erg
    spanne = (max(xs) - min(xs)) * (KURVE_OBEN - KURVE_UNTEN)
    if spanne < 3:
        erg["text"] = f"Außentemperatur schwankte nur um {spanne:.1f} K (mindestens 3 K nötig)"
        return erg
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    d = sxy / sxx
    r = sxy / (sxx * syy) ** 0.5 if syy > 0 else 0.0
    erg.update(d=round(d, 1), r=round(r, 2))
    if abs(r) < 0.5 or abs(d) < 1.0:
        erg["text"] = f"Kurve passt (Zusammenhang r = {r:.2f}, Abweichung {d:+.1f} K)"
        return erg
    schritt = round(clamp(d / 2, -P08_SCHRITT, P08_SCHRITT) * 2) / 2
    neu = clamp(p08 + schritt, P08_MIN, P08_MAX)
    erg["schritt"] = round(neu - p08, 1)
    if erg["schritt"] == 0:
        erg["text"] = f"Kurve {'zu steil' if d < 0 else 'zu flach'}, aber P08 steht an der Grenze ({P08_MIN:g}–{P08_MAX:g} °C)"
    else:
        erg["text"] = f"Kurve {'zu steil' if d < 0 else 'zu flach'} (r = {r:.2f}) → P08 {p08:g} → {neu:g} °C"
    return erg


def takt_sperre(starts: list[list[float]], now: float, sperre_bis: float) -> tuple[bool, float]:
    """starts = [[Zeit, Zählerstand Kompressorstarts], …]. ≥ 3 Starts in 2 h → 2 h keine Änderungen."""
    if now < sperre_bis:
        return True, sperre_bis
    alt = [s for s in starts if now - s[0] <= TAKT_FENSTER]
    if len(alt) >= 2 and alt[-1][1] - alt[0][1] >= TAKT_STARTS:
        return True, now + TAKT_SPERRE
    return False, sperre_bis

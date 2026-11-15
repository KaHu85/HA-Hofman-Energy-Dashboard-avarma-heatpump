"""Eigene Regelung (optional): die eingebaute Heizkurve der WP über P09 sanft verschieben.

Idee nach holle74/avarma-eigenbau-regelung, aber ausfallsicher: Die WP heizt immer mit ihrer eigenen Heizkurve,
die Integration verschiebt sie nur in engen Grenzen. Fällt Home Assistant aus, bleibt die zuletzt gesetzte
Verschiebung stehen.
"""

from __future__ import annotations

from typing import Any

LERN_SCHRITT = 0.5      # K je Lernschritt
LERN_ABSTAND = 3 * 3600  # s zwischen zwei Lernschritten
LERN_TOTBAND = 0.3      # K Abweichung vom Raum-Soll, ab der nachgeführt wird
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


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def mean(values: list[float | None]) -> float | None:
    vals = [v for v in values if v is not None]
    return round(sum(vals) / len(vals), 2) if vals else None


def lern_schritt(lern: float, raum: float | None, soll: float, now: float, zuletzt: float,
                 grenze: float = MAX_STANDARD) -> tuple[float, float]:
    """Raum dauerhaft zu kalt → Kurve +0,5 K, zu warm → −0,5 K; höchstens alle 3 h, Grenze ± max. Verschiebung."""
    if raum is None or now - zuletzt < LERN_ABSTAND:
        return lern, zuletzt
    if raum < soll - LERN_TOTBAND:
        return clamp(lern + LERN_SCHRITT, -grenze, grenze), now
    if raum > soll + LERN_TOTBAND:
        return clamp(lern - LERN_SCHRITT, -grenze, grenze), now
    return lern, zuletzt


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


def takt_sperre(starts: list[list[float]], now: float, sperre_bis: float) -> tuple[bool, float]:
    """starts = [[Zeit, Zählerstand Kompressorstarts], …]. ≥ 3 Starts in 2 h → 2 h keine Änderungen."""
    if now < sperre_bis:
        return True, sperre_bis
    alt = [s for s in starts if now - s[0] <= TAKT_FENSTER]
    if len(alt) >= 2 and alt[-1][1] - alt[0][1] >= TAKT_STARTS:
        return True, now + TAKT_SPERRE
    return False, sperre_bis

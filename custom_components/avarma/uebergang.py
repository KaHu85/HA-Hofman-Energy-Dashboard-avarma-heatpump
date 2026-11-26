"""Übergangszeit (optional, Technikerzugang, auf eigene Gefahr): bei milder Außentemperatur Lüfter, Höchstfrequenz
und Frequenzreduktion so stellen, dass die WP möglichst wenig taktet. Darunter gelten wieder die Normalwerte.
"""

from __future__ import annotations

MITTEL = 1800        # s: Außentemperatur über 30 min mitteln (kurze Sonne/Wind lösen nichts aus)
WECHSEL_MIN = 3600   # s: höchstens jede Stunde zwischen Übergangszeit und Normal umschalten
FEHL_PAUSE = 3600    # s: nimmt die WP einen Wert nicht an, erst nach 1 h erneut versuchen

# Schlüssel, Parameter, Name, Einheit, Faktor (Register × Faktor = Anzeige), Grundwert Übergangszeit, min, max
WERTE = (
    ("p60", 60, "Lüfter max. Drehzahl", "U/min", 10, 400, 400, 1500),
    ("p45", 45, "Kompressor max. Frequenz", "Hz", 1, 50, 50, 85),
    ("p114", 114, "Frequenzreduktion bei VL-Soll", "%", 1, 15, 0, 60),
)
# Welcher Außenfühler zählt (auswählbar auf der Seite „Übergangszeit“)
FUEHLER = {"eigen": "Eigener Außenfühler (aus den Optionen)", "wp": "Außenfühler der WP", "min": "Kleinerer Wert von beiden"}
# Schlüssel: Grundwert, min, max, Schritt
TEMP = {"ab": (13.0, 5.0, 20.0, 0.5), "hyst": (2.0, 0.5, 4.0, 0.5)}

# Kompressor-Stufen: unterhalb der Übergangszeit P45 (Höchstfrequenz) nach Außentemperatur stellen – mild weniger
# (kleinere Spitzen nach dem Abtauen, besserer COP), bei Frost mehr bis zum Werkswert 85 Hz (volle Leistung).
# Unter der kältesten Stufe gilt „kalt_hz“. Schlüssel, Grundwert ab °C, Grundwert Hz
STUFEN = (("s1", 5.0, 52), ("s2", 0.0, 56), ("s3", -5.0, 60), ("s4", -10.0, 72))
KALT_HZ = 85                       # Grundwert unter der kältesten Stufe (Werkswert P45, 9 kW)
STUFE_TEMP = (-15.0, 15.0, 0.5)   # min, max, Schritt
STUFE_HZ = (40, 85, 1)
STUFE_HYST = 1.0                   # K: in eine kältere Stufe (mehr Hz) erst 1 K unter der Grenze


def standard() -> dict:
    return {"on": False, "hinweis_ok": False, "fuehler": "eigen", "aktiv": False, "seit": 0.0, "fertig": True, "normal": {}, "verlauf": [], "t_buf": [], "fehl": {},
            **{k: v[0] for k, v in TEMP.items()}, **{w[0]: w[5] for w in WERTE},
            "stufen_on": False, "stufe": None, "stufe_seit": 0.0, "kalt_hz": KALT_HZ,
            **{f"{k}_ab": ab for k, ab, _hz in STUFEN}, **{f"{k}_hz": hz for k, _ab, hz in STUFEN}}


def aktiv_neu(aktiv: bool, t: float | None, ab: float, hyst: float, now: float, seit: float) -> bool:
    """Ab `ab` °C (Mittel 30 min) Übergangszeit, zurück erst unter `ab − hyst`; höchstens jede Stunde umschalten."""
    if t is None or now - seit < WECHSEL_MIN:
        return aktiv
    return t >= ab - hyst if aktiv else t >= ab


def aussen(wahl: str, eigen: float | None, wp: float | None) -> tuple[float | None, str]:
    """Außentemperatur nach Auswahl; fehlt der gewählte Fühler, gilt der andere (steht dann im Status)."""
    if wahl == "wp":
        return (wp, "WP-Fühler") if wp is not None else (eigen, "eigener Fühler (WP-Fühler fehlt)")
    if wahl == "min" and eigen is not None and wp is not None:
        return (min(eigen, wp), "kleinerer Wert (eigener Fühler)" if eigen <= wp else "kleinerer Wert (WP-Fühler)")
    if eigen is not None:
        return eigen, "eigener Fühler"
    return wp, "WP-Fühler (kein eigener Fühler gewählt)"


def stufe_neu(akt: str | None, t: float | None, uz: dict, now: float, seit: float) -> str | None:
    """Kompressor-Stufe für die Außentemperatur (Mittel 30 min). Die wärmste Stufe, deren Grenze erreicht ist, gilt.

    Kälter (mehr Leistung) sofort, sobald es 1 K unter der Grenze der aktuellen Stufe ist; wärmer (weniger Leistung)
    höchstens einmal pro Stunde. "kalt" = unter allen Stufen. Ohne bisherige Stufe (akt None) sofort die passende.
    """
    if t is None:
        return akt
    grenzen = sorted(((uz[f"{k}_ab"], k) for k, _a, _h in STUFEN), reverse=True)
    roh = next((k for ab, k in grenzen if t >= ab), "kalt")
    if roh == akt or akt is None:
        return roh
    ab_von = lambda k: float("-inf") if k == "kalt" else uz[f"{k}_ab"]
    akt_ab, roh_ab = ab_von(akt), ab_von(roh)
    if roh_ab < akt_ab:  # kälter → mehr Hz
        return akt if t >= akt_ab - STUFE_HYST else roh
    return roh if now - seit >= WECHSEL_MIN else akt


def stufe_name(uz: dict, k: str | None) -> str:
    if not k:
        return "keine Stufe (Normalwert)"
    if k == "kalt":
        return f"unter {min(uz[s[0] + '_ab'] for s in STUFEN):g} °C ({uz['kalt_hz']:g} Hz)"
    nr = [s[0] for s in STUFEN].index(k) + 1
    return f"Stufe {nr} (ab {uz[k + '_ab']:g} °C, {uz[k + '_hz']:g} Hz)"

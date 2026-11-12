"""Einsparungen der WP gegenüber Öl, Gas, Pellets und Stückholz (Kosten und CO₂ je Monat und Jahr)."""

from __future__ import annotations

from typing import Any

# Preise und Fixkosten: (Schlüssel, Name, Einheit, max, Schritt, Vorgabe)
PRICES = [  # Grundwerte = Beispiel aus Vorarlberg 11/2026, jeder trägt seine eigenen ein
    ("strom_preis", "Strom Arbeitspreis", "€/kWh", 2, 0.0001, 0.197),
    ("strom_netz", "Strom Netzkosten", "€/kWh", 1, 0.0001, 0.0),
    ("strom_grund", "Strom Grundgebühr WP", "€/Jahr", 2000, 0.01, 25.20),
    ("strom_einspeis", "PV Einspeisevergütung", "€/kWh", 1, 0.0001, 0.07),
    ("wp_wartung", "Wartung Wärmepumpe", "€/Jahr", 5000, 0.01, 0.0),
    ("oel_l", "Heizöl Preis pro Liter", "€/l", 5, 0.001, 1.85),
    ("oel_wartung", "Wartung Ölheizung", "€/Jahr", 5000, 0.01, 200.0),
    ("gas_kwh", "Gas Preis pro kWh", "€/kWh", 2, 0.0001, 0.13),
    ("gas_m3", "Gas Preis pro m³", "€/m³", 20, 0.001, 1.43),
    ("gas_hs", "Gas Umrechnung (lt. Rechnung)", "kWh/m³", 13, 0.01, 11.0),
    ("gas_grund", "Gas Grundgebühr und Zähler", "€/Jahr", 2000, 0.01, 150.0),
    ("gas_wartung", "Wartung Gasheizung", "€/Jahr", 5000, 0.01, 200.0),
    ("pellet_kg", "Pellets Preis pro kg", "€/kg", 5, 0.001, 0.45),
    ("pellet_t", "Pellets Preis pro Tonne", "€/t", 5000, 0.01, 450.0),
    ("pellet_wartung", "Wartung Pelletsheizung", "€/Jahr", 5000, 0.01, 80.0),
    ("holz_rm", "Stückholz Preis pro Raummeter", "€/rm", 1000, 0.01, 155.0),
    ("holz_wartung", "Wartung Holzheizung", "€/Jahr", 5000, 0.01, 80.0),
]
DEFAULTS = {k: d for k, _n, _u, _m, _s, d in PRICES}

# Brennstoffe: Heizwert je Einheit (kWh), Nutzungsgrad, CO₂ je kWh Brennstoff (Klimabilanz), dazu Kamin-CO₂
OEL_KWH_L, PELLET_KWH_KG, HOLZ_KWH_RM = 10.0, 4.9, 1900.0
FUELS = {  # Schlüssel: (Name, Nutzungsgrad, CO₂ kg/kWh, Kamin-CO₂ kg/kWh)
    "oel": ("Heizöl", 0.92, 0.310, 0.0),
    "gas": ("Gas", 0.95, 0.247, 0.0),
    "pellets": ("Pellets", 0.90, 0.036, 0.403),
    "holz": ("Stückholz", 0.75, 0.020, 0.403),
}
CO2_STROM = 0.227  # kg/kWh Strom Österreich (OIB-RL 6)


def linked(key: str, value: float, p: dict[str, float]) -> dict[str, float]:
    """Gekoppelte Preise: €/kWh ↔ €/m³ (Gas) und €/kg ↔ €/t (Pellets). Liefert alle geänderten Werte."""
    out = {key: value}
    hs = p.get("gas_hs") or DEFAULTS["gas_hs"]
    if key == "gas_kwh":
        out["gas_m3"] = round(value * hs, 3)
    elif key == "gas_m3":
        out["gas_kwh"] = round(value / hs, 4)
    elif key == "gas_hs" and value:
        out["gas_m3"] = round((p.get("gas_kwh") or 0) * value, 3)  # €/kWh bleibt, €/m³ folgt
    elif key == "pellet_kg":
        out["pellet_t"] = round(value * 1000)
    elif key == "pellet_t":
        out["pellet_kg"] = round(value / 1000, 3)
    return out


def fuel_price_kwh(fuel: str, p: dict[str, float]) -> float:
    """Brennstoffpreis je kWh Brennstoff (0 = kein Preis eingetragen)."""
    if fuel == "oel":
        return (p.get("oel_l") or 0) / OEL_KWH_L
    if fuel == "gas":
        return p.get("gas_kwh") or 0
    if fuel == "pellets":
        return (p.get("pellet_kg") or 0) / PELLET_KWH_KG
    return (p.get("holz_rm") or 0) / HOLZ_KWH_RM


def _fixed(fuel: str, p: dict[str, float]) -> float:
    """Fixkosten der Alternative je Monat (Grundgebühr, Wartung)."""
    w = p.get(f"{'pellet' if fuel == 'pellets' else fuel}_wartung") or 0
    grund = (p.get("gas_grund") or 0) if fuel == "gas" else 0
    return (w + grund) / 12


def month_row(w: float, s: float, share: tuple[float, float], p: dict[str, float]) -> dict[str, Any]:
    """Kosten und CO₂ eines Monats: Wärme w und WP-Strom s in kWh, share = (Netzanteil, Akkuanteil)."""
    netz = s * share[0]
    eigen = s - netz  # PV und Akku
    wp = netz * ((p.get("strom_preis") or 0) + (p.get("strom_netz") or 0)) + eigen * (p.get("strom_einspeis") or 0) \
        + ((p.get("strom_grund") or 0) + (p.get("wp_wartung") or 0)) / 12
    row: dict[str, Any] = {"waerme": round(w, 1), "strom": round(s, 1), "netz": round(netz, 1),
                           "akku": round(s * share[1], 1), "pv": round(eigen - s * share[1], 1),
                           "kosten": {"wp": round(wp, 2)}, "ersparnis": {}, "co2": {}, "co2_kamin": {}}
    co2_wp = netz * CO2_STROM
    for f, (_n, eta, co2, kamin) in FUELS.items():
        fuel_kwh = w / eta
        co2_f = fuel_kwh * co2
        row["co2"][f] = round(co2_f - co2_wp, 1)
        row["co2_kamin"][f] = round(co2_f + fuel_kwh * kamin - co2_wp, 1)
        price = fuel_price_kwh(f, p)
        if price <= 0:
            row["kosten"][f] = row["ersparnis"][f] = None
            continue
        cost = fuel_kwh * price + _fixed(f, p)
        row["kosten"][f] = round(cost, 2)
        row["ersparnis"][f] = round(cost - wp, 2)
    return row


def _add(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in b.items():
        if isinstance(v, dict):
            out[k] = _add(a.get(k, {}), v)
        elif v is None or (k in a and a[k] is None):
            out[k] = None
        else:
            out[k] = round((a.get(k) or 0) + v, 2)
    return out


def tables(ledger: dict[str, dict], buckets: dict[str, list], p: dict[str, float]) -> dict[str, Any]:
    """Monats- und Jahrestabellen.

    Herkunft des WP-Stroms je Monat aus den gemessenen Anteilen (nur mit Netz-Sensor), sonst aus dem
    Jahresmittel; ganz ohne Messung zählt der gesamte WP-Strom als Netzstrom.
    """
    years: dict[str, list[float]] = {}
    for ym, (m, g, b) in buckets.items():
        y = years.setdefault(ym[:4], [0.0, 0.0, 0.0])
        y[0], y[1], y[2] = y[0] + m, y[1] + g, y[2] + b
    months: dict[str, Any] = {}
    sums: dict[str, Any] = {}
    # erst ab dem ersten Monat mit Wärme (davor lief die WP noch nicht, also auch keine Fixkosten)
    first = min((ym for ym, e in ledger.items() if (e.get("w") or 0) > 0), default=None)
    for ym in sorted(ledger):
        e = ledger[ym]
        if first is None or ym < first or e.get("w") is None or e.get("s") is None:
            continue
        m, g, b = buckets.get(ym) or (0, 0, 0)
        est = m < 0.5 and bool(buckets)  # „geschätzt“ nur, wenn es überhaupt Messungen gibt
        if m < 0.5:
            m, g, b = years.get(ym[:4]) or (0, 0, 0)
        share = (g / m, b / m) if m >= 0.5 else (1.0, 0.0)  # ohne Messung: alles Netz (vorsichtig)
        row = month_row(e["w"], e["s"], share, p)
        row["geschaetzt"] = est
        months[ym] = row
        y = ym[:4]
        sums[y] = _add(sums.get(y, {}), {k: v for k, v in row.items() if k != "geschaetzt"})
    return {"monate": months, "jahre": sums}

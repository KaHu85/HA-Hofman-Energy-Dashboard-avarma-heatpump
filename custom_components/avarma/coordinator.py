"""Abfrage der Wärmepumpe, Zähler, Fehlerüberwachung und Code-Freigabe."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
import time
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_BATTERY_INVERT, CONF_BATTERY_SENSOR, CONF_GRID_SENSOR, CONF_NOTIFY, CONF_TECH_CODE, CONF_TECH_SWITCH, DOMAIN, DRV, ERR, FAULT_BITS, REG_DRV, REG_FAULTS, REG_FREQ,
    REG_HIST, REG_R290_ALARM, REG_R290_KONZ, REG_STARTS, UNLOCK_MINUTES, USER_CODE,
)
from .modbus import AvarmaModbus, ModbusError

_LOGGER = logging.getLogger(__name__)

FAST_BLOCKS = [(4096, 12), (4352, 50), (4608, 28)]
SLOW_BLOCKS = [  # (Intervall s, Blöcke)
    (900, [(8192, 60), (8252, 60), (8312, 29), (4864, 8)]),   # Parameter P00..P150, SG-Ready
    (300, [(5120, 60), (5180, 60), (5240, 60), (5300, 22)]),  # Energiezähler
    (600, [(6666, 1)]),                                       # Abtauung gesperrt
]
STORE_VERSION = 1
SAVE_INTERVAL = 300  # s
KOMP_DELAY_OFF = 45  # s, wie früher delay_off der Template-Binärsensors

# Zähler, die beim ersten Start aus dem Recorder (alte Utility-Meter) übernommen werden
STARTS_PERIODS = {"heute": "day", "woche": "week", "monat": "month", "jahr": "year"}
ENERGY_ACC = {f"{src}_{p}": (src, p) for src in ("waerme", "strom") for p in ("week", "month", "year")}


def period_key(kind: str, now: datetime) -> str:
    if kind == "day":
        return now.date().isoformat()
    if kind == "week":
        y, w, _ = now.isocalendar()
        return f"{y}-W{w}"
    if kind == "month":
        return f"{now.year}-{now.month:02d}"
    return str(now.year)


def s16(v: int | None) -> int | None:
    if v is None:
        return None
    return v - 0x10000 if v & 0x8000 else v


class AvarmaCoordinator(DataUpdateCoordinator[dict[int, int]]):
    """Liest alle Register und hält abgeleitete Zustände."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: AvarmaModbus, scan: int) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=timedelta(seconds=scan), config_entry=entry)
        self.entry = entry
        self.client = client
        self.regs: dict[int, int] = {}
        self._slow_due = [0.0] * len(SLOW_BLOCKS)
        self._store = Store(hass, STORE_VERSION, f"{DOMAIN}.{entry.entry_id}")
        self.acc: dict[str, Any] = {}
        self._last_ts: float | None = None
        self._last_nonzero = 0.0
        self.faults: list[str] | None = None
        self._r290_was = False
        self.unlock_user_until = 0.0
        self.unlock_tech_until = 0.0
        self._unlock_cb = None
        self._gbuf: list[tuple[float, bool, float | None, float]] = []  # (dt s, Kompressor an, Netzbezug W, Akku-Entladung W)
        self._g_ts: float | None = None
        self._ui_ts: float | None = None
        self._saved_at = 0.0

    # ------------------------------------------------------------ Register
    def u(self, addr: int) -> int | None:
        return self.regs.get(addr)

    def s(self, addr: int) -> int | None:
        return s16(self.regs.get(addr))

    async def _read_blocks(self, blocks) -> None:
        for start, count in blocks:
            vals = await self.client.read_holding(start, count)
            for i, v in enumerate(vals):
                self.regs[start + i] = v

    async def _async_update_data(self) -> dict[int, int]:
        try:
            try:
                await self._read_blocks(FAST_BLOCKS)
            except ModbusError:
                await self._read_blocks(FAST_BLOCKS)  # ein zweiter Versuch
        except ModbusError as err:
            raise UpdateFailed(str(err)) from err
        mono = time.monotonic()
        for i, (interval, blocks) in enumerate(SLOW_BLOCKS):
            if mono >= self._slow_due[i]:
                try:
                    await self._read_blocks(blocks)
                    self._slow_due[i] = mono + interval
                except ModbusError as err:
                    _LOGGER.debug("Langsamer Block %s: %s", blocks[0], err)
                    self._slow_due[i] = mono + 30
        self._update_derived()
        return self.regs

    async def async_write(self, addr: int, value: int, reread: tuple[int, int] | None = None) -> None:
        try:
            await self.client.write_register(addr, value)
            start, count = reread or (addr, 1)
            await asyncio.sleep(1)
            vals = await self.client.read_holding(start, count)
            for i, v in enumerate(vals):
                self.regs[start + i] = v
        except ModbusError as err:
            raise HomeAssistantError(f"Wärmepumpe: Schreiben fehlgeschlagen ({err})") from err
        self.async_update_listeners()

    # ------------------------------------------------------------ Kompressor
    @property
    def compressor_running(self) -> bool | None:
        f = self.u(REG_FREQ)
        if f is None:
            return None
        return f > 0 or (time.monotonic() - self._last_nonzero) < KOMP_DELAY_OFF

    # ------------------------------------------------------------ Energie
    def _esum(self, start: int, count: int) -> float | None:
        vals = [self.regs.get(start + i) for i in range(count)]
        if any(v is None for v in vals):
            return None
        return round(sum(s16(v) for v in vals) / 10, 1)

    def energy_today(self, kind: str) -> float | None:
        return self._esum(5120 if kind == "waerme" else 5254 if kind == "strom" else 5187, 24)

    def energy_month_display(self, kind: str) -> float | None:
        # Die Tageswerte der WP enthalten nur abgeschlossene Tage -> heute (Stundenwerte) addieren
        days, today = self._esum({"waerme": 5144, "strom": 5278, "ren": 5211}[kind], 31), self.energy_today(kind)
        return None if days is None or today is None else round(days + today, 1)

    def _week_from_days(self, d0: int, now: datetime) -> float:
        """Summe der Tageswerte dieser Woche (nur Tage im laufenden Monat)."""
        first = max(1, now.day - now.weekday())
        done = sum(s16(self.regs.get(d0 + d - 1) or 0) for d in range(first, now.day)) / 10
        return round(done + (self.energy_today("ren") or 0), 1)

    def energy_year(self, kind: str) -> float | None:
        m0, d0 = {"waerme": (5175, 5144), "strom": (5309, 5278), "ren": (5242, 5211)}[kind]
        months = [self.regs.get(m0 + i) for i in range(12)]
        days = self._esum(d0, 31)
        if any(v is None for v in months) or days is None:
            return None
        months = [s16(v) / 10 for v in months]
        cur = months[dt_util.now().month - 1]
        return round(sum(months) - cur + max(cur, days) + (self.energy_today(kind) or 0), 1)

    # ------------------------------------------------------------ Fehler
    def fault_list(self) -> list[str] | None:
        if any(self.regs.get(a) is None for a in REG_FAULTS + REG_DRV[:1]):
            return None
        out = []
        for reg, bits in zip(REG_FAULTS, FAULT_BITS):
            r = self.regs[reg]
            for b, code in bits.items():
                if code is not None and r & (1 << b):
                    out.append(f"E{code:02d} {ERR.get(code, '')}".strip())
        r = self.regs[REG_DRV[0]]
        for b, t in DRV.items():
            if r & (1 << b):
                out.append(f"E20 Treiber: {t}")
        return out

    def fault_history(self) -> list[str]:
        out = []
        for i in range(8):
            c = self.regs.get(REG_HIST + i) or 0
            if c > 0:
                out.append(f"E{c:02d} {ERR.get(c, 'unbekannt')}")
        return out

    # ------------------------------------------------------------ Speicher/Zähler
    async def async_load_store(self) -> None:
        data = await self._store.async_load()
        self.acc = data or {}

    def _save(self) -> None:
        """Höchstens alle 5 Minuten speichern.

        async_delay_save verschiebt den Termin bei jedem Aufruf neu; bei der Abfrage alle 10 s würde
        so erst beim Beenden von Home Assistant geschrieben (Stromausfall = Zähler seit Neustart weg).
        """
        now = time.monotonic()
        if now - self._saved_at >= SAVE_INTERVAL:
            self._saved_at = now
            self._store.async_delay_save(lambda: self.acc, 10)

    async def async_init_from_recorder(self, old: dict[str, float | None], starts_24h_ago: float | None) -> None:
        """Erster Start: Werte der bisherigen Utility-Meter/History-Stats übernehmen."""
        self.acc.setdefault("init_old", old)
        if starts_24h_ago is not None:
            self.acc.setdefault("samples", [[time.time() - 86400, starts_24h_ago]])

    def _update_derived(self) -> None:
        now = dt_util.now()
        ts = time.time()
        mono = time.monotonic()
        f = self.u(REG_FREQ) or 0
        if f > 0:
            self._last_nonzero = mono
        running = self.compressor_running
        acc = self.acc
        old = acc.get("init_old") or {}

        # Laufzeit heute (Sekunden)
        day = period_key("day", now)
        if acc.get("run_day") != day:
            acc["run_day"], acc["run_s"] = day, 0.0
            if "run_init" not in acc and old.get("laufzeit_heute") is not None:
                acc["run_s"] = float(old["laufzeit_heute"]) * 3600
            acc["run_init"] = True
        if running and self._last_ts is not None:
            acc["run_s"] += min(ts - self._last_ts, 120)
        self._last_ts = ts

        # Kompressor-Starts je Periode (Basis = Zählerstand zu Periodenbeginn)
        total = self.u(REG_STARTS)
        if total is not None:
            for name, kind in STARTS_PERIODS.items():
                key = period_key(kind, now)
                if acc.get(f"st_{name}_key") != key or total < acc.get(f"st_{name}_base", 0):
                    base = total
                    if f"st_{name}_key" not in acc and old.get(f"starts_{name}") is not None:
                        base = total - int(float(old[f"starts_{name}"]))
                    acc[f"st_{name}_key"], acc[f"st_{name}_base"] = key, base
            samples = acc.setdefault("samples", [])
            if not samples or ts - samples[-1][0] >= 300:
                samples.append([ts, total])
            while len(samples) > 2 and samples[1][0] <= ts - 86400:
                samples.pop(0)

        # Wärme/Strom Woche, Monat, Jahr (aus "heute", das täglich auf 0 springt)
        for kind in ("waerme", "strom", "ren"):
            src = self.energy_today(kind)
            if src is None:
                continue
            last = acc.get(f"e_{kind}_last")
            delta = 0.0 if last is None else (src - last if src >= last else src)
            acc[f"e_{kind}_last"] = src
            for p in ("week", "month", "year"):
                k = f"{kind}_{p}"
                key = period_key(p, now)
                if acc.get(f"e_{k}_key") != key:
                    start = 0.0
                    if f"e_{k}_key" not in acc and old.get(k) is not None:
                        start = float(old[k])
                    elif f"e_{k}_key" not in acc and kind == "ren" and p == "week":
                        start = self._week_from_days(5211, now)
                    acc[f"e_{k}_key"], acc[f"e_{k}"] = key, start
                else:
                    acc[f"e_{k}"] = round(acc[f"e_{k}"] + delta, 2)
            if kind == "strom":
                acc["pf_m"] = round(acc.get("pf_m", 0.0) + delta, 3)
        self._track_power_factor(ts)
        self._track_grid(now, ts, running)
        self._track_ledger(now)
        self._track_days(now)
        self._save()
        self._check_faults()

    # ------------------------------------------------------------ Elektrische Leistung
    def apparent_power(self) -> float | None:
        """Scheinleistung U × I in VA (Netzspannung 4381, Strom 4379)."""
        u, i = self.u(4381), self.u(4379)
        if u is None or i is None:
            return None
        return u * i / 10

    def _track_power_factor(self, ts: float) -> None:
        """Faktor Wirk-/Scheinleistung laufend am Stromzähler der WP abgleichen.

        U × I überschätzt den Verbrauch (Leistungsfaktor < 1). Verglichen wird die über die Zeit
        summierte Scheinleistung mit dem, was der WP-Zähler im selben Zeitraum gezählt hat. Ab 20 kWh
        werden beide Summen halbiert, ältere Tage verlieren so langsam an Gewicht.
        """
        dt = 0.0 if self._ui_ts is None else min(ts - self._ui_ts, 120)
        self._ui_ts = ts
        va = self.apparent_power()
        if va is None or dt <= 0:
            return
        acc = self.acc
        acc["pf_ui"] = round(acc.get("pf_ui", 0.0) + va * dt / 3_600_000, 4)
        acc.setdefault("pf_m", 0.0)
        if acc["pf_m"] >= 20:
            acc["pf_m"], acc["pf_ui"] = acc["pf_m"] / 2, acc["pf_ui"] / 2

    @property
    def power_factor(self) -> float | None:
        """Wirk-/Scheinleistung (0,5…1); None, solange zu wenig gezählt wurde (unter 2 kWh)."""
        m, ui = self.acc.get("pf_m", 0.0), self.acc.get("pf_ui", 0.0)
        if m < 2 or ui <= 0:
            return None
        return min(max(m / ui, 0.5), 1.0)

    def electric_power(self) -> float | None:
        """Elektrische Leistung der WP in W (Scheinleistung × Abgleichfaktor)."""
        va = self.apparent_power()
        if va is None:
            return None
        return round(va * (self.power_factor or 1.0))

    def power_sources(self) -> dict[str, float] | None:
        """Aktuelle Leistung nach Herkunft (W), gleiche Reihenfolge wie beim Zählen: Netz, Akku, PV."""
        p = self.electric_power()
        if p is None or not self.grid_sensor:
            return None
        g = min(p, self._grid_w() or 0.0)
        b = min(p - g, self._batt_w())
        return {"netz": round(g), "akku": round(b), "pv": round(p - g - b)}

    # ------------------------------------------------------------ Einsparungen
    def _track_ledger(self, now: datetime) -> None:
        """Wärme und Strom je Monat aus den Monatszählern der WP (laufendes Jahr) festhalten.

        Die WP kennt nur die Monate des laufenden Jahres; was hier gespeichert ist, bleibt auch
        nach dem Jahreswechsel erhalten und ergibt so die Vorjahre.
        """
        led = self.acc.setdefault("ledger", {})
        for kind, m0 in (("w", 5175), ("s", 5309)):
            for i in range(now.month):
                if i == now.month - 1:
                    v = self.energy_month_display("waerme" if kind == "w" else "strom")
                else:
                    raw = self.regs.get(m0 + i)
                    v = None if raw is None else s16(raw) / 10
                if v is not None:
                    led.setdefault(f"{now.year}-{i + 1:02d}", {})[kind] = round(v, 1)

    def _track_days(self, now: datetime) -> None:
        """Je Tag Wärme der WP (Tageszähler) und Außentemperatur (Mittel) für den Heizwärmebedarf, 400 Tage."""
        dw = self.acc.setdefault("dw", {})
        day = now.strftime("%Y-%m-%d")
        e = dw.setdefault(day, [None, 0.0, 0])
        q, t = self.energy_today("waerme"), self.s(4360)
        if q is not None:
            e[0] = q
        if t is not None:
            e[1], e[2] = round(e[1] + t / 10, 1), e[2] + 1
        for k in sorted(dw)[:-400]:
            del dw[k]

    def heat_demand(self) -> dict[str, Any]:
        from .einsparung import heat_demand

        return heat_demand(self.acc.get("dw") or {}, self.prices, dt_util.now().strftime("%Y-%m-%d"))

    @property
    def prices(self) -> dict[str, float]:
        from .einsparung import DEFAULTS

        return {**DEFAULTS, **(self.acc.get("preise") or {})}

    def set_price(self, key: str, value: float) -> None:
        from .einsparung import linked

        self.acc.setdefault("preise", {}).update(linked(key, value, self.prices))
        self._store.async_delay_save(lambda: self.acc, 5)  # Eingaben sofort sichern
        self.async_update_listeners()

    def savings(self) -> dict[str, Any]:
        from .einsparung import tables

        return tables(self.acc.get("ledger") or {}, self.acc.get("gl") or {}, self.prices)

    def source_days(self) -> dict[str, dict[str, float]]:
        """WP-Strom je Tag nach Herkunft (kWh), letzte 40 Tage."""
        return {d: {"pv": round(max(m - g - b, 0), 2), "akku": round(b, 2), "netz": round(g, 2)}
                for d, (m, g, b) in sorted((self.acc.get("gd") or {}).items())}

    # ------------------------------------------------------------ Netzanteil des WP-Stroms
    @property
    def grid_sensor(self) -> str | None:
        return self.entry.options.get(CONF_GRID_SENSOR) or None

    @property
    def battery_sensor(self) -> str | None:
        return self.entry.options.get(CONF_BATTERY_SENSOR) or None

    def _power_w(self, entity_id: str | None) -> float | None:
        st = self.hass.states.get(entity_id) if entity_id else None
        try:
            w = float(st.state)
        except (AttributeError, TypeError, ValueError):
            return None
        if st.attributes.get("unit_of_measurement") == "kW":
            w *= 1000
        return w

    def _grid_w(self) -> float | None:
        w = self._power_w(self.grid_sensor)
        return None if w is None else max(w, 0.0)

    def _batt_w(self) -> float:
        """Entladeleistung des Akkus in W (Standard wie Victron: − = Entladen); ohne Akku-Sensor 0."""
        w = self._power_w(self.battery_sensor)
        if w is None:
            return 0.0
        return max(w if self.entry.options.get(CONF_BATTERY_INVERT) else -w, 0.0)

    def add_grid(self, now: datetime, meas: float, grid: float, batt: float = 0.0) -> None:
        for p in ("day", "week", "month", "year"):
            key = period_key(p, now)
            if self.acc.get(f"g_{p}_key") != key:
                self.acc[f"g_{p}_key"], self.acc[f"g_{p}_m"], self.acc[f"g_{p}_g"] = key, 0.0, 0.0
                self.acc[f"g_{p}_b"] = 0.0
            self.acc[f"g_{p}_m"] = round(self.acc[f"g_{p}_m"] + meas, 3)
            self.acc[f"g_{p}_g"] = round(self.acc[f"g_{p}_g"] + grid, 3)
            self.acc[f"g_{p}_b"] = round(self.acc.get(f"g_{p}_b", 0.0) + batt, 3)
        # je Monat für die Einsparungsseite: [gemessen, Netz, Akku]
        bk = self.acc.setdefault("gl", {}).setdefault(now.strftime("%Y-%m"), [0.0, 0.0, 0.0])
        bk[0], bk[1], bk[2] = round(bk[0] + meas, 3), round(bk[1] + grid, 3), round(bk[2] + batt, 3)
        # je Tag für die PV-Seite (nur die letzten 40 Tage)
        gd = self.acc.setdefault("gd", {})
        bd = gd.setdefault(now.strftime("%Y-%m-%d"), [0.0, 0.0, 0.0])
        bd[0], bd[1], bd[2] = round(bd[0] + meas, 3), round(bd[1] + grid, 3), round(bd[2] + batt, 3)
        for k in sorted(gd)[:-40]:
            del gd[k]

    def _track_grid(self, now: datetime, ts: float, running: bool | None) -> None:
        """WP-Strom auf Netz, Akku und PV aufteilen.

        Die WP zählt ihren Strom in 0,1-kWh-Schritten. Jeder Schritt wird über die Zeit seit dem
        letzten Schritt verteilt (gewichtet nach Kompressorlaufzeit) und mit dem in dieser Zeit
        gemessenen Netzbezug verglichen: Netzanteil = min(WP-Strom, Netzbezug). Vom Rest stammt
        min(Rest, Akku-Entladung) aus dem Akku, was dann noch übrig ist, aus PV. Annahme: Netzbezug
        wird zuerst der WP zugerechnet, danach der Akku (PV-Anteil eher zu niedrig).
        """
        if not self.grid_sensor:
            return
        dt = 0.0 if self._g_ts is None else min(ts - self._g_ts, 120)
        self._g_ts = ts
        if dt > 0:
            self._gbuf.append((dt, bool(running), self._grid_w(), self._batt_w()))
            del self._gbuf[:-1500]
        src = self.energy_today("strom")
        if src is None:
            return
        last = self.acc.get("g_last")
        self.acc["g_last"] = src
        if last is None:
            self._gbuf.clear()
            return
        delta = src - last if src >= last else src
        if delta <= 0:
            return
        buf = [b for b in self._gbuf if b[2] is not None]
        self._gbuf.clear()
        if not buf:
            share, bshare = self.grid_share("day"), self.battery_share("day")
            if share is None:
                return
            self.add_grid(now, delta, delta * share, delta * (bshare or 0.0))
            return
        weights = [d * (1.0 if r else 0.05) for d, r, _, _ in buf]
        tot = sum(weights)
        grid = batt = 0.0
        for (d, _r, w, b), wt in zip(buf, weights):
            e = delta * wt / tot
            g = min(e, w * d / 3_600_000)
            grid += g
            batt += min(e - g, b * d / 3_600_000)
        grid = min(grid, delta)
        self.add_grid(now, delta, grid, min(batt, delta - grid))

    def grid_share(self, p: str) -> float | None:
        """Anteil des WP-Stroms aus dem Netz (0..1) in der Periode."""
        if self.acc.get(f"g_{p}_key") != period_key(p, dt_util.now()):
            return None
        m = self.acc.get(f"g_{p}_m") or 0
        return None if m < 0.05 else self.acc[f"g_{p}_g"] / m

    def battery_share(self, p: str) -> float | None:
        """Anteil des WP-Stroms aus dem Akku (0..1) in der Periode."""
        if self.acc.get(f"g_{p}_key") != period_key(p, dt_util.now()):
            return None
        m = self.acc.get(f"g_{p}_m") or 0
        return None if m < 0.05 else (self.acc.get(f"g_{p}_b") or 0.0) / m

    def source_kwh(self, p: str, src: str) -> float | None:
        """Gemessener WP-Strom der Periode nach Herkunft: "netz", "akku" oder "pv" (ohne Akku-Sensor: PV+Akku)."""
        if self.acc.get(f"g_{p}_key") != period_key(p, dt_util.now()):
            return 0.0  # neue Periode, noch kein WP-Strom gezählt
        m, g, b = (self.acc.get(f"g_{p}_{k}") or 0.0 for k in ("m", "g", "b"))
        return round({"netz": g, "akku": b, "pv": max(m - g - b, 0.0)}[src], 2)

    def starts(self, name: str) -> int | None:
        total = self.u(REG_STARTS)
        if total is None or f"st_{name}_base" not in self.acc:
            return None
        return max(total - self.acc[f"st_{name}_base"], 0)

    def starts_24h(self) -> int | None:
        total = self.u(REG_STARTS)
        samples = self.acc.get("samples") or []
        if total is None or not samples:
            return None
        return max(total - samples[0][1], 0)

    def runtime_today_h(self) -> float:
        return round(self.acc.get("run_s", 0.0) / 3600, 2)

    # ------------------------------------------------------------ Meldungen
    def _notify(self, title: str, message: str, data: dict | None = None) -> None:
        svc = (self.entry.options.get(CONF_NOTIFY) or "").strip()
        if not svc or "." not in svc:
            return
        domain, service = svc.split(".", 1)
        payload = {"title": title, "message": message}
        if data:
            payload["data"] = data
        self.hass.async_create_task(
            self.hass.services.async_call(domain, service, payload, blocking=False)
        )

    def _check_faults(self) -> None:
        cur = self.fault_list()
        if cur is None:
            return
        prev, self.faults = self.faults, cur
        if prev is not None:
            new = [f for f in cur if f not in prev]
            if new:
                stamp = dt_util.now().strftime("%d.%m.%Y %H:%M")
                self.hass.bus.async_fire(f"{DOMAIN}_stoerung", {"fehler": new, "alle": cur})
                persistent_notification.async_create(
                    self.hass, f"Aktive Fehler: {', '.join(cur)} ({stamp})", "Wärmepumpe: Störung", "avarma_fehler")
                self._notify("⚠️ Wärmepumpe: Störung", ", ".join(cur),
                             {"push": {"interruption-level": "time-sensitive"}, "url": "/waermepumpe/fehler"})
        konz = self.u(REG_R290_KONZ) or 0
        r290 = bool(self.u(REG_R290_ALARM)) or konz > 0 or any(f.startswith("E51") for f in cur)
        if r290 and not self._r290_was:
            k = f"{konz / 10:.1f}"
            persistent_notification.async_create(
                self.hass,
                f"Die Wärmepumpe meldet Kältemittel (R290/Propan) – Konzentration {k} %, Fehler: {', '.join(cur) or 'keine'}. "
                "Keine Zündquellen, Bereich lüften, WP stromlos schalten, Fachbetrieb rufen.",
                "⚠️ WÄRMEPUMPE: KÄLTEMITTEL-ALARM", "avarma_r290")
            self._notify("⚠️ Wärmepumpe: Kältemittel-ALARM",
                         f"R290-Leck gemeldet ({k} %). Keine Zündquellen, lüften, WP stromlos, Fachbetrieb rufen.",
                         {"push": {"sound": {"name": "default", "critical": 1, "volume": 1.0}, "interruption-level": "critical"}})
        self._r290_was = r290

    # ------------------------------------------------------------ Code-Freigabe
    @property
    def user_unlocked(self) -> bool:
        return time.monotonic() < self.unlock_user_until

    @property
    def tech_unlocked(self) -> bool:
        return time.monotonic() < self.unlock_tech_until

    def enter_code(self, code: str) -> str:
        code = (code or "").strip()
        tech = (self.entry.options.get(CONF_TECH_CODE) or "").strip()
        until = time.monotonic() + UNLOCK_MINUTES * 60
        if tech and code == tech:
            self.unlock_tech_until = self.unlock_user_until = until
            level = "techniker"
        elif code == USER_CODE:
            self.unlock_user_until = until
            level = "benutzer"
        else:
            raise HomeAssistantError("Wärmepumpe: Falscher Code.")
        self._schedule_relock()
        self.async_update_listeners()
        return level

    def unlock_user(self) -> None:
        """Benutzer-Freigabe per Schalter (Code 99 steht ohnehin in der Anleitung)."""
        self.unlock_user_until = time.monotonic() + UNLOCK_MINUTES * 60
        self._schedule_relock()
        self.async_update_listeners()

    def unlock_tech_switch(self) -> None:
        """Techniker-Freigabe per Schalter – nur wenn in den Optionen erlaubt und ein Code hinterlegt ist."""
        o = self.entry.options
        if not (o.get(CONF_TECH_SWITCH) and (o.get(CONF_TECH_CODE) or "").strip()):
            raise HomeAssistantError("Techniker-Freigabe nur über „WP Code eingeben“ mit dem Techniker-Code "
                                     "(oder in den Optionen der Integration „per Schalter erlauben“ aktivieren).")
        self.unlock_tech_until = self.unlock_user_until = time.monotonic() + UNLOCK_MINUTES * 60
        self._schedule_relock()
        self.async_update_listeners()

    def lock(self, tech_only: bool = False) -> None:
        self.unlock_tech_until = 0.0
        if not tech_only:
            self.unlock_user_until = 0.0
        self.async_update_listeners()

    def _schedule_relock(self) -> None:
        if self._unlock_cb:
            self._unlock_cb()

        @callback
        def _relock(_now) -> None:
            self._unlock_cb = None
            self.async_update_listeners()

        self._unlock_cb = async_call_later(self.hass, UNLOCK_MINUTES * 60 + 1, _relock)

    def check_unlocked(self, level: str, what: str) -> None:
        if level == "T" and not self.tech_unlocked:
            raise HomeAssistantError(f"{what} wurde NICHT geändert. Zuerst den Techniker-Code eingeben.")
        if level == "U" and not self.user_unlocked:
            raise HomeAssistantError(f"{what} wurde NICHT geändert. Zuerst den Benutzer-Code (99) oder Techniker-Code eingeben.")

    async def async_shutdown_store(self) -> None:
        if self._unlock_cb:
            self._unlock_cb()
        await self._store.async_save(self.acc)

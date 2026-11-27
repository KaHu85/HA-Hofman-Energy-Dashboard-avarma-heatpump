"""Abfrage der Wärmepumpe, Zähler, Fehlerüberwachung und Code-Freigabe."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
import time
from typing import Any

from homeassistant.components import logbook, persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_BATTERY_INVERT, CONF_MODELL, CONF_BATTERY_SENSOR, CONF_GRID_SENSOR, CONF_OUTDOOR_SENSOR, CONF_ROOM_SENSORS, CONF_WEATHER, CONF_NOTIFY, CONF_TECH_CODE, CONF_TECH_SWITCH, DOMAIN, DRV, ERR, ERR_INFO, FAULT_BITS, REG_DRV, REG_FAULTS, REG_FREQ,
    REG_HIST, REG_R290_ALARM, REG_R290_KONZ, REG_STARTS, REG_DEFROSTS, UNLOCK_MINUTES, USER_CODE, REG_ON, REG_MODE,
)
from .modbus import AvarmaModbus, ModbusError
from . import const as _const
from .params import P as PARAMS, addr

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
ADDR_NAME = {addr(x[0]): f"P{x[0]:02d}" for x in PARAMS}
ADDR_NAME.update({_const.REG_CLOCK_DATE: "Uhr", _const.REG_CLOCK_TIME: "Uhr", _const.REG_MODE: "Betriebsart",
                  _const.REG_ON: "Ein/Aus", _const.REG_FAULT_RESET: "Fehler-Reset"})

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
        self.want_ids: dict[str, str] = {}
        self.uz_info: dict[str, Any] = {}  # Status der Übergangszeit (für Sensoren)
        self._uz_einst: dict[str, Any] = {}  # Einstellungen der Übergangszeit, deren Protokoll noch aussteht
        self._uz_einst_cb = None
        self.rg_info: dict[str, Any] = {}  # Status der eigenen Regelung (für Sensoren)  # unique_id -> gewünschte Entity-ID (siehe AvarmaEntity.pin)
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

    async def async_write(self, addr: int, value: int, reread: tuple[int, int] | None = None, wer: str = "Hand") -> None:
        try:
            await self.client.write_register(addr, value)
            self.zaehle_schreiben(addr, wer)
            start, count = reread or (addr, 1)
            await asyncio.sleep(1)
            vals = await self.client.read_holding(start, count)
            for i, v in enumerate(vals):
                self.regs[start + i] = v
        except ModbusError as err:
            raise HomeAssistantError(f"Wärmepumpe: Schreiben fehlgeschlagen ({err})") from err
        self.async_update_listeners()

    # ------------------------------------------------------------ Schreibvorgänge
    def zaehle_schreiben(self, reg: int, wer: str = "Hand") -> None:
        """Jeden Schreibvorgang in die WP zählen (gesamt, heute, je Parameter und Herkunft, 60 Tage Verlauf)."""
        s = self._schreib_tag()
        name = ADDR_NAME.get(reg, f"Reg {reg}")
        s["gesamt"] = s.get("gesamt", 0) + 1
        s["heute"] = s.get("heute", 0) + 1
        s["heute_p"][name] = s["heute_p"].get(name, 0) + 1
        s["heute_wer"][wer] = s["heute_wer"].get(wer, 0) + 1
        self._store.async_delay_save(lambda: self.acc, 5)

    def _schreib_tag(self) -> dict:
        s = self.acc.setdefault("schreib", {"gesamt": 0, "seit": dt_util.now().strftime("%d.%m.%Y")})
        tag = period_key("day", dt_util.now())
        if s.get("tag") != tag:
            if s.get("tag"):
                hist = s.setdefault("hist", [])
                hist.append({"datum": s["tag"][8:10] + "." + s["tag"][5:7] + ".", "n": s.get("heute", 0),
                             "p": s.get("heute_p", {}), "wer": s.get("heute_wer", {})})
                del hist[:-60]
            s.update(tag=tag, heute=0, heute_p={}, heute_wer={})
        return s

    def schreib_info(self) -> dict:
        s = self._schreib_tag()
        return {"seit": s.get("seit"), "gesamt": s.get("gesamt", 0), "je_parameter": dict(sorted(s["heute_p"].items())),
                "herkunft": s["heute_wer"], "verlauf": list(reversed(s.get("hist", [])[-14:]))}

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

    @staticmethod
    def fault_hints(faults: list[str]) -> dict[str, str]:
        """Bemerkung aus der Betriebsanleitung je Fehler (Schlüssel = Text aus fault_list/fault_history)."""
        out = {}
        for f in faults:
            m = f[1:3]
            if m.isdigit() and int(m) in ERR_INFO and not f.startswith("E20 Treiber"):
                out[f] = ERR_INFO[int(m)]
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

        # Abtauungen heute und letzte 24 h. Abtauen ist kein Start, erscheint im Binärsensor „Kompressor läuft"
        # aber als Stopp, kurzer Lauf und Neustart – daher eigens zählen
        ab = self.u(REG_DEFROSTS)
        if ab is not None:
            key = period_key("day", now)
            if acc.get("ab_day_key") != key or ab < acc.get("ab_day_base", 0):
                acc["ab_day_key"], acc["ab_day_base"] = key, ab
            ab_s = acc.setdefault("ab_samples", [])
            if not ab_s or ts - ab_s[-1][0] >= 300:
                ab_s.append([ts, ab])
            while len(ab_s) > 2 and ab_s[1][0] <= ts - 86400:
                ab_s.pop(0)

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

    # ------------------------------------------------------------ Eigene Regelung (P09 sanft verschieben)
    def _temp(self, entity_id: str | None) -> float | None:
        st = self.hass.states.get(entity_id) if entity_id else None
        try:
            return float(st.state)
        except (AttributeError, TypeError, ValueError):
            return None

    @property
    def outdoor_ext(self) -> float | None:
        return self._temp(self.entry.options.get(CONF_OUTDOOR_SENSOR))

    @property
    def room_now(self) -> float | None:
        from .regelung import mean

        return mean([self._temp(e) for e in self.entry.options.get(CONF_ROOM_SENSORS) or []])

    @property
    def rg(self) -> dict[str, Any]:
        return self.acc.setdefault("rg", {"on": False, "soll": 22.0, "max": 5.0, "lern": 0.0, "lern_ts": 0.0, "write_ts": 0.0})

    def p09(self) -> float | None:
        v = self.s(addr(9))
        return None if v is None else v / 10

    @property
    def rg_fein(self) -> dict[str, float]:
        """Feineinstellung der Raum-Nachführung (Profil oder eigene Werte)."""
        from .regelung import fein_standard

        rg = self.rg
        f = rg.setdefault("fein", fein_standard(rg.get("profil", "hk")))
        for k, v in fein_standard(rg.get("profil", "hk")).items():
            f.setdefault(k, v)
        rg.setdefault("profil", "hk")
        return f

    async def async_regelung_profil(self, profil: str) -> None:
        """Profil wählen: setzt alle Feinwerte auf dessen Startwerte („Benutzerdefiniert“ lässt sie stehen)."""
        from .regelung import PROFILE, fein_standard

        rg = self.rg
        if profil != "frei":
            rg["fein"] = fein_standard(profil)
        if rg.get("profil") != profil:
            rg["profil"] = profil
            logbook.async_log_entry(self.hass, "Wärmepumpe", f"Eigene Regelung: Profil „{PROFILE[profil]}“"
                                    + (" – Feineinstellung auf dessen Startwerte gesetzt" if profil != "frei" else ""), DOMAIN)
        self._store.async_delay_save(lambda: self.acc, 5)
        self.async_update_listeners()

    async def async_regelung_fein(self, key: str, value: float) -> None:
        """Ein Feinwert von Hand geändert → Profil „Benutzerdefiniert“."""
        from .regelung import FEIN

        f, alt = self.rg_fein, self.rg_fein.get(key)
        if alt == value:
            return
        f[key] = value
        self.rg["profil"] = "frei"
        name, unit = FEIN[key][0], FEIN[key][1]
        logbook.async_log_entry(self.hass, "Wärmepumpe", f"Eigene Regelung: {name} {alt:g} → {value:g} {unit} (Profil Benutzerdefiniert)", DOMAIN)
        self._store.async_delay_save(lambda: self.acc, 5)
        self.async_update_listeners()

    async def _forecast(self, now_ts: float) -> list[list[float]]:
        """Stundenprognose [[Zeit, °C], …] der gewählten Wetter-Entität (alle 30 min neu abgefragt)."""
        rg, ent = self.rg, self.entry.options.get(CONF_WEATHER)
        if not ent:
            return []
        if now_ts - rg.get("prog_ts", 0) < 1800 and rg.get("prog_ent") == ent:
            return rg.get("prog_fc", [])
        rg["prog_ts"], rg["prog_ent"] = now_ts, ent
        try:
            res = await self.hass.services.async_call("weather", "get_forecasts", {"type": "hourly"},
                                                      target={"entity_id": ent}, blocking=True, return_response=True)
            fc = []
            for f in (res or {}).get(ent, {}).get("forecast") or []:
                zeit = dt_util.parse_datetime(str(f.get("datetime")))
                if zeit is not None and f.get("temperature") is not None:
                    fc.append([zeit.timestamp(), float(f["temperature"])])
            rg["prog_fc"] = sorted(fc)[:48]
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Wetterprognose nicht abrufbar", exc_info=True)
            rg["prog_fc"] = []
        return rg["prog_fc"]

    def seite_aus(self, page: str) -> bool:
        """Seite in den Optionen abgewählt (nur Seiten, die es beim Speichern schon gab)."""
        from .const import CONF_PAGES, CONF_PAGES_KNOWN, PAGES_V1

        pages = self.entry.options.get(CONF_PAGES)
        known = self.entry.options.get(CONF_PAGES_KNOWN) or PAGES_V1
        return pages is not None and page in known and page not in pages

    async def _regelung_aus(self, grund: str) -> bool:
        """Regelung ausschalten und P09 auf den Grundwert zurück (ohne Verbindung: später erneut versuchen)."""
        rg, p09, base = self.rg, self.p09(), self.rg.get("base")
        if p09 is None:
            return False
        if base is not None and abs(p09 - base) >= 0.05:
            await self.async_write(addr(9), int(round(base * 10)), wer="Regelung")
        rg["on"] = False
        self._store.async_delay_save(lambda: self.acc, 5)
        logbook.async_log_entry(self.hass, "Wärmepumpe", f"Eigene Regelung ausgeschaltet ({grund}): Heizkurve P09 zurück auf "
                                f"{(base if base is not None else p09):+.1f} K", DOMAIN)
        return True

    async def async_regelung_tick(self) -> None:
        """Alle 5 min: Bausteine rechnen, bei eingeschalteter Regelung P09 sanft nachführen (nie zwei gleichzeitig)."""
        lock = self.__dict__.setdefault("_rg_lock", asyncio.Lock())
        async with lock:
            await self._regelung_tick()

    async def _regelung_tick(self) -> None:
        from . import regelung as R

        rg, now_ts, now = self.rg, time.time(), dt_util.now()
        if rg.get("on") and self.seite_aus("regelung"):
            await self._regelung_aus("Seite „Regelung“ in den Optionen abgewählt")
        if rg.get("on") and not self.entry.options.get(CONF_ROOM_SENSORS) and not rg.get("ohne_fuehler"):
            p09, base = self.p09(), rg.get("base")
            if p09 is not None and base is not None:
                if abs(p09 - base) >= 0.05:
                    await self.async_write(addr(9), int(round(base * 10)), wer="Regelung")
                rg.update(ohne_fuehler=True, lern=0.0, lern_ts=time.time())
                logbook.async_log_entry(self.hass, "Wärmepumpe", "Eigene Regelung: keine Raumfühler mehr gewählt – "
                                        f"Heizkurve P09 zurück auf den Grundwert {base:+.1f} K, Regelung pausiert", DOMAIN)
        if self.entry.options.get(CONF_ROOM_SENSORS):
            rg.pop("ohne_fuehler", None)
        # Andere Raumfühler gewählt: Gelerntes passt nicht mehr zu ihnen → Raum-Nachführung neu beginnen
        fuehler = sorted(self.entry.options.get(CONF_ROOM_SENSORS) or [])
        if rg.get("fuehler") is not None and rg["fuehler"] != fuehler:
            rg.update(lern=0.0, lern_ts=now_ts, room_buf=[])
            logbook.async_log_entry(self.hass, "Wärmepumpe", "Eigene Regelung: andere Raumfühler gewählt, "
                                    "Raum-Nachführung beginnt neu bei 0 K", DOMAIN)
        rg["fuehler"] = fuehler
        # Raum-Mittel der letzten 3 h (und 1 h) puffern, Steigung der WP-Heizkurve mitlernen
        room = self.room_now
        buf = [b for b in rg.get("room_buf", []) if now_ts - b[0] <= 3 * 3600]
        if room is not None:
            buf.append([now_ts, room])
        rg["room_buf"] = buf
        room3h = R.mean([b[1] for b in buf]) if buf else None
        std = [b[1] for b in buf if now_ts - b[0] <= 3600]
        room1h = R.mean(std)
        # Minimum der letzten Stunde, erst wenn der Puffer lang genug ist (nach Neustart nicht sofort absenken)
        fein = self.rg_fein
        warm = [b[1] for b in buf if now_ts - b[0] <= fein["warm_dauer"] * 60]
        room1h_min = min(warm) if warm and now_ts - buf[0][0] >= fein["warm_dauer"] * 60 - 600 else None
        t_wp, otc, p09 = self.s(4360), self.s(4389), self.p09()
        t_wp = None if t_wp is None else t_wp / 10
        if t_wp is not None and otc is not None and p09 is not None and (not rg.get("pts") or now_ts - rg["pts"][-1][2] >= 3600):
            pts = rg.setdefault("pts", [])
            pts.append([t_wp, round(otc / 10 - p09, 1), now_ts])
            del pts[:-300]
        slope = R.steigung([[p[0], p[1]] for p in rg.get("pts", [])])
        p08 = self.s(addr(8))
        p08 = None if p08 is None else p08 / 10
        if p08 is not None:
            if rg.get("p08") is not None and abs(p08 - rg["p08"]) >= 0.05:
                self._kurve_geaendert(rg["p08"], p08, t_wp, "von Hand bzw. am Display")
            rg["p08"] = p08
        fc = await self._forecast(now_ts)
        kommend = [p[1] for p in fc if now_ts - 3600 <= p[0] <= now_ts + 24 * 3600]
        t_min = round(min(kommend), 1) if kommend else None
        prog, prog_jetzt, prog_mittel = R.prognose(fc, now_ts, fein["vorschau"], slope, fein["prog_gewicht"])
        grenze = rg.get("max", R.MAX_STANDARD)
        sb = [b for b in rg.get("sonne_buf", []) if now_ts - b[0] <= R.SONNE_MITTEL]
        sb.append([now_ts, R.sonnenkorrektur(t_wp, self.outdoor_ext, slope, grenze)])
        rg["sonne_buf"] = sb
        sonne = round(sum(b[1] for b in sb) / len(sb), 1)  # über 60 min geglättet (Wolken)
        st_total = self.u(REG_STARTS)
        starts = [s for s in rg.get("starts", []) if now_ts - s[0] <= R.TAKT_FENSTER]
        if st_total is not None:
            starts.append([now_ts, st_total])
        rg["starts"] = starts
        vor = R.vorladen(t_min, now.hour)
        tag, tag_jetzt, tag_mittel = (R.tagesgang(fc, now_ts, fein["tag_staerke"], fein["tag_max"], slope, room1h,
                                                  rg.get("soll", 22.0)) if rg.get("tag_on") else (0.0, None, None))
        self._tag_statistik(now_ts, now, t_wp)
        lern, lern_ts = R.clamp(rg.get("lern", 0.0), -grenze, grenze), rg.get("lern_ts", 0.0)
        if rg.get("on"):
            lern, lern_ts = R.lern_schritt(lern, room3h, room1h, rg.get("soll", 22.0), now_ts, lern_ts, grenze,
                                             sonne + vor + prog, room1h_min, R.tag_fein(fein) if rg.get("tag_on") else fein)
            rg["lern"], rg["lern_ts"] = lern, lern_ts
        if (rg.get("on") and room is not None and t_wp is not None and p09 is not None and self.s(addr(19)) == 1
                and self.u(REG_ON) == 1 and self.u(REG_MODE) in (2, 3)):
            kp = [p for p in rg.get("kurve_pts", []) if now_ts - p[0] <= 7 * 86400]
            if not kp or now_ts - kp[-1][0] >= 3600:
                kp.append([now_ts, t_wp, lern, tag])
            rg["kurve_pts"] = kp
        if rg.get("on") and rg.get("kurve_lernen") and p08 is not None and now.hour >= R.KURVE_STUNDE \
                and rg.get("kurve_tag") != now.date().isoformat():
            lern = await self._kurve_lernen(p08, t_wp, now_ts, now)
            p08 = rg.get("p08", p08)
        grund = rg.get("base", p09 if p09 is not None else 0.0)
        target = R.ziel(grund, [lern, sonne, vor, prog, tag], grenze)
        info = {"raum_mittel": room, "raum_3h": room3h, "raum_1h": room1h, "raum_soll": rg.get("soll", 22.0), "aussen_wp": t_wp,
                "aussen_extern": self.outdoor_ext, "steigung": slope, "prognose_min": t_min, "grundwert": grund,
                "raum": lern, "sonne": sonne, "vorladen": vor, "ziel": target, "p09": p09, "max": grenze,
                "prognose": prog, "prognose_jetzt": prog_jetzt, "prognose_mittel": prog_mittel, "wetter": self.entry.options.get(CONF_WEATHER),
                "profil": rg.get("profil", "hk"), "fein": dict(fein), "p08": p08,
                "tag": tag, "tag_on": bool(rg.get("tag_on")), "tag_jetzt": tag_jetzt, "tag_mittel": tag_mittel,
                "tag_hist": list(reversed(rg.get("tag_hist", [])[-10:])), "kurve_lernen": bool(rg.get("kurve_lernen")),
                "kurve": rg.get("kurve_info"), "kurve_punkte": len([p for p in rg.get("kurve_pts", [])
                                                                     if now_ts - p[0] <= R.KURVE_TAGE * 86400])}
        if not rg.get("on"):
            info["status"] = "aus – es wird nichts geschrieben"
        elif not self.entry.options.get(CONF_ROOM_SENSORS):
            info["status"] = "pausiert: keine Raumfühler gewählt – P09 steht auf dem Grundwert"
        elif self.s(addr(19)) != 1:
            info["status"] = "pausiert: Heizkurve der WP (P19) ist aus"
        elif self.u(REG_ON) != 1 or self.u(REG_MODE) not in (2, 3):
            info["status"] = "pausiert: WP aus oder nicht im Heizbetrieb"
        elif p09 is None:
            info["status"] = "pausiert: keine Verbindung zur WP"
        elif (gesperrt := R.takt_sperre(starts, now_ts, rg.get("takt_bis", 0.0)))[0]:
            rg["takt_bis"] = gesperrt[1]
            bis = dt_util.as_local(dt_util.utc_from_timestamp(gesperrt[1])).strftime("%H:%M")
            info["status"] = f"Takt-Schutz: viele Kompressorstarts – keine Änderung bis {bis}"
        elif R.schreiben(target, p09, now_ts, rg.get("write_ts", 0.0)):
            neu = R.schritt(target, p09)
            vl, otc_now = self.s(4366), self.s(4389)
            darf, rg["absenk_seit"] = R.absenkbremse(neu, p09, self.compressor_running, None if vl is None else vl / 10,
                                                     None if otc_now is None else otc_now / 10, rg.get("absenk_seit"), now_ts)
            if not darf:
                info["status"] = (f"Absenkbremse: Kompressor läuft, Vorlauf liegt über dem neuen Soll – "
                                  f"wartet mit dem Absenken auf {neu:+.1f} K (höchstens 60 min)")
            else:
                try:
                    await self.async_write(addr(9), int(round(neu * 10)), wer="Regelung")
                    rg["write_ts"], rg["absenk_seit"] = now_ts, None
                    info["status"] = f"aktiv – P09 auf {neu:+.1f} K gesetzt" + (f" (Ziel {target:+.1f} K, in Schritten)" if neu != target else "")
                    logbook.async_log_entry(self.hass, "Wärmepumpe", f"Eigene Regelung: Heizkurve P09 {p09:+.1f} → {neu:+.1f} K "
                                            f"(Raum {lern:+.1f}, Sonne {sonne:+.1f}, Prognose {prog:+.1f}, Vorladen {vor:+.1f}"
                                            + (f", Wärmste Stunden {tag:+.1f}" if rg.get("tag_on") else "") + ")", DOMAIN)
                except Exception as err:  # noqa: BLE001
                    info["status"] = f"Schreiben fehlgeschlagen: {err}"
        elif p09 is not None and abs(target - p09) >= R.SCHREIB_MIN:
            ab = dt_util.as_local(dt_util.utc_from_timestamp(rg.get("write_ts", 0.0) + R.SCHREIB_ABSTAND)).strftime("%H:%M")
            info["status"] = f"aktiv – wartet: nächste Änderung auf {target:+.1f} K ab {ab} (Parameter höchstens alle 30 min)"
        else:
            info["status"] = "aktiv – P09 passt (Abweichung unter 0,5 K)"
        if rg.get("on") and self.entry.options.get(CONF_ROOM_SENSORS) and room is None:
            info["status"] += " · Raumfühler liefert gerade keinen Wert, Raum-Nachführung hält"
        self.rg_info = info
        self.async_update_listeners()

    def _kurve_geaendert(self, alt: float, neu: float, aussen: float | None, wer: str) -> None:
        """P08 hat sich geändert: Raum-Nachführung um die Wirkung bei der aktuellen Außentemperatur gegensteuern.

        Sonst korrigieren Kurve und Raum-Nachführung doppelt (gesehen am 22.11.: P08 50 → 45 bei −3,3 K Abzug → zu kalt).
        Die gesammelten Lernpunkte werden auf die neue Kurve umgerechnet.
        """
        from . import regelung as R

        rg = self.rg
        if not rg.get("on") or aussen is None:
            logbook.async_log_entry(self.hass, "Wärmepumpe", f"Heizkurve P08 {alt:g} → {neu:g} °C ({wer})", DOMAIN)
            return
        grenze = rg.get("max", R.MAX_STANDARD)
        wirkung = R.kurve_wirkung(alt, neu, aussen)
        vorher = rg.get("lern", 0.0)
        rg["lern"] = round(R.clamp(vorher - wirkung, -grenze, grenze), 1)
        rg["lern_ts"], rg["write_ts"] = time.time(), 0.0  # neue Summe gleich schreiben dürfen
        rg["kurve_pts"] = [[p[0], p[1], round(p[2] - R.kurve_wirkung(alt, neu, p[1]), 2), *p[3:]] for p in rg.get("kurve_pts", [])]
        self._store.async_delay_save(lambda: self.acc, 5)
        logbook.async_log_entry(self.hass, "Wärmepumpe", f"Heizkurve P08 {alt:g} → {neu:g} °C ({wer}): Soll bei {aussen:g} °C außen "
                                f"{wirkung:+.1f} K – Raum-Nachführung {vorher:+.1f} → {rg['lern']:+.1f} K angepasst", DOMAIN)

    async def _kurve_lernen(self, p08: float, aussen: float | None, now_ts: float, now) -> float:
        """Einmal am Tag: Steigung der Heizkurve (P08) aus der Raum-Nachführung der letzten Tage nachstellen."""
        from . import regelung as R

        rg = self.rg
        rg["kurve_tag"] = now.date().isoformat()
        pts = [p for p in rg.get("kurve_pts", []) if now_ts - p[0] <= R.KURVE_TAGE * 86400]
        erg = R.p08_lernen(pts, p08)
        erg["zeit"] = now.strftime("%d.%m. %H:%M")
        rg["kurve_info"] = erg
        if erg["schritt"] and aussen is not None:
            neu = round(p08 + erg["schritt"], 1)
            try:
                await self.async_write(addr(8), int(round(neu * 10)), wer="Regelung")
            except Exception as err:  # noqa: BLE001
                erg["text"] += f" – Schreiben fehlgeschlagen: {err}"
                rg["kurve_tag"] = None  # beim nächsten Durchlauf erneut versuchen
            else:
                self._kurve_geaendert(p08, neu, aussen, f"gelernt: {erg['text']}")
                rg["p08"] = neu
        else:
            logbook.async_log_entry(self.hass, "Wärmepumpe", f"Heizkurve lernen: {erg['text']}", DOMAIN)
        self._store.async_delay_save(lambda: self.acc, 5)
        return rg.get("lern", 0.0)

    def _tag_statistik(self, now_ts: float, now, t_wp: float | None) -> None:
        """Je Tag: mittlere Außentemperatur (gesamt, während der Kompressor läuft, je erzeugter kWh Wärme), Laufzeit,
        Starts, Wärme, Strom, COP.

        Läuft immer mit (auch ohne „Wärmste Stunden“), damit es Vergleichstage gibt. Die WP schreibt die Wärme/den Strom
        der letzten Stunde erst einige Minuten nach Mitternacht in ihren Tageszähler und setzt ihn dann zurück. Ein Tag
        wird deshalb erst abgeschlossen, wenn der Zähler zurückgesetzt ist (spätestens 2 h nach Mitternacht).
        """
        rg, datum = self.rg, now.date().isoformat()
        w, strom = self.energy_today("waerme"), self.energy_today("strom")
        # Wärme-Gewichtung: Der Tageszähler wächst stundenweise. Ein Zuwachs gehört zu den Außentemperaturen seit dem
        # letzten Zuwachs – deren Mittel wird mit den kWh gewichtet.
        seg = rg.setdefault("tag_seg", {"t": 0.0, "n": 0, "w": None})
        if t_wp is not None:
            seg["t"] += t_wp
            seg["n"] += 1
        zuwachs = None
        if w is not None:
            if seg["w"] is not None and w != seg["w"]:
                if 0 < w - seg["w"] < 15 and seg["n"]:
                    zuwachs = (w - seg["w"], seg["t"] / seg["n"])
                seg.update(t=0.0, n=0)
            seg["w"] = w

        alt = rg.get("tag_alt")
        if alt:
            reset = w is not None and alt.get("waerme") is not None and w < alt["waerme"] - 0.5
            if reset or now_ts - alt["ende"] > 7200:
                self._tag_abschluss(alt)
                rg.pop("tag_alt", None)
            else:
                if w is not None:
                    alt["waerme"] = w
                if strom is not None:
                    alt["strom"] = strom
                if zuwachs:
                    alt["w_sum"] = alt.get("w_sum", 0.0) + zuwachs[0]
                    alt["w_t"] = alt.get("w_t", 0.0) + zuwachs[0] * zuwachs[1]
                zuwachs = None

        st = rg.get("tag_stat")
        if st and st.get("datum") != datum:
            if rg.get("tag_alt"):
                self._tag_abschluss(rg.pop("tag_alt"))
            st["ende"] = now_ts
            rg["tag_alt"] = st
            st = None
        if st is None:
            st = {"datum": datum, "n": 0, "sum_t": 0.0, "lauf_s": 0.0, "lauf_t": 0.0, "an": False, "zuletzt": now_ts}
        dt = min(max(now_ts - st.get("zuletzt", now_ts), 0), 600)
        st["zuletzt"] = now_ts
        if t_wp is not None:
            st["n"] += 1
            st["sum_t"] += t_wp
            if self.compressor_running:
                st["lauf_s"] += dt
                st["lauf_t"] += t_wp * dt
        if zuwachs and not rg.get("tag_alt"):
            st["w_sum"] = st.get("w_sum", 0.0) + zuwachs[0]
            st["w_t"] = st.get("w_t", 0.0) + zuwachs[0] * zuwachs[1]
        if (tot := self.u(REG_STARTS)) is not None:
            st.setdefault("st0", tot)
            st["st_end"] = tot
        if not rg.get("tag_alt"):  # solange der Vortag offen ist, gehören die Zählerstände noch ihm
            if w is not None:
                st["waerme"] = w
            if strom is not None:
                st["strom"] = strom
        st["an"] = st.get("an") or bool(rg.get("tag_on") and rg.get("on"))
        rg["tag_stat"] = st

    def _tag_abschluss(self, st: dict) -> None:
        if not st.get("n"):
            return
        cop = round(st["waerme"] / st["strom"], 2) if st.get("waerme") and st.get("strom") else None
        hist = self.rg.setdefault("tag_hist", [])
        hist.append({"datum": st["datum"][8:10] + "." + st["datum"][5:7] + ".", "an": st.get("an", False),
                     "aussen": round(st["sum_t"] / st["n"], 1),
                     "aussen_lauf": round(st["lauf_t"] / st["lauf_s"], 1) if st.get("lauf_s") else None,
                     "aussen_w": round(st["w_t"] / st["w_sum"], 1) if st.get("w_sum", 0) >= 1 else None,
                     "starts": (st["st_end"] - st["st0"]) if st.get("st0") is not None and st.get("st_end") is not None else None,
                     "laufzeit": round(st.get("lauf_s", 0) / 3600, 1), "waerme": st.get("waerme"), "strom": st.get("strom"), "cop": cop})
        del hist[:-60]

    async def async_tag_set(self, on: bool) -> None:
        rg = self.rg
        if bool(rg.get("tag_on")) != on:
            rg["tag_on"] = on
            logbook.async_log_entry(self.hass, "Wärmepumpe", "Wärmste Stunden nutzen " + ("eingeschaltet" if on else "ausgeschaltet"), DOMAIN)
            self._store.async_delay_save(lambda: self.acc, 5)
        await self.async_regelung_tick()

    async def async_kurve_lernen_set(self, on: bool) -> None:
        rg = self.rg
        if bool(rg.get("kurve_lernen")) != on:
            rg["kurve_lernen"] = on
            logbook.async_log_entry(self.hass, "Wärmepumpe", "Heizkurve lernen (P08) " + ("eingeschaltet" if on else "ausgeschaltet"), DOMAIN)
            self._store.async_delay_save(lambda: self.acc, 5)
        self.async_update_listeners()

    async def async_regelung_set(self, on: bool) -> None:
        """Ein: aktuellen P09 als Grundwert merken. Aus: Grundwert zurückschreiben."""
        rg = self.rg
        if on and not rg.get("on"):
            rg.update(on=True, base=self.p09() if self.p09() is not None else 0.0, lern=0.0, lern_ts=time.time(), write_ts=0.0)
        elif not on and rg.get("on"):
            base = rg.get("base")
            rg["on"] = False
            if base is not None and self.p09() is not None and abs(self.p09() - base) >= 0.05:
                await self.async_write(addr(9), int(round(base * 10)), wer="Regelung")
                logbook.async_log_entry(self.hass, "Wärmepumpe", f"Eigene Regelung aus: Heizkurve P09 zurück auf {base:+.1f} K", DOMAIN)
        self._store.async_delay_save(lambda: self.acc, 5)
        await self.async_regelung_tick()

    # ------------------------------------------------------------ Modell / Werkseinstellungen
    @property
    def modell(self) -> str:
        from .params import MODELL_STANDARD, MODELLE

        m = self.entry.options.get(CONF_MODELL)
        return m if m in MODELLE else MODELL_STANDARD

    def werk(self, p: int):
        from .params import werk

        return werk(self.modell, p)

    @property
    def p45_max(self) -> int:
        """Höchste Frequenz, die die Übergangszeit für P45 schreiben darf: Werkswert des Modells (9 kW: 85 Hz)."""
        return int(self.werk(45) or 85)

    # ------------------------------------------------------------ Übergangszeit (P60/P45/P114, Technikerzugang)
    @property
    def uz(self) -> dict[str, Any]:
        from .uebergang import STUFEN, standard

        uz = self.acc.setdefault("uz", standard())
        for k, v in standard().items():
            uz.setdefault(k, v)
        mx = self.p45_max  # anderes Modell gewählt: Frequenzen nicht über dessen Werkswert
        for k in ["kalt_hz", "p45"] + [f"{s[0]}_hz" for s in STUFEN]:
            if isinstance(uz.get(k), (int, float)) and uz[k] > mx:
                uz[k] = mx
        return uz

    def uz_ist(self, key: str) -> int | None:
        """Aktueller Wert in der WP (Anzeige-Einheit, P60 in U/min)."""
        from .uebergang import WERTE

        p, f = next((w[1], w[4]) for w in WERTE if w[0] == key)
        v = self.s(addr(p))
        return None if v is None else v * f

    def _uz_log(self, text: str) -> None:
        self.uz["verlauf"] = ([{"zeit": dt_util.now().strftime("%d.%m. %H:%M"), "text": text}] + self.uz["verlauf"])[:100]
        logbook.async_log_entry(self.hass, "Wärmepumpe", f"Übergangszeit: {text}", DOMAIN, "sensor.wp_ubergangszeit_status")
        self._store.async_delay_save(lambda: self.acc, 5)

    async def _uz_apply(self, ziel: dict[str, int], grund: str, now_ts: float) -> list[str]:
        """Abweichende Werte schreiben und zurücklesen. Liefert die Werte, die (noch) nicht passen."""
        from .uebergang import FEHL_PAUSE, WERTE

        uz, offen = self.uz, []
        for key, p, name, unit, f, *_ in WERTE:
            soll, ist = ziel.get(key), self.uz_ist(key)
            if soll is None or ist is None or ist == soll:
                continue
            if now_ts - uz["fehl"].get(key, 0.0) < FEHL_PAUSE:
                offen.append(f"P{p}")
                continue
            try:
                await self.async_write(addr(p), int(round(soll / f)), wer="Übergangszeit")
            except Exception as err:  # noqa: BLE001
                uz["fehl"][key] = now_ts
                self._uz_log(f"P{p} {name} {ist:g} → {soll:g} {unit} fehlgeschlagen ({err})")
                offen.append(f"P{p}")
                continue
            neu = self.uz_ist(key)
            if neu == soll:
                uz["fehl"].pop(key, None)
                self._uz_log(f"P{p} {name} {ist:g} → {soll:g} {unit} ({grund})")
            else:
                uz["fehl"][key] = now_ts
                self._uz_log(f"P{p} {name}: WP hat {soll:g} {unit} nicht übernommen (liest {neu if neu is not None else '–'})")
                offen.append(f"P{p}")
        return offen

    async def async_uebergang_tick(self) -> None:
        """Alle 5 min: Außentemperatur mitteln, zwischen Übergangszeit und Normal umschalten, Werte nachziehen.

        Nie zwei Durchläufe gleichzeitig (Takt + Wertänderung), sonst wird doppelt geschrieben und protokolliert.
        """
        lock = self.__dict__.setdefault("_uz_lock", asyncio.Lock())
        async with lock:
            await self._uebergang_tick()

    async def _uebergang_tick(self) -> None:
        if self.uz["on"] and self.seite_aus("uebergang"):
            self.uz["on"] = False
            self._uz_log("ausgeschaltet, weil die Seite „Übergangszeit“ in den Optionen abgewählt wurde – Normalwerte zurück")
        from .regelung import mean
        from .uebergang import MITTEL, STUFEN, WERTE, aktiv_neu, aussen, stufe_name, stufe_neu

        uz, now_ts = self.uz, time.time()
        t_wp = self.s(4360)
        t_wp = None if t_wp is None else t_wp / 10
        t, quelle = aussen(uz["fuehler"], self.outdoor_ext, t_wp)
        buf = [b for b in uz["t_buf"] if now_ts - b[0] <= MITTEL]
        if t is not None:
            buf.append([now_ts, t])
        uz["t_buf"] = buf
        t_mittel = mean([b[1] for b in buf])
        ist = {w[0]: self.uz_ist(w[0]) for w in WERTE}
        normal = uz["normal"]
        # Normalbetrieb: was in der WP steht, gilt (Änderung am Display/auf der Parameterseite wird als Normalwert übernommen)
        if not uz["aktiv"] and uz["fertig"]:
            for key, p, name, unit, *_ in WERTE:
                if key == "p45" and uz.get("stufe"):
                    continue  # P45 setzt gerade eine Kompressor-Stufe
                if ist[key] is not None and normal.get(key) != ist[key]:
                    if key in normal:
                        self._uz_log(f"Normalwert P{p} {name} in der WP geändert: {normal[key]:g} → {ist[key]:g} {unit} übernommen")
                    normal[key] = ist[key]
        info = {"aussen_mittel": t_mittel, "aussen_quelle": quelle, "aussen_wp": t_wp, "aussen_eigen": self.outdoor_ext,
                "ab": uz["ab"], "zurueck_unter": round(uz["ab"] - uz["hyst"], 1), "aktiv": uz["aktiv"], "ein": uz["on"],
                "ist": ist, "uebergang": {w[0]: uz[w[0]] for w in WERTE}, "normal": dict(normal), "verlauf": uz["verlauf"],
                "stufen_on": bool(uz.get("stufen_on")), "stufe": uz.get("stufe"), "stufe_name": stufe_name(uz, uz.get("stufe")),
                "stufen": [{"nr": i + 1, "ab": uz[f"{k}_ab"], "hz": uz[f"{k}_hz"]} for i, (k, _a, _h) in enumerate(STUFEN)],
                "kalt_hz": uz.get("kalt_hz")}
        if not uz["on"] and not uz["aktiv"] and uz["fertig"] and not uz.get("stufe"):
            info["status"] = "aus – es wird nichts geschrieben"
        elif not (self.entry.options.get(CONF_TECH_CODE) or "").strip():
            info["status"] = "pausiert: kein Techniker-Code in den Optionen hinterlegt"
        elif any(v is None for v in ist.values()):
            info["status"] = "pausiert: keine Verbindung zur WP"
        else:
            aktiv = uz["aktiv"]
            if uz["on"]:
                aktiv = aktiv_neu(aktiv, t_mittel, uz["ab"], uz["hyst"], now_ts, uz["seit"])
            else:
                aktiv = False  # ausgeschaltet, während die Übergangszeit galt → Normalwerte zurück
            if aktiv != uz["aktiv"]:
                uz.update(aktiv=aktiv, seit=now_ts, fertig=False, fehl={})
                if aktiv:
                    self._uz_log(f"Übergangszeit beginnt (außen {t_mittel:.1f} °C, Mittel 30 min ≥ {uz['ab']:.1f} °C)")
                elif not uz["on"]:
                    self._uz_log("ausgeschaltet – Normalwerte zurück")
                else:
                    self._uz_log(f"Übergangszeit endet (außen {t_mittel:.1f} °C < {uz['ab'] - uz['hyst']:.1f} °C) – Normalwerte zurück")
            stufe = None
            if uz["on"] and uz.get("stufen_on") and not aktiv:
                stufe = stufe_neu(uz.get("stufe"), t_mittel, uz, now_ts, uz.get("stufe_seit", 0.0))
            if stufe != uz.get("stufe"):
                self._uz_log(f"Kompressor: {stufe_name(uz, uz.get('stufe'))} → {stufe_name(uz, stufe)}"
                             + (f" (außen {t_mittel:.1f} °C)" if t_mittel is not None else ""))
                uz.update(stufe=stufe, stufe_seit=now_ts, fertig=False)
                uz["fehl"].pop("p45", None)
            ziel = {w[0]: uz[w[0]] for w in WERTE} if aktiv else dict(normal)
            grund = "Übergangszeit" if aktiv else "Normalwert"
            if stufe:
                ziel["p45"] = min(int(uz[f"{stufe}_hz"]), self.p45_max)
                grund = f"Kompressor-{stufe_name(uz, stufe)}"
            offen = await self._uz_apply(ziel, grund, now_ts)
            uz["fertig"] = not offen
            info["aktiv"], info["ist"] = aktiv, {w[0]: self.uz_ist(w[0]) for w in WERTE}
            was = "Übergangszeit aktiv" if aktiv else "Normalwerte"
            info["status"] = f"{was} – " + (f"noch offen: {', '.join(offen)}" if offen else "alle Werte passen")
            if stufe:
                info["status"] = f"Kompressor-{stufe_name(uz, stufe)} – " + (f"noch offen: {', '.join(offen)}" if offen else "alle Werte passen")
            if uz["on"] and not aktiv and t_mittel is not None:
                info["status"] += f" (Übergangszeit ab {uz['ab']:.1f} °C, jetzt {t_mittel:.1f} °C)"
            info["stufe"], info["stufe_name"] = stufe, stufe_name(uz, stufe)
        self.uz_info = info
        self._store.async_delay_save(lambda: self.acc, 5)
        self.async_update_listeners()

    async def async_uebergang_set(self, on: bool) -> None:
        """Ein nur mit in den Optionen hinterlegtem Techniker-Code. Aus geht immer (Normalwerte zurück)."""
        uz = self.uz
        if on and not uz["on"]:
            if not (self.entry.options.get(CONF_TECH_CODE) or "").strip():
                raise HomeAssistantError("Übergangszeit: zuerst in den Optionen der Integration den Techniker-Code hinterlegen.")
            if not uz["hinweis_ok"]:
                raise HomeAssistantError("Übergangszeit: zuerst den Warnhinweis auf der Seite „Übergangszeit“ lesen und bestätigen.")
            uz.update(on=True, seit=0.0)
            self._uz_log("eingeschaltet")
        elif not on and uz["on"]:
            uz["on"] = False
            if not uz["aktiv"]:
                self._uz_log("ausgeschaltet")
        await self.async_uebergang_tick()

    async def async_uz_stufen_set(self, on: bool) -> None:
        """Kompressor-Stufen ein/aus (ein nur mit Techniker-Code). Aus → P45 zurück auf den Normalwert."""
        uz = self.uz
        if on and not (self.entry.options.get(CONF_TECH_CODE) or "").strip():
            raise HomeAssistantError("Kompressor-Stufen: zuerst in den Optionen der Integration den Techniker-Code hinterlegen.")
        if bool(uz.get("stufen_on")) != on:
            uz.update(stufen_on=on, stufe_seit=0.0)
            self._uz_log("Kompressor-Stufen " + ("eingeschaltet" if on else "ausgeschaltet – P45 zurück auf den Normalwert"))
        await self.async_uebergang_tick()

    async def async_uebergang_wert(self, field: str, value: float) -> None:
        """Einstellung der Übergangszeit ändern (nur mit hinterlegtem Techniker-Code), sofort anwenden."""
        from .uebergang import WERTE

        if not (self.entry.options.get(CONF_TECH_CODE) or "").strip():
            raise HomeAssistantError("Übergangszeit: zuerst in den Optionen der Integration den Techniker-Code hinterlegen.")
        uz, namen = self.uz, {w[0]: (w[1], w[2], w[3]) for w in WERTE}
        value = int(value) if field.removeprefix("normal_") in namen else float(value)
        if field.startswith("normal_"):
            key = field.removeprefix("normal_")
            alt = uz["normal"].get(key)
            uz["normal"][key], uz["fertig"] = value, False  # erst schreiben, dann wieder aus der WP übernehmen
            p, name, unit = namen[key]
            self._uz_log(f"Normalwert P{p} {name} {alt if alt is not None else '–'} → {value:g} {unit} eingestellt")
        else:
            self._uz_einst.setdefault(field, uz.get(field))  # Wert vor der ersten von mehreren schnellen Änderungen
            uz[field] = value
            if self._uz_einst_cb:
                self._uz_einst_cb()
            self._uz_einst_cb = async_call_later(self.hass, 20, self._uz_einst_log)
        await self.async_uebergang_tick()

    async def async_uebergang_fuehler(self, wahl: str) -> None:
        """Außenfühler der Übergangszeit wählen; das 30-min-Mittel beginnt neu."""
        from .uebergang import FUEHLER

        if not (self.entry.options.get(CONF_TECH_CODE) or "").strip():
            raise HomeAssistantError("Übergangszeit: zuerst in den Optionen der Integration den Techniker-Code hinterlegen.")
        uz = self.uz
        if wahl != uz["fuehler"]:
            self._uz_log(f"Außenfühler {FUEHLER.get(uz['fuehler'], uz['fuehler'])} → {FUEHLER[wahl]}")
            uz.update(fuehler=wahl, t_buf=[])
        await self.async_uebergang_tick()

    @callback
    def _uz_einst_log(self, _now=None) -> None:
        """Einstellungen erst 20 s nach dem letzten Klick protokollieren – ein Eintrag je Wert statt einer je Klick."""
        from .uebergang import WERTE

        namen = {w[0]: (w[1], w[2], w[3]) for w in WERTE}
        self._uz_einst_cb = None
        for field, alt in self._uz_einst.items():
            neu = self.uz.get(field)
            if alt == neu:
                continue
            if field in namen:
                p, name, unit = namen[field]
                self._uz_log(f"Wert Übergangszeit P{p} {name} {alt:g} → {neu:g} {unit} eingestellt")
            elif field == "kalt_hz":
                self._uz_log(f"Kompressor unter der kältesten Stufe {alt:g} → {neu:g} Hz")
            elif field[:1] == "s" and field[1:2].isdigit():
                art = "ab" if field.endswith("_ab") else "Höchstfrequenz"
                self._uz_log(f"Kompressor-Stufe {field[1]} {art} {alt:g} → {neu:g} " + ("°C" if field.endswith("_ab") else "Hz"))
            else:
                self._uz_log(("Übergangszeit ab" if field == "ab" else "Hysterese") + f" {alt:g} → {neu:g} " + ("°C" if field == "ab" else "K"))
        self._uz_einst = {}

    def _track_days(self, now: datetime) -> None:
        """Je Tag Wärme der WP (Tageszähler) und Außentemperatur (Mittel) für den Heizwärmebedarf, 400 Tage."""
        dw = self.acc.setdefault("dw", {})
        day = now.strftime("%Y-%m-%d")
        e = dw.setdefault(day, [None, 0.0, 0])
        q, t = self.energy_today("waerme"), self.outdoor_ext
        if t is None and self.s(4360) is not None:
            t = self.s(4360) / 10
        if q is not None:
            e[0] = q
        if t is not None:
            e[1], e[2] = round(e[1] + t, 1), e[2] + 1
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

    def init_abtau(self, day_base: float | None, ago: float | None) -> None:
        """Erster Start mit Abtau-Zählung: Zählerstände zu Tagesbeginn und vor 24 h aus dem Recorder übernehmen."""
        if day_base is not None:
            self.acc.update(ab_day_key=period_key("day", dt_util.now()), ab_day_base=day_base)
        if ago is not None:
            self.acc.setdefault("ab_samples", [[time.time() - 86400, ago]])

    def abtau_heute(self) -> int | None:
        total = self.u(REG_DEFROSTS)
        if total is None or "ab_day_base" not in self.acc:
            return None
        return max(int(total - self.acc["ab_day_base"]), 0)

    def abtau_24h(self) -> int | None:
        total = self.u(REG_DEFROSTS)
        samples = self.acc.get("ab_samples") or []
        if total is None or not samples:
            return None
        return max(int(total - samples[0][1]), 0)

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
                hints = self.fault_hints(cur)
                text = f"Aktive Fehler ({stamp}):\n" + "\n".join(f"- **{f}**" + (f" – {hints[f]}" if f in hints else "") for f in cur)
                persistent_notification.async_create(self.hass, text, "Wärmepumpe: Störung", "avarma_fehler")
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
        if self._uz_einst_cb:
            self._uz_einst_cb()
            self._uz_einst_log()
        await self._store.async_save(self.acc)

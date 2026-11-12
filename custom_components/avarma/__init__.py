"""Avarma (Hofman) R290 Wärmepumpe über Modbus RS485."""

from __future__ import annotations

import logging
import os

from homeassistant.components import frontend, persistent_notification
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers import config_validation as cv, entity_registry as er
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CLOCK_SYNC, CONF_DASHBOARD, CONF_PROTOCOL, CONF_SCAN_INTERVAL, CONF_SLAVE, DEFAULT_SCAN, DOMAIN, PLATFORMS, STATIC_URL,
)
from .coordinator import AvarmaCoordinator
from .modbus import AvarmaModbus

_LOGGER = logging.getLogger(__name__)

OLD_PLATFORMS = {"modbus", "template", "utility_meter", "history_stats", "automation"}
OLD_HELPERS = {"input_text.wp_code", "input_boolean.wp_benutzer_freigabe", "input_boolean.wp_techniker_freigabe"}
# Werte der früheren YAML-Version, die beim allerersten Start übernommen werden
OLD_VALUES = {
    "laufzeit_heute": "sensor.wp_kompressor_laufzeit_heute",
    "starts_heute": "sensor.wp_kompressor_starts_heute", "starts_woche": "sensor.wp_kompressor_starts_woche",
    "starts_monat": "sensor.wp_kompressor_starts_monat", "starts_jahr": "sensor.wp_kompressor_starts_jahr",
    "waerme_week": "sensor.wp_warme_woche", "waerme_month": "sensor.wp_warme_monat", "waerme_year": "sensor.wp_warme_jahr",
    "strom_week": "sensor.wp_strom_woche", "strom_month": "sensor.wp_strom_monat", "strom_year": "sensor.wp_strom_jahr",
}
STARTS_ENTITY = "sensor.wp_kompressor_starts_gesamt"
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Liefert das Schema-Bild für das Dashboard unter /avarma_static/schema.svg aus."""
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL, os.path.join(os.path.dirname(__file__), "www"), True)]
    )
    integration = await async_get_integration(hass, DOMAIN)

    async def _resource(_event=None) -> None:
        # Eigene Karte für den Display-Nachbau (ersetzt card-mod) als Lovelace-Ressource
        from .dashboard import async_ensure_resource

        if not await async_ensure_resource(hass, str(integration.version), STATIC_URL):
            frontend.add_extra_js_url(hass, f"{STATIC_URL}/avarma-cards.js?v={integration.version}")

    if hass.state is CoreState.running:
        hass.async_create_task(_resource())
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _resource)
    return True


async def _old_package_active(hass: HomeAssistant) -> bool:
    from homeassistant import config as conf_util

    try:
        conf = await conf_util.async_hass_config_yaml(hass)
    except Exception:  # noqa: BLE001
        return False
    for hub in conf.get("modbus") or []:
        for s in hub.get("sensors") or []:
            if str(s.get("unique_id", "")).startswith("avarma_"):
                return True
    return False


@callback
def _migrate_registry(hass: HomeAssistant) -> int:
    """Entfernt verwaiste Einträge der früheren YAML-Version, damit die Entity-IDs frei werden."""
    reg = er.async_get(hass)
    n = 0
    for ent in list(reg.entities.values()):
        uid = str(ent.unique_id)
        if (ent.platform in OLD_PLATFORMS and uid.startswith("avarma_")) or ent.entity_id in OLD_HELPERS:
            reg.async_remove(ent.entity_id)
            n += 1
    return n


def _grid_backfill(hass: HomeAssistant, strom_id: str, grid_id: str, until: float,
                   batt_id: str | None = None) -> list[tuple[float, float, float, float]]:
    """Netz- und Akkuanteil des WP-Stroms rückwirkend aus den Statistiken (5-Minuten-Werte, davor Stundenwerte).

    Liefert (Zeitpunkt, WP-Strom kWh, davon Netz kWh, davon Akku kWh) je Zeitabschnitt seit Jahresbeginn.
    Mittelwerte glätten Laden/Entladen innerhalb eines Abschnitts – rückwirkend nur eine Näherung.
    """
    from datetime import datetime, timedelta

    from homeassistant.components.recorder.statistics import statistics_during_period

    start = dt_util.as_utc(dt_util.start_of_local_day().replace(month=1, day=1))
    end = datetime.fromtimestamp(until, dt_util.UTC)
    out: list[tuple[float, float, float]] = []
    short_from = None
    for period, step in (("5minute", 300), ("hour", 3600)):
        frm = start if period == "5minute" else start
        to = end if period == "5minute" else short_from or end
        st = statistics_during_period(hass, frm, to, {strom_id, grid_id} | ({batt_id} if batt_id else set()),
                                      period, None, {"mean", "sum"})
        e = {(r["start"] if isinstance(r["start"], float) else r["start"].timestamp()): r.get("sum")
             for r in st.get(strom_id, [])}
        g = {(r["start"] if isinstance(r["start"], float) else r["start"].timestamp()): r.get("mean")
             for r in st.get(grid_id, [])}
        bt = {(r["start"] if isinstance(r["start"], float) else r["start"].timestamp()): r.get("mean")
              for r in st.get(batt_id, [])} if batt_id else {}
        ks = sorted(k for k in e if e[k] is not None)
        if period == "5minute":
            short_from = datetime.fromtimestamp(ks[0], dt_util.UTC) if ks else None
        last = ks[0] if ks else None
        for a, b in zip(ks, ks[1:]):
            de = e[b] - e[a]
            if de <= 0:
                continue
            bins = [t for t in ks if last < t <= b][-12:] or [b]  # Schritt über die Zeit seit dem letzten verteilen
            part = de / len(bins)
            grid = batt = 0.0
            for t in bins:
                gp = min(part, max(g.get(t) or 0, 0) * step / 3_600_000)
                grid += gp
                batt += min(part - gp, max(-(bt.get(t) or 0), 0) * step / 3_600_000)
            out.append((b, de, grid, batt))
            last = b
        if period == "hour" and short_from is None:
            break
    return out


def _recorder_values(hass: HomeAssistant) -> tuple[dict, float | None]:
    from datetime import timedelta

    from homeassistant.components.recorder import history

    old: dict[str, float | None] = {}
    today = dt_util.now().date()
    for key, eid in OLD_VALUES.items():
        old[key] = None
        states = history.get_last_state_changes(hass, 30, eid).get(eid, [])
        for st in reversed(states):
            try:
                val = float(st.state)
            except (TypeError, ValueError):
                continue
            if key == "laufzeit_heute" and dt_util.as_local(st.last_updated).date() != today:
                break
            old[key] = val
            break
    ago = None
    point = dt_util.utcnow() - timedelta(hours=24)
    st = history.get_significant_states(
        hass, point, point + timedelta(minutes=1), [STARTS_ENTITY], include_start_time_state=True,
        significant_changes_only=False).get(STARTS_ENTITY)
    if st:
        try:
            ago = float(st[0].state)
        except (TypeError, ValueError, IndexError):
            ago = None
    return old, ago


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if await _old_package_active(hass):
        persistent_notification.async_create(
            hass,
            "Das alte YAML-Paket (packages/avarma.yaml) ist noch aktiv. Bitte die Datei entfernen und Home Assistant "
            "neu starten – sonst fragen zwei Programme gleichzeitig die Wärmepumpe ab und stören sich.",
            "Avarma-Integration nicht gestartet", "avarma_paket")
        raise ConfigEntryError("Altes YAML-Paket avarma.yaml ist noch aktiv")
    removed = _migrate_registry(hass)
    if removed:
        _LOGGER.info("%s Einträge der alten YAML-Version aus der Entitäten-Registry entfernt", removed)

    d = {**entry.data, **entry.options}
    client = AvarmaModbus(d[CONF_HOST], d[CONF_PORT], d[CONF_SLAVE], d[CONF_PROTOCOL])
    coord = AvarmaCoordinator(hass, entry, client, int(d.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN)))
    await coord.async_load_store()
    if not coord.acc and "recorder" in hass.config.components:
        try:
            from homeassistant.components.recorder import get_instance

            old, ago = await get_instance(hass).async_add_executor_job(_recorder_values, hass)
            await coord.async_init_from_recorder(old, ago)
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Übernahme alter Zählerstände nicht möglich: %s", err)
    await coord.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coord

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    g_init = "|".join(filter(None, (coord.grid_sensor, coord.battery_sensor, "gl2")))
    if coord.grid_sensor and coord.acc.get("g_init") != g_init and "recorder" in hass.config.components:
        import time as _time

        from homeassistant.components.recorder import get_instance

        strom_id = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_strom_heute")
        sensor_id, until = coord.grid_sensor, _time.time()
        for p in ("day", "week", "month", "year"):
            coord.acc.pop(f"g_{p}_key", None)
        coord.acc["g_init"] = g_init
        year = str(dt_util.now().year)  # Monatsanteile des laufenden Jahres werden neu berechnet
        coord.acc["gl"] = {k: v for k, v in (coord.acc.get("gl") or {}).items() if not k.startswith(year)}
        coord.acc["gd"] = {}
        batt_id = coord.battery_sensor

        async def _backfill() -> None:
            try:
                rows = await get_instance(hass).async_add_executor_job(_grid_backfill, hass, strom_id, sensor_id, until, batt_id)
            except Exception:  # noqa: BLE001
                _LOGGER.warning("Netzanteil konnte nicht rückwirkend berechnet werden", exc_info=True)
                return
            from datetime import datetime

            for ts, de, grid, batt in sorted(rows):
                coord.add_grid(dt_util.as_local(datetime.fromtimestamp(ts, dt_util.UTC)), de, grid, batt)
            coord._save()
            coord.async_update_listeners()
            _LOGGER.info("Netzanteil rückwirkend aus %s Abschnitten berechnet", len(rows))

        if strom_id:
            hass.async_create_task(_backfill())

    if d.get(CONF_CLOCK_SYNC, True):
        from .button import set_clock

        @callback
        def _clock(_now) -> None:
            hass.async_create_task(set_clock(coord))

        entry.async_on_unload(async_track_time_change(hass, _clock, hour=3, minute=17, second=0))
        from .button import clock_offset_minutes

        off = clock_offset_minutes(coord)
        if off is not None and abs(off) > 3:
            _LOGGER.info("Uhr der Wärmepumpe weicht um %.0f min ab – wird gestellt", off)
            hass.async_create_task(set_clock(coord))
    @callback
    def _dst_check(now) -> None:
        """Am Tag der Zeitumstellung daran erinnern, die Uhr am Display zu stellen."""
        from datetime import timedelta

        local = dt_util.as_local(now)
        if local.utcoffset() == dt_util.as_local(now - timedelta(days=1)).utcoffset():
            return
        art = "Sommerzeit (+1 h)" if local.utcoffset() > dt_util.as_local(now - timedelta(days=1)).utcoffset() else "Winterzeit (−1 h)"
        text = (f"Heute wurde auf {art} umgestellt. Die Wärmepumpe übernimmt die Uhrzeit nicht über Modbus – "
                "bitte die Uhr direkt am Display der Wärmepumpe stellen (Uhrzeit und Datum prüfen). "
                "Sonst beginnen die Tageszähler (Wärme/Strom/COP heute) zur falschen Zeit.")
        persistent_notification.async_create(hass, text, "Wärmepumpe: Zeitumstellung – Uhr am Display stellen", "avarma_dst")
        coord._notify("🕒 Wärmepumpe: Zeitumstellung", "Bitte die Uhr am Display der Wärmepumpe stellen.")

    entry.async_on_unload(async_track_time_change(hass, _dst_check, hour=9, minute=0, second=0))
    if d.get(CONF_DASHBOARD, True):
        from .dashboard import async_register_dashboard, async_remove_dashboard

        if async_register_dashboard(hass):
            entry.async_on_unload(lambda: async_remove_dashboard(hass))
    entry.async_on_unload(entry.add_update_listener(_reload))
    return True


async def _reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        coord: AvarmaCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coord.async_shutdown_store()
        await coord.client.close()
    return ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Beim Löschen der Integration die Lovelace-Ressource der Display-Karte wieder entfernen."""
    from homeassistant.components.lovelace.const import LOVELACE_DATA

    if hass.config_entries.async_entries(DOMAIN):
        return
    res = getattr(hass.data.get(LOVELACE_DATA), "resources", None)
    if res is None or not hasattr(res, "async_delete_item"):
        return
    try:
        await res.async_get_info()
        for item in list(res.async_items()):
            if str(item.get("url", "")).startswith(f"{STATIC_URL}/avarma-cards.js"):
                await res.async_delete_item(item["id"])
    except Exception:  # noqa: BLE001
        _LOGGER.debug("Ressource konnte nicht entfernt werden", exc_info=True)

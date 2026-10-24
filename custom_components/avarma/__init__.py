"""Avarma (Hofman) R290 Wärmepumpe über Modbus RS485."""

from __future__ import annotations

import logging
import os

from homeassistant.components import persistent_notification
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers import config_validation as cv, entity_registry as er
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CLOCK_SYNC, CONF_PROTOCOL, CONF_SCAN_INTERVAL, CONF_SLAVE, DEFAULT_SCAN, DOMAIN, PLATFORMS, STATIC_URL,
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

    if d.get(CONF_CLOCK_SYNC, True):
        from .button import set_clock

        @callback
        def _clock(_now) -> None:
            hass.async_create_task(set_clock(coord))

        entry.async_on_unload(async_track_time_change(hass, _clock, hour=3, minute=17, second=0))
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

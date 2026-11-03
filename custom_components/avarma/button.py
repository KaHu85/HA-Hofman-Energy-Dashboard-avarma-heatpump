"""Fehler quittieren und Uhr stellen."""

from __future__ import annotations

import asyncio
import logging

from homeassistant.components import logbook
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN, REG_CLOCK_DATE, REG_CLOCK_TIME, REG_FAULT_RESET
from .entity import AvarmaEntity
from .modbus import ModbusError

_LOGGER = logging.getLogger(__name__)


async def set_clock(c) -> None:
    """Uhr der Wärmepumpe auf die Home-Assistant-Zeit stellen.

    Datum und Zeit werden gemeinsam mit Funktion 0x10 geschrieben. Einzelnes Schreiben
    mit 0x06 wurde von der Steuerung bestätigt, aber offenbar nicht übernommen.
    """
    now = dt_util.now()
    try:
        await c.client.write_registers(REG_CLOCK_DATE, [now.month * 256 + now.day, now.hour * 256 + now.minute])
    except ModbusError:
        # Fallback für Steuerungen ohne 0x10
        await c.client.write_register(REG_CLOCK_DATE, now.month * 256 + now.day)
        await c.client.write_register(REG_CLOCK_TIME, now.hour * 256 + now.minute)
    await asyncio.sleep(1)
    vals = await c.client.read_holding(REG_CLOCK_DATE, 2)
    c.regs[REG_CLOCK_DATE], c.regs[REG_CLOCK_TIME] = vals
    c.async_update_listeners()
    _LOGGER.info("Uhr der Wärmepumpe gestellt auf %s (gelesen: %02d.%02d. %02d:%02d)", now.strftime("%d.%m. %H:%M"),
                 vals[0] % 256, vals[0] // 256, vals[1] // 256, vals[1] % 256)


def clock_offset_minutes(c) -> float | None:
    """Abweichung der WP-Uhr von der HA-Zeit in Minuten (None, wenn unbekannt)."""
    d, t = c.u(REG_CLOCK_DATE), c.u(REG_CLOCK_TIME)
    if not d or t is None:
        return None
    now = dt_util.now()
    try:
        wp = now.replace(month=d // 256, day=d % 256, hour=t // 256, minute=t % 256, second=0, microsecond=0)
    except ValueError:
        return None
    return (wp - now).total_seconds() / 60


class FaultReset(AvarmaEntity, ButtonEntity):
    _attr_icon = "mdi:alert-remove"

    async def async_press(self) -> None:
        await self.coordinator.async_write(REG_FAULT_RESET, 1, reread=(4390, 7))
        logbook.async_log_entry(self.hass, "Wärmepumpe", "Fehler quittiert", DOMAIN, self.entity_id)


class ClockSet(AvarmaEntity, ButtonEntity):
    _attr_icon = "mdi:clock-edit"

    async def async_press(self) -> None:
        await set_clock(self.coordinator)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    c = hass.data[DOMAIN][entry.entry_id]
    add([FaultReset(c, "fehler_reset", "Fehler quittieren"), ClockSet(c, "uhr_stellen", "Uhr stellen")])

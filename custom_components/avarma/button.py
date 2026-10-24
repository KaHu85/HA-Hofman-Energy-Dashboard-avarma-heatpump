"""Fehler quittieren und Uhr stellen."""

from __future__ import annotations

from homeassistant.components import logbook
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN, REG_CLOCK_DATE, REG_CLOCK_TIME, REG_FAULT_RESET
from .entity import AvarmaEntity


async def set_clock(c) -> None:
    now = dt_util.now()
    await c.client.write_register(REG_CLOCK_DATE, now.month * 256 + now.day)
    await c.async_write(REG_CLOCK_TIME, now.hour * 256 + now.minute, reread=(REG_CLOCK_DATE, 2))


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

"""Parameter P02..P150 / P201..P208 als Zahlen – Schreiben nur nach Code-Freigabe."""

from __future__ import annotations

from homeassistant.components import logbook
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .einsparung import HAUS, PRICES
from .entity import AvarmaEntity
from .params import P, addr


class ParamNumber(AvarmaEntity, NumberEntity):
    _attr_mode = NumberMode.BOX

    def __init__(self, c, p, scale, unit, mn, mx, lvl, name, desc) -> None:
        super().__init__(c, f"set_p{p:03d}", f"Set P{p:02d} {name}")
        self.p, self.scale, self.lvl, self.pname, self.reg = p, scale, lvl, name, addr(p)
        self._attr_native_min_value, self._attr_native_max_value, self._attr_native_step = mn, mx, scale
        self._attr_native_unit_of_measurement = unit
        self._attr_extra_state_attributes = {"parameter": f"P{p:02d}", "stufe": "Techniker" if lvl == "T" else "Benutzer",
                                             "erklaerung": desc}

    @property
    def native_value(self):
        v = self.coordinator.s(self.reg)
        return None if v is None else round(v * self.scale, 2)

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.check_unlocked(self.lvl, f"P{self.p:02d}")
        raw = int(round(value / self.scale))
        await self.coordinator.async_write(self.reg, raw)
        logbook.async_log_entry(self.hass, "Wärmepumpe", f"P{self.p:02d} {self.pname} auf {value:g} gesetzt",
                                DOMAIN, self.entity_id)


class PriceNumber(AvarmaEntity, NumberEntity):
    """Preise und Fixkosten für die Einsparungsseite (nur in Home Assistant gespeichert)."""

    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:cash-edit"

    def __init__(self, c, key, name, unit, mx, step, mn=0, prefix="preis_") -> None:
        super().__init__(c, f"{prefix}{key}", name)
        self.pkey = key
        self.entity_id = f"number.wp_{prefix}{key}"
        self._attr_native_min_value, self._attr_native_max_value, self._attr_native_step = mn, mx, step
        self._attr_native_unit_of_measurement = unit

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self):
        return self.coordinator.prices.get(self.pkey)

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.set_price(self.pkey, value)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    c = hass.data[DOMAIN][entry.entry_id]
    add([ParamNumber(c, p, sc, u, mn, mx, lvl, name, desc)
         for p, sc, u, mn, mx, lvl, grp, name, desc in P if lvl != "X"]
        + [PriceNumber(c, k, n, u, mx, st) for k, n, u, mx, st, _d in PRICES]
        + [PriceNumber(c, k, n, u, mx, st, mn, prefix="") for k, n, u, mn, mx, st, _d in HAUS])

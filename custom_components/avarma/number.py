"""Parameter P02..P150 / P201..P208 als Zahlen – Schreiben nur nach Code-Freigabe."""

from __future__ import annotations

from homeassistant.components import logbook
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from homeassistant.util import slugify

from .const import DOMAIN
from .einsparung import HAUS, PRICES
from .entity import AvarmaEntity
from .params import P, addr, id_name


class ParamNumber(AvarmaEntity, NumberEntity):
    _attr_mode = NumberMode.BOX

    def __init__(self, c, p, scale, unit, mn, mx, lvl, name, desc) -> None:
        super().__init__(c, f"set_p{p:03d}", f"Set P{p:02d} {name}")
        self.pin(f"number.{slugify(f'WP Set P{p:02d} {id_name(p, name)}')}")  # Entity-ID bleibt beim früheren Namen
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
        self.pin(f"number.wp_{prefix}{key}")
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


class RegelSollNumber(AvarmaEntity, NumberEntity):
    """Einstellungen der eigenen Regelung (nur in Home Assistant, nicht in der WP): Raum-Soll bzw. max. Verschiebung."""

    _attr_mode = NumberMode.BOX

    def __init__(self, c, key, name, field, default, mn, mx, step, unit, icon) -> None:
        super().__init__(c, key, name)
        self.field, self.default = field, default
        self._attr_native_min_value, self._attr_native_max_value, self._attr_native_step = mn, mx, step
        self._attr_native_unit_of_measurement, self._attr_icon = unit, icon

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self):
        return self.coordinator.rg.get(self.field, self.default)

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.rg[self.field] = value
        self.coordinator._store.async_delay_save(lambda: self.coordinator.acc, 5)
        self.async_write_ha_state()


class RegelFeinNumber(AvarmaEntity, NumberEntity):
    """Feineinstellung der Raum-Nachführung (in Home Assistant gespeichert). Ändern → Profil „Benutzerdefiniert“."""

    _attr_mode = NumberMode.BOX

    def __init__(self, c, key, name, unit, mn, mx, step) -> None:
        super().__init__(c, f"rg_{key}", f"Regelung {name}")
        self.key = key
        self.pin(f"number.wp_rg_{key}")
        self._attr_native_min_value, self._attr_native_max_value, self._attr_native_step = mn, mx, step
        self._attr_native_unit_of_measurement, self._attr_icon = unit, "mdi:tune-vertical"
        self._attr_extra_state_attributes = {"min": mn, "max": mx}

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self):
        return self.coordinator.rg_fein.get(self.key)

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_regelung_fein(self.key, value)


def _rg_fein_numbers(c) -> list:
    from .regelung import FEIN

    return [RegelFeinNumber(c, k, name, unit, mn, mx, st) for k, (name, unit, mn, mx, st, *_p) in FEIN.items()]


class UebergangNumber(AvarmaEntity, NumberEntity):
    """Einstellungen der Übergangszeit (in Home Assistant gespeichert). Ändern nur mit hinterlegtem Techniker-Code."""

    _attr_mode = NumberMode.BOX

    def __init__(self, c, field, name, mn, mx, step, unit, icon) -> None:
        super().__init__(c, f"uz_{field}", name)
        self.field = field
        self.pin(f"number.wp_uz_{field}")
        self._attr_native_min_value, self._attr_native_max_value, self._attr_native_step = mn, mx, step
        self._attr_native_unit_of_measurement, self._attr_icon = unit, icon
        self._attr_extra_state_attributes = {"min": mn, "max": mx}

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self):
        uz = self.coordinator.uz
        if self.field.startswith("normal_"):
            return uz["normal"].get(self.field.removeprefix("normal_"))
        return uz.get(self.field)

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_uebergang_wert(self.field, value)


def _uz_numbers(c) -> list:
    from .uebergang import STUFE_HZ, STUFE_TEMP, STUFEN, TEMP, WERTE

    ents = [UebergangNumber(c, "ab", "Übergangszeit ab Außentemperatur", *TEMP["ab"][1:], "°C", "mdi:thermometer-chevron-up"),
            UebergangNumber(c, "hyst", "Übergangszeit Hysterese", *TEMP["hyst"][1:], "K", "mdi:arrow-expand-vertical")]
    for i, (k, _ab, _hz) in enumerate(STUFEN, 1):
        ents.append(UebergangNumber(c, f"{k}_ab", f"Kompressor-Stufe {i} ab", *STUFE_TEMP, "°C", "mdi:thermometer"))
        ents.append(UebergangNumber(c, f"{k}_hz", f"Kompressor-Stufe {i} Höchstfrequenz", *STUFE_HZ, "Hz", "mdi:sine-wave"))
    ents.append(UebergangNumber(c, "kalt_hz", "Kompressor unter der kältesten Stufe", *STUFE_HZ, "Hz", "mdi:snowflake"))
    for key, p, name, unit, f, _g, mn, mx in WERTE:
        ents.append(UebergangNumber(c, key, f"Übergangszeit P{p} {name}", mn, mx, f, unit, "mdi:weather-partly-cloudy"))
        pmin, pmax = next((r[3] * f, r[4] * f) for r in P if r[0] == p)
        ents.append(UebergangNumber(c, f"normal_{key}", f"Normalwert P{p} {name}", pmin, pmax, f, unit, "mdi:home-thermometer-outline"))
    return ents


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    c = hass.data[DOMAIN][entry.entry_id]
    add([ParamNumber(c, p, sc, u, mn, mx, lvl, name, desc)
         for p, sc, u, mn, mx, lvl, grp, name, desc in P if lvl != "X"]
        + [PriceNumber(c, k, n, u, mx, st) for k, n, u, mx, st, _d in PRICES]
        + [PriceNumber(c, k, n, u, mx, st, mn, prefix="") for k, n, u, mn, mx, st, _d in HAUS]
        + [RegelSollNumber(c, "regelung_raum_soll", "Regelung Raum-Soll", "soll", 22.0, 15, 26, 0.1, "°C", "mdi:home-thermometer"),
           RegelSollNumber(c, "regelung_max", "Regelung max. Verschiebung", "max", 5.0, 2, 10, 0.5, "K", "mdi:arrow-expand-vertical")]
        + _rg_fein_numbers(c)
        + _uz_numbers(c))

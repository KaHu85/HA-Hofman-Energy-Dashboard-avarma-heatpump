"""Betriebsart."""

from __future__ import annotations

from homeassistant.components import logbook
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MODES, REG_MODE
from .entity import AvarmaEntity


class ModeSelect(AvarmaEntity, SelectEntity):
    _attr_icon = "mdi:hvac"
    _attr_options = list(MODES.values())

    @property
    def current_option(self):
        return MODES.get(self.coordinator.u(REG_MODE))

    async def async_select_option(self, option: str) -> None:
        self.coordinator.check_unlocked("U", "Die Betriebsart")
        value = next(k for k, v in MODES.items() if v == option)
        await self.coordinator.async_write(REG_MODE, value)
        logbook.async_log_entry(self.hass, "Wärmepumpe", f"Betriebsart auf {option} gesetzt", DOMAIN, self.entity_id)


class UebergangFuehlerSelect(AvarmaEntity, SelectEntity):
    """Welcher Außenfühler für die Übergangszeit zählt."""

    _attr_icon = "mdi:thermometer"

    def __init__(self, c, key, name) -> None:
        from .uebergang import FUEHLER

        super().__init__(c, key, name)
        self.pin("select.wp_uz_aussenfuehler")
        self._attr_options = list(FUEHLER.values())

    @property
    def available(self) -> bool:
        return True

    @property
    def current_option(self):
        from .uebergang import FUEHLER

        return FUEHLER.get(self.coordinator.uz.get("fuehler"))

    async def async_select_option(self, option: str) -> None:
        from .uebergang import FUEHLER

        await self.coordinator.async_uebergang_fuehler(next(k for k, v in FUEHLER.items() if v == option))


class RegelProfilSelect(AvarmaEntity, SelectEntity):
    """Gebäude / Heizsystem für die Raum-Nachführung der eigenen Regelung."""

    _attr_icon = "mdi:home-thermometer-outline"

    def __init__(self, c, key, name) -> None:
        from .regelung import PROFILE

        super().__init__(c, key, name)
        self.pin("select.wp_regelung_profil")
        self._attr_options = list(PROFILE.values())

    @property
    def available(self) -> bool:
        return True

    @property
    def current_option(self):
        from .regelung import PROFILE

        self.coordinator.rg_fein  # legt Profil/Feinwerte bei Bedarf an
        return PROFILE.get(self.coordinator.rg.get("profil", "hk"))

    async def async_select_option(self, option: str) -> None:
        from .regelung import PROFILE

        await self.coordinator.async_regelung_profil(next(k for k, v in PROFILE.items() if v == option))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    c = hass.data[DOMAIN][entry.entry_id]
    add([ModeSelect(c, "betriebsart", "Betriebsart"), UebergangFuehlerSelect(c, "uz_aussenfuehler", "Übergangszeit Außenfühler"),
         RegelProfilSelect(c, "regelung_profil", "Regelung Gebäude / Heizsystem")])

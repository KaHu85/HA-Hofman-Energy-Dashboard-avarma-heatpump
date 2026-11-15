"""Gemeinsame Basis der Entitäten."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import DOMAIN, MANUFACTURER
from .coordinator import AvarmaCoordinator


def _domain(obj) -> str:
    """Plattform der Entität (sensor, number, …) aus der Home-Assistant-Basisklasse."""
    for cls in type(obj).__mro__:
        mod = cls.__module__.split(".")
        if len(mod) >= 3 and mod[:2] == ["homeassistant", "components"] and cls.__name__.endswith("Entity"):
            return mod[2]
    return "sensor"


class AvarmaEntity(CoordinatorEntity[AvarmaCoordinator]):
    """Entitätsname = 'WP <Name>' (Gerätename 'WP').

    Die Entity-ID wird fest als `<plattform>.wp_<name>` vorgegeben – unabhängig von Bereich oder Gerätenamen –,
    weil das mitgelieferte Dashboard genau diese IDs verwendet (wie in der früheren YAML-Version).
    """

    _attr_has_entity_name = True

    def __init__(self, coordinator: AvarmaCoordinator, key: str, name: str) -> None:
        super().__init__(coordinator)
        self.key = key
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self.pin(f"{_domain(self)}.{slugify('WP ' + name)}")
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name="WP",
            manufacturer=MANUFACTURER,
            model="R290 Monoblock (Modbus)",
            sw_version=str(coordinator.u(4615) or ""),
            configuration_url="https://github.com/KaHu85/HA-Hofman-Energy-Dashboard-avarma-heatpump",
        )

    def pin(self, entity_id: str) -> None:
        """Gewünschte Entity-ID festlegen; abweichende IDs korrigiert die Integration beim Start."""
        self.entity_id = entity_id
        self.coordinator.want_ids[self._attr_unique_id] = entity_id

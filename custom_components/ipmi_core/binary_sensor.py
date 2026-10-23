"""The actual physical chassis power state, not the desired state."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import IpmiCoreCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([
        IpmiCorePowerSensor(entry),
        IpmiCoreCommunicationSensor(entry),
        IpmiCoreHardwareWarningSensor(entry),
    ])


class IpmiCorePowerSensor(CoordinatorEntity[IpmiCoreCoordinator], BinarySensorEntity):
    """True means ON; failed polling reports unavailable, never OFF."""

    _attr_has_entity_name = True
    _attr_translation_key = "power"
    _attr_device_class = BinarySensorDeviceClass.POWER

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry.runtime_data.coordinator)
        self._attr_unique_id = f"{entry.entry_id}_power"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="IPMI",
        )

    @property
    def is_on(self) -> bool:
        return self.coordinator.data


class IpmiCoreCommunicationSensor(CoordinatorEntity[IpmiCoreCoordinator], BinarySensorEntity):
    """Report whether the *last IPMI state read* succeeded.

    This is distinct from chassis power: the BMC can answer with chassis OFF.
    A failed read makes chassis power unavailable but leaves this diagnostic
    sensor available so it can explicitly report a communication problem.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "bmc_communication"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry.runtime_data.coordinator)
        self._attr_unique_id = f"{entry.entry_id}_bmc_communication"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="IPMI",
        )

    @property
    def available(self) -> bool:
        """Keep diagnosis visible when the normal power entity is unavailable."""
        return True

    @property
    def is_on(self) -> bool:
        """True only when the last IPMI power query completed successfully."""
        return self.coordinator.last_update_success


class IpmiCoreHardwareWarningSensor(CoordinatorEntity, BinarySensorEntity):
    """Expose BMC SDR health warnings without assuming missing = healthy."""

    _attr_has_entity_name = True
    _attr_translation_key = "hardware_warnings"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry.runtime_data.telemetry)
        self._attr_unique_id = f"{entry.entry_id}_hardware_warnings"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="IPMI",
        )

    @property
    def available(self) -> bool:
        # An empty set of SDR readings is common while chassis is OFF.
        data = self.coordinator.data
        return (
            self.coordinator.last_update_success
            and data is not None
            and bool(data.sensors or data.warnings)
        )

    @property
    def is_on(self) -> bool:
        data = self.coordinator.data
        return bool(data and data.warnings)

    @property
    def extra_state_attributes(self) -> dict[str, list[str]]:
        data = self.coordinator.data
        return {"affected_sensors": list(data.warnings) if data else []}

"""Guarded chassis power-on and graceful ACPI OS shutdown controls."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .client import IpmiCoreError
from .const import DOMAIN
from .coordinator import IpmiCoreCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([IpmiCorePowerOnButton(entry), IpmiCoreGracefulShutdownButton(entry)])


class IpmiCorePowerOnButton(CoordinatorEntity[IpmiCoreCoordinator], ButtonEntity):
    """Request power on only after verifying that the BMC is reachable."""

    _attr_has_entity_name = True
    _attr_translation_key = "power_on"
    _attr_icon = "mdi:power-on"

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry.runtime_data.coordinator)
        self._attr_unique_id = f"{entry.entry_id}_power_on"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="IPMI",
        )

    async def async_press(self) -> None:
        if not self.coordinator.last_update_success:
            raise HomeAssistantError("IPMI power state is unavailable")
        try:
            await self.coordinator.async_power_on()
        except (TimeoutError, IpmiCoreError) as err:
            raise HomeAssistantError("IPMI power-on command failed") from err


class IpmiCoreGracefulShutdownButton(CoordinatorEntity[IpmiCoreCoordinator], ButtonEntity):
    """OS-controlled ACPI shutdown; no hard power-off or automatic scheduling."""

    _attr_has_entity_name = True
    _attr_translation_key = "graceful_shutdown"
    _attr_icon = "mdi:power-sleep"

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry.runtime_data.coordinator)
        self._attr_unique_id = f"{entry.entry_id}_graceful_shutdown"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="IPMI",
        )

    async def async_press(self) -> None:
        if not self.coordinator.last_update_success:
            raise HomeAssistantError("IPMI power state is unavailable")
        try:
            await self.coordinator.async_graceful_shutdown()
        except (TimeoutError, IpmiCoreError) as err:
            raise HomeAssistantError("Graceful ACPI shutdown request failed") from err

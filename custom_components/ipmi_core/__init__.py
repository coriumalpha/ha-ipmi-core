"""IPMI Core: bounded BMC power control and read-only SDR telemetry."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant

from .client import IpmiCoreClient
from .coordinator import IpmiCoreCoordinator
from .telemetry_coordinator import IpmiCoreTelemetryCoordinator

PLATFORMS = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.SENSOR]


@dataclass(slots=True)
class IpmiCoreRuntime:
    """Objects owned by one configured BMC."""

    client: IpmiCoreClient
    coordinator: IpmiCoreCoordinator
    telemetry: IpmiCoreTelemetryCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one configured BMC and its entities."""
    client = IpmiCoreClient(
        host=entry.data[CONF_HOST],
        port=int(entry.data[CONF_PORT]),
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
    )
    coordinator = IpmiCoreCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    telemetry = IpmiCoreTelemetryCoordinator(
        hass, entry, client, coordinator._async_operation
    )
    entry.runtime_data = IpmiCoreRuntime(client, coordinator, telemetry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # Telemetry is noncritical: startup, power state and controls cannot be
    # made unavailable merely because SDR enumeration fails or chassis is OFF.
    entry.async_create_background_task(
        hass, telemetry.async_refresh(), "ipmi_core_initial_telemetry", eager_start=False
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the entities for this BMC."""
    await entry.runtime_data.telemetry.async_shutdown()
    await entry.runtime_data.coordinator.async_shutdown()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

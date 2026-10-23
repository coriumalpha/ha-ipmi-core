"""Discover and expose supported numeric BMC SDR sensors without hardcoding names."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .telemetry_coordinator import IpmiCoreTelemetryCoordinator
from .telemetry_models import SensorSample


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Register newly discovered sensors as telemetry becomes available.

    Home Assistant may start while the chassis is OFF and there may be no
    numeric readings. Later updates can safely discover and add entities.
    """
    coordinator = entry.runtime_data.telemetry
    registered: set[str] = set()

    @callback
    def async_sync_entities() -> None:
        if not coordinator.last_update_success or coordinator.data is None:
            return
        newly_found = []
        for key, sample in coordinator.data.sensors.items():
            if key in registered:
                continue
            registered.add(key)
            newly_found.append(IpmiCoreMetricSensor(entry, key, sample))
        if newly_found:
            async_add_entities(newly_found)

    entry.async_on_unload(coordinator.async_add_listener(async_sync_entities))
    async_sync_entities()


class IpmiCoreMetricSensor(CoordinatorEntity[IpmiCoreTelemetryCoordinator], SensorEntity):
    """Numerical readout with strict units, no fabricated zero on missing data."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, entry: ConfigEntry, key: str, sample: SensorSample) -> None:
        super().__init__(entry.runtime_data.telemetry)
        self._key = key
        self._attr_name = sample.name
        self._attr_unique_id = f"{entry.entry_id}_sdr_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="IPMI",
        )
        self._attr_native_unit_of_measurement = sample.unit
        if sample.unit == "°C":
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_suggested_display_precision = 1
        elif sample.unit == "V":
            self._attr_device_class = SensorDeviceClass.VOLTAGE
            self._attr_suggested_display_precision = 3
        elif sample.unit == "A":
            self._attr_device_class = SensorDeviceClass.CURRENT
            self._attr_suggested_display_precision = 3
        elif sample.unit == "W":
            self._attr_device_class = SensorDeviceClass.POWER
            self._attr_suggested_display_precision = 1
        elif sample.unit == "RPM":
            # RPM is not a SensorDeviceClass in Home Assistant 2026.9.
            self._attr_suggested_display_precision = 0

    def _reading(self) -> SensorSample | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.sensors.get(self._key)

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self._reading() is not None

    @property
    def native_value(self) -> float | None:
        sample = self._reading()
        return sample.value if sample else None

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        sample = self._reading()
        if sample is None:
            return None
        # Preserve BMC warnings even when a value remains numerically valid.
        health = sample.health
        severity = "failed" if health & 4 else (
            "critical" if health & 2 else "warning" if health & 1 else "ok"
        )
        return {"bmc_health": severity}

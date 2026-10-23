"""Strictly typed, size-bounded BMC telemetry over the local worker protocol.

This module does not import Home Assistant or pyghmi and is safe to test offline.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math

# Each unit is an explicit contract with Home Assistant, not a guess from names.
SUPPORTED_UNITS = frozenset({"°C", "RPM", "V", "A", "W"})
MAX_SENSORS = 96
MAX_NAME_LENGTH = 80


class TelemetryProtocolError(ValueError):
    """Unsafe or invalid worker response (never include raw payload in logs)."""


@dataclass(frozen=True, slots=True)
class SensorSample:
    """One numeric measurement confirmed by the BMC."""

    key: str
    name: str
    unit: str
    value: float
    health: int


@dataclass(frozen=True, slots=True)
class TelemetrySnapshot:
    """Atomic hardware telemetry. Missing sensors become unavailable."""

    sensors: dict[str, SensorSample]
    warnings: tuple[str, ...]


def valid_name(name: object) -> bool:
    """Limit sensor names for UI/log hygiene; no host-specific exceptions."""
    return (
        isinstance(name, str)
        and 1 <= len(name) <= MAX_NAME_LENGTH
        and name == name.strip()
        and all(character.isprintable() for character in name)
    )


def sensor_key(name: str, unit: str, occurrence: int) -> str:
    """Deterministic BMC-local key; HA config entry supplies server identity."""
    raw = f"{name.casefold()}\0{unit}\0{occurrence}".encode("utf-8")
    return hashlib.blake2s(raw, digest_size=10).hexdigest()


def parse_telemetry_response(response: dict) -> TelemetrySnapshot:
    """Validate bounded child output, dropping malformed individual readings."""
    readings = response.get("sensors")
    warnings = response.get("warnings")
    if not isinstance(readings, list) or not isinstance(warnings, list):
        raise TelemetryProtocolError("Invalid telemetry data shape")
    if len(readings) > MAX_SENSORS or len(warnings) > MAX_SENSORS:
        raise TelemetryProtocolError("Too many telemetry entries")
    used: dict[tuple[str, str], int] = {}
    sensors: dict[str, SensorSample] = {}
    for item in readings:
        if not isinstance(item, dict):
            continue
        name, unit, value, health = (item.get(k) for k in ("name", "unit", "value", "health"))
        if not valid_name(name) or unit not in SUPPORTED_UNITS:
            continue
        if type(value) not in (int, float) or not math.isfinite(value):
            continue
        if type(health) is not int or not 0 <= health <= 7:
            continue
        # Make duplicate names distinct and keep stable keys when order is stable.
        identity = (name.casefold(), unit)
        used[identity] = used.get(identity, 0) + 1
        key = sensor_key(name, unit, used[identity])
        sensors[key] = SensorSample(key, name, unit, round(float(value), 3), health)
    alerts: list[str] = []
    for item in warnings:
        if not isinstance(item, dict):
            continue
        name, health = item.get("name"), item.get("health")
        if valid_name(name) and type(health) is int and 1 <= health <= 7:
            if name not in alerts:
                alerts.append(name)
    return TelemetrySnapshot(sensors, tuple(alerts))

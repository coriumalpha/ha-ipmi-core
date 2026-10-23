"""Short-lived pyghmi worker; spawned by client.py, not a Home Assistant entry.

The allowlist is status, guarded power_on, ACPI graceful_shutdown and read-only telemetry. Credentials come from the
parent through standard input and must never be echoed or logged.
"""

from __future__ import annotations

import json
import math
import sys


def perform(request: dict) -> dict:
    """Make a verified state query or one strictly allowlisted chassis request."""
    action = request.get("action")
    if action not in ("status", "power_on", "graceful_shutdown", "telemetry"):
        raise ValueError("Unsupported operation")
    from pyghmi.ipmi import command

    ipmi = None
    try:
        ipmi = command.Command(
            bmc=request["host"],
            port=request["port"],
            userid=request["username"],
            password=request["password"],
            privlevel=request["privlevel"],
            keepalive=False,
        )
        if action == "telemetry":
            # Do not query chassis power, and never invoke any writable command.
            # A fresh subprocess bounds SDR initialization and data reads.
            readings = []
            warnings = []
            for reading in ipmi.get_sensor_data():
                if len(readings) + len(warnings) >= 192:
                    break
                name = getattr(reading, "name", None)
                if not isinstance(name, str):
                    continue
                name = name.strip()
                if not (1 <= len(name) <= 80 and name.isprintable()):
                    continue
                if getattr(reading, "unavailable", 0):
                    continue
                health = getattr(reading, "health", 0)
                if type(health) is not int or not 0 <= health <= 7:
                    try:
                        health = int(health)
                    except (ValueError, TypeError):
                        health = 0
                if not 0 <= health <= 7:
                    health = 0
                if health and len(warnings) < 96:
                    warnings.append({"name": name, "health": health})
                unit = getattr(reading, "units", "")
                value = getattr(reading, "value", None)
                if unit not in ("°C", "RPM", "V", "A", "W"):
                    continue
                if type(value) not in (int, float) or not math.isfinite(value):
                    continue
                if len(readings) < 96:
                    readings.append({"name": name, "unit": unit,
                                     "value": round(float(value), 3), "health": health})
            return {"ok": True, "sensors": readings, "warnings": warnings}
        result = ipmi.get_power()
        state = result.get("powerstate") if isinstance(result, dict) else None
        if state not in ("on", "off"):
            raise ValueError("Invalid power state")
        if action == "status":
            return {"ok": True, "powerstate": state}
        if action == "graceful_shutdown":
            if state == "off":
                return {"ok": True, "sent": False, "powerstate": "off"}
            # ACPI soft shutdown; never hard-off, reset or cycle.
            result = ipmi.set_power("shutdown", wait=False)
            if not isinstance(result, dict) or result.get("pendingpowerstate") != "shutdown":
                raise ValueError("ACPI shutdown request not accepted")
            return {"ok": True, "sent": True, "powerstate": "on"}
        if state == "on":
            return {"ok": True, "sent": False, "powerstate": "on"}
        # Explicit allowlist: never expose OFF, reset, cycle or raw commands.
        command_result = ipmi.set_power("on", wait=False)
        if isinstance(command_result, dict) and (
            command_result.get("error") or command_result.get("code")
        ):
            raise ValueError("Power-on request not accepted")
        return {"ok": True, "sent": True, "powerstate": "off"}
    finally:
        if ipmi is not None:
            try:
                ipmi.ipmi_session.logout()
            except Exception:
                # Process exit discards all pyghmi global state. Avoid leaking
                # potentially sensitive backend errors to parent stdout.
                pass


def main() -> int:
    try:
        request = json.load(sys.stdin)
        if not isinstance(request, dict):
            raise ValueError("Invalid request")
        response = perform(request)
    except Exception:
        # Never emit exception messages: may contain connection or account data.
        print('{"ok":false}')
        return 1
    print(json.dumps(response, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

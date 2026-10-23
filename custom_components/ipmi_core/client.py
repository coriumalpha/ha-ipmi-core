"""Run IPMI operations in bounded subprocesses, never in HA's Python process.

pyghmi may block indefinitely in Session.wait_for_rsp() on old BMCs. An
asyncio timeout cannot stop a blocked executor thread; a child *process* can
be terminated and reaped after a deadline. Each operation has isolated session
state to avoid pyghmi 1.6.19's reuse-after-logout bug.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys
from threading import Lock

from .const import OPERATOR_PRIVILEGE, WORKER_TIMEOUT
from .telemetry_models import TelemetrySnapshot, TelemetryProtocolError, parse_telemetry_response


class IpmiCoreError(Exception):
    """An IPMI operation failed; never interpret failure as OFF."""


@dataclass(frozen=True, slots=True)
class PowerOnResult:
    """Physical power state observed immediately before an optional ON."""

    sent: bool
    observed_on: bool


@dataclass(frozen=True, slots=True)
class GracefulShutdownResult:
    """Verified pre-request physical state and ACPI request acknowledgement."""

    sent: bool
    observed_off: bool


class IpmiCoreClient:
    """Minimal client exposing status and guarded power-on only."""

    def __init__(self, host: str, port: int, username: str, password: str) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._lock = Lock()

    def _invoke(self, action: str) -> dict:
        """One bounded child per operation, serializing calls per BMC entry.

        Secrets are sent via stdin, never command-line args, env vars or logs.
        subprocess.run kills/reaps the child on timeout; no shell is invoked.
        """
        request = json.dumps(
            {
                "action": action,
                "host": self._host,
                "port": self._port,
                "username": self._username,
                "password": self._password,
                "privlevel": OPERATOR_PRIVILEGE,
            }
        )
        worker = Path(__file__).with_name("worker.py")
        with self._lock:
            try:
                outcome = subprocess.run(
                    [sys.executable, "-I", str(worker)],
                    input=request,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    timeout=WORKER_TIMEOUT,
                    check=False,
                )
            except subprocess.TimeoutExpired as err:
                raise IpmiCoreError("IPMI worker timed out") from err
            except OSError as err:
                raise IpmiCoreError("Could not start IPMI worker") from err
        if outcome.returncode != 0:
            raise IpmiCoreError("IPMI worker failed")
        if len(outcome.stdout) > 65536:
            raise IpmiCoreError("Excessive IPMI worker output")
        try:
            response = json.loads(outcome.stdout)
        except (json.JSONDecodeError, TypeError, ValueError) as err:
            raise IpmiCoreError("Invalid IPMI worker response") from err
        if not isinstance(response, dict) or response.get("ok") is not True:
            raise IpmiCoreError("Invalid IPMI worker response")
        return response

    def get_power(self) -> bool:
        """Only a definitive physical state is returned as a boolean."""
        result = self._invoke("status")
        power = result.get("powerstate")
        if power not in ("on", "off"):
            raise IpmiCoreError("Invalid BMC power state")
        return power == "on"

    def power_on(self) -> PowerOnResult:
        """Worker reads real power before requesting ON; never guess state."""
        result = self._invoke("power_on")
        sent = result.get("sent")
        state = result.get("powerstate")
        if type(sent) is not bool or state not in ("on", "off"):
            raise IpmiCoreError("Invalid BMC power-on response")
        if sent != (state == "off"):
            raise IpmiCoreError("Inconsistent BMC power-on response")
        return PowerOnResult(sent=sent, observed_on=state == "on")

    def graceful_shutdown(self) -> GracefulShutdownResult:
        """Signal OS ACPI shutdown only when the BMC confirms chassis ON."""
        result = self._invoke("graceful_shutdown")
        sent = result.get("sent")
        state = result.get("powerstate")
        if type(sent) is not bool or state not in ("on", "off"):
            raise IpmiCoreError("Invalid ACPI shutdown response")
        if sent != (state == "on"):
            raise IpmiCoreError("Inconsistent ACPI shutdown response")
        return GracefulShutdownResult(sent=sent, observed_off=state == "off")

    def get_telemetry(self) -> TelemetrySnapshot:
        """Read bounded numerical SDR telemetry; no chassis writes or guesses."""
        result = self._invoke("telemetry")
        try:
            return parse_telemetry_response(result)
        except TelemetryProtocolError as err:
            raise IpmiCoreError("Invalid IPMI telemetry response") from err

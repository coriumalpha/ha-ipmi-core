# Changelog

Version numbers describe the integration source. A version entry does not imply a GitHub Release, HACS catalog listing or hardware certification.

## 0.1.7 — Read-only SDR telemetry

- Add a separate 180-second telemetry coordinator and dynamic numeric BMC SDR sensor discovery.
- Support temperature, fan RPM, voltage, current and power values where the BMC provides supported units.
- Expose per-metric health flags and a diagnostic aggregate hardware-warning sensor.
- Use bounded, read-only worker actions; unreadable sensors are unavailable rather than zero.
- Preserve existing guarded ON and graceful ACPI shutdown behavior.

## 0.1.6 — BMC communication diagnostics

- Add a diagnostic binary sensor representing the result of the last chassis-state IPMI query.
- Enable the manual ACPI shutdown button for new entity registrations; existing entity-registry preferences remain in effect.
- Preserve fail-closed state handling and bounded shutdown confirmation.

## 0.1.5 — Guarded ACPI shutdown

- Introduce a manual ACPI OS-shutdown request with physical OFF confirmation and a read-only cooldown.
- Never send hard-off, reset, cycle or a forced fallback after timeout.
- Add concurrency guards and offline shutdown regression tests.

## 0.1.4 — Integration branding

- Bundle local Home Assistant icon assets and their SVG source.
- Add reproducible image rendering and validation tooling.

## 0.1.3 — Verified power-on behavior

- Read physical BMC state before requesting ON; skip if already ON.
- Confirm successful power-on through bounded read-only polling instead of optimistic updates.
- Suppress duplicate operations and preserve failure as unavailable.

## 0.1.2 — Worker isolation

- Move IPMI operations to short-lived subprocesses with a hard timeout and cleanup.
- Send BMC credentials over stdin rather than process arguments.

## 0.1.1 — Session-handling experiment

- Explore reusing a client session across operations; subsequently superseded by process isolation.

## 0.1.0 — Initial integration

- Add chassis power detection, a guarded ON button, configuration flow and offline tests.

## Open technical work

- Refresh or invalidate telemetry immediately after verified power transitions, rather than allowing values from the preceding polling interval to remain visible.
- Improve diagnostics for sporadic worker failures without logging raw backend exceptions or account information.
- Explore optional read-only SEL, inventory and richer BMC health indicators without exposing serial numbers or asset identifiers by default.

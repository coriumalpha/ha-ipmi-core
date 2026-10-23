# Hardware telemetry in IPMI Core 0.1.7

This document describes the implementation currently shipped with the integration, rather than a release candidate.

## Polling and discovery

- A separate telemetry coordinator refreshes every **180 seconds**; chassis-power polling retains its own 30–300-second configurable rate.
- Each telemetry read calls `pyghmi==1.6.19` from an isolated subprocess with a 12-second timeout and explicit read-only allowlisting.
- Supported numerical units are **°C**, **RPM**, **V**, **A** and **W**. All readings must have validated, finite values and bounded metadata.
- Sensors are dynamically created when readings first become valid. Starting Home Assistant with a chassis OFF does not require integration reconfiguration to discover measurements after startup.
- Unique entity identities are derived from sensor name, unit and occurrence, scoped to the Home Assistant configuration entry; no host-specific constants are needed.

## Sensor availability

Missing, failed or unusable readings should not be presented as zero. If a previously known reading is absent from the latest telemetry snapshot, its entity becomes unavailable. Hardware-warning state is based on health flags reported by the BMC; a valid RPM or temperature number does not necessarily mean a healthy component.

**Known limitation:** telemetry polling is independent of chassis state. Following a verified OFF transition, previously sampled numeric values may remain visible until the next telemetry refresh. Immediately after ON, sensors can remain unavailable until a new valid snapshot is acquired. Avoid treating these briefly stale metrics as fresh measurements.

Future work will coordinate transition-aware invalidation and a bounded refresh after ON, while preserving the separation between BMC control and telemetry failures.

## Diagnostics and safety

- Hardware-warning sensor aggregates affected SDR names when the BMC reports health flags.
- The BMC connectivity diagnostic reports only the success of the most recent chassis state read.
- Telemetry failures do not change the verified chassis-power sensor.
- Workers serialize access to a given BMC, so a slow SDR transaction may delay another operation by up to the configured worker deadline.
- No generic IPMI commands, sensor configuration changes, fan control, power cuts or SEL clearing are exposed.

## Testing

Offline tests exercise telemetry parsing, validation, dynamic sensor creation, health warnings and worker timeouts with synthetic BMC fixtures. These tests do not establish compatibility with arbitrary hardware. For a safe hardware acceptance check, verify measurements while powered on, confirm that warning flags are displayed correctly, and observe unavailability after a clean shutdown and subsequent telemetry refresh.

Do not publish raw IPMI dumps, BMC addresses, asset numbers or identifying inventory records when reporting issues.

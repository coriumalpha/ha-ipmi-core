# BMC sensors and future capabilities

IPMI Core 0.1.7 includes read-only numerical SDR telemetry and diagnostics. Registration is capability-driven: sensors are added only when supported, valid measurements become available.

| Area | Current support | Possible improvements |
| --- | --- | --- |
| Chassis and connectivity | Verified physical ON/OFF and last BMC state-query success | Last successful query timestamp, duration and error categories |
| Hardware warnings | Aggregate BMC threshold warnings and per-reading `bmc_health` | More detailed health classifications |
| Thermal | Supported temperature values and fan RPM | Per-device controls for sensor visibility; no fan writes |
| Electrical | Supported voltage, current and instantaneous power | PSU presence and failure diagnostics if available |
| Event log and inventory | Not implemented | Read-only bounded SEL summaries and selectively redacted FRU information |

## Implementation principles

1. Discover only reported BMC capabilities and map units and state classes conservatively.
2. Keep telemetry failures independent of chassis-power availability.
3. Use explicit, read-only, bounded worker actions; do not add raw command facilities.
4. Give missing, stale or unparseable readings **unavailable** status rather than invented zeros.
5. Maintain stable per-config-entry sensor identities; never encode private hostnames or IPs into entity implementation constants.
6. Sanitize diagnostics. Avoid raw packets, secret values, serial numbers, asset tags and vendor-specific identifying traces.
7. Validate behavior across multiple BMC implementations before claiming broad compatibility.

## Telemetry lifecycle improvement

Chassis state and SDR polling operate independently. As a result, a recently powered-off device can still show a previous telemetry sample until the next poll, and a just-started chassis can temporarily have no valid readings.

Future work: on *verified* power-state transitions, invalidate stale metrics promptly; schedule a bounded refresh following startup, with debouncing and coordination with the shared worker lock. Any error must leave physical chassis state unaffected. Treat BMC-side cached readings as potentially stale, not authoritative proof of current thermal conditions.

## Potential read-only APIs

The pinned `pyghmi` library provides candidate read-only interfaces for sensor discovery, health, system event logs and inventory. Assess bounded execution, privacy, stable IDs and vendor behavior before incorporating any new API.

**Out of scope:** changing fan controls or sensor thresholds; SEL clearing; user management; firmware updates; arbitrary IPMI commands; hard power cuts.

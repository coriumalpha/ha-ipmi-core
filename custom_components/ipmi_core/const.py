"""Constants for the IPMI Core integration."""

DOMAIN = "ipmi_core"
CONF_POLL_SECONDS = "poll_seconds"
DEFAULT_PORT = 623
DEFAULT_POLL_SECONDS = 60
MIN_POLL_SECONDS = 30
MAX_POLL_SECONDS = 300
# Operator is intentionally required, not configurable in v0.1.
# It is the least standard IPMI role with chassis power-control privileges.
OPERATOR_PRIVILEGE = 3
OPERATION_TIMEOUT = 20

# Shorter than OPERATION_TIMEOUT; subprocess.run kills and reaps on expiry.
WORKER_TIMEOUT = 12

# Bounded read-only confirmation after an explicit power-on command.
POWER_ON_CONFIRM_INTERVAL = 3
POWER_ON_CONFIRM_TIMEOUT = 35
POWER_ON_RETRY_COOLDOWN = 60

# ACPI OS shutdown request (never chassis hard-off).
SHUTDOWN_CONFIRM_INTERVAL = 10
SHUTDOWN_CONFIRM_TIMEOUT = 300
SHUTDOWN_RETRY_COOLDOWN = 600

# Slow, independent, read-only hardware telemetry: keep chassis polls at 60 s.
TELEMETRY_POLL_SECONDS = 180
MAX_TELEMETRY_SENSORS = 96

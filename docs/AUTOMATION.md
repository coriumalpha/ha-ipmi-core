# Automating chassis controls safely

IPMI Core supplies *controls and verified state*, not a backup scheduler or application-level shutdown policy.

## Conditional power-on

A generic Home Assistant automation can request power-on only if the integration's physical chassis sensor is OFF. Replace the entity IDs with those created for **your own configured BMC**. This example intentionally does not schedule an automatic shutdown.

```yaml
alias: "Example · guarded IPMI power-on"
triggers:
  - trigger: time
    at: "02:30:00"
    weekday: mon
conditions:
  - condition: state
    entity_id: binary_sensor.example_server_power
    state: "off"
actions:
  - action: button.press
    target:
      entity_id: button.example_server_power_on
mode: single
```

If the power sensor is `unknown` or `unavailable`, this automation sends **no** command.

## Before an ACPI shutdown

An OS-managed shutdown can still interrupt databases, virtual machines and backups. A notification or inline-button confirmation is a possible UI, but that decision belongs to your separate orchestration. Require a verified powered-on state, explicitly authenticate the person confirming an action, reject stale or duplicate confirmations and verify OFF after requesting ACPI.

For Telegram callbacks, validate the **real user ID**, chat ID, callback data and originating message ID. The ID of a bot is *not* the ID of the human operator. The supplied ACPI button intentionally never falls back to hard-off if the OS remains running.

## Telemetry during boot

Power status may be confirmed before BMC SDR sensors have fresh readings. If a notification includes temperatures or fans, wait for actual valid sensor values (and allow time for post-boot polling). Never convert `unavailable` to zero or claim that a cached reading is current.

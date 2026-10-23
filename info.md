# IPMI Core

**Security-focused IPMI power management and hardware monitoring for Home Assistant.**

Published by **Arcotangana** · Maintained by [@coriumalpha](https://github.com/coriumalpha) · Version **0.1.7**

IPMI Core communicates directly with a Baseboard Management Controller (BMC). It offers **verified physical power states**, guarded power-on, **OS-managed ACPI shutdown**, BMC connectivity status, and read-only hardware telemetry (temperature, fan RPM, voltage and supported power measurements).

## Security-first design

- Confirms actual chassis ON/OFF rather than assuming a command succeeded.
- Checks power state before acting and guards against duplicate/conflicting requests.
- Exposes **no hard power-off, reset, power-cycle or arbitrary IPMI command**.
- Uses isolated, timeout-bounded worker subprocesses, with credentials passed through stdin.
- Never forces a shutdown if ACPI fails or the operating system does not respond.

**Important:** The integration does not know whether virtual machines, services or backups are busy. Verify workloads can safely stop before using the ACPI control. Restrict BMC access to a trusted management network; never expose IPMI UDP/623 to the Internet.

## Install with HACS

1. In HACS, open **⋮ → Custom repositories**.
2. Add `https://github.com/coriumalpha/ha-ipmi-core` and select **Integration**.
3. Open **IPMI Core** and choose **Download**. Select the default branch if no release is available.
4. Restart Home Assistant.
5. Go to **Settings → Devices & services → Add integration → IPMI Core**.
6. Enter your BMC hostname/IP, UDP port (typically 623), dedicated IPMI Operator credentials and preferred polling interval.

**Requirements:** Compatible IPMI 2.0 BMC, Home Assistant supporting custom integrations and network access to the BMC. Tested with Home Assistant **2026.9.1**; broad vendor compatibility is not guaranteed.

[Complete documentation](https://github.com/coriumalpha/ha-ipmi-core#readme) · [Security policy](https://github.com/coriumalpha/ha-ipmi-core/blob/main/SECURITY.md) · [Report an issue](https://github.com/coriumalpha/ha-ipmi-core/issues)

**License:** AGPL-3.0.

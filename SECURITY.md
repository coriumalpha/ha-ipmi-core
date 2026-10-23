# Security policy

IPMI Core controls physical server power and communicates with a privileged out-of-band management interface. Treat bugs affecting command scope, authentication, secrets handling or chassis state as potentially security-sensitive.

## Reporting vulnerabilities

Use **GitHub private vulnerability reporting** for this repository when that feature is enabled. Otherwise contact the repository maintainer privately through the GitHub account associated with the project before disclosing sensitive details publicly. Do not open a public issue containing exploit steps, secrets, IPMI packets, internal IP addresses, hardware identifiers or production logs.

## Deployment guidance

- Isolate the BMC on a restricted management network. Do not expose UDP/623 to the public Internet.
- Use a dedicated BMC Operator account with a unique password and restrict Home Assistant administrative access.
- Protect Home Assistant's configuration store and backups, which contain integration credentials.
- Review BMC firmware and negotiated IPMI cipher-suite limitations.
- The integration deliberately does not expose raw command execution, hard-off, reset, cycle or BMC configuration changes.
- Verify the behavior of OS-level ACPI handling before using graceful shutdown in real systems.
- Do not treat an unavailable chassis-state sensor as proof of a powered-off machine.

No independent security audit or manufacturer certification is claimed.

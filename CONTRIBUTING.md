# Contributing

Contributions should preserve the integration's intentionally limited IPMI command surface. Please start with a reproducible issue or a focused pull request.

- Run `python3 -m unittest discover -s tests -v` and `python3 -m compileall -q custom_components/ipmi_core tests`.
- Use synthetic BMC fixture data and reserved documentation IP ranges (e.g. `192.0.2.0/24`) in examples.
- Never include real BMC addresses, hostnames, login names, credentials, chat IDs, asset tags, serial numbers, full logs or internal network diagrams.
- For new IPMI operations, document the read/write behavior, failure semantics, timeout, privilege requirements and physical-safety implications.
- Power-control behavior needs offline tests and an explicit hardware maintenance plan before broad deployment.

Security-sensitive reports should follow [SECURITY.md](SECURITY.md), not a public issue.

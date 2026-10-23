# IPMI Core — distribution metadata

**Project:** IPMI Core · **Publisher:** Arcotangana · **GitHub maintainer:** [@coriumalpha](https://github.com/coriumalpha)

**Repository:** https://github.com/coriumalpha/ha-ipmi-core · **Integration version:** 0.1.7 · **License:** AGPL-3.0

> Security-focused IPMI power management and hardware monitoring for Home Assistant, with verified power states, guarded controls and graceful ACPI shutdown.

These are presentation and release details, **not** BMC hardware identifiers. The integration's internal domain remains `ipmi_core` and its Home Assistant manifest contains only supported fields. `hacs.json` controls the HACS display name and selects the concise `info.md` presentation; the GitHub repository description/topics are configured in repository settings rather than in `hacs.json`.

## Repository metadata to set in GitHub

**Description:** Security-focused IPMI power management and hardware monitoring for Home Assistant, with verified power states, guarded controls and graceful ACPI shutdown.

**Website:** https://github.com/coriumalpha/ha-ipmi-core

**Topics:** `home-assistant`, `hacs`, `ipmi`, `bmc`, `server-management`, `hardware-monitoring`, `acpi`

The maintainer must set these in **Settings / About** if the connected GitHub integration does not expose repository metadata editing.

## HACS installation and updates

When the repository is public: **HACS → Custom repositories → paste the repository URL → select Integration → Add → Download → restart Home Assistant**.

The `custom_components/ipmi_core/` layout is recognized automatically. HACS can use the default branch even without a GitHub Release; tagged Releases are useful later but are not required for custom-repository installations.

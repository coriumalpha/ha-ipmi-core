# IPMI Core 0.1.7 — publication checklist

**Status (2026-10-23):** Public repository. The maintainer confirmed the decision to publish it. Home Assistant Hassfest, basic checks, brand regeneration and the official HACS Action passed on `main`. Installation as a **custom HACS integration** can now be tested.

This checklist applies to the **new** `ha-ipmi-core` repository. The prior development repository is retained independently as a private archive. Historical cleanup tasks for the old repository do not apply to this new Git history.

## Repository and privacy

- [x] New Git repository created independently of the private development archive.
- [x] The initial commit is a root commit with no inherited parents.
- [x] No imported issues or pull requests; the HACS preparation branch was fast-forwarded to `main`.
- [x] Fast-forward HACS preparation branch to `main` without rewriting Git history.
- [x] Author/committer email is accepted by the maintainer and does not require anonymization.
- [x] GitHub account name, codeowner and project links are intentional public project identifiers.
- [x] Reviewed text files contain no known personal hostnames, internal infrastructure addresses or Telegram IDs.
- [x] Existing Home Assistant brand PNGs regenerated with pinned dependencies and verified.
- [ ] Incorporate the **final high-resolution publisher logo** as an unchanged master PNG and derive full-colour icon variants without JPEG conversion or palette quantization; then switch the README to the master.
- [ ] Final inspection of any future release artifacts for embedded metadata or identifying content.
- [ ] Confirm no personal configuration, credentials, backups or debug outputs have been added before publication.

**Important:** Subsequent documentation maintenance commits are acceptable; the objective is **no inherited private development history**, not permanently restricting the repository to one commit.

## Source and documentation

- [x] IPMI Core source, translations, brand assets, tests and license are in `main`.
- [x] README, changelog and telemetry/sensor guides reflect source version 0.1.7.
- [x] HACS metadata and installation instructions prepared for custom-repository distribution.
- [x] Publisher **Arcotangana**, maintainer **@coriumalpha** and project version **0.1.7** documented.
- [x] Generic automation guidance, contributor instructions and security policy are present.
- [x] `hacs.json` and the Home Assistant integration manifest are present.
- [ ] Complete third-party license and pinned-dependency review.
- [ ] Perform a clean installation from this repository in a supported Home Assistant environment and verify the entities and controls without using private configurations.
- [ ] Confirm any vendor-specific claims remain appropriately qualified.

## CI and validation

- [x] Python compilation, JSON validation and offline unit tests pass.
- [x] Home Assistant Hassfest validation passes.
- [x] Brand assets regenerated using CI-pinned dependencies.
- [x] Read-only CI regenerates assets without diffs after the workflow is returned to validation-only mode.
- [x] Official HACS validation **passes on `main`**; repository topics have been configured on GitHub.
- [ ] Review GitHub Actions logs and generated installation artifacts before promoting them as release assets.

## Public release

- [x] Repository is **Public** at maintainer's instruction (required for custom HACS access).
- [ ] Test installation via **HACS → Custom repositories → Integration** using this repository URL.
- [x] CI rerun confirms official HACS validation passes on `main`.
- [ ] Optionally publish a tagged `v0.1.7` GitHub Release after the final logo and installation smoke test; a GitHub Release is **not required** to install from a custom HACS repository.
- [ ] Verify README, release links, installation package and assets from an unauthenticated session.
- [ ] Optionally submit to the HACS default catalog after satisfying its publication requirements.

## Known limitations

- SDR telemetry can temporarily retain earlier values after a chassis power-state transition because telemetry polling is independent of chassis-state polling.
- General compatibility with all vendors and BMC firmware versions is not established.
- IPMI Core does not validate hypervisor workloads or job completion before an ACPI shutdown.
- Offline tests, Hassfest and a successful hardware test do not constitute an independent security audit.

**Publication decision:** Custom HACS repository distribution is technically validated on `main`. A clean-install smoke test, final master logo asset and optional GitHub Release remain; no historical private commits were imported.

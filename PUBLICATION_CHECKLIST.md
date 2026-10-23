# IPMI Core 0.1.7 — publication checklist

**Status:** Custom HACS distribution in preparation. **Visibility must be reviewed by the maintainer** before release. On 2026-10-23 GitHub reported this new repository as public; if publication has not been approved, switch it back to private in GitHub settings.

This checklist applies to the **new** `ha-ipmi-core` repository. The prior development repository is retained independently as a private archive. Historical cleanup tasks for the old repository do not apply to this new Git history.

## Repository and privacy

- [x] New Git repository created independently of the private development archive.
- [x] The initial commit is a root commit with no inherited parents.
- [x] No imported issues or pull requests; a temporary `release/hacs-custom-0.1.7` preparation branch now exists alongside `main`.
- [ ] Merge or fast-forward the vetted release branch to `main` after final review.
- [x] Author/committer email is accepted by the maintainer and does not require anonymization.
- [x] GitHub account name, codeowner and project links are intentional public project identifiers.
- [x] Reviewed text files contain no known personal hostnames, internal infrastructure addresses or Telegram IDs.
- [x] Replacement brand PNGs were generated with pinned dependencies from the supplied project logo (no embedded private BMC details).
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
- [ ] Official HACS validation completes successfully. Last HACS Action failed **only because the repository has no GitHub topics**; add relevant topics in GitHub's About panel and rerun.
- [ ] Review GitHub Actions logs and generated installation artifacts before promoting them as release assets.

## Public release

- [ ] Confirm the current repository visibility and approve **Public** only after final review (required for custom HACS access).
- [ ] Test installation via **HACS → Custom repositories → Integration** using this repository URL.
- [ ] Rerun CI and confirm the official HACS validator passes.
- [ ] Create a tagged `v0.1.7` GitHub Release, with tested installation instructions and a clear hardware-compatibility disclaimer.
- [ ] Verify README, release links, installation package and assets from an unauthenticated session.
- [ ] Optionally submit to the HACS default catalog after satisfying its publication requirements.

## Known limitations

- SDR telemetry can temporarily retain earlier values after a chassis power-state transition because telemetry polling is independent of chassis-state polling.
- General compatibility with all vendors and BMC firmware versions is not established.
- IPMI Core does not validate hypervisor workloads or job completion before an ACPI shutdown.
- Offline tests, Hassfest and a successful hardware test do not constitute an independent security audit.

**Publication decision:** The new Git history has no inherited private commits, and the reviewed source is suitable for continued release preparation. The remaining unchecked items are release checks—not unresolved historical-data cleanup in this new repository.

# IPMI Core 0.1.7 — pre-publication checklist

**Status: private.** Source version 0.1.7 is integrated in the default branch.
Repository visibility has not been changed.

## Current source

- [x] Source, translations, README, changelog and brand assets in `main`
- [x] Existing tests and basic CI checks pass
- [x] No hardcoded BMC address or server name in integration logic
- [x] HACS configuration (`hacs.json`) and Home Assistant manifest present
- [x] Hassfest validation passes
- [ ] Official HACS validator passes (HACS rejects *private* repositories)
- [ ] Clean-install acceptance and dependency/license review completed

## Historical GitHub data — publication blockers

- [x] Current issue and PR bodies and visible comments anonymized for the known server name and management IP
- [ ] Inspect and remove **previous revisions** of edited comments and descriptions
- [ ] Clean old git branch refs, tags, author metadata and reachable history
- [ ] Check PR diffs and hidden PR refs, Actions logs and artifact history
- [ ] Ensure GitHub has purged any genuinely sensitive old objects (GitHub
  Support may be required; rewriting just `main` is not enough)
- [ ] Avoid reintroducing old commits from earlier clones

**Do not switch this existing repository to public while historical-data checks remain outstanding.**

## HACS distribution

To request admission to the default catalog, the repository must be public,
the official HACS Action and Hassfest checks must pass, and a GitHub Release
must be published. None of those publication steps has been authorized yet.

Documentation:
- https://hacs.dev/docs/publish/action/
- https://github.com/home-assistant/actions
- https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository

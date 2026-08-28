# Changelog

## 2026-08-27

### Additions and New Features

- Added permanent importer coverage for unsupported bundle schemas and asset paths that escape the
  physical bundle boundary.
- Advanced the publisher boundary to bundle v2, evidence v3, editorial projection v1, generator
  v2, prompts v3, rubric v3, and publication records v2.
- Added independent projection validation for identity, packet binding, active-repository cards,
  source-content hashes, bounded offsets, and exact source substrings.

### Behavior or Interface Changes

- Accept only complete bundles produced after two author validation summaries and a valid anonymous
  A/B referee selection.
- Rename evidence `budgets` to `collection_limits`, require the projection artifact in post front
  matter, archive it with the bundle, and reject generic date-derived Work log titles.
- Require the generator's 64-character lowercase hexadecimal source/config fingerprint instead of
  interpreting every generator revision as a Git object ID.
- Make imported report dates immutable: identical bundle imports are idempotent and every different
  bundle for that date is rejected before staging.

### Fixes and Maintenance

- Centralized the exact publication-v2 receipt contract in `scripts/publication_record.py`; status
  rendering and crash-recovery markers now reject unknown, incomplete, malformed, or misnamed
  records before they can participate in a transaction.
- Removed superseded pre-bundle collector, editorial, and run-state directories from the active
  publisher tree. Historical source remains available through repository history.
- Aligned the checked-in static service with the installed LAN-and-Tailscale `0.0.0.0:8016` binding.
- Validate that every declared revision range exactly covers all parents of every attributed commit,
  preserving non-linear same-day provenance across the repository boundary.
- Resolve the publisher repository root through Git while retaining explicit root injection for
  temporary importer tests.
- Reworked failure tests to compare one complete publisher transaction snapshot, preserving source,
  records, archives, releases, staging, and the served pointer with one stable behavioral assertion.
- Classified permanent importer contracts separately from producer-owned historical and host
  cutover checks in [operations.md](operations.md).
- Updated [operations.md](operations.md) to record the explicitly activated producer timer and its
  producer-owned oldest-first missed-date cursor.
- Added transaction locking and crash recovery: one publisher-global lock spans checks through commit,
  the publication record is installed last, and startup reconciles interrupted transaction markers.
- Tightened idempotency to require byte-identical archived manifest, evidence, projection, and post,
  the exact installed source post, and the expected live release pointer.
- Tightened v2 JSON contracts to exact fields, bound candidate summaries to the editorial projection,
  and independently enforce projection context, excerpt, and commit-subject limits.
- Treat a projected screenshot's confined, hash-bound publication path as its provenance citation,
  while continuing to reject every image outside bundle evidence.
- Synchronized shared style guides, tests, and repository support files from the starter template.

### Removals and Deprecations

- Removed date replacement, publication ranking, and incomplete editorial-bundle paths from the
  publisher contract and permanent tests.
- Removed all pre-bundle publication records during the clean pre-production cutover. Status
  rendering now accepts only authoritative publication v2 records and fails on unsupported schemas
  instead of synthesizing compatibility rows.

### Developer Tests and Notes

- All 35 focused importer and status tests passed under Python 3.12, including projection tampering, exact
  excerpt integrity, date immutability, idempotency, and complete transaction rollback.
- All 443 focused importer, typing, pyflakes, indentation, ASCII, whitespace, and source-line-limit
  checks passed.
- All 554 Bandit, shebang, dependency-import, and absolute-import checks passed.
- The real documentation tree completed a strict staged MkDocs build without changing `site`.
- Corrected historical screenshot link text to match each target filename. Markdown-link lint now owns
  the rendered documentation tree rather than reinterpreting byte-identical bundle archives as
  standalone pages; immutable payload links remain protected by importer path, manifest, and hash
  validation. Generated publication prose and immutable bundle archives are excluded from mutating
  ASCII hygiene, while the rendered source tree retains link lint. The full publisher test command
  now reports 1080 passing tests with no failures. The real MkDocs source completed a strict build.
- A clean live import for report date 2026-08-26 completed from generator run
  `20260828T003950Z-bdee87fdc1` and bundle
  `d6d06817bec1b057411b10d135400e0db8024a7f750f603bd45c630d783c5799`. The final post title is
  "Making the Interface Tell the Truth"; the archived manifest, post, projection, and evidence are
  byte-identical to the producer bundle, all ten assets are installed, and the served release
  pointer and live thematic HTTP route resolve to that exact bundle.

## 2026-08-26

### Additions and New Features

- Added `scripts/import_publication_bundle.py` as the sole generator-facing bundle command.
- Added independent bundle, evidence, authority, hash, path, provenance, candidate, referee, asset,
  front-matter, and paragraph-evidence validation.
- Added anonymous referee mapping validation that proves the selected post is the exact valid
  candidate selected during judging.
- Added complete MkDocs source staging, strict builds, immutable bundle archives and releases,
  atomic served-release switching, idempotent imports, and initial date-state controls.
- Added publisher contract tests for tampering, schema rejection, idempotency, date-state controls,
  staged-build failure, install rollback, and last-good release preservation.
- Added [CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md) and
  [FILE_STRUCTURE.md](FILE_STRUCTURE.md) for the publisher ownership boundary.

### Behavior or Interface Changes

- Publication state now uses one record per imported date with bundle, generator, evidence, source
  post, and immutable release identities.
- Bundles carry explicit prompt and rubric contracts that the importer validates as part of the
  cross-repository boundary.
- The status page now renders current bundle publications while identifying pre-bundle records as
  historical legacy entries.
- Generation, GitHub collection, mirror synchronization, LLM execution, and publication scheduling
  now belong to `vosslab-podcast`; this repository retains local content and static serving.

### Fixes and Maintenance
- Removed the former GitHub collector, daily generation wrappers, layered LLM editor, split
  publication-state module, editorial reconciliation service/timer, and their retired tests.
  The importer and static serving service are now the only active execution paths in this repository.
- Replaced stale manual-generation agent guidance with concise pointers to the current publisher
  ownership and repository documentation.
- Added transaction rollback flags for failures after prior source or publication records move.
- Ensured failed staged builds remove their proposed staging directories without changing current
  source or the served site pointer.
- Added PyYAML as an explicit runtime dependency and made the `scripts` package importable through
  `source_me.sh`.
- Excluded the vendored repository style guide from MkDocs content so its maintainer-only links do
  not break strict site builds.
- Updated the repository landing page, [operations.md](operations.md), and the local site home page
  for bundle-import ownership and recovery.

## 2026-08-21

### Additions and New Features

- Added depth-1 Vosslab repository-checkout synchronization before scheduled daily collection.
- Added commit-pinned mirror provenance for README, dated changelog, and screenshot evidence.

### Fixes and Maintenance

- Made repository enrichment error ordering deterministic.
- Added HTTPS validation at outbound GitHub resource boundaries.
- Corrected the historical recreate wrapper and excluded generated releases from source control.
- Reconciled source-boundary documentation with current collection behavior.

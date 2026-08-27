# Changelog

## 2026-08-27

### Additions and New Features

- Added permanent importer coverage for unsupported bundle schemas and asset paths that escape the
  physical bundle boundary.
- Advanced the evidence contract to v2 with explicit commit-to-parent revision ranges and
  attributed branch-tip snapshots.

### Fixes and Maintenance

- Validate that every declared revision range exactly covers all parents of every attributed commit,
  preserving non-linear same-day provenance across the repository boundary.
- Resolve the publisher repository root through Git while retaining explicit root injection for
  temporary importer tests.
- Reworked failure tests to compare one complete publisher transaction snapshot, preserving source,
  records, archives, releases, staging, and the served pointer with one stable behavioral assertion.
- Classified permanent importer contracts separately from producer-owned historical and host
  cutover checks in [operations.md](operations.md).

### Developer Tests and Notes

- All 11 focused importer tests passed under Python 3.12, including schema, asset-path, hash,
  idempotency, quality precedence, and transaction rollback behavior.
- The full publisher suite passed 1035 tests with the same eight historical or untracked-document
  link failures, and the real MkDocs source completed a strict build.

## 2026-08-26

### Additions and New Features

- Added `scripts/import_publication_bundle.py` as the sole generator-facing command for current v1
  publication bundles.
- Added independent bundle, evidence, authority, hash, path, provenance, candidate, referee, asset,
  front-matter, and paragraph-evidence validation.
- Added anonymous referee mapping validation that proves a final post is the exact valid candidate
  selected during judging.
- Added complete MkDocs source staging, strict builds, immutable bundle archives and releases,
  atomic served-release switching, idempotent imports, and final-over-provisional replacement.
- Added publisher contract tests for tampering, schema rejection, idempotency, quality precedence,
  staged-build failure, install rollback, and last-good release preservation.
- Added [CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md) and
  [FILE_STRUCTURE.md](FILE_STRUCTURE.md) for the publisher ownership boundary.

### Behavior or Interface Changes

- Publication state now uses one v1 record per imported date with bundle, generator, evidence,
  source post, quality, and immutable release identities.
- Current v1 bundles now carry the producer's v2 prompt and rubric contracts; the importer validates
  those versions as part of the cross-repository contract.
- The status page now renders current bundle publications while identifying pre-bundle records as
  historical legacy entries.
- Generation, GitHub collection, mirror synchronization, LLM execution, and publication scheduling
  now belong to `vosslab-podcast`; this repository retains local content and static serving.

### Fixes and Maintenance
- Removed the former GitHub collector, daily generation wrappers, layered LLM editor, split
  publication-state module, editorial reconciliation service/timer, and their superseded tests.
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

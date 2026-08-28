# Changelog

## 2026-08-27

### Additions and New Features

- Added permanent importer coverage for unsupported bundle schemas and asset paths that escape the
  physical bundle boundary.
- Advanced the publisher boundary to bundle v2, evidence v3, editorial projection v1, generator
  v2, prompts v3, rubric v3, and publication records v2.
- Added independent projection validation for identity, packet binding, active-repository cards,
  source-content hashes, bounded offsets, and exact source substrings.
- Added operator-facing [INSTALL.md](INSTALL.md), [USAGE.md](USAGE.md),
  [COOKBOOK.md](COOKBOOK.md), [TROUBLESHOOTING.md](TROUBLESHOOTING.md),
  [FAQ.md](FAQ.md), and [DEVELOPMENT.md](DEVELOPMENT.md) guides.
- Added [FILE_FORMATS.md](FILE_FORMATS.md) for the producer bundle, validated publication record,
  and presentation deployment receipt contracts.
- Added [ROADMAP.md](ROADMAP.md) for runtime consolidation, cross-repository admission policy,
  and deployment/recovery import-boundary work with named owners.
- Added [RELATED_PROJECTS.md](RELATED_PROJECTS.md), which records `vosslab-podcast` as the confirmed
  companion producer and documents the bounded related-projects review.

### Behavior or Interface Changes

- Versioned publisher-local post-validation policies; v3 historical bundles remain the only
  importable contract while v4 maker-policy checks are available only through explicit direct tests.
- Changed the daily-post evidence boundary from paragraph-level comments to narrative sections:
  every narrative section needs a known packet citation, up to three prose blocks may omit their
  own comment, and final Project coverage remains outside that allowance.
- Added `publish_site.sh` as the one-command LAN presentation workflow. It strictly builds an
  immutable source-identified release, atomically switches `site`, verifies the live root and status
  pages, and requires no static-service restart.
- Replaced the stock Material notebook icon with one editable Vosslab Work Log press badge used as
  the header logo, masthead signature, and browser favicon. Its full-canvas silhouette and simplified
  folded sheet remain legible at 16-pixel browser-tab size.
- Expanded the site footer to link GitHub, YouTube, Bluesky, LinkedIn, Facebook, Patreon, and
  PayPal, and linked the approved Neil R. Voss site-content notice directly to CC BY 4.0.
- Made the paginated work log the root MkDocs landing page and removed the separate blog gate while
  preserving established post and archive permalinks under `/blog/`.
- Accept only complete bundles produced after two author validation summaries and a valid anonymous
  A/B referee selection.
- Rename evidence `budgets` to `collection_limits`, require the projection artifact in post front
  matter, archive it with the bundle, and reject generic date-derived Work log titles.
- Require the generator's 64-character lowercase hexadecimal source/config fingerprint instead of
  interpreting every generator revision as a Git object ID.
- Make imported report dates immutable: identical bundle imports are idempotent and every different
  bundle for that date is rejected before staging.
- Kept repository Markdown outside the built blog: reader navigation remains Work log and Status,
  with the blog archive available through the blog plugin rather than an operator-facing guide.
- Made Python 3.13 the publication runtime. `publish_site.sh` resolves `python3.13` from `PATH`
  before loading the repository shell environment, so an activated Python 3.13 virtual environment
  is optional rather than required.

### Fixes and Maintenance

- Recast the oversized stacked homepage masthead as a compact newspaper nameplate and tightened
  the sheet's top spacing so the latest article begins within the opening two inches on desktop.
- Added an exact presentation-deployment receipt and made importer idempotency recognize a derived
  release only when it names the same base bundle. Manual publication shares the importer lock and
  rejects drift in importer-owned posts and status before staging.
- Corrected deployment documentation to identify a receipt-bound presentation release as a valid
  serving target for an unchanged imported bundle.
- Replaced the generic Material presentation with an editorial broadsheet system: reusable
  light/dark tokens, layered page edges, a sheet-and-canvas shell, lead-story columns, print-like
  rules, post framing, tables, social links, and print behavior now share one stylesheet contract.
- Brightened the light-theme gold accent from `#b2781b` to `#e6b862`, raising its contrast against
  the `#1d4142` header from 2.97:1 to 6.04:1 and clearing the repository's 5.5:1 target.
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
- Refreshed the README, architecture, file-routing, operations, and agent-routing documentation to
  describe the current producer/publisher boundary and presentation-publication path.
- Refreshed the managed README screenshot from the live work-log landing page with reader-only
  navigation.

### Removals and Deprecations

- Removed date replacement, publication ranking, and incomplete editorial-bundle paths from the
  publisher contract and permanent tests.
- Removed all pre-bundle publication records during the clean pre-production cutover. Status
  rendering now accepts only authoritative publication v2 records and fails on unsupported schemas
  instead of synthesizing compatibility rows.

### Decisions and Failures

- Did not create `docs/NEWS.md` or `docs/RELEASE_HISTORY.md`: the changelog has date-only entries,
  the required root `pyproject.toml` version authority is absent, and no release-note generator is
  present. Resolve the version-authority gap before deriving release history from this changelog.
- Did not create a `docs/TODO.md`; the actionable repository work is already owned and prioritized
  in [ROADMAP.md](ROADMAP.md).

### Developer Tests and Notes

- Deployment tests cover initial and changed-source immutable promotion, unchanged-source
  idempotency, bundle binding, imported-post drift rejection, failed-build preservation, and
  identical-bundle retries after a presentation release, plus the Python 3.13 runtime gate.
- Brand-asset contract tests verify a scalable SVG canvas, resolved accessible naming, unique IDs,
  and one owned source path shared by the MkDocs logo and favicon.
- All 1193 repository tests pass under Python 3.13, and the real documentation tree completes a
  strict MkDocs build with that interpreter.
- All 334 focused Markdown-link, ASCII, whitespace, source-line-limit, and publication-bundle tests
  passed under Python 3.12.
- Chromium rendering checks passed for the root work log, preserved post permalink, status table,
  light and dark schemes, reduced motion, computed card styles, and a 390-pixel viewport without
  horizontal overflow. Desktop and mobile screenshots were reviewed in both color schemes.
- All 35 focused importer and status tests passed under Python 3.12, including projection tampering, exact
  excerpt integrity, date immutability, idempotency, and complete transaction rollback.
- All 443 focused importer, typing, pyflakes, indentation, ASCII, whitespace, and source-line-limit
  checks passed.
- All 554 Bandit, shebang, dependency-import, and absolute-import checks passed.
- The real documentation tree completed a strict staged MkDocs build without changing `site`.
- `publish_site.sh` successfully published and verified the corrected reader-only LAN release at
  `http://aella.local:8016/`.
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

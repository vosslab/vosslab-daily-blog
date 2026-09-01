# File structure

## Top-level layout

```text
AGENTS.md                         repository-specific agent rules
README.md                         project overview and operator quick start
mkdocs.yml                        Material, blog, navigation, and brand configuration
publish_site.sh                   presentation publication and live checks
deploy/                           LAN static-service unit
docs/                             MkDocs source, durable documentation, and visual assets
data/                             validated audit archives and current publication records
generated/                        ignored locks, staging, and immutable releases
scripts/                          import, validation, transaction, and deployment modules
tests/                            offline contract, deployment, and policy checks
pip_requirements.txt              runtime Python dependencies
pip_requirements-dev.txt          development and test dependencies
source_me.sh                      shell environment setup for repo-local commands
```

## Source and presentation

- [docs/index.md](index.md) is the work-log landing page and blog index.
- [docs/blog/posts/](blog/posts/) contains importer-owned `YYYY-MM-DD.md` post sources.
- [docs/status.md](status.md) is generated from current publication records.
- [docs/assets/publications/](assets/publications/) contains only importer-installed,
  survivor-surface-authorized evidence assets.
- [docs/assets/brand/](assets/brand/) contains shared branding.
- [docs/stylesheets/extra.css](stylesheets/extra.css) contains custom reader presentation.
- [mkdocs.yml](../mkdocs.yml) connects source, theme, blog plugin, navigation, brand, and CSS.

## Publisher modules

- [scripts/import_publication_bundle.py](../scripts/import_publication_bundle.py) is the
  producer-facing sealed-transfer and manual-bundle importer.
- `scripts/publication_import_cli.py` parses bundle input and date-replacement requests.
- `scripts/bundle_snapshot.py` seals the transfer or held manual directory view and declares the
  v9 core paths.
- `scripts/publication_surface.py` validates the canonical survivor-scoped authority and exposes
  its allowed bundle and publish image paths.
- `scripts/publication_staging.py` stages the post, only surface-authorized assets, audit archive,
  current record, and strict build.
- [scripts/validate_daily_post.py](../scripts/validate_daily_post.py) validates post source and
  surface-based evidence and image references.
- [scripts/validate_editorial_projection.py](../scripts/validate_editorial_projection.py)
  validates evidence-to-projection binding.
- `scripts/publication_article_projection.py` creates canonical reader-body projections and checks
  the built article's visible body and allowed image scope.
- [scripts/publication_record.py](../scripts/publication_record.py) validates v6 records plus v5
  and v3 read-only historical records.
- [scripts/publication_transaction.py](../scripts/publication_transaction.py) owns locking,
  commit ordering, rollback, and recovery.
- [scripts/site_deployment.py](../scripts/site_deployment.py) publishes presentation-only releases.
- `scripts/publication_source_safety.py` owns the executable source policy applied before staging.

## Publication inputs

The automatic producer handoff is a canonical sealed stdin envelope. A manual operator import can
use the equivalent physical directory. Both have this bundle-relative layout:

```text
PATH/
+- bundle.json
+- evidence.json
+- repository_roster.json
+- editorial_projection.json
+- publication_surface.json
+- post.md
`- assets/
```

`publication_surface.json` is the v9 authority shared by the importer, post validator, stager,
archive, record, and rendered-page verifier. Its permitted assets must exactly equal the bundle
asset manifest. The aggregate evidence packet can contain additional screenshots, but they are not
published unless the surface selects them.

## Generated artifacts

```text
data/
+- publications/YYYY-MM-DD.json             current v6 receipt for each report date
`- publication_bundles/YYYY-MM-DD/          validated v9 audit copy for each report date

generated/
+- publisher.lock                           shared importer and presentation-publisher lock
+- staging/                                 disposable content-import stages
+- site-staging/                            disposable presentation-build stages
`- releases/
   +- YYYY-MM-DD/                           date-owned content release
   `- site-SOURCE_ID/                       immutable presentation release and receipt

site                                       atomic symlink to the served complete release
```

`generated/` and `site` are ignored by Git. A content release is identified by `report_date` and
anchored by bundle and publication-surface hashes. A presentation release is identified by the
SHA-256 of its staged MkDocs source and includes `.deployment.json`. Replacement stages the full
date-owned release before it exchanges stable directories and writes the current v6 record last.

## Documentation map

- [operations.md](operations.md) provides import, service, and recovery steps.
- [CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md) defines ownership, data flow, contracts, and
  verification boundaries.
- [INSTALL.md](INSTALL.md) and [USAGE.md](USAGE.md) describe setup and commands.
- [FILE_FORMATS.md](FILE_FORMATS.md) describes sealed input and persisted receipt formats.
- [CHANGELOG.md](CHANGELOG.md) records dated contract changes.
- [E2E_TESTS.md](E2E_TESTS.md), [PYTEST_STYLE.md](PYTEST_STYLE.md), and
  [REPO_STYLE.md](REPO_STYLE.md) define validation and repository conventions.

## Where to add work

- Put sealed-bundle and survivor-surface admission changes in
  [scripts/import_publication_bundle.py](../scripts/import_publication_bundle.py) and the focused
  importer tests.
- Put surface schema changes in `scripts/publication_surface.py`, then update the producer v9
  writer and the publisher's importer, stager, record, and rendered-page checks together.
- Put transaction and recovery changes in
  [scripts/publication_transaction.py](../scripts/publication_transaction.py).
- Put presentation deployment changes in [scripts/site_deployment.py](../scripts/site_deployment.py)
  and [tests/test_site_deployment.py](../tests/test_site_deployment.py).
- Put theme, CSS, navigation, and brand work in [mkdocs.yml](../mkdocs.yml), [docs/](.), and
  [docs/assets/](assets/); publish with [publish_site.sh](../publish_site.sh).

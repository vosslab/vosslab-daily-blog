# File structure

## Top-level layout

```text
AGENTS.md                         repository-specific agent rules
README.md                         project overview and operator quick start
mkdocs.yml                        Material, blog, navigation, and brand configuration
publish_site.sh                   one-command presentation publication and live checks
deploy/                           user-service unit for LAN static serving
docs/                             MkDocs source, durable documentation, and visual assets
data/                             publisher-owned immutable audit input and current records
generated/                        ignored staging, locks, and immutable built releases
scripts/                          importer, validation, transaction, and deployment modules
tests/                            fast contract, deployment, and repository-policy checks
pip_requirements.txt              runtime Python dependencies
pip_requirements-dev.txt          development and test dependencies
source_me.sh                      shell environment setup for repo-local commands
```

## Source and presentation

- [docs/index.md](index.md) is the work-log landing page and blog index.
- [docs/blog/posts/](blog/posts/) contains importer-owned `YYYY-MM-DD.md` post sources.
- [docs/status.md](status.md) is an importer-rendered view of current publication records.
- [docs/assets/publications/](assets/publications/) contains importer-installed evidence assets.
- [docs/assets/brand/](assets/brand/) contains shared site brand assets, including the SVG used for
  the Material navigation logo and favicon.
- [docs/stylesheets/extra.css](stylesheets/extra.css) contains the custom newspaper-style Material
  presentation.
- [mkdocs.yml](../mkdocs.yml) connects the source tree, blog plugin, theme, navigation, social
  links, SVG favicon, SVG logo, and extra stylesheet.

## Publisher modules

- [scripts/import_publication_bundle.py](../scripts/import_publication_bundle.py) is the
  generator-facing bundle importer and content-release coordinator.
- [scripts/publication_record.py](../scripts/publication_record.py) validates persisted publication
  records.
- [scripts/publication_transaction.py](../scripts/publication_transaction.py) owns the shared
  filesystem lock, ordered install, rollback, and crash recovery for content imports.
- [scripts/render_publication_status.py](../scripts/render_publication_status.py) renders the
  record-derived status source.
- [scripts/site_deployment.py](../scripts/site_deployment.py) protects importer-owned source,
  snapshots presentation source, builds it strictly, writes deployment receipts, and atomically
  promotes immutable presentation releases.
- [scripts/validate_daily_post.py](../scripts/validate_daily_post.py) validates post policy and
  [scripts/validate_editorial_projection.py](../scripts/validate_editorial_projection.py) validates
  evidence-to-projection binding.

## Publication inputs

The producer supplies one physical directory with this layout:

```text
PATH/
+- bundle.json
+- evidence.json
+- editorial_projection.json
+- post.md
`- assets/
```

The importer validates and copies these inputs. It never relies on the producer path after a
successful import.

## Generated artifacts

```text
data/
+- publications/YYYY-MM-DD.json             current record for each published date
`- publication_bundles/BUNDLE_ID/           immutable validated bundle audit copy

generated/
+- publisher.lock                           shared importer and presentation-publisher lock
+- staging/                                 disposable content-import transaction stages
+- site-staging/                            disposable presentation-build stages
`- releases/
   +- BUNDLE_ID/                            immutable content release
   `- site-SOURCE_ID/                       immutable presentation release and receipt

site                                       atomic symlink to the served complete release
```

`generated/` and `site` are ignored by Git. A content release is identified by its bundle ID. A
manual presentation release is identified by the SHA-256 identity of the staged MkDocs source and
contains `.deployment.json`, which records the base bundle it presents. Neither release form is
rewritten after promotion.

## Documentation map

- [operations.md](operations.md) provides import, manual publication, service, and recovery steps.
- [CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md) describes ownership, data flow, release contracts,
  and verification boundaries.
- [INSTALL.md](INSTALL.md) and [USAGE.md](USAGE.md) describe environment setup and command use.
- [CHANGELOG.md](CHANGELOG.md) records dated behavior and contract changes.
- [E2E_TESTS.md](E2E_TESTS.md), [PYTEST_STYLE.md](PYTEST_STYLE.md), and
  [REPO_STYLE.md](REPO_STYLE.md) define validation and repository conventions.

## Where to add work

- Put bundle-validation changes in [scripts/import_publication_bundle.py](../scripts/import_publication_bundle.py)
  and its focused tests in [tests/test_publication_bundle_import.py](../tests/test_publication_bundle_import.py).
- Put content transaction and recovery changes in
  [scripts/publication_transaction.py](../scripts/publication_transaction.py).
- Put manual presentation deployment changes in
  [scripts/site_deployment.py](../scripts/site_deployment.py) and
  [tests/test_site_deployment.py](../tests/test_site_deployment.py).
- Put theme, CSS, navigation, and brand assets in [mkdocs.yml](../mkdocs.yml), [docs/](.), and
  [docs/assets/](assets/); publish them with [publish_site.sh](../publish_site.sh).
- Put static serving changes in
  [deploy/vosslab-daily-blog.service](../deploy/vosslab-daily-blog.service).
- Put persistent documentation in [docs/](.) and link it from [README.md](../README.md) when it
  serves operators or contributors.

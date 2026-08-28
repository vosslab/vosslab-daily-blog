# File structure

## Active publisher files

```text
scripts/
  __init__.py
  import_publication_bundle.py   complete generator-facing importer
  publication_record.py         exact publication-receipt schema and value validation
  publication_transaction.py    global lock, ordered commit, rollback, and crash recovery
  render_publication_status.py   publication v2 status rendering
  validate_daily_post.py         deterministic article policy
  validate_editorial_projection.py exact excerpt and packet binding policy
deploy/
  vosslab-daily-blog.service     static server on port 8016
docs/
  blog/posts/YYYY-MM-DD.md       current imported source posts
  assets/publications/           imported evidence assets
  status.md                      importer-rendered current status
  operations.md                  operator runbook
data/
  publications/YYYY-MM-DD.json  current publisher record
  publication_bundles/BUNDLE_ID validated audit copy
generated/
  publisher.lock                 publisher-global runtime transaction lock
  staging/                       temporary complete proposals
  releases/BUNDLE_ID/            immutable built sites
site                             atomic pointer to the served release
tests/
  test_publication_bundle_import.py
  test_publication_status.py
```

## Bundle input

```text
PATH/
  bundle.json
  evidence.json
  editorial_projection.json
  post.md
  assets/
```

The input stays producer-owned. The importer copies validated contract files into the immutable
publisher archive rather than relying on the producer path after publication.

## Runtime ownership

- `docs/` is the complete MkDocs source and changes only after a staged strict build succeeds.
- `data/publications/` holds one current record per date.
- `data/publication_bundles/` and `generated/releases/` use bundle IDs and are immutable.
- `generated/staging/` is disposable after success or failure.
- `site` is a relative symlink switched as the transaction's final operation.

## Change placement

- Put bundle schema and staging changes in `scripts/import_publication_bundle.py`.
- Put lock, commit-ordering, rollback, and crash-recovery changes in
  `scripts/publication_transaction.py`.
- Put publication-receipt schema and value rules in `scripts/publication_record.py`.
- Put post content policy in `scripts/validate_daily_post.py`.
- Put projection binding and exact-excerpt policy in `scripts/validate_editorial_projection.py`.
- Put publication-record status rendering in `scripts/render_publication_status.py`.
- Put static serving changes in `deploy/vosslab-daily-blog.service`.
- Put site content and theme changes in `docs/` and `mkdocs.yml`.
- Add importer contract and failure-preservation coverage to
  `tests/test_publication_bundle_import.py`.
- Coordinate any bundle or evidence schema version change with `vosslab-podcast`.

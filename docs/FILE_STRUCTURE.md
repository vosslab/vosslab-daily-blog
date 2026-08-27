# File structure

## Active publisher files

```text
scripts/
  __init__.py
  import_publication_bundle.py   complete generator-facing importer
  validate_daily_post.py         deterministic article policy
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
  staging/                       temporary complete proposals
  releases/BUNDLE_ID/            immutable built sites
site                             atomic pointer to the served release
tests/
  test_publication_bundle_import.py
```

## Bundle input

```text
PATH/
  bundle.json
  evidence.json
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

Historical `data/daily/`, `data/editorial/`, and `data/run/` directories predate the bundle contract.
They are retained as audit material and are not inputs to new publication runs.

## Change placement

- Put bundle schema and transaction changes in `scripts/import_publication_bundle.py`.
- Put post content policy in `scripts/validate_daily_post.py`.
- Put static serving changes in `deploy/vosslab-daily-blog.service`.
- Put site content and theme changes in `docs/` and `mkdocs.yml`.
- Add importer contract and failure-preservation coverage to
  `tests/test_publication_bundle_import.py`.
- Coordinate any bundle or evidence schema version change with `vosslab-podcast`.

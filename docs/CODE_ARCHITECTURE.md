# Code architecture

## Overview

This repository is the publisher half of a two-repository work-log system. It accepts a complete,
producer-owned publication bundle, validates its evidence and editorial contract independently, and
serves a strict MkDocs build on the local network. It preserves the last good release while bundle
validation, source staging, or MkDocs building fails.

The producer repository owns evidence collection, generation, Git evidence, and scheduling. This
repository owns publication validation, current MkDocs source, immutable records and releases, the
served `site` pointer, and the static server. The complete handoff contract and recovery commands
are documented in [operations.md](operations.md).

## Major components

- [scripts/import_publication_bundle.py](../scripts/import_publication_bundle.py) validates a
  physical bundle directory, stages a proposed source tree, and installs a new content release.
- [scripts/validate_daily_post.py](../scripts/validate_daily_post.py) and
  [scripts/validate_editorial_projection.py](../scripts/validate_editorial_projection.py) enforce
  deterministic post, evidence, projection, and asset rules.
- [scripts/publication_record.py](../scripts/publication_record.py) defines the validated
  publication-record schema. [scripts/render_publication_status.py](../scripts/render_publication_status.py)
  derives the status page exclusively from those records.
- [scripts/publication_transaction.py](../scripts/publication_transaction.py) owns the shared lock,
  ordered content-release commit, rollback, and interrupted-import recovery.
- [scripts/site_deployment.py](../scripts/site_deployment.py) owns presentation-source snapshots,
  strict MkDocs builds, source-identified presentation releases, and atomic pointer promotion.
  [publish_site.sh](../publish_site.sh) is its small operator entry point.
- [mkdocs.yml](../mkdocs.yml), [docs/index.md](index.md),
  [docs/stylesheets/extra.css](stylesheets/extra.css), and
  [docs/assets/brand/vosslab-work-log-mark.svg](assets/brand/vosslab-work-log-mark.svg) define the
  Material theme, newspaper presentation, and shared logo/favicon surface.
- [deploy/vosslab-daily-blog.service](../deploy/vosslab-daily-blog.service) uses Python's static
  HTTP server to serve the `site` symlink on port 8016. It is independent of generation and import.

## Bundle import flow

```text
vosslab-podcast                         vosslab-daily-blog

evidence -> projection -> authors -> bundle
                                            |
                                            v
                                validate contract and article
                                            |
                                            v
                             stage complete source + strict build
                                            |
                                            v
                     immutable archive + content release + record
                                            |
                                            v
                                 atomically replace site pointer
```

The importer accepts the bundle, evidence, and editorial-projection schemas named in the bundle
contract. It independently checks canonical identities, hashes, report date and timezone, selected
post identity, evidence authority, exact excerpts, repository coverage, provenance, and confined
assets. Article validation then checks front matter, evidence comments, excerpts, and image
provenance before the importer writes publisher state.

Under `generated/publisher.lock`, the importer copies `docs/` into a unique proposal below
`generated/staging/`, applies the validated post and assets, renders `status.md` from existing plus
proposed publication records, and runs a strict MkDocs build. The transaction module moves the
immutable content release and audit archive into place, replaces `site` atomically, and writes the
publication record last. Its transaction marker lets the next import recover an interrupted commit.

## Presentation publication flow

`./publish_site.sh` publishes repository-owned cosmetic or navigation changes without changing
bundle content. The command invokes [scripts/site_deployment.py](../scripts/site_deployment.py),
which takes the same publisher lock and first reconciles any interrupted content import.

Before snapshotting, the presentation publisher verifies that each importer-owned
`docs/blog/posts/YYYY-MM-DD.md` byte-matches its archived `post.md`, and that `docs/status.md`
matches the installed records. It also rejects symlinks in the MkDocs source. This boundary keeps
the manual path responsible for presentation only; content, evidence assets, records, and status
remain importer-owned.

The publisher snapshots `docs/` and [mkdocs.yml](../mkdocs.yml) below `generated/site-staging/`.
It hashes the staged relative paths and bytes, builds with `python -m mkdocs build --strict`, and
promotes the complete result as `generated/releases/site-SOURCE_ID/`. The release includes an exact
`.deployment.json` receipt containing the schema version, source identity, release ID, build time,
and newest base bundle ID. Promotion atomically changes `site` only after the release exists.

An unchanged snapshot reuses the same immutable presentation release. A content importer accepts a
served presentation release only when its receipt binds it to the recorded base bundle; otherwise,
the importer reports incomplete state instead of treating an arbitrary site pointer as valid.

## State and recovery

`data/publications/YYYY-MM-DD.json` is the current validated record for a report date. It names the
bundle identity, generator provenance, immutable archive inputs, source post, content release, and
installation time. `data/publication_bundles/BUNDLE_ID/` retains the validated input files, while
`generated/releases/BUNDLE_ID/` retains the content build. Both are immutable.

Content imports use `generated/staging/`; manual presentation builds use
`generated/site-staging/`. These directories are disposable transaction workspaces. The `site`
symlink always identifies the complete release currently served. The static server resolves that
symlink for each request, so either successful promotion needs no server restart.

## Verification

- [tests/test_publication_bundle_import.py](../tests/test_publication_bundle_import.py) covers
  bundle validation, date immutability, idempotency, and content transaction failure preservation.
- [tests/test_site_deployment.py](../tests/test_site_deployment.py) covers immutable presentation
  releases, snapshot identity, pointer promotion, imported-source protection, and build failures.
- [tests/test_brand_assets.py](../tests/test_brand_assets.py) checks the shared SVG brand surface.
- [tests/test_markdown_links.py](../tests/test_markdown_links.py) verifies local documentation links.
- The operator runs `./publish_site.sh` to perform a strict staged build, promote it, and check the
  locally served homepage and status route.

## Extension points

- Add bundle, evidence, projection, or record schemas as explicit new versions and coordinate the
  producer change with `vosslab-podcast`.
- Add deterministic content-policy checks beside
  [scripts/validate_daily_post.py](../scripts/validate_daily_post.py) with focused tests.
- Add presentation behavior in [mkdocs.yml](../mkdocs.yml),
  [docs/stylesheets/extra.css](stylesheets/extra.css), or [docs/assets/](assets/) and publish it
  through [publish_site.sh](../publish_site.sh).
- Add static-service changes in
  [deploy/vosslab-daily-blog.service](../deploy/vosslab-daily-blog.service), then reload the user
  service as described in [operations.md](operations.md).

## Known gaps

- Verify the installed user-service unit remains synchronized with
  [deploy/vosslab-daily-blog.service](../deploy/vosslab-daily-blog.service) after service changes.

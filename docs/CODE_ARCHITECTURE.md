# Code architecture

## Overview

This repository is the publisher half of a two-repository work-log system. It accepts one complete
producer-owned publication bundle, independently validates its editorial evidence authority, and
serves a strict MkDocs build on the local network. A failed import, source stage, or build preserves
the last good release.

`vosslab-podcast` owns collection, evidence, model execution, the survivor selection, bundle
creation, and the 04:00 America/Chicago producer timer. This repository owns sealed-bundle import,
publication records, date-owned content releases, the current MkDocs source, the `site` pointer,
and static serving. [operations.md](operations.md) documents the operating boundary.

## Major components

- [scripts/import_publication_bundle.py](../scripts/import_publication_bundle.py) receives a
  sealed stdin envelope or a deliberate physical bundle directory, validates it, and coordinates a
  date-owned content import.
- `scripts/publication_import_cli.py` owns the automated `--bundle-stdin`, manual `--bundle`, and
  explicit `--replace-existing` command contract.
- `scripts/bundle_snapshot.py` creates one bounded, checksum-verified transfer snapshot or one
  held no-follow directory snapshot. All validation, staging, archival, and idempotency checks use
  that sealed view.
- `scripts/publication_surface.py` validates the v1 survivor-scoped publication surface. Its
  canonical identity binds the aggregate packet, selected packets and repositories, source
  artifacts, projection, allowed evidence IDs, and the exact allowed image paths.
- [scripts/validate_daily_post.py](../scripts/validate_daily_post.py) and
  [scripts/validate_editorial_projection.py](../scripts/validate_editorial_projection.py) enforce
  the selected post's deterministic source, evidence, projection, and image rules.
  `scripts/publication_source_safety.py` provides the executable canonical-source policy bound by
  the bundle.
- `scripts/publication_staging.py` derives the staged post, asset copy, current v6 record, audit
  archive, and rendered-page check from the sealed bundle and its publication surface.
- [scripts/publication_record.py](../scripts/publication_record.py) validates current publication
  v6 receipts and the v5 and v3 read-only historical receipt paths.
  `scripts/publication_article_projection.py` produces the reader-body projection and verifies the
  single built article, including its surface-authorized image scope.
- [scripts/publication_transaction.py](../scripts/publication_transaction.py) owns the importer
  lock, ordered install, rollback, and interrupted-import recovery.
- [scripts/site_deployment.py](../scripts/site_deployment.py) publishes presentation-only changes
  through strict MkDocs builds and atomic pointer promotion. [publish_site.sh](../publish_site.sh)
  is its operator entry point.
- [mkdocs.yml](../mkdocs.yml), [docs/index.md](index.md),
  [docs/stylesheets/extra.css](stylesheets/extra.css), and
  [docs/assets/brand/vosslab-work-log-mark.svg](assets/brand/vosslab-work-log-mark.svg) define the
  reader presentation. [deploy/vosslab-daily-blog.service](../deploy/vosslab-daily-blog.service)
  serves the `site` pointer on port 8016.

## Bundle import flow

```text
vosslab-podcast                           vosslab-daily-blog

survivor scope -> v9 bundle -> sealed snapshot
                                               |
                                               v
                                validate surface, evidence, and post
                                               |
                                               v
                          stage only surface-authorized post assets
                                               |
                                               v
                         strict build and rendered article verification
                                               |
                                               v
                    archive + v6 record + date-owned release + site pointer
```

The v9 bundle contains `bundle.json`, `evidence.json`, `repository_roster.json`,
`editorial_projection.json`, `publication_surface.json`, `post.md`, and the exact declared assets.
The manifest hashes each object and binds `publication_surface.json` by both SHA-256 and surface
ID. The surface is immutable publication authority: accepted evidence IDs must exactly match
projection excerpts, and every accepted image must be one selected screenshot with its exact
bundle asset path and reader publish path.

The importer rejects malformed, duplicate, truncated, trailing, oversized, checksum-invalid, or
path-unsafe transfer input before validation. It then checks report identity, selected artifact,
roster and lifecycle provenance, evidence, projection, source-safety policy, and the surface.
The asset manifest must exactly equal the surface image set; it is not inferred from all aggregate
packet screenshots. Post validation uses the same surface for evidence and image admission.

Under `generated/publisher.lock`, staging copies `docs/` into a unique proposal, writes the
validated post, and copies only surface-authorized assets. It builds a v6 publication record that
stores the surface manifest, surface ID, surface SHA-256, selected artifact, and canonical
reader-body digest. Before promotion, the strict build verifies the full article projection and
ensures article-local rendered images remain within the surface's allowed publish paths.

The transaction installs the date-owned audit archive and content release, atomically switches
`site`, and writes the record last. `report_date` remains the sole publication identity; bundle and
surface hashes are integrity evidence rather than a second publication namespace.

## Presentation publication flow

[publish_site.sh](../publish_site.sh) publishes checked-in navigation, CSS, and brand changes
without changing imported content. [scripts/site_deployment.py](../scripts/site_deployment.py)
shares the importer lock, reconciles interrupted imports, validates that importer-owned source
matches its archive and records, builds a source-identified release strictly, and atomically
promotes `site`.

Presentation deployment rechecks every imported article against its archived reader-body projection
and record. Current v6 records additionally anchor the installed publication surface. This keeps
the manual path responsible for presentation while imported post, evidence assets, archive, status,
and records remain importer-owned.

## State and recovery

`data/publications/YYYY-MM-DD.json` is the current receipt for one report date. New imports write
`vosslab.daily-blog.publication.v6` records. They bind the bundle, selected artifact, reader-body
digest, generator provenance, and the archived `publication_surface.json` identity and hash.
Existing v5 and v3 receipts are retained only for reading and redeploying historical material; a
replacement with a v9 bundle writes a v6 receipt.

`data/publication_bundles/YYYY-MM-DD/` stores the accepted v9 input. The disposable import and
presentation workspaces are `generated/staging/` and `generated/site-staging/`; date-owned content
releases live below `generated/releases/YYYY-MM-DD/`. `site` always identifies the complete release
currently served, so promotion needs no static-server restart.

## Verification

- [tests/test_publication_bundle_import.py](../tests/test_publication_bundle_import.py) covers
  sealed bundle admission, surface-controlled assets, date-owned idempotency, replacement, and
  transaction preservation.
- [tests/test_validate_daily_post.py](../tests/test_validate_daily_post.py) covers source post,
  evidence, and surface image admission.
- `tests/test_publication_article_projection.py` covers canonical reader-body and rendered-article
  verification.
- [tests/test_site_deployment.py](../tests/test_site_deployment.py) covers immutable presentation
  releases, source protection, pointer promotion, and build failures.
- [tests/test_markdown_links.py](../tests/test_markdown_links.py) verifies local documentation
  links.

The operator uses [publish_site.sh](../publish_site.sh) for a strict staged build and local page
checks. A complete same-date producer rerun is one-time acceptance evidence; the permanent tests
remain offline deterministic contract checks.

## Extension points

- Add a producer/publisher contract as an explicit new schema version, then update producer and
  publisher together.
- Put survivor-scope validation in `scripts/publication_surface.py` and exercise it through the
  importer and staged-rendering tests.
- Put deterministic post-policy checks beside
  [scripts/validate_daily_post.py](../scripts/validate_daily_post.py).
- Put reader presentation changes in [mkdocs.yml](../mkdocs.yml), [docs/](.), or
  [docs/assets/](assets/) and publish them through [publish_site.sh](../publish_site.sh).

## Known gaps

- Verify the installed user-service unit remains synchronized with
  [deploy/vosslab-daily-blog.service](../deploy/vosslab-daily-blog.service) after unit changes.

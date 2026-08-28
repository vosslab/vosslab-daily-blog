# Publication file formats

This reference describes the durable files exchanged and retained by the publisher. The producer
creates a complete bundle; the publisher validates it, copies its four core files into an immutable
archive, and writes its own publication and presentation receipts. The operating model and ownership
boundary are described in [operations.md](operations.md), and implementation responsibilities are in
[CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md).

## Format conventions

- JSON files are UTF-8 JSON objects. Contract validators reject unknown and missing top-level
  fields where the schema defines an exact field set.
- SHA-256 identities use 64 lowercase hexadecimal characters.
- Content-addressed JSON identities hash a compact, sorted-key, ASCII-escaped JSON rendering.
- Timestamps are timezone-aware ISO-8601 strings; publisher receipts use whole-second UTC values
  ending in `Z`.
- Paths in a producer bundle use forward slashes and are confined to the physical bundle directory.
  Symlinks are rejected for the bundle, its declared files, and its asset tree.

Schema names are versioned contracts. A producer and publisher change them together; accepting a
new shape under an existing schema name is not supported.

## Producer bundle

A bundle is one physical directory passed to `scripts/import_publication_bundle.py --bundle`. Its
required core layout is:

```text
BUNDLE_ID/
  bundle.json
  evidence.json
  editorial_projection.json
  post.md
  assets/
    NAME
```

`bundle.json` has schema version `vosslab.daily-blog.bundle.v2`. It binds the report identity and
the exact bytes or canonical JSON values of the other bundle artifacts.

| Field | Meaning |
| --- | --- |
| `bundle_id` | SHA-256 identity of the full manifest except this field. |
| `report_date`, `timezone`, `created_at` | Publication identity and creation time. |
| `generator` | Producer run ID, 64-character revision fingerprint, and supported generator version. |
| `contracts` | Evidence, projection, prompt, and rubric contract versions. |
| `evidence`, `editorial_projection`, `post` | Fixed filenames plus their identities and hashes. |
| `assets` | Every bundled screenshot asset and its evidence provenance. |
| `candidates`, `referee` | Two validation summaries and the anonymous A/B selection of the final post. |

The core filenames are fixed: `evidence.json`, `editorial_projection.json`, and `post.md`. Asset
files are optional, but `assets/` is always physical and its complete contents must exactly match
the manifest. Each asset path is `assets/NAME`; its bytes, Git blob provenance, screenshot evidence
ID, and resulting post-relative publish path are validated.

## Evidence packet

`evidence.json` uses `vosslab.daily-blog.evidence.v3`. It is the source packet from which the
editorial projection and post provenance are derived.

| Field | Meaning |
| --- | --- |
| `report_date`, `timezone`, `complete` | Must match the bundle; `complete` is `true`. |
| `collection_limits` | Producer-declared collection bounds. |
| `mirrors`, `activity` | Typed repository mirror and attributed-commit provenance. |
| `items` | Ordered evidence records, highest authority first. |
| `packet_id` | SHA-256 identity of this object without `packet_id`. |

Each item has an `evidence_id`, evidence kind and authority fields, repository and Git object
provenance, source text and hash, acquisition metadata, and optional screenshot asset and publish
paths. The publisher recomputes the item identity and content hash. It permits only the defined
evidence kinds and requires their canonical authority rank and level.

## Editorial projection

`editorial_projection.json` uses `vosslab.daily-blog.editorial-projection.v1`. It is a bounded,
inspectable selection of the evidence packet rather than a new source of facts.

| Field | Meaning |
| --- | --- |
| `projection_id` | SHA-256 identity of this object without `projection_id`. |
| `packet_id` | Exact identity of the accompanying evidence packet. |
| `report_date`, `timezone` | Must match the bundle and evidence packet. |
| `projection_limits` | Positive bounds for rendered context, excerpts, and commit subjects. |
| `repositories` | One card for every active evidence repository. |
| `excerpts` | Exact, hash-checked slices of evidence items. |

Every repository card is checked against evidence activity. Every excerpt is checked against its
source evidence ID, provenance fields, byte-range slice, content hash, and derived `excerpt_id`.

## Daily post

`post.md` is UTF-8 Markdown with opening YAML front matter. The importer installs its exact bytes
as `docs/blog/posts/YYYY-MM-DD.md`; presentation publication verifies that this checked-in post has
not drifted from the immutable archive.

```yaml
---
date: YYYY-MM-DD
slug: lowercase-hyphenated-slug
generator_run: PRODUCER_RUN_ID
evidence_manifest: evidence.json
editorial_projection: editorial_projection.json
---
```

The post contains exactly one descriptive H1, at least one H2, and exactly one `<!-- more -->`
excerpt marker. Narrative sections cite projection evidence with comments such as
`<!-- evidence: ev-0123456789abcdef -->`. Embedded images must be the evidence-backed asset paths
declared by the bundle; fenced payloads are not accepted.

## Publisher records

After a successful import, the publisher writes one immutable-input record at
`data/publications/YYYY-MM-DD.json`. It uses `vosslab.daily-blog.publication.v2` and has exactly:

`schema_version`, `report_date`, `timezone`, `bundle_id`, `generator_run`, `generator_revision`,
`evidence_manifest`, `editorial_projection_manifest`, `post_path`, `release_id`, and `imported_at`.

The record repeats the accepted bundle identity and names its archived evidence and projection,
installed post, and content release. `release_id` equals `bundle_id`; the derived paths must match
the report date and bundle ID exactly. The record is the publisher's current receipt for that date,
not a producer input.

The importer archives `bundle.json`, `evidence.json`, `editorial_projection.json`, and `post.md`
under `data/publication_bundles/BUNDLE_ID/`, and installs the corresponding built content release
at `generated/releases/BUNDLE_ID/`. Treat both locations as immutable. Temporary transaction paths
under `generated/staging/` are disposable and are not an interface.

## Presentation receipt

`./publish_site.sh` may publish repository-owned presentation changes while imported content stays
unchanged. Its immutable release is `generated/releases/site-SOURCE_ID/` and contains
`.deployment.json` with schema `vosslab.daily-blog.site-deployment.v1`.

| Field | Meaning |
| --- | --- |
| `source_identity` | SHA-256 identity of the staged `mkdocs.yml` plus every staged `docs/` path and file hash. |
| `release_id` | `site-` followed by `source_identity`. |
| `base_bundle_id` | Accepted bundle served by this presentation release, or empty before any import. |
| `built_at` | Whole-second UTC build timestamp. |
| `schema_version` | Deployment receipt schema name. |

The `site` symlink is the mutable pointer to a complete release. It is not a document to edit.
The publisher changes it atomically only after a strict MkDocs build and receipt validation.

## Inspect and validate

Inspect a current accepted bundle through its record, then validate an incoming bundle before import:

```bash
python3.13 -m json.tool data/publications/YYYY-MM-DD.json
python3.13 -m json.tool data/publication_bundles/BUNDLE_ID/bundle.json
source source_me.sh && python3.13 scripts/validate_daily_post.py \
  --candidate /path/to/bundle/post.md \
  --evidence /path/to/bundle/evidence.json \
  --projection /path/to/bundle/editorial_projection.json \
  --bundle /path/to/bundle/bundle.json
```

The importer performs the complete cross-file validation and strict staged build. Its permanent
contract coverage is in `tests/test_publication_bundle_import.py`; presentation receipt coverage is
in `tests/test_site_deployment.py`.

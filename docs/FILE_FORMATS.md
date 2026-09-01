# Publication file formats

This reference defines the durable producer-to-publisher handoff and the receipts retained by the
publisher. The producer creates one complete bundle and normally sends its sealed bytes through
standard input. The publisher validates a bounded snapshot, archives the accepted bytes, and writes
publisher-owned receipts. [operations.md](operations.md) describes the operating boundary; [CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md)
maps the implementation.

## Format conventions

- JSON artifacts are UTF-8 JSON objects with closed, versioned top-level schemas.
- SHA-256 identities use 64 lowercase hexadecimal characters. Canonical JSON identities use compact,
  sorted-key, ASCII-escaped JSON.
- Timestamps are timezone-aware ISO-8601 strings. Publisher receipts use whole-second UTC timestamps
  ending in `Z`.
- Producer paths use forward slashes and are confined below the physical bundle root. The root,
  artifacts, and asset directory are regular physical filesystem objects; links are not accepted.

A schema name identifies one exact contract. Producer and publisher change a schema name together;
they do not admit a new shape under an existing name.

## Sealed transfer and bundle v9

Automated producer publication invokes `scripts/import_publication_bundle.py --bundle-stdin`. The
transfer is exact binary data: ASCII magic `vosslab.daily-blog.bundle-transfer.v1\n`, an unsigned
eight-byte big-endian canonical-JSON-header length, that canonical header, then the ordered entry
bytes. The header has exact `schema_version`, `report_date`, `bundle_sha256`, and `entries` fields;
each entry has `path`, `size`, and SHA-256. It names every six core artifact and every direct asset
once, in canonical order. The importer validates the header and every entry hash, requires EOF after
the final entry, and rejects malformed, duplicate, truncated, trailing, or oversized input.

The full envelope is limited to 128 MiB. Its contained artifacts remain limited to 128 KiB per JSON
file, 2 MiB for `post.md`, and 8 MiB per declared asset. The cap accommodates the production policy's
maximum screenshot set without making the receiver retain unbounded standard-input bytes.

`--bundle PATH` remains the manual operator interface. It uses the same bundle-v9 validation after a
held no-follow descriptor snapshot of the physical directory.

The importer accepts one directory passed to `scripts/import_publication_bundle.py --bundle`. Its
physical layout has six core artifacts and one physical asset directory:

```text
publication/
  bundle.json
  evidence.json
  repository_roster.json
  editorial_projection.json
  publication_surface.json
  post.md
  assets/
    NAME
```

`bundle.json` uses `vosslab.daily-blog.bundle.v9` and has exactly these 16 top-level fields:

| Field | Meaning |
| --- | --- |
| `schema_version` | Exact bundle-v9 schema name. |
| `bundle_sha256` | SHA-256 of the manifest with this field omitted. |
| `best_artifact_id` | Promoted `artifact-` identity for the one published post. |
| `report_date`, `timezone`, `created_at` | Date-owned publication identity, IANA timezone, and producer timestamp. |
| `generator` | Producer run ID, 64-character source/config revision, and generator version. |
| `contracts` | Evidence, projection, prompt, rubric, candidate-validation, and source-safety identities. |
| `evidence` | Fixed `evidence.json` path, packet identity, and canonical JSON hash. |
| `repository_roster` | Fixed `repository_roster.json` path, roster identity, and canonical JSON hash. |
| `editorial_projection` | Fixed `editorial_projection.json` path, projection identity, and canonical JSON hash. |
| `publication_surface` | Fixed `publication_surface.json` path, surface identity, and canonical JSON hash. |
| `post` | Fixed `post.md` path, byte hash, and `artifact_id` equal to `best_artifact_id`. |
| `assets` | The exact survivor-scoped direct `assets/NAME` files, with byte hash and evidence provenance. |
| `maker_activation` | Accepted activation ID and editorial prompt-contract checksum. |
| `editorial_prompt_contract` | The complete prompt-contract object bound to that activation. |

The manifest contains the promoted final artifact, not editorial working material. It has no
`candidates` or `referee` field. Candidate generation, review, and promotion remain producer-owned;
the publisher admits only the selected post whose artifact identity cross-binds to the manifest.

The activation and prompt-contract fields must equal the publisher's sealed maker activation receipt.
The contract's candidate-validation policy is also checked through `contracts`; this proves the
accepted editorial policy identity without importing intermediate candidate output.

### Publication source safety

Bundle v9 `contracts.publication_source_safety` must exactly equal policy
`publication_source_safety.v1` with vector SHA-256
`d50166736d79be7f7715cc0f7585fac71dfb2aecc1c631b10e01aeca2fb63c6b`, over its 35-case
executable corpus. This is a producer-publisher contract identity, not an optional advisory. The
publisher applies its own copy of the policy to the sealed `post.md` before creating a stage.

The policy accepts complete front matter and ordinary Markdown. In active content it admits only
the `<!-- more -->` marker and exact evidence comments, survivor-scoped evidence-asset paths, and HTTPS
URLs to `github.com` or `api.github.com`. It rejects raw HTML, Markdown attribute lists, other HTML
comments, malformed links, credentials or nonstandard ports, and every other external or local
target. Code spans and fenced code remain inert examples rather than active document markup.

## Survivor-scoped publication surface

`publication_surface.json` uses `vosslab.daily-blog.publication-surface.v1`. It is the immutable
authority shared by Stage 6, bundle construction, import, post admission, staging, and built-page
verification. It prevents an aggregate evidence packet from silently widening the survivor set.

The surface has exactly these fields:

| Field | Meaning |
| --- | --- |
| `schema_version` | Exact publication-surface schema name. |
| `surface_id` | SHA-256 of the canonical surface object with this field omitted. |
| `report_date`, `timezone` | Must equal the bundle, evidence packet, and projection report identity. |
| `aggregate_packet_id` | Exact `packet_id` of the accompanying complete evidence packet. |
| `source_packet_ids` | Canonically sorted, unique SHA-256 identities of the survivor source packets. |
| `repositories` | Canonically sorted repository coverage, exactly matching the evidence activity coverage. |
| `source_artifacts` | Canonically ordered survivor attestations. Each has exactly `kind`, `artifact_id`, and `content_hash`; there is one `DailyOutline` and at least one `RepoStory`. |
| `editorial_projection_id` | Exact identity of the accompanying projection. |
| `allowed_evidence_ids` | Canonically sorted, unique evidence IDs; exactly the projection excerpt IDs. |
| `allowed_images` | Canonically ordered, structured image authorities described below. |

Each `allowed_images` entry has exactly `evidence_id`, `asset_path`, and `publish_path`. The
`evidence_id` must be one allowed screenshot evidence ID, and both paths must equal that evidence
item's sealed values. `asset_path` values and `publish_path` values are each unique. The canonical
order is the tuple `(evidence_id, asset_path, publish_path)`.

The bundle's `publication_surface` manifest must name `publication_surface.json`, repeat its
`surface_id`, and carry the canonical JSON SHA-256. The importer validates all three bindings before
using the surface. Its `assets` manifest must be exactly the surface's `asset_path` set: neither a
survivor asset may be omitted nor an unselected aggregate-packet screenshot admitted. The post and
the rendered Material article may use only the corresponding `publish_path` set.

## Bounded descriptor snapshot

Before parsing producer data, the importer opens the bundle root with a no-follow directory
descriptor. It reads `bundle.json`, the other JSON artifacts, `post.md`, and every declared asset
through that held root rather than reopening producer pathnames later in the import.

| Artifact | Maximum bytes |
| --- | ---: |
| Each JSON artifact | 128 KiB |
| `post.md` | 2 MiB |
| Each asset | 8 MiB |
| Complete stdin transfer | 128 MiB |

The manifest declares the complete direct contents of `assets/`. An extra, missing, linked, or
nonregular asset fails validation. The archive, staging tree, idempotency check, and final install
consume the same sealed bytes.

## Evidence and projection

`evidence.json` uses `vosslab.daily-blog.evidence.v4`. It binds complete activity, mirrors,
authority-ranked items, source content, and `packet_id` to the bundle's report identity. The
publisher recomputes item and packet identities, validates the owner-qualified repository roster and
provenance, and verifies hashes before accepting the packet.

`editorial_projection.json` uses `vosslab.daily-blog.editorial-projection.v2`. It is a bounded,
inspectable selection of the evidence packet. Its `projection_id`, `packet_id`, report identity,
repository cards, and hash-checked excerpts must agree with the accompanying evidence and manifest.

## Selected post and assets

`post.md` is UTF-8 Markdown with the closed front-matter contract below. The publisher installs its
validated bytes at `docs/blog/posts/YYYY-MM-DD.md` and verifies those bytes on identical retries.

```yaml
---
date: YYYY-MM-DD
slug: lowercase-hyphenated-slug
generator_run: PRODUCER_RUN_ID
evidence_manifest: evidence.json
editorial_projection: editorial_projection.json
---
```

The post has one descriptive H1, at least one H2, one `<!-- more -->` marker, and evidence comments
such as `<!-- evidence: ev-0123456789abcdef -->`. Images name only the exact survivor-scoped,
evidence-backed publish paths. The post manifest's `artifact_id` is the sole admitted
selected-artifact identity.

## Publisher receipts and archives

The importer archives the held snapshot under `data/publication_bundles/YYYY-MM-DD/`: the six core
artifacts and every declared asset retain their bundle-relative paths. It installs the selected post,
date-owned built release, and record as one transaction. The report date is the sole publication
identity; a bundle digest is integrity evidence, not a second publication namespace.

New `data/publications/YYYY-MM-DD.json` records use `vosslab.daily-blog.publication.v6` with exactly these
fields:

`schema_version`, `report_date`, `timezone`, `bundle_sha256`, `best_artifact_id`,
`article_body_sha256`, `generator_run`, `generator_revision`, `evidence_manifest`,
`editorial_projection_manifest`, `publication_surface_manifest`, `publication_surface_id`,
`publication_surface_sha256`, `post_path`, and `imported_at`.

This is the current publisher receipt for that date. It points to the archived evidence, projection,
and surface plus the installed post. `publication_surface_id` and
`publication_surface_sha256` bind the receipt to the sealed survivor authority;
`article_body_sha256` binds the canonical ordered visible reader projection rendered from that post.
The importer verifies the corresponding built Material article before writing the record, and
presentation deployment repeats the verification before promotion. The record is written last as the
transaction commit marker.
The import command reports one transient JSON result with `status`, `report_date`, and
`bundle_sha256`: `imported`, `idempotent`, or `replaced`.

The reader-visible site has its own immutable receipt. A presentation release at
`generated/releases/site-SOURCE_ID/` carries `.deployment.json` with schema
`vosslab.daily-blog.site-deployment.v2`, `source_identity`, `release_id`, `base_report_date`,
`built_at`, and `schema_version`. The mutable `site` link changes only after the complete
receipt-bound release exists.

An unchanged accepted bundle is idempotent only when its archived snapshot, installed post,
date-owned release, record, and served site remain coherent. `--replace-existing` stages and validates
a complete replacement, then exchanges stable date paths and writes the new publication-v6 record last.

Existing `vosslab.daily-blog.publication.v5` and `vosslab.daily-blog.publication.v3` receipts remain
supported solely for reading already-published state and rebuilding its presentation release. They
are not accepted new-import schemas. A replacement imports bundle v9 and writes a v6 receipt. Their
retained bundle-v8 archives, historical receipts, and posts remain read-only: the compatibility path
neither newly admits nor rewrites them.

## Inspect records

Inspect a current accepted publication and its retained manifest:

```bash
python3.13 -m json.tool data/publications/YYYY-MM-DD.json
python3.13 -m json.tool data/publication_bundles/YYYY-MM-DD/bundle.json
python3.13 -m json.tool data/publication_bundles/YYYY-MM-DD/publication_surface.json
```

The importer is the complete cross-file validator. Its offline deterministic contract coverage is in
[`tests/test_publication_bundle_import.py`](../tests/test_publication_bundle_import.py); presentation
receipt coverage is in [`tests/test_site_deployment.py`](../tests/test_site_deployment.py).

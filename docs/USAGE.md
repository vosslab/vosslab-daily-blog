# Usage

Use this repository to import a complete producer bundle, validate a bundle candidate, publish
checked-in presentation changes, and inspect the local static site. Generation and scheduling stay
in `vosslab-podcast`.

## Quick start

Normal publication is initiated by `vosslab-podcast`, which streams one sealed
`vosslab.daily-blog.bundle.v9` envelope to the publisher with `--bundle-stdin`. The publisher
accepts a canonical header and checksum-bound entries up to 128 MiB, then validates the bundle,
its survivor-scoped `publication_surface.json`, and the selected post before strictly building a
complete staged site, archiving its inputs, and atomically promoting the release. This is not a
manual shell command because the producer owns the envelope.

For inspection or a deliberate operator import, retain the physical-directory interface:

```bash
source source_me.sh && python3.13 scripts/import_publication_bundle.py \
  --bundle /absolute/path/to/out/vosslab/daily_blog/YYYY-MM-DD/publication
```

The command prints JSON with `status: imported` for a new accepted bundle or `status: idempotent`
for the exact already-installed content. To deliberately publish a replacement for an occupied
report date, use `--replace-existing`:

```bash
source source_me.sh && python3.13 scripts/import_publication_bundle.py \
  --bundle /absolute/path/to/out/vosslab/daily_blog/YYYY-MM-DD/publication \
  --replace-existing
```

The importer validates and strictly builds the complete replacement before atomically swapping the
date-owned post, archive, content release, record, and `site` pointer.

The two input modes are mutually exclusive. `--bundle-stdin` is the automated sealed transfer;
`--bundle PATH` requires physical non-symlinked files and is manual only. Both enforce 128 KiB JSON,
2 MiB post, 8 MiB asset, and 128 MiB complete-transfer limits.

Publish CSS, brand, reader navigation, or MkDocs configuration after editing the working tree:

```bash
./publish_site.sh
```

This command uses `python3.13` from `PATH`; activate an optional Python 3.13 virtual environment
before running it when dependencies should remain isolated. It snapshots the MkDocs inputs,
performs a strict build, creates an immutable presentation release, atomically switches `site`,
and checks the local `/` and `/status/` endpoints.

## Validate a bundle post

Validate the selected post together with its sealed evidence, projection, and bundle manifests
before an import:

```bash
source source_me.sh && python3.13 scripts/validate_daily_post.py \
  --candidate /path/to/bundle/post.md \
  --evidence /path/to/bundle/evidence.json \
  --projection /path/to/bundle/editorial_projection.json \
  --bundle /path/to/bundle/bundle.json
```

The validator prints `Daily post validation passed.` when front matter, narrative structure,
evidence references, projection excerpts, image provenance, and the v9 source-safety policy satisfy
the publisher contract. The importer additionally binds the post and staged assets to the sealed
survivor-scoped `publication_surface.json`. That policy is `publication_source_safety.v1`, digest
`d50166736d79be7f7715cc0f7585fac71dfb2aecc1c631b10e01aeca2fb63c6b`, over a 35-case executable
corpus. For v9, active Markdown may use only surface-approved evidence assets and canonical HTTPS GitHub
links; raw HTML, attribute syntax, and non-evidence comments are rejected.

## Inputs and outputs

| Workflow | Input | Output |
| --- | --- | --- |
| Bundle import | Automated sealed stdin envelope, or manual physical directory containing `bundle.json`, `evidence.json`, `repository_roster.json`, `editorial_projection.json`, `publication_surface.json`, `post.md`, and the surface-selected `assets/` | Current post in `docs/blog/posts/YYYY-MM-DD.md`, publication-v6 record with reader-body digest and surface identity in `data/publications/YYYY-MM-DD.json`, audit bundle in `data/publication_bundles/YYYY-MM-DD/`, and content release in `generated/releases/YYYY-MM-DD/` |
| Presentation publish | Current `docs/` tree and `mkdocs.yml` | Immutable `generated/releases/site-SOURCE_ID/` release and an updated `site` symlink |
| Post validation | Candidate Markdown plus bundle, evidence, and projection JSON files | Exit status and validation message; no publisher state changes |

The importer owns published posts, evidence assets, `docs/status.md`, publication records, and
content releases. `publish_site.sh` rejects drift in those importer-owned files, so use the producer
workflow for content changes and reserve manual publishing for presentation changes.

## Verify the running site

The enabled user service serves the current `site` pointer on port 8016. It follows pointer changes,
so a successful import or manual presentation publish needs no restart:

```bash
systemctl --user status vosslab-daily-blog.service
curl --fail http://aella.local:8016/
curl --fail http://aella.local:8016/status/
readlink site
```

For a source-only check that does not promote a release, run:

```bash
source source_me.sh && python3.13 -m mkdocs build --strict
```

See [operations.md](operations.md) for source recovery, service repair, idempotency guarantees, and
the producer-owned schedule.

## Historical records

New imports accept only bundle v9 and write publication v6 receipts. Installed bundle v8 material
and publication v5 or v3 receipts remain read-only history for presentation verification and
redeployment; they are not accepted as new producer input. A same-date replacement with a current
bundle upgrades that date to the v9/v6 contract.

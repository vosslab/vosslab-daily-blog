# Usage

Use this repository to import a complete producer bundle, validate a bundle candidate, publish
checked-in presentation changes, and inspect the local static site. Generation and scheduling stay
in `vosslab-podcast`.

## Quick start

Import one complete physical publication-bundle directory. The importer validates the bundle,
strictly builds a complete staged site, archives its inputs, and atomically promotes the release:

```bash
source source_me.sh && python3.13 scripts/import_publication_bundle.py \
  --bundle /absolute/path/to/out/vosslab/daily_blog/YYYY-MM-DD/RUN_ID
```

The command prints JSON with `status: imported` for a new accepted bundle or `status: idempotent`
for the exact already-installed bundle. A different bundle for an occupied report date fails.

Publish CSS, brand, reader navigation, or MkDocs configuration after editing the working tree:

```bash
./publish_site.sh
```

This command uses `python3.13` from `PATH`; activate an optional Python 3.13 virtual environment
before running it when dependencies should remain isolated. It snapshots the MkDocs inputs,
performs a strict build, creates an immutable presentation release, atomically switches `site`,
and checks the local `/` and `/status/` endpoints.

## Validate a bundle post

Validate the selected post and the three bundle JSON files before an import:

```bash
source source_me.sh && python3.13 scripts/validate_daily_post.py \
  --candidate /path/to/bundle/post.md \
  --evidence /path/to/bundle/evidence.json \
  --projection /path/to/bundle/editorial_projection.json \
  --bundle /path/to/bundle/bundle.json
```

The validator prints `Daily post validation passed.` when front matter, narrative structure,
evidence references, projection excerpts, and image provenance satisfy the publisher policy.

## Inputs and outputs

| Workflow | Input | Output |
| --- | --- | --- |
| Bundle import | Physical directory containing `bundle.json`, `evidence.json`, `editorial_projection.json`, `post.md`, and `assets/` | Current post in `docs/blog/posts/`, record in `data/publications/`, audit bundle in `data/publication_bundles/`, and immutable bundle release in `generated/releases/` |
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

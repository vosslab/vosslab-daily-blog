# Operations and recovery

## Ownership boundary

`vosslab-podcast` owns mirrors, date activity, evidence, author and referee routes, bundle creation,
and the single scheduled publication job. `vosslab-daily-blog` owns bundle validation, MkDocs source,
publication records, immutable releases, the atomic `site` pointer, and static serving.

The publication bundle is the complete interface. This repository performs no GitHub collection,
mirror synchronization, evidence interpretation, or LLM execution.

## Durable components

| Component | Location | Owner |
| --- | --- | --- |
| Current source post | `docs/blog/posts/YYYY-MM-DD.md` | bundle importer |
| Current publication record | `data/publications/YYYY-MM-DD.json` | bundle importer |
| Imported bundle audit copy | `data/publication_bundles/BUNDLE_ID/` | bundle importer |
| Temporary complete proposal | `generated/staging/` | bundle importer |
| Immutable built release | `generated/releases/BUNDLE_ID/` | bundle importer |
| Served release pointer | `site` | bundle importer |
| Publication schedule | `vosslab-daily-publication.timer` in `vosslab-podcast` | producer |
| Static server | `vosslab-daily-blog.service` | publisher |

Historical `data/daily/`, editorial, and run records remain audit material from the previous
publisher design. New v1 imports use only publication records and bundle archives.

## Normal flow

1. The producer passes one complete physical bundle directory to
   `scripts/import_publication_bundle.py`.
2. The importer validates bundle v1 and evidence v2, canonical bundle identity, hashes, date and
   timezone, every attributed commit-parent range and branch-tip snapshot, evidence authority and
   provenance, assets, candidate summaries, referee result, and post.
3. It copies the complete current `docs/` tree into a unique staging directory and installs the
   proposed post and assets there.
4. It renders the proposed status page from current publication records plus the proposed record.
5. The article validator runs again against staging, followed by a strict MkDocs build.
6. The importer installs the built release, bundle archive, publication record, and complete source
   tree, then atomically switches `site` as the final operation.

The static server resolves `site` for each request, so a successful release promotion needs no
service restart.

## Manual import

```bash
cd /home/vosslab/nsh/vosslab-daily-blog
source source_me.sh && python3 scripts/import_publication_bundle.py \
  --bundle /absolute/path/to/out/vosslab/daily_blog/YYYY-MM-DD/RUN_ID
```

The bundle path, its files, and its asset directory must be physical rather than symlinked. The
importer confines every manifest path below that directory.

An identical bundle returns `idempotent`. A different final bundle can supersede a provisional
record for the same date. A provisional bundle or different final bundle cannot replace an existing
final publication.

## Source validation

Validate the checked-in MkDocs source independently:

```bash
cd /home/vosslab/nsh/vosslab-daily-blog
source source_me.sh && .venv/bin/mkdocs build --strict
```

Validate an individual bundle post directly:

```bash
source source_me.sh && python3 scripts/validate_daily_post.py \
  --candidate /path/to/bundle/post.md \
  --evidence /path/to/bundle/evidence.json \
  --bundle /path/to/bundle/bundle.json
```

## Operator checks

```bash
systemctl --user status vosslab-daily-blog.service
systemctl --user status vosslab-daily-publication.timer
curl --fail http://aella.local:8016/blog/
curl --fail http://aella.local:8016/status/
readlink site
```

Inspect one current record and its immutable inputs:

```bash
python3 -m json.tool data/publications/2026-08-23.json
python3 -m json.tool data/publication_bundles/BUNDLE_ID/bundle.json
python3 -m json.tool data/publication_bundles/BUNDLE_ID/evidence.json
```

## Verification classes

Permanent pytest coverage protects bundle-schema dispatch, artifact hashes, confined asset paths,
referee-selected post identity, idempotency, quality precedence, and complete transaction rollback:

```bash
source source_me.sh && python3 -m pytest tests/test_publication_bundle_import.py
```

The producer repository owns the durable full-flow E2E, which imports a synthetic bundle into a
temporary publisher tree and performs a strict MkDocs build. Historical filename absence, the
installed host-unit snapshot, and the August 22-23 editorial comparison are one-time cutover checks.
Their results belong in the producer ownership record rather than this permanent pytest suite.

## Scheduling cutover

Only the producer's `vosslab-daily-publication.timer` schedules publication. The publisher retains
only `deploy/vosslab-daily-blog.service` for static serving.

Before enabling the producer timer, disable the former Hermes cron, mirror timer, and editorial
timer. Complete and record the producer's historical editorial review, then verify the user timer
list contains one publication schedule and that the static service remains enabled.

## Failure guarantees

- Schema, path, hash, provenance, front-matter, or post validation failure occurs before staging.
- A staged article or strict MkDocs build failure removes the proposed stage and leaves current
  source and serving unchanged.
- An install failure restores the prior source tree and publication record and removes newly placed
  release and archive directories.
- The served pointer changes last. The static service therefore continues to expose the last good
  immutable release across validation, build, or earlier install failures.

## Recovery

Read the importer error and the producer's `site_import` phase failure. Correct the bundle producer,
runtime dependency, disk, or source issue, then run the same producer date again. A new producer run
creates a new immutable bundle and typed run record.

If the static service itself fails, restart only the server and confirm the current immutable
pointer:

```bash
systemctl --user restart vosslab-daily-blog.service
readlink site
curl --fail http://aella.local:8016/
```

Manual edits to `site` or an immutable release bypass the publication contract. Repair source or the
bundle and use the importer instead.

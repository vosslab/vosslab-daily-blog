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
| Temporary presentation build | `generated/site-staging/` | manual site publisher |
| Immutable presentation release | `generated/releases/site-SOURCE_ID/` | manual site publisher |
| Served release pointer | `site` | importer or manual site publisher |
| Publication schedule | `vosslab-daily-publication.timer` in `vosslab-podcast` | producer |
| Static server | `vosslab-daily-blog.service` | publisher |

## Normal flow

1. The producer passes one complete physical bundle directory to
   `scripts/import_publication_bundle.py`.
2. The importer validates bundle v2, evidence v3, editorial projection v1, canonical identities,
   hashes, date and timezone, every attributed commit-parent range and branch-tip snapshot,
   evidence authority and provenance, exact excerpts, assets, two candidate validation summaries,
   the valid A/B referee selection, and the selected post.
3. It copies the complete current `docs/` tree into a unique staging directory and installs the
   proposed post and assets there.
4. It renders the proposed status page from current publication records plus the proposed record.
5. The article validator runs again against staging, followed by a strict MkDocs build.
6. The importer installs the built release, bundle archive, and complete source tree, then atomically
   switches `site`, and installs the publication record last.
7. The importer-global filesystem lock covers idempotency, date immutability, staging, and commit.
   Startup reconciliation rolls back interrupted staged transactions before another import proceeds.

The static server resolves `site` for each request, so a successful release promotion needs no
service restart. The checked-in service binds `0.0.0.0` for LAN and Tailscale access; it is not a
public-internet deployment contract.

## Publish repository presentation changes

Use the repository-owned command after changing `mkdocs.yml`, CSS, brand assets, or reader
navigation:

```bash
cd /home/vosslab/nsh/vosslab-daily-blog
./publish_site.sh
```

The command shares `generated/publisher.lock` with bundle imports. It rejects drift in imported
posts or the record-derived status page, snapshots `docs/` and `mkdocs.yml`, performs a strict staged
build, and installs `generated/releases/site-SOURCE_ID/`. Each presentation release carries an exact
`.deployment.json` receipt binding its source identity to the newest installed bundle. The `site`
symlink changes atomically only after the complete release exists.

Repeated publication of unchanged source is idempotent. The importer accepts a valid presentation
release as serving its recorded base bundle, so an identical producer retry remains idempotent.
Changing imported posts or `docs/status.md` remains importer-only work and fails before staging.

The script verifies `http://127.0.0.1:8016/` and `/status/` after promotion. It does not restart the
server because the running static process follows the new symlink automatically.

## Manual import

```bash
cd /home/vosslab/nsh/vosslab-daily-blog
source source_me.sh && python3.13 scripts/import_publication_bundle.py \
  --bundle /absolute/path/to/out/vosslab/daily_blog/YYYY-MM-DD/RUN_ID
```

The bundle path, its files, and its asset directory must be physical rather than symlinked. The
importer confines every manifest path below that directory.

An identical bundle returns `idempotent` only when all four archived bundle files match the incoming
bytes, the installed source post matches, and `site` serves that bundle through either its immutable
bundle release or a receipt-bound presentation release. Any drift fails loudly. Any different bundle
for an already-published report date is rejected before staging.

## Source validation

Validate the checked-in MkDocs source independently:

```bash
cd /home/vosslab/nsh/vosslab-daily-blog
source source_me.sh && python3.13 -m mkdocs build --strict
```

Validate an individual bundle post directly:

```bash
source source_me.sh && python3.13 scripts/validate_daily_post.py \
  --candidate /path/to/bundle/post.md \
  --evidence /path/to/bundle/evidence.json \
  --projection /path/to/bundle/editorial_projection.json \
  --bundle /path/to/bundle/bundle.json
```

## Operator checks

```bash
systemctl --user status vosslab-daily-blog.service
systemctl --user status vosslab-daily-publication.timer
curl --fail http://aella.local:8016/
curl --fail http://aella.local:8016/status/
readlink site
```

The checked-in unit is `deploy/vosslab-daily-blog.service`. Install or refresh it only when the unit
definition itself changes:

```bash
mkdir -p ~/.config/systemd/user
cp deploy/vosslab-daily-blog.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now vosslab-daily-blog.service
```

Inspect one current record and its immutable inputs:

```bash
python3.13 -m json.tool data/publications/2026-08-23.json
python3.13 -m json.tool data/publication_bundles/BUNDLE_ID/bundle.json
python3.13 -m json.tool data/publication_bundles/BUNDLE_ID/evidence.json
python3.13 -m json.tool data/publication_bundles/BUNDLE_ID/editorial_projection.json
```

## Verification classes

Permanent pytest coverage protects schema dispatch, artifact hashes, projection identity and packet
binding, exact excerpts, active-repository coverage, confined asset paths, referee-selected post
identity, date immutability, idempotency, and complete transaction rollback:

```bash
source source_me.sh && python3.13 -m pytest tests/test_publication_bundle_import.py
```

The producer repository owns the durable full-flow E2E, which imports a synthetic bundle into a
temporary publisher tree and performs a strict MkDocs build. Historical filename absence, the
installed host-unit snapshot, and the August 22-23 editorial comparison are one-time cutover checks.
Their results belong in the producer ownership record rather than this permanent pytest suite.

## Scheduling cutover

Only the producer's `vosslab-daily-publication.timer` schedules publication. The publisher retains
only `deploy/vosslab-daily-blog.service` for static serving.

The former Hermes cron, mirror timer, and editorial timer are retired. On August 27, 2026, the
operator explicitly activated the producer timer to restore publication while the historical
editorial comparisons remained pending. The producer now owns a durable oldest-first cursor for
missed dates. Verify the user timer list contains one publication schedule and that the static
service remains enabled.

## Failure guarantees

- Schema, path, hash, provenance, projection, front-matter, or post validation failure occurs before
  staging.
- A staged article or strict MkDocs build failure removes the proposed stage and leaves current
  source and serving unchanged.
- An install failure restores the prior source tree and publication record and removes newly placed
  release and archive directories.
- A process crash during installation leaves no success record ahead of the source, release, and
  served pointer; the next import reconciles its transaction marker and removes orphan staging and
  `.site-next-*` links.
- Idempotency succeeds only when `site` serves the record's bundle release or a valid receipt-bound
  presentation release, and the archived manifest, evidence, projection, and selected post match the
  incoming bytes exactly.
- The publication record changes last. The static service therefore continues to expose the last good
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

Manual edits to `site` or an immutable release bypass the publication contract. Repair presentation
source with a strict build followed by `publish_site.sh`; repair importer-owned content through a
new producer bundle and the importer.

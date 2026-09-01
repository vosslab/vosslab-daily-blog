# Operations and recovery

## Ownership boundary

`vosslab-podcast` owns mirrors, date activity, evidence, author and referee routes, bundle creation,
and the single scheduled publication job. Its systemd timer directly runs
`./make_blog.py --yesterday` at 04:00 America/Chicago. `vosslab-daily-blog` owns bundle validation,
MkDocs source, publication records, date-owned content releases, the atomic `site` pointer, and
static serving.

The publication bundle is the complete interface. This repository performs no GitHub collection,
mirror synchronization, evidence interpretation, or LLM execution.

## Durable components

| Component | Location | Owner |
| --- | --- | --- |
| Current source post | `docs/blog/posts/YYYY-MM-DD.md` | bundle importer |
| Current publication record | `data/publications/YYYY-MM-DD.json` | bundle importer |
| Imported bundle audit copy | `data/publication_bundles/YYYY-MM-DD/` | bundle importer |
| Temporary complete proposal | `generated/staging/` | bundle importer |
| Date-owned built release | `generated/releases/YYYY-MM-DD/` | bundle importer |
| Temporary presentation build | `generated/site-staging/` | manual site publisher |
| Immutable presentation release | `generated/releases/site-SOURCE_ID/` | manual site publisher |
| Served release pointer | `site` | importer or manual site publisher |
| Publication schedule | `vosslab-daily-publication.timer` runs `./make_blog.py --yesterday` at 04:00 America/Chicago | producer |
| Static server | `vosslab-daily-blog.service` | publisher |

## Normal flow

1. The producer writes one complete sealed bundle-transfer envelope to
   `scripts/import_publication_bundle.py --bundle-stdin`. The binary envelope has a canonical,
   checksum-bound header and exact declared entries; its total size is capped at 128 MiB. The public
   `--bundle PATH` interface remains for deliberate manual imports.
2. The importer seals the transfer bytes before validation. A manual directory import instead opens
   one held, no-follow descriptor for its physical root and seals `bundle.json` before reading the
   declared files. It accepts only bundle
   `vosslab.daily-blog.bundle.v9`: the exact 16-field manifest binds the report identity, contracts,
   activation receipt, evidence, roster, projection, the sealed survivor-scoped
   `publication_surface.json`, selected `post.md`, declared assets, and one `best_artifact_id`.
   The surface has its own canonical identity and binds the allowed evidence IDs, repository coverage,
   source artifacts, and selected image paths; the asset manifest must match that image selection
   exactly. The selected post manifest must carry the same artifact identity. Candidate and referee
   deliberation remain producer-owned run history and are not bundle inputs. The snapshot
   retains JSON files to 128 KiB, `post.md` to 2 MiB, each declared asset to 8 MiB, and the full
   transfer to 128 MiB; it rejects
   symlinks, nonregular files, and undeclared assets before later validation, staging, or archiving.
   The importer then checks canonical identities, hashes, date and timezone, roster provenance,
   repository lifecycle, survivor-surface authority, exact excerpts, projection, assets, and the
   selected post. Bundle v9 requires the exact `publication_source_safety.v1` identity: policy-vector digest
   `d50166736d79be7f7715cc0f7585fac71dfb2aecc1c631b10e01aeca2fb63c6b` for its 35-case
   executable corpus.
3. It copies the complete current `docs/` tree into a unique staging directory and installs the
   proposed post and assets there.
4. It renders the proposed status page from current publication records plus the proposed record.
5. Before staging, article validation applies the source-safety policy to the sealed selected post:
   it permits ordinary Markdown, declared evidence-asset paths, canonical HTTPS GitHub URLs, exact
   evidence comments, and the survivor-surface image paths; it rejects active raw HTML, Markdown
   attribute syntax, other comments, and other link targets. The staged strict MkDocs build independently
   verifies the full ordered reader-body projection and the article-local rendered image sources against
   that same surface, so the renderer cannot substitute a title-and-date shell or introduce an
   unselected image. Its SHA-256 is recorded in the new publication-v6 receipt.
6. The importer installs the date-owned built release, audit archive, and complete source tree,
   then atomically switches `site` and installs the publication record last.
7. The importer-global filesystem lock covers idempotency, replacement, staging, and commit.
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
build, verifies every built reader article against its archived body projection and current receipt,
and installs `generated/releases/site-SOURCE_ID/`. Each presentation release carries an exact
`.deployment.json` receipt binding its source identity to the newest installed report date. The `site`
symlink changes atomically only after the complete release exists.

Repeated publication of unchanged source is idempotent. The importer accepts a valid presentation
release as serving its recorded base report date, so an identical producer retry remains idempotent.
Changing imported posts or `docs/status.md` remains importer-only work and fails before staging.

The script verifies `http://127.0.0.1:8016/` and `/status/` after promotion. It does not restart the
server because the running static process follows the new symlink automatically.

## Manual import

```bash
cd /home/vosslab/nsh/vosslab-daily-blog
source source_me.sh && python3.13 scripts/import_publication_bundle.py \
  --bundle /absolute/path/to/out/vosslab/daily_blog/YYYY-MM-DD/publication
```

The bundle path, its files, and its asset directory must be physical rather than symlinked. The
importer confines every manifest path below that directory. This manual interface is distinct from
the automated `--bundle-stdin` transfer, which does not expose a producer filesystem path and admits
only its canonical, checksum-bound, 128 MiB envelope.

An identical bundle returns `idempotent` only when the archived files match the incoming bytes, the
installed source post matches, and `site` serves that report date directly or through a receipt-bound
presentation release. The producer automatically supplies `--replace-existing` for its scheduled
same-date daily publication. The public importer flag remains available for a deliberate manual
replacement; either path stages and validates the complete replacement before exchanging its stable
directories. New imports write the publication-v6 record last, binding the selected artifact,
reader-body digest, and sealed publication-surface identity as the authoritative commit marker for
the complete set. New imports accept v9 only. Historical v8 bundles and publication-v5/v3 records
remain readable and redeployable through the read-only presentation-validation path; they are never
new-import schemas. Replacing a historical date with a v9 bundle creates a v6 record. Historical
posts, including any old links outside the current source-safety policy, remain read-only material.

## Source validation

Validate the checked-in MkDocs source independently:

```bash
cd /home/vosslab/nsh/vosslab-daily-blog
source source_me.sh && python3.13 -m mkdocs build --strict
```

The importer validates each selected `post.md` with its sealed evidence, projection, survivor-scoped
surface, and bundle manifests before it stages any publisher state. Bundle v9 additionally binds
`publication_source_safety.v1` and its policy-vector digest
`d50166736d79be7f7715cc0f7585fac71dfb2aecc1c631b10e01aeca2fb63c6b`, derived from its 35-case
executable corpus; source safety admits only
canonical publication Markdown, survivor-surface image paths, and HTTPS GitHub links. It accepts active
v4-maker policy v3: digest
`3a4b7148579e509b6c32fa19b31d107dc4278eb5f721b2a01353a1a9a51264ee`,
`projected_repositories` coverage, and `reader_visible_markdown` word counting. Activation
`daily-blog-maker-activation-6b104be9c6907eeeffcf330f6b10173857b39c6b05baa46d4cf009a67daa7547`
selects `v4-three-examples-corpus-v2`. The policy caps candidates at 24,000 characters and requires
one opening prose block of at most 100 words before one excerpt marker, with no pre-marker H2.
Policy versions 1 and 2 fail closed. The publisher independently recomputes and enforces the active
contract; producer snapshot, generator, bundle, and reuse identities remain producer-owned.

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

Inspect one current record and its validated inputs:

```bash
python3.13 -m json.tool data/publications/YYYY-MM-DD.json
python3.13 -m json.tool data/publication_bundles/YYYY-MM-DD/bundle.json
python3.13 -m json.tool data/publication_bundles/YYYY-MM-DD/evidence.json
python3.13 -m json.tool data/publication_bundles/YYYY-MM-DD/editorial_projection.json
python3.13 -m json.tool data/publication_bundles/YYYY-MM-DD/publication_surface.json
```

## Verification classes

Permanent pytest coverage protects schema dispatch, artifact hashes, projection identity and packet
binding, exact excerpts, active-repository coverage, confined asset paths, selected-post/artifact
identity, one survivor-scoped evidence and image authority from import through rendered-page
validation, idempotency, explicit date replacement, and complete transaction rollback:

```bash
source source_me.sh && python3.13 -m pytest tests/test_publication_bundle_import.py
```

Permanent tests are offline deterministic behavior contracts. Fixture capture, calibration,
artifact-only review, crash-recovery matrix, staged strict build, and complete-page inspection are
one-time evidence. Their repetition counts, thresholds, reviewer count, internal key layouts, and
generated prose bytes are not permanent assertions. Installed host-unit state is telemetry.

## Scheduling cutover

The producer's `vosslab-daily-publication.timer` schedules publication by directly running
`./make_blog.py --yesterday` at 04:00 America/Chicago. It is noninteractive and automatically
replaces the same report date when a corrected completed bundle is ready. The publisher retains only
`deploy/vosslab-daily-blog.service` for static serving. Verify the timer and static service with:

```bash
systemctl --user status vosslab-daily-publication.timer
systemctl --user list-timers vosslab-daily-publication.timer
systemctl --user status vosslab-daily-blog.service
```

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
- Idempotency succeeds only when `site` serves the record's date-owned release or a valid receipt-bound
  presentation release, and the archived manifest, evidence, projection, sealed surface, selected post,
  and survivor-scoped assets match the incoming bytes exactly.
- Import and later presentation publication verify the staged built article against the admitted
  ordered reader-body projection and the record-bound surface image paths. A matching date or title
  alone cannot satisfy that check.
- The publication record changes last. The static service therefore continues to expose the last
  good served release across validation, build, or earlier install failures.

## Recovery

Read the importer error and the producer's `site_import` phase failure. Correct the bundle producer,
runtime dependency, disk, or source issue, then run the same producer date again. Its scheduled or
re-run publication path supplies same-date replacement automatically when the completed bundle changed.
For a v9 surface or selected-image admission failure, correct the producer's survivor-scoped surface
and replay the same date; no manual publisher-side expansion of evidence or image authority is valid.

If the static service itself fails, restart only the server and confirm the current served pointer:

```bash
systemctl --user restart vosslab-daily-blog.service
readlink site
curl --fail http://aella.local:8016/
```

Manual edits to `site`, a date-owned content release, or a source-hash presentation release bypass
the publication contract. Repair presentation source with a strict build followed by
`publish_site.sh`; repair importer-owned content through a new producer bundle and the importer.

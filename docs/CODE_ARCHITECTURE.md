# Code architecture

## Purpose

This repository is a local publication sink. It accepts a complete producer-owned bundle, validates
the contract independently, proposes a complete MkDocs source tree, and installs an immutable built
release without exposing partial work.

## Repository boundary

```text
vosslab-podcast                         vosslab-daily-blog

evidence -> editorial -> bundle  --->  validate -> stage -> strict build
                                                     |
                                                     v
                                         source + record + release
                                                     |
                                                     v
                                             atomic site pointer
```

The producer passes a directory path to one command. The publisher does not import producer modules
and the producer does not edit publisher-owned source or releases.

## Import pipeline

`scripts/import_publication_bundle.py` performs four boundaries:

1. **Contract validation** verifies v1 schemas, required manifest fields, canonical bundle and
   evidence identities, hashes, report identity, generator and editorial versions, two candidate
   summaries, referee verdict, evidence authority, exact provenance, and asset confinement.
2. **Article validation** calls `scripts.validate_daily_post.validate_post` for front matter,
   structure, first-person voice, excerpt placement, evidence comments, changelog use, and image
   provenance.
3. **Complete staging** copies current MkDocs source, applies the proposed post and assets, renders
   status, archives the bundle inputs, and performs a strict build into the same unique stage.
4. **Atomic installation** moves the immutable release, bundle archive, publication record, and
   complete source into place before atomically replacing the served `site` symlink.

## Contract model

The importer accepts only `vosslab.daily-blog.bundle.v1` and
`vosslab.daily-blog.evidence.v2`. It reimplements canonical JSON hashing and evidence identities so
producer code cannot define its own validation result inside the publisher process.

Evidence v2 represents every attributed commit-to-parent range and every attributed branch-tip
snapshot explicitly. The importer verifies that the declared ranges exactly match all parents in
the typed commit records before accepting their evidence items.

Within that schema generation, the accepted editorial contracts are `daily-blog-prompts-v2` and
`daily-blog-rubric-v2`. A prompt or rubric revision advances both producer and importer expectations
together while producer-only shadow evaluations remain outside the publication interface.

The referee result includes its anonymous A/B label-to-candidate mapping. For a final bundle, the
importer requires the winning label to map to a valid summary and requires that candidate hash to
equal the exact `post.md` hash.

Evidence items arrive in descending authority order:

1. dated changelog
2. changed documentation
3. diff
4. README context
5. screenshot
6. commit metadata

Every item carries its content hash and acquisition provenance. Screenshot entries connect an exact
Git blob hash to one bundle asset hash and one confined MkDocs publication path.

## Publication state

`data/publications/YYYY-MM-DD.json` is the current publisher-owned record for a v1 date. It names
the bundle, generator run and revision, evidence archive, source post, quality, release, and import
time. Historical records from the pre-bundle design remain readable as `legacy` entries on the
status page.

`data/publication_bundles/BUNDLE_ID/` retains the validated manifest, evidence, and selected post.
`generated/releases/BUNDLE_ID/` retains the strict built site. Both paths are immutable.

## Replacement policy

An exact installed bundle returns success without staging. A final bundle may supersede a
provisional bundle for the same report date. A lower-quality bundle and a different final bundle are
rejected after exact idempotency is checked.

## Failure containment

Validation has no publisher writes. Staging writes only below `generated/staging/`. Installation
tracks prior source and record movement so an exception restores them and removes newly installed
archive and release directories. The `site` pointer changes last through `os.replace`.

## Static serving

`deploy/vosslab-daily-blog.service` uses Python's static HTTP server on port 8016 and serves the
`site` symlink. It has no generator, GitHub, mirror, or model dependency. Scheduling belongs to the
producer repository.

## Extension points

- Add a new bundle schema beside v1 and dispatch explicitly after both repositories implement it.
- Extend article policy in `validate_daily_post.py` with focused deterministic tests.
- Extend publication records only through a new publication schema version.
- Add source assets through bundle evidence; the importer remains the sole installation path.

# Code architecture

## Purpose

This repository is a local publication sink. It accepts a complete producer-owned bundle, validates
the contract independently, proposes a complete MkDocs source tree, and installs an immutable built
release without exposing partial work.

## Repository boundary

```text
vosslab-podcast                         vosslab-daily-blog

evidence -> projection -> authors -> A/B referee -> bundle
                                                   |
                                                   v
                                      validate -> stage -> strict build
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

1. **Contract validation** verifies bundle v2, evidence v3, and projection v1 fields; canonical
   identities and hashes; report identity; generator and editorial versions; two candidate
   validation summaries; the valid A/B referee selection; evidence authority; exact projection
   excerpts; repository coverage; provenance; and asset confinement.
2. **Article validation** calls `scripts.validate_daily_post.validate_post` for front matter,
   structure, first-person voice, excerpt placement, evidence comments, changelog use, and image
   provenance. It independently rejects an unresolved `thematic-lowercase-slug` sentinel.
3. **Complete staging** copies current MkDocs source, applies the proposed post and assets, renders
   status, archives the bundle inputs, and performs a strict build into the same unique stage.
4. **Atomic installation** moves the immutable release, bundle archive, and complete source into place,
   atomically replaces the served `site` pointer, and installs the publication record last. A
   publisher-global filesystem lock spans idempotency checks through commit; a transaction marker
   lets startup reconcile interrupted staging before accepting another import.

The lock is a runtime resource at `generated/publisher.lock`, not a source-tree artifact. Transaction
marker, rollback, and crash-reconciliation ownership lives in `scripts/publication_transaction.py`;
the importer owns validation and staging and delegates the final state transition to that module.

## Contract model

The importer accepts only `vosslab.daily-blog.bundle.v2`,
`vosslab.daily-blog.evidence.v3`, and
`vosslab.daily-blog.editorial-projection.v1`. It reimplements canonical JSON hashing and evidence
and projection identities so producer code cannot define its own validation result inside the
publisher process.

Evidence v3 represents every attributed commit-to-parent range and branch-tip snapshot explicitly
and names collection bounds through `collection_limits`. The importer verifies that the declared
ranges exactly match all parents in the typed commit records before accepting their evidence items.

Editorial projection v1 binds to one evidence packet identity. Its repository cards cover every
active evidence repository. Each exact excerpt names a known evidence item and source-content hash;
its integer start/end offsets must be inside that source, and its text must equal the source slice.
The bundle manifest hashes the complete projection file.

The accepted execution contracts are `daily-blog-generator-v2`, `daily-blog-prompts-v3`, and
`daily-blog-rubric-v3`. Both author results must carry deterministic validation summaries before
bundle creation. The referee winner must map to a valid candidate, and that candidate hash must
equal the exact `post.md` hash. Producer-only shadow evaluations remain outside the publication
interface.

The bundle `contracts` object names `evidence_schema`, `editorial_projection_schema`,
`prompt_version`, and `rubric_version`. The generator revision is a required 64-character lowercase
hexadecimal fingerprint of the exact producer source/config contract; it is not assumed to be a Git
object ID. Selected-post front matter binds `evidence_manifest: evidence.json` and
`editorial_projection: editorial_projection.json`.

Evidence items arrive in descending authority order:

1. dated changelog
2. changed documentation
3. diff
4. README context
5. screenshot
6. commit metadata

Every item carries its content hash and acquisition provenance. Screenshot entries connect an exact
Git blob hash to one bundle asset hash and one confined MkDocs publication path. That verified path is
the image's provenance citation; duplicate model-authored evidence comments are not authoritative.

## Publication state

`data/publications/YYYY-MM-DD.json` is the current publisher-owned v2 record for one date. It names
the bundle, generator run and revision, evidence and projection archives, source post, release, and
import time. The status page is derived only from validated v2 publication records; an unsupported
record schema stops the import instead of inventing a compatibility row.

`data/publication_bundles/BUNDLE_ID/` retains the validated manifest, evidence, editorial
projection, and selected post. `generated/releases/BUNDLE_ID/` retains the strict built site. Both
paths are immutable.

## Date immutability

An exact installed bundle returns success without staging only when its archived manifest, evidence,
projection, and post match the incoming bytes and `site` resolves to its expected immutable release.
Any drift is reported as incomplete or divergent state. Any different bundle for an occupied report
date is rejected after exact idempotency is checked.

## Failure containment

Validation has no publisher writes. Staging writes only below `generated/staging/`. Installation
tracks prior source and record movement so an exception restores them and removes newly installed
archive and release directories. The `site` pointer is atomically replaced before the publication
record is installed last.

## Static serving

`deploy/vosslab-daily-blog.service` uses Python's static HTTP server on port 8016 and serves the
`site` symlink. It binds `0.0.0.0` for LAN and Tailscale reachability. It has no generator, GitHub,
mirror, or model dependency. Scheduling belongs to the producer repository.

## Extension points

- Add a new schema beside the current contract and dispatch explicitly after both repositories
  implement it.
- Extend article policy in `validate_daily_post.py` with focused deterministic tests.
- Extend projection policy in `validate_editorial_projection.py` with exact evidence-bound tests.
- Extend publication records only through a new publication schema version.
- Add source assets through bundle evidence; the importer remains the sole installation path.

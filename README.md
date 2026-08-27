# Vosslab Daily Blog

Publishes evidence-grounded Vosslab work logs to a private MkDocs site while preserving the last
good release across validation and build failures.

The site is the publisher half of a two-repository workflow. `vosslab-podcast` generates one
versioned publication bundle; this repository independently validates, imports, builds, and serves
it on the local network.

## What publication proves

- Every imported post belongs to a schema-versioned, SHA-256-identified bundle.
- Evidence authority and exact Git provenance survive the repository boundary.
- Required front matter and paragraph-level evidence references are deterministic checks.
- A complete proposed MkDocs source tree must pass a strict build before installation.
- The source tree, publication record, immutable release, and `site` pointer change as one
  transaction.
- Identical imports are successful and idempotent; a final bundle can supersede its provisional
  date.

The publication record retains the generator run, generator revision, evidence manifest, bundle ID,
quality, source post, and immutable release identity.

## Quick start

Use Python 3.12 and install the publisher dependencies:

```bash
cd /home/vosslab/nsh/vosslab-daily-blog
python3 -m venv .venv
.venv/bin/python -m pip install -r pip_requirements.txt -r pip_requirements-dev.txt
```

Import one complete producer bundle:

```bash
source source_me.sh && python3 scripts/import_publication_bundle.py \
  --bundle /home/vosslab/nsh/vosslab-podcast/out/vosslab/daily_blog/2026-08-23/RUN_ID
```

Success prints a JSON result with `status: imported`, or `status: idempotent` when the exact bundle
is already installed. The current source post appears at `docs/blog/posts/YYYY-MM-DD.md`, the bundle
audit copy appears under `data/publication_bundles/BUNDLE_ID/`, and the built release appears under
`generated/releases/BUNDLE_ID/`.

The normal operator path starts in the producer repository and already invokes this importer:

```bash
cd /home/vosslab/nsh/vosslab-podcast
source source_me.sh && python3 automation/publish_daily_blog.py --date 2026-08-23
```

## Local site

- `http://aella.local:8016`
- `http://192.168.2.13:8016`

`deploy/vosslab-daily-blog.service` serves the atomic `site` pointer. Generation and scheduling
belong to `vosslab-podcast`; this repository supplies no publication timer.

Validate the checked-in source without importing a bundle:

```bash
source source_me.sh && .venv/bin/mkdocs build --strict
```

## Publication bundle

The importer accepts one physical directory containing:

```text
bundle.json
evidence.json
post.md
assets/
```

It accepts the current v1 bundle and v2 evidence schemas. It verifies the bundle identity,
artifact hashes, report date, timezone, generator and editorial contract versions, two candidate
validation summaries, structured referee result, authority ordering, evidence item identities,
asset paths, Git blob provenance, front matter, evidence citations, and publication quality.

The post front matter requires `date`, `slug`, `publication_quality`, `generator_run`, and
`evidence_manifest`. A final publication is stable: a different later bundle cannot silently replace
it. Historical August 24-25 content remains unchanged until a separately requested generation run.

The current v1 bundle contract requires the producer's `daily-blog-prompts-v2` and
`daily-blog-rubric-v2` editorial versions. Producer shadow evaluations remain outside this
repository and never enter the importer.

## Documentation

- [docs/operations.md](docs/operations.md): import, scheduling boundary, inspection, and recovery.
- [docs/CODE_ARCHITECTURE.md](docs/CODE_ARCHITECTURE.md): validation and atomic publication design.
- [docs/FILE_STRUCTURE.md](docs/FILE_STRUCTURE.md): source, state, release, and test layout.
- [docs/CHANGELOG.md](docs/CHANGELOG.md): dated repository changes.
- [docs/E2E_TESTS.md](docs/E2E_TESTS.md): repository test conventions and end-to-end checks.

## Status and license

Beta delivery ends at the private local MkDocs site on port 8016. Static serving remains independent
of generator availability, so the last good built release stays readable during producer or import
failures.

Code is available under [LGPL-3.0](LICENSE.LGPL-3.0). Site content is available under
[CC BY 4.0](LICENSE.CC-BY-4.0).

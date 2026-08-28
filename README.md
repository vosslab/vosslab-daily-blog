# Vosslab Daily Blog

An evidence-grounded private-LAN work-log publisher for people who want a readable daily record of
Vosslab work, with each article traceable to a validated, immutable release.

[Read the live work log on the LAN](http://aella.local:8016/)

## A work log with receipts

This is a private reading experience, not a public feed. It turns completed Vosslab work into a
calm, newspaper-like daily log while retaining the evidence needed to inspect how each entry was
published.

- Read the current work log at [aella.local:8016](http://aella.local:8016/).
- Follow each article from its validated publication bundle to an immutable built release.
- Keep the last good site readable when a later bundle, validation run, or build fails.
- Publish visual and reader-navigation refinements without rewriting the imported blog.

<!-- screenshots:begin (managed by screenshot-docs) -->
![Vosslab Work Log landing page with the newest field note visible at the top](docs/screenshots/work_log_home.png)
<!-- screenshots:end -->

## Know the boundary

The site is the publisher half of a two-repository workflow. `vosslab-podcast` owns collection,
evidence, generation, model execution, bundle creation, and scheduling. This repository owns the
independent validation, MkDocs source, publication records, immutable releases, atomic `site`
pointer, and static LAN service.

The bundle is the complete interface between those responsibilities. This publisher does not collect
GitHub activity, run models, or schedule articles; it validates and serves complete producer output.

The service is intentionally private to the LAN and Tailscale interface. It is beta infrastructure,
not a public-internet publishing service.

## Publish the presentation

Use this one command after changing checked-in CSS, brand assets, or reader navigation. It leaves
imported posts and the record-derived status page under importer control.

```bash
cd /home/vosslab/nsh/vosslab-daily-blog
./publish_site.sh
```

The script uses `python3.13` from `PATH`. A virtual environment is optional; activate one before
publishing when you want isolated dependencies:

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install -r pip_requirements.txt -r pip_requirements-dev.txt
source .venv/bin/activate
./publish_site.sh
```

Success ends with:

```text
Published and verified: http://aella.local:8016/
```

The command validates the source, performs a strict staged MkDocs build, writes an immutable
source-identified release, atomically switches `site`, and verifies the live home and status pages.
The static server follows that pointer, so a successful publish needs no service restart.

## Bring in an article

Normal daily publication starts in `vosslab-podcast`, whose scheduler creates a complete bundle and
invokes this repository's importer. To inspect or manually import a completed bundle, use:

```bash
cd /home/vosslab/nsh/vosslab-daily-blog
source source_me.sh && python3.13 scripts/import_publication_bundle.py \
  --bundle /absolute/path/to/out/vosslab/daily_blog/YYYY-MM-DD/RUN_ID
```

An accepted import reports `status: imported`; retrying the exact archived bundle reports
`status: idempotent`. A different bundle for an already imported date is rejected rather than
silently changing history.

## What the publisher protects

- Bundle, evidence, and editorial-projection schemas and their content identities.
- Article front matter, evidence references, and provenance before rendering.
- A complete strict MkDocs build before any reader sees the proposed release.
- Atomic promotion, so failures continue serving the last known-good release.
- Presentation releases that are receipt-bound to the imported publication they render.

## Documentation

Start here when operating or extending the publisher:

- [docs/INSTALL.md](docs/INSTALL.md), [docs/USAGE.md](docs/USAGE.md),
  [docs/COOKBOOK.md](docs/COOKBOOK.md), [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md), and
  [docs/FAQ.md](docs/FAQ.md) cover setup and operation.
- [docs/CODE_ARCHITECTURE.md](docs/CODE_ARCHITECTURE.md),
  [docs/FILE_STRUCTURE.md](docs/FILE_STRUCTURE.md), [docs/FILE_FORMATS.md](docs/FILE_FORMATS.md),
  and [docs/operations.md](docs/operations.md) define the system and its contracts.
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md), [docs/E2E_TESTS.md](docs/E2E_TESTS.md),
  [docs/ROADMAP.md](docs/ROADMAP.md), [docs/RELATED_PROJECTS.md](docs/RELATED_PROJECTS.md), and
  [docs/CHANGELOG.md](docs/CHANGELOG.md) guide extension and project decisions.

## Status and licenses

The LAN service on port 8016 is a beta delivery path. Static serving is independent of generator
availability, so readers keep access to the last good release while producer or import work is
repaired.

The publisher code is available under [LGPL-3.0](LICENSE.LGPL-3.0). Published site content is
available under [CC BY 4.0](LICENSE.CC-BY-4.0).

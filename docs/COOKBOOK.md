# Cookbook

Use these short, repeatable procedures when operating the publisher from its checkout. They
combine commands from [USAGE.md](USAGE.md) and [operations.md](operations.md); use those documents
for the full contract and recovery rules.

## Verify a presentation change

Run the checks that cover the presentation deployment path before publishing a CSS, reader
navigation, brand, or MkDocs configuration change:

```bash
source source_me.sh && python3.13 -m pytest tests/test_site_deployment.py
source source_me.sh && python3.13 -m mkdocs build --strict
```

The pytest module proves immutable presentation-release promotion, idempotency, and failed-build
preservation in temporary publisher roots. The strict build validates the reader-facing source tree;
it does not replace imported content or publish the result.

## Publish and inspect a release

Promote only presentation-owned source, then inspect the immutable release receipt selected by the
atomic `site` pointer:

```bash
./publish_site.sh
readlink site
python3.13 -m json.tool "$(readlink -f site)/.deployment.json"
curl --fail http://aella.local:8016/
curl --fail http://aella.local:8016/status/
```

The receipt identifies the release's source hash and the newest imported bundle it renders. Do not
edit `site`, `generated/releases/`, imported posts, or `docs/status.md` by hand; the publisher
rejects imported-source drift before it can create a presentation release.

## Inspect one imported article

For a known report date, compare its publication record with the currently installed inputs before
investigating a rendering or provenance question:

```bash
python3.13 -m json.tool data/publications/YYYY-MM-DD.json
python3.13 -m json.tool data/publication_bundles/YYYY-MM-DD/bundle.json
python3.13 -m json.tool data/publication_bundles/YYYY-MM-DD/evidence.json
python3.13 -m json.tool data/publication_bundles/YYYY-MM-DD/editorial_projection.json
```

Replace `YYYY-MM-DD` with the publication date. The installed post is the archive's byte-identical
selected `post.md`. The importer accepts the exact current checksum idempotently and installs a
different bundle only through the explicit replacement path. Use [operations.md](operations.md)
when the source bundle, rather than the published presentation, needs repair.

## Diagnose the served site

Check the user service and the pointer before restarting anything:

```bash
systemctl --user status vosslab-daily-blog.service
readlink site
curl --fail http://127.0.0.1:8016/
curl --fail http://127.0.0.1:8016/status/
```

If the service alone has failed, restart it and repeat the checks. If an import or presentation
publish has failed, correct its source issue and rerun that supported workflow; the previous served
release remains available until a complete replacement is promoted.

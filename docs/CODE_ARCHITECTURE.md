# Code architecture

## Responsibility

This repository renders and deploys producer-supplied publications. It does not decide whether a
post is correct, grounded, complete, readable, or worth publishing. `vosslab-podcast` owns those
decisions and verifies delivery. If MkDocs can render the supplied Markdown, this repository can
publish it.

## Import flow

```text
vosslab-podcast
  final post + referenced assets + transient routing manifest
                         |
                         v
vosslab-daily-blog
  confined placement -> strict MkDocs build -> atomic deploy -> route receipt
```

[scripts/import_publication_bundle.py](../scripts/import_publication_bundle.py) receives the
transient handoff. It reads only the routing fields needed to choose the report-date post path and
confined asset names. It writes the producer's Markdown bytes without interpreting them.

[scripts/publication_staging.py](../scripts/publication_staging.py) creates a disposable source
snapshot. The post is placed at `docs/blog/posts/YYYY-MM-DD.md`. Assets are limited to those sent
for that post and are placed beside it under `docs/blog/posts/YYYY-MM-DD/`. Replacing a report date
replaces that whole date-owned asset directory, so unused images do not accumulate.

[scripts/publication_transaction.py](../scripts/publication_transaction.py) owns the import lock,
atomic source/release exchange, site-pointer switch, and rollback. Its JSON marker exists only in
the disposable staging directory.

[scripts/site_deployment.py](../scripts/site_deployment.py) builds the current MkDocs source and
atomically promotes the rendered release. [publish_site.sh](../publish_site.sh) is the manual
presentation deployment entry point.

## Durable and temporary state

Durable reader source consists of final Markdown and images referenced by it. Rendered releases
live under `generated/releases/`, and `site` points to the currently served release.

The bundle routing JSON, transfer envelope, transaction marker, and staging directory are temporary.
This repository does not retain publication bundles, evidence, rosters, projections, editorial
receipts, or citation metadata under `data/`.

## Failure boundary

The renderer can fail for confined file placement, an MkDocs build failure, deployment failure, or
failure to find the rendered route. MkDocs is the authority on whether supplied Markdown is
renderable. No display-repository code reevaluates editorial content or producer workflow state.

The remaining pytest files are shared repository-hygiene tests. End-to-end publication confidence
comes from the real producer handoff followed by a strict MkDocs build and rendered-route check.

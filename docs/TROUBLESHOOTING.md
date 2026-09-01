# Troubleshooting

Use the first failing command as the diagnosis. The publisher leaves the current validated release
served until a complete replacement validates and promotes, so do not manually edit `site`, a
release directory, an imported post, or `docs/status.md` to force a recovery.

## Gather the current state

Run these checks from the repository root before changing anything:

```bash
systemctl --user status vosslab-daily-blog.service
curl --fail http://127.0.0.1:8016/
curl --fail http://127.0.0.1:8016/status/
readlink site
```

The service is only the static server. Bundle generation and the scheduled
`vosslab-daily-publication.timer` belong to `vosslab-podcast`; see
[operations.md](operations.md) for the ownership boundary.

## Publish command fails

`publish_site.sh` requires Python 3.13 and uses `python3.13` from `PATH` by default. When that
interpreter is unavailable, install it or create an optional local environment with it:

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install -r pip_requirements.txt -r pip_requirements-dev.txt
.venv/bin/python -m mkdocs --version
```

Then activate the environment for the same presentation publish:

```bash
source .venv/bin/activate
./publish_site.sh
```

The runtime contract intentionally rejects other Python feature versions in
`scripts/site_deployment.py`; correct the selected executable instead of bypassing the check.

## Strict build fails

Run the source-only build to isolate an MkDocs, navigation, Markdown, or asset error without
promoting a release:

```bash
source source_me.sh && python3.13 -m mkdocs build --strict
```

Correct the reported source file, then repeat the source-only build before running
`./publish_site.sh`. A failed staged build does not replace the live `site` pointer. For the
ordinary presentation workflow, use [USAGE.md](USAGE.md).

## Site endpoint fails

First distinguish a static-server failure from a bad served pointer:

```bash
systemctl --user status vosslab-daily-blog.service
journalctl --user-unit vosslab-daily-blog.service --no-pager
readlink site
test -f "$(readlink -f site)/index.html"
```

If the pointer resolves to a release with `index.html`, restart only the static service and retry
the loopback checks:

```bash
systemctl --user restart vosslab-daily-blog.service
curl --fail http://127.0.0.1:8016/
curl --fail http://127.0.0.1:8016/status/
```

If the unit file itself changed, install the checked-in definition and reload systemd before the
restart:

```bash
mkdir -p ~/.config/systemd/user
cp deploy/vosslab-daily-blog.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now vosslab-daily-blog.service
```

Do not replace the `site` symlink by hand. Repair the source or bundle and let the publisher promote
a complete release. Source-hash presentation releases are immutable; date-owned content releases
are current and replaceable through the importer.

## Presentation publish rejects source

The manual publisher verifies that importer-owned content remains byte-for-byte consistent with its
accepted bundle, that `docs/status.md` matches the publication records, and that every staged built
reader article still contains its ordered canonical body projection and surface-approved images.
Errors such as `Imported post has drifted from its bundle`, `Publication status has drifted from
installed records`, or `Built article embeds an image outside its publication surface` indicate a
contract violation, not a cosmetic publish problem.

- Restore the imported content through the producer/importer workflow; do not edit it to match a
  guess.
- Keep CSS, reader navigation, brand, and MkDocs changes outside importer-owned posts and
  `docs/status.md`; repository documentation is not part of the built blog.
- Run `./publish_site.sh` again after the source is coherent.

See [operations.md](operations.md) for the files owned by the importer and the publication receipt
guarantees.

## Bundle v9 import rejects

Inspect the sealed manifest and its survivor authority before retrying an import:

```bash
source source_me.sh && python3.13 -m json.tool \
  /path/to/bundle/bundle.json
source source_me.sh && python3.13 -m json.tool \
  /path/to/bundle/publication_surface.json
```

The automated importer requires the producer's canonical sealed `--bundle-stdin` envelope. The
manual interface requires one physical directory with `bundle.json`, `evidence.json`,
`repository_roster.json`, `editorial_projection.json`, `publication_surface.json`, `post.md`, and
the surface-selected `assets/` directory. Both apply 128 KiB JSON, 2 MiB post, 8 MiB asset, and
128 MiB complete-transfer bounds. The importer accepts only
`vosslab.daily-blog.bundle.v9` for new input.

`publication_surface.json` is the immutable survivor-scoped authority. Its identity must match the
bundle manifest; its evidence IDs must exactly match the projection excerpts; and its structured
image entries must bind each selected screenshot evidence ID, bundle asset path, and published path.
The selected post, archive, staged assets, publication-v6 receipt, and rendered article all use that
same authority.

Use the first exact error to choose the repair:

| Error or protocol result | Cause | Repair |
| --- | --- | --- |
| `snapshot_rejected` at `receive` or `validate` | The transfer, manifest, hash, path, or bounded physical snapshot is invalid. | Create a new producer bundle; preserve the sealed input rather than editing it in place. |
| `Unsupported publication bundle schema` | The input is not bundle v9. | Re-run the current producer workflow for the report date. |
| `Publication surface ...` | The surface identity, evidence, projection, repository coverage, or source artifacts disagree. | Rebuild one bundle from the selected survivor set; keep its post, projection, evidence IDs, and surface together. |
| `Bundle assets do not exactly match publication surface images` | The asset manifest contains an unselected aggregate screenshot or omits a surface-selected screenshot. | Include exactly the selected surface images and no aggregate-only images. |
| `Bundle asset does not match screenshot evidence` or `Bundle asset publication path mismatch` | An asset is not the screenshot or published path bound by the selected evidence. | Regenerate the asset manifest and bytes from that surface entry. |
| `post embeds an image outside bundle evidence` | The post references an image path outside the selected surface. | Change the post to use a surface-selected published path, or create a new survivor-scoped surface that legitimately includes it. |
| `Bundle post validation failed` | Front matter, provenance, evidence references, coverage, or source safety is invalid. | Repair the producer's selected post and create a new complete bundle. |
| `staged_build_failed` at `stage` | MkDocs or rendered-page verification failed, including an article image outside the surface. | Correct the producer bundle or a repository presentation defect identified by the strict-build output, then retry. |
| `publication_conflict` at `preflight` | A different bundle already owns the report date. | Use the producer's same-date replacement workflow or the deliberate `--replace-existing` manual import. |
| `commit_failed` at `commit` | A local storage or atomic-promotion operation failed. | Preserve the error, inspect the filesystem and service state, then rerun the supported command after repairing the host issue. |

The producer-facing failure envelope intentionally exposes only a bounded category and phase. Read
the corresponding producer `site_import` failure and local importer diagnostics for the exact cause;
do not infer a content repair from the category alone.

A source-safety error means the bundle-v9 post failed the 35-case executable
`publication_source_safety.v1` corpus (digest
`d50166736d79be7f7715cc0f7585fac71dfb2aecc1c631b10e01aeca2fb63c6b`) or uses markup outside its
ordinary Markdown, declared evidence assets, canonical HTTPS GitHub links, exact evidence comments,
and excerpt-marker allowance; correct the producer output rather than editing publisher-owned state. Fix
the producer output in `vosslab-podcast`, create a new complete bundle, and retry
the producer's date workflow. An exact retry of an already installed bundle is reported as
`idempotent`. When publishing an intentional regeneration for an occupied report date, include
`--replace-existing` so the importer stages and atomically swaps that date's content.

Use [USAGE.md](USAGE.md) for the import command and [operations.md](operations.md) for the
transaction and recovery guarantees.

## Historical bundle records

Bundle v8 archives and publication-v5 or publication-v3 receipts remain read-only installed
history. The publisher can read and redeploy that retained history for later presentation
verification, but it never accepts v8, v5, or v3 material as new producer input and never rewrites
it to satisfy the v9 source-safety or surface rules. Replace a report date with a current bundle
when it needs a corrected publication; the replacement writes a strict bundle-v9 archive and
publication-v6 receipt.

## Interrupted publication

Imports and presentation publishes share `generated/publisher.lock`. A later publisher operation
reconciles interrupted import staging and clears abandoned presentation staging while holding that
lock. Preserve the repository state, identify the first error, correct its cause, and rerun the
same supported import or publish command.

The recovery design keeps the prior validated release in service when validation, staging, or
promotion fails. If the current pointer or release is missing after a host-level storage failure,
stop and inspect the service and filesystem state before attempting another operation; no supported
manual pointer repair exists.

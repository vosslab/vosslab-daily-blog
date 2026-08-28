# Troubleshooting

Use the first failing command as the diagnosis. The publisher leaves the current immutable release
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
a complete immutable release.

## Presentation publish rejects source

The manual publisher verifies that importer-owned content remains byte-for-byte consistent with its
accepted bundle and that `docs/status.md` matches the publication records. Errors such as
`Imported post has drifted from its bundle` or `Publication status has drifted from installed
records` indicate a contract violation, not a cosmetic publish problem.

- Restore the imported content through the producer/importer workflow; do not edit it to match a
  guess.
- Keep CSS, reader navigation, brand, and MkDocs changes outside importer-owned posts and
  `docs/status.md`; repository documentation is not part of the built blog.
- Run `./publish_site.sh` again after the source is coherent.

See [operations.md](operations.md) for the files owned by the importer and the publication receipt
guarantees.

## Bundle import rejects input

Inspect the complete bundle with the validator before retrying an import:

```bash
source source_me.sh && python3.13 scripts/validate_daily_post.py \
  --candidate /path/to/bundle/post.md \
  --evidence /path/to/bundle/evidence.json \
  --projection /path/to/bundle/editorial_projection.json \
  --bundle /path/to/bundle/bundle.json
```

The importer requires a physical bundle directory with its four declared files and one `assets/`
directory. Schema, hash, path, provenance, front-matter, and strict-build errors are rejected before
publication. Fix the producer output in `vosslab-podcast`, create a new complete bundle, and retry
the producer's date workflow. An exact retry of an already installed bundle is reported as
`idempotent`; a different bundle for an occupied report date is intentionally rejected.

Use [USAGE.md](USAGE.md) for the import command and [operations.md](operations.md) for the
transaction and recovery guarantees.

## Interrupted publication

Imports and presentation publishes share `generated/publisher.lock`. A later publisher operation
reconciles interrupted import staging and clears abandoned presentation staging while holding that
lock. Preserve the repository state, identify the first error, correct its cause, and rerun the
same supported import or publish command.

The recovery design keeps the prior immutable release in service when validation, staging, or
promotion fails. If the current pointer or release is missing after a host-level storage failure,
stop and inspect the service and filesystem state before attempting another operation; no supported
manual pointer repair exists.

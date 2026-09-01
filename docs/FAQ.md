# Frequently asked questions

This page answers the boundary and operating questions that come up before using the private-LAN
work log. Use the linked reference documents for commands, recovery procedures, and contracts.

## What does it publish?

The repository validates complete publication bundles and presents the accepted work-log articles as
a strict MkDocs site. It owns the current source tree, publication records, date-owned content
releases, the atomic `site` pointer, and the static server. The full design is in
[CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md).

## Where are articles made?

`vosslab-podcast` makes the articles. It collects evidence, runs the author and referee routes,
creates the complete bundle, and owns scheduling. Its systemd timer directly runs
`./make_blog.py --yesterday` at 04:00 America/Chicago. This repository neither generates blog
content nor runs models or Git collection; it independently validates and imports the finished
bundle.
See [operations.md](operations.md) for the repository boundary.

## Is the site public?

No. The checked-in service serves the selected current release on port 8016 for LAN and Tailscale
access. It is beta infrastructure, not a public-internet publishing service. The service contract
and installation steps are in [INSTALL.md](INSTALL.md) and [operations.md](operations.md).

## When should I publish?

Run `./publish_site.sh` after changing publisher-owned presentation material such as CSS, brand
assets, reader navigation, or MkDocs configuration. Repository documentation remains outside the
built blog. The command performs a strict staged build and atomically promotes a presentation
release without changing imported posts or the record-derived status page. The everyday workflow
is in [USAGE.md](USAGE.md).

## How do I add an article?

Start the normal daily workflow in `vosslab-podcast`, which sends its complete bundle as a sealed
standard-input transfer to this repository's importer. The manual physical-bundle command remains
available for inspection or deliberate operator work. An exact retry is idempotent. When the producer deliberately regenerates
a date, its import uses `--replace-existing`; the publisher exchanges the validated date-owned
directories and commits their publication record last after a strict build. The supported import
command and input/output locations are in
[USAGE.md](USAGE.md).

## What proves the page is the accepted article?

Each new `vosslab.daily-blog.publication.v6` record binds the selected artifact, the canonical
publication-surface identity, and a SHA-256 of the ordered reader-visible post body. The importer
verifies the staged built article before import, and the presentation publisher verifies it again
before promoting a release. Normal template chrome is allowed; a page that merely repeats the
expected title and date is not sufficient.

## Which source markup can a new article use?

Every new bundle-v9 import names the exact `publication_source_safety.v1` policy: canonical-vector
digest `d50166736d79be7f7715cc0f7585fac71dfb2aecc1c631b10e01aeca2fb63c6b` over its 35-case
executable corpus. Before staging, the publisher independently admits ordinary Markdown, permitted
evidence images, canonical HTTPS GitHub links, exact evidence comments, and the excerpt marker.
The staged reader-body verification independently confirms that the built Material article preserves
the sealed ordered body rather than merely validating the incoming source.

## How does the survivor surface affect evidence and images?

The aggregate evidence packet remains the sealed audit record, but it is not automatic permission
to cite or publish every collected item. Bundle v9 carries one canonical `publication_surface.json`
for the promoted survivor set. It names the covered repositories, allowed evidence IDs, and each
selected screenshot's evidence ID, bundle asset path, and published path. The publisher verifies
that this surface agrees with the packet and editorial projection, then uses it as the same
authority for post admission, archive contents, staged assets, and rendered-page image paths.

Only surface-selected images are copied into the date-owned article assets. An aggregate screenshot
outside that surface remains audit evidence and cannot appear in the Markdown or rendered article.
This keeps a grounded survivor's images admissible without expanding its publication scope to every
image collected during the run.

## What happens to older publication records?

New imports create v6 records from bundle v9. Exact v5 and v3 records remain readable,
redeployable installed history for presentation verification. They are not accepted as new imports;
replacing their date with a current bundle writes a v6 record. The historical read-only path leaves
the installed post unchanged, so content admitted under an older policy remains historical material.

## Which Python do I use?

Use Python 3.13. `publish_site.sh` selects `python3.13` from `PATH`; activate a Python 3.13 virtual
environment first when dependencies should remain isolated. Follow [INSTALL.md](INSTALL.md) for
setup and [TROUBLESHOOTING.md](TROUBLESHOOTING.md) when the publisher rejects the interpreter.

# Frequently asked questions

This page answers the boundary and operating questions that come up before using the private-LAN
work log. Use the linked reference documents for commands, recovery procedures, and contracts.

## What does it publish?

The repository validates complete publication bundles and presents the accepted work-log articles as
a strict MkDocs site. It owns the current source tree, publication records, immutable releases, the
atomic `site` pointer, and the static server. The full design is in
[CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md).

## Where are articles made?

`vosslab-podcast` makes the articles. It collects evidence, runs the author and referee routes,
creates the complete bundle, and owns scheduling. This repository neither generates blog content
nor runs models or Git collection; it independently validates and imports the finished bundle.
See [operations.md](operations.md) for the repository boundary.

## Is the site public?

No. The checked-in service serves the selected immutable release on port 8016 for LAN and Tailscale
access. It is beta infrastructure, not a public-internet publishing service. The service contract
and installation steps are in [INSTALL.md](INSTALL.md) and [operations.md](operations.md).

## When should I publish?

Run `./publish_site.sh` after changing publisher-owned presentation material such as CSS, brand
assets, reader navigation, or MkDocs configuration. Repository documentation remains outside the
built blog. The command performs a strict staged build and atomically promotes a presentation
release without changing imported posts or the record-derived status page. The everyday workflow
is in [USAGE.md](USAGE.md).

## How do I add an article?

Start the normal daily workflow in `vosslab-podcast`, then import its complete physical bundle with
this repository's importer. An exact retry is idempotent; a different bundle for an already
published report date is rejected to protect history. The supported import command and input/output
locations are in [USAGE.md](USAGE.md).

## Which Python do I use?

Use Python 3.13. `publish_site.sh` selects `python3.13` from `PATH`; activate a Python 3.13 virtual
environment first when dependencies should remain isolated. Follow [INSTALL.md](INSTALL.md) for
setup and [TROUBLESHOOTING.md](TROUBLESHOOTING.md) when the publisher rejects the interpreter.

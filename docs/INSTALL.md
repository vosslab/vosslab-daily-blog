# Install

This repository is used directly from its working tree. Installation provides the Python
dependencies needed to validate bundles, build MkDocs, and run the repository-owned publisher.

## Requirements

- A checkout of `vosslab-daily-blog`.
- Python 3.13 for validation, MkDocs builds, and `publish_site.sh`.
- `pip` to install the checked-in publication and development dependencies.
- `systemd --user` only when this host should serve the LAN site on port 8016.

The producer repository, `vosslab-podcast`, owns bundle generation and scheduling. This repository
accepts an already complete publication bundle; it does not need producer credentials or model
runtime configuration.

## Install dependencies

From the repository root, install the checked-in dependencies into Python 3.13:

```bash
python3.13 -m pip install -r pip_requirements.txt -r pip_requirements-dev.txt
```

An isolated environment is optional. When you use one, select it explicitly for publication:

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install -r pip_requirements.txt -r pip_requirements-dev.txt
source .venv/bin/activate
./publish_site.sh
```

`pip_requirements.txt` installs MkDocs Material and YAML support. The development requirements add
pytest and repository hygiene tools. The repository is not packaged for `pip install`; run its
scripts from the checkout after sourcing `source_me.sh`.

## Verify install

Confirm that the environment can load the MkDocs command used for strict builds:

```bash
python3.13 -m mkdocs --version
```

Then validate the checked-in publication source without changing the served release:

```bash
source source_me.sh && python3.13 -m mkdocs build --strict
```

## Install the LAN service

Install the checked-in user service only on a host that should expose the site to the LAN and
Tailscale interface:

```bash
mkdir -p ~/.config/systemd/user
cp deploy/vosslab-daily-blog.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now vosslab-daily-blog.service
```

The service uses Python's static HTTP server, binds `0.0.0.0:8016`, and serves the atomic `site`
pointer. It does not generate posts or schedule publication; see [operations.md](operations.md)
for the operational boundary and recovery procedure.

## Runtime selection

`publish_site.sh` resolves `python3.13` before loading the repository shell environment. Activate a
Python 3.13 virtual environment before running the script when it should own publication.

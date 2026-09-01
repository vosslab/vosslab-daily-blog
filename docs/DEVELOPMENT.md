# Development

This guide is for contributors changing the publisher itself. The producer repository,
`vosslab-podcast`, owns evidence collection, content generation, bundle construction, and
scheduling; this repository owns the validation and static-publication boundary. Read
[CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md) before changing that boundary and
[operations.md](operations.md) before changing the service or recovery behavior.

## Work from the checkout

Install dependencies as described in [INSTALL.md](INSTALL.md), optionally into a repository-local
environment, then source the repository environment before invoking Python scripts. `source_me.sh`
establishes the checkout on `PYTHONPATH`, disables bytecode files, and preserves local shell setup.

```bash
cd /home/vosslab/nsh/vosslab-daily-blog
source source_me.sh
```

The publisher contract uses Python 3.13. A repository-local environment is optional; these commands
use the default system interpreter:

```bash
python3.13 -m pytest tests/
python3.13 -m mkdocs build --strict
```

Activate `.venv` before running `publish_site.sh` when an isolated Python 3.13 environment should
own publication. The deployment module validates the resolved interpreter before publication.

## Choose the correct change boundary

| Change | Primary owner | Required companion work |
| --- | --- | --- |
| Bundle, evidence, editorial-projection, or record contract | validators and importer | Coordinate an explicit versioned change with `vosslab-podcast`, then add focused contract tests. |
| Incoming bundle filesystem boundary | `scripts/bundle_snapshot.py` | Preserve one held no-follow snapshot; test root, roster, asset, and symlink replacement behavior. |
| Import transaction, recovery, or release lifecycle | `scripts/publication_transaction.py` and importer | Prove failure preservation and retry behavior in `tests/test_publication_bundle_import.py`. |
| Presentation snapshot, source identity, or promotion | `scripts/site_deployment.py` | Add deployment tests and run a strict staged build. |
| Theme, reader navigation, logo, or public site content | `mkdocs.yml` and `docs/` | Run the strict build, then use `./publish_site.sh` when the checked-in presentation is ready. |
| Repository documentation | root Markdown and `docs/*.md` | Run documentation hygiene; repository Markdown is excluded from the built blog. |
| Static server configuration | `deploy/vosslab-daily-blog.service` | Follow the install and reload procedure in [operations.md](operations.md). |

Do not manually modify importer-owned posts, evidence assets, `docs/status.md`, publication
records, immutable releases, or the `site` pointer. The importer and presentation publisher use
those artifacts as their publication contract; manual changes undermine their identity checks.

## Validate in layers

Start with the focused test module nearest the change. Keep permanent pytest tests deterministic;
whole-system and browser checks belong in the separate execution tiers described by
[E2E_TESTS.md](E2E_TESTS.md).

```bash
source source_me.sh && python3.13 -m pytest tests/test_publication_bundle_import.py
source source_me.sh && python3.13 -m pytest tests/test_site_deployment.py
source source_me.sh && python3.13 -m pytest tests/
source source_me.sh && python3.13 -m mkdocs build --strict
git diff --check
```

For a presentation-only change, finish the local checks before `./publish_site.sh`. That command
performs the staged strict build and atomically promotes a new release, so it is both the delivery
step and an integration check. Its endpoint verification requires the local static service to be
running; use [operations.md](operations.md) to inspect or repair that service rather than adding a
second server path.

## Keep the handoff durable

When a change alters a behavior or contract, update the smallest authoritative documentation set:

- Record implementation and contract changes in [CHANGELOG.md](CHANGELOG.md).
- Update [CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md) for responsibility or lifecycle changes.
- Update [operations.md](operations.md), [INSTALL.md](INSTALL.md), or [USAGE.md](USAGE.md) only
  when their operator-facing workflow changes.
- Add or revise focused tests before relying on a manual proof.

The design goal is a narrow, versioned producer/publisher interface with failure-atomic publishing.
If a proposed change requires a special case across that boundary, first identify the missing
contract or ownership rule and repair it at the design level.

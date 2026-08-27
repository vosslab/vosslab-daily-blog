# Vosslab Daily Blog

A private MkDocs Material site for dated, evidence-grounded Vosslab work logs.

## Live URLs

- `http://aella.local:8016`
- `http://192.168.2.13:8016`

## Publication architecture

Each completed Central calendar day has durable evidence and publication records:

- `data/daily/YYYY-MM-DD.json`: dated, re-creatable GitHub evidence. A historical recollection replaces this record.
- `data/publications/YYYY-MM-DD.json`: collection, canonical-publication, and editorial-revision state.
- `data/editorial/candidates/YYYY-MM-DD.md` and `data/editorial/manifests/YYYY-MM-DD.json`: a validated editorial candidate and its generation record.

The canonical post is deterministic and publishes from validated evidence. Editorial work produces a later revision of an already-published canonical post. The status page reads publication records directly.

Site builds stage under `generated/staging/`, promote into `generated/releases/`, and atomically switch the `site` release pointer. The static service reads that pointer directly.

## Mirror-backed evidence

`vosslab-daily-blog-mirrors.timer` refreshes a cache of depth-1 Vosslab public-repository checkouts independently of canonical publication. For an account-linked commit, the collector reads `README.md`, `docs/CHANGELOG.md`, and commit-selected `docs/screenshots/` blobs as `commit:path` Git objects, then records the source commit and blob SHA. This prevents a newer checkout tip or local working-tree edit from changing historical evidence. The canonical publisher never waits for the whole cache refresh: it fetches an exact needed commit from an available mirror, and a missing matching mirror uses the bounded public GitHub API fallback.

## Local setup

```bash
cd ~/nsh/vosslab-daily-blog
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt -r pip_requirements-dev.txt
```

Collection requires `GITHUB_TOKEN` in the Hermes environment file consumed by the scheduler wrapper. The defaults are `vosslab` for the GitHub owner, `America/Chicago` for the report timezone, and `/home/vosslab/repo-mirrors/vosslab` for synchronized depth-1 mirrors. Editorial reconciliation also requires the configured Hermes runtime.

## Commands

```bash
# Process one completed date: mirror sync, canonical publication, then editorial reconciliation
scripts/process_day.sh 2026-08-19

# Collect and publish the canonical post for the previous completed Central day
.venv/bin/python scripts/daily_publish.py

# Recreate canonical publication for a completed historical day
.venv/bin/python scripts/daily_publish.py --date 2026-08-10

# Reconcile one eligible editorial revision
.venv/bin/python scripts/reconcile_editorial.py --limit 1

# Reconcile a named date
.venv/bin/python scripts/reconcile_editorial.py --date 2026-08-10

# Validate source-site content
.venv/bin/mkdocs build --strict
```

## Scheduler ownership

- Hermes cron runs `~/.hermes/scripts/vosslab-daily-blog-publish.sh` at 02:00 America/Chicago for deterministic collection and canonical publication.
- `vosslab-daily-blog-editorial.timer` starts editorial reconciliation at 02:15 America/Chicago with its own service timeout and journal.

## Layout

- `scripts/collect_github_events.py`: authenticated public-evidence collection.
- `scripts/daily_publish.py`: canonical collection-to-publication coordinator.
- `scripts/reconcile_editorial.py`: editorial candidate and promotion coordinator.
- `scripts/publication_state.py`: durable publication state and atomic release promotion.
- `scripts/run_layered_editorial.py`: evidence-grounded editorial candidate creation.
- `scripts/validate_daily_post.py`: deterministic post validator.
- `docs/operations.md`: service, state, scheduler, and recovery runbook.

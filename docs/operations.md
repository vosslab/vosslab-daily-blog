# Operations and recovery

## Durable components

| Component | Location | Owner |
| --- | --- | --- |
| Evidence record | `data/daily/YYYY-MM-DD.json` | collector |
| Publication state | `data/publications/YYYY-MM-DD.json` | publication coordinators |
| Canonical source post | `docs/blog/posts/YYYY-MM-DD.md` | canonical publisher |
| Editorial candidate | `data/editorial/candidates/YYYY-MM-DD.md` | editorial reconciler |
| Staged releases | `generated/staging/` | release helper |
| Immutable releases | `generated/releases/` | release helper |
| Served release pointer | `site` | release helper |
| Canonical scheduler | Hermes cron job `767ec5575844` | daily publisher |
| Editorial scheduler | `vosslab-daily-blog-editorial.timer` | editorial reconciler |
| Static server | `vosslab-daily-blog.service` | systemd |

## State model

| Collection | Canonical | Editorial | Meaning |
| --- | --- | --- | --- |
| `empty` or `ready` | `published` | `pending`, `degraded`, or `promoted` | A reader-visible canonical post exists. |
| `failed` | `pending` | `pending` | Status records a bounded collection failure for operator review. |
| `ready` | `staging` | `pending` | A validated canonical source is moving through a staged build. |
| `ready` | `published` | `staging` | A published date is receiving an editorial candidate. |

## Normal flow

1. At 01:30 America/Chicago, `vosslab-daily-blog-mirrors.timer` refreshes the depth-1 public-repository cache under `/home/vosslab/repo-mirrors/vosslab`. This is cache warming, not a publication prerequisite.
2. At 02:00 America/Chicago, Hermes cron runs the deterministic canonical publisher for the previous completed Central day.
3. The collector sends `GITHUB_TOKEN` as a Bearer authorization header and writes the dated evidence record. It reads documentation and screenshots from the exact account-linked commit in a matching mirror, fetching that exact commit when needed; a missing matching mirror uses the bounded public-GitHub fallback.
4. The publisher writes the date's publication state, renders its canonical post, validates it, builds a staged release, and atomically switches `site`. A collection failure preserves the prior content but also publishes its safe failure state to `/status/`.
5. At 02:15 America/Chicago, the systemd editorial timer reconciles one eligible date.
6. The reconciler writes a candidate and manifest under `data/editorial/`, validates the candidate, stages an editorial release, and updates the publication record after promotion.
7. `docs/status.md` renders from durable publication records and releases with each state transition.

## Operator checks

```bash
cd ~/nsh/vosslab-daily-blog
systemctl --user status vosslab-daily-blog.service
systemctl --user status vosslab-daily-blog-editorial.timer
systemctl --user list-timers vosslab-daily-blog-editorial.timer
hermes cron list
curl --fail http://aella.local:8016/blog/
curl --fail http://aella.local:8016/status/
```

## Manual operations

```bash
cd ~/nsh/vosslab-daily-blog

# Process a completed date from mirror synchronization through editorial reconciliation
scripts/process_day.sh 2026-08-19

# Publish canonical content for a completed date
.venv/bin/python scripts/daily_publish.py --date 2026-08-10

# Reconcile a named editorial revision
.venv/bin/python scripts/reconcile_editorial.py --date 2026-08-10

# Inspect one durable record
python3 -m json.tool data/publications/2026-08-10.json

# Validate source content without release promotion
.venv/bin/mkdocs build --strict
```

A successful staged build promotes an atomic release pointer. The static service resolves `site` for each request, so release promotion needs no service restart.

## Recovery

- A collection failure writes `collection: failed` while the existing served release remains unchanged.
- A canonical staging failure preserves the previously served release and leaves the date visible in its durable state.
- An editorial failure writes `editorial: degraded`; the published canonical post remains current.
- The next editorial timer run reconciles pending and degraded dates in descending date order.
- A service recovery starts with `systemctl --user restart vosslab-daily-blog.service`, then the operator checks above verify the live release.

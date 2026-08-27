# Vosslab Work Log

A private work log for dated Vosslab GitHub activity, served on the local network at [`aella.local:8016`](http://aella.local:8016).

## What appears here

- A canonical daily post generated from a completed date's validated GitHub evidence.
- An editorial revision when the published date later receives a validated enhancement.
- A status page that reports collection, canonical-publication, and editorial-revision state for each tracked date.

!!! info "Evidence boundary"

    Each post is grounded in a dated, re-creatable GitHub evidence packet. It records bounded public activity, account-wide public-repository commits, and README, report-date changelog, and commit-selected screenshot evidence when available. Matching depth-1 mirrors under `/home/vosslab/repo-mirrors/vosslab` supply commit-pinned local document and screenshot blobs; the GitHub API supplies a bounded fallback when a mirror is unavailable.

## Daily publishing path

1. The canonical publisher collects authenticated evidence for the previous completed Central day.
2. It stores a re-creatable dated evidence record and a durable publication-state record.
3. It renders, validates, stages, and atomically publishes the canonical post.
4. The editorial reconciler creates a candidate from the published date's evidence and promotes a validated revision through its own release.

[Browse the work log](blog/index.md){ .md-button .md-button--primary }
[View publication status](status.md){ .md-button }

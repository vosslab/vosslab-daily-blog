# Vosslab Daily Blog instructions

This is a standalone MkDocs Material site. It is not part of `vosslab-podcast`.

## Daily writer checklist

- [ ] Read `data/daily/latest.json`, then the referenced date-specific JSON source artifact.
- [ ] Modify only the corresponding `docs/blog/posts/YYYY-MM-DD.md` and `docs/status.md` unless a build fix is necessary.
- [ ] Keep the YAML `date.created` value and one H1.
- [ ] State only facts directly supported by the source artifact.
- [ ] Describe the source as a **bounded public GitHub evidence packet**: public Events, account-wide public-repository commits, and commit-pinned README, report-date changelog, and screenshot evidence when available.
- [ ] Link repository names; keep commit identifiers in the evidence packet unless a public post explicitly needs one for reader context.
- [ ] Write a clear no-activity note when the source has no qualifying events.
- [ ] Do not mention the podcast project or local LLMs.
- [ ] Run `.venv/bin/mkdocs build --strict` before declaring the post published.
- [ ] Leave the last good built site intact if source collection is incomplete or build validation fails.

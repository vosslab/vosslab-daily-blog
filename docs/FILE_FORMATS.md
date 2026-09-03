# File formats

## Producer handoff

The automated importer receives a bounded binary transfer envelope on standard input. Its JSON
manifest is temporary routing data. The payload delivered to this repository contains:

- `bundle.json`, used only to obtain the report date, bundle identity, post route, and asset routes;
- `post.md`, treated as authoritative producer-supplied bytes;
- zero or more direct files under `assets/`, limited to images referenced by the final post.

The importer does not persist the envelope or `bundle.json`. It does not receive or archive evidence,
repository rosters, editorial projections, review results, or publication-surface JSON.

## Installed source

For report date `YYYY-MM-DD`, durable source uses:

```text
docs/blog/posts/YYYY-MM-DD.md
docs/blog/posts/YYYY-MM-DD/<selected-image>
```

The Markdown uses `YYYY-MM-DD/<selected-image>` as its relative image path. A same-date replacement
replaces both the Markdown and the complete sibling asset directory. Images discovered upstream but
not referenced by the final Markdown are neither transferred nor installed.

## Rendered releases

MkDocs writes a complete static site into a disposable stage. Successful output is promoted below
`generated/releases/`, and `site` is atomically switched to the current release. Deployment metadata
inside a rendered release describes rendering mechanics only; it is not an editorial publication
record.

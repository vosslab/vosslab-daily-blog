# Human guidance

<!-- VENDORED HEADER: START -->
Record the durable guidance Neil Voss states, or approves for preservation here, in his own words:
first person or close paraphrase, one to three lines per bullet. Material he supplies as a source
may inform [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md) once it is settled, and an entry of uncertain
origin belongs there too. Rules: [REPO_STYLE.md](REPO_STYLE.md).
[PROPAGATED HEADER - ENTRIES BELOW ARE YOURS]
<!-- VENDORED HEADER: END -->

## Decision priority

- The LLMs control which images go into the blog post (perhaps a separate decorator LLM agent puts them in)
- the machine uses a deterministic system for copying only the used images to the daily-blog repo and where they are stored along side the blog

- once the final blog post is created, all the previous steps become unneeded; a fresh run would replace them. But before the final blog post is
  created, the previous steps are needed for tracing issues.

## Review expectations

## Working style

- Have single-repository propagation add a `devel/changelog_lib.py`-compatible changelog entry only
  when it makes real changes; recurring `.gitignore` churn must not create one.

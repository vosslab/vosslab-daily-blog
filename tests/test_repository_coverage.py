"""Behavioral contracts for complete daily repository coverage."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from scripts.collect_github_events import (
    build_repository_evidence,
    changelog_entries_for_date,
    readme_context,
    read_mirror_document,
    resolve_repo_checkout,
    render_post,
)
from scripts.run_layered_editorial import (
    claim_packet,
    ensure_repository_coverage,
    finalize_article,
)
from scripts.validate_daily_post import validate_post


class RepositoryCoverageValidationTests(unittest.TestCase):
    def test_rejects_article_that_omits_an_active_repository(self) -> None:
        evidence = {
            "report_date": "2026-08-20",
            "source_url": "https://api.github.com/users/vosslab/events/public?per_page=100&page=1",
            "events": [{"repo": "vosslab/active-project"}],
            "repositories": [
                {
                    "repo": "vosslab/active-project",
                    "commits": [],
                    "commit_source_url": "",
                }
            ],
            "screenshots": [],
        }
        candidate = """---
date:
  created: 2026-08-20
slug: coverage
---

# Coverage matters

I recorded a bounded work log that keeps the public source visible.
<!-- more -->

## What changed

I focused on the evidence that was available rather than treating the snapshot as a complete history.

## Where the work stands

The result is intentionally bounded and not complete commit history, with more detail available in the source.

Reconstructed from [public GitHub activity](https://api.github.com/users/vosslab/events/public?per_page=100&page=1).
It is a bounded snapshot, not complete commit history.
"""

        issues = validate_post(candidate, evidence)

        self.assertIn("article omits active repository: vosslab/active-project", issues)

    def test_canonical_render_includes_commit_only_owned_repository(self) -> None:
        record = {
            "report_date": "2026-08-20",
            "timezone": "America/Chicago",
            "source_url": "https://api.github.com/users/vosslab/events/public?per_page=100&page=1",
            "pages_fetched": 1,
            "max_pages": 3,
            "events": [],
            "repositories": [{
                "repo": "vosslab/active-without-event",
                "event_count": 0,
                "description": "A project with a dated commit.",
                "commits": [{"subject": "documented activity"}],
            }],
            "screenshots": [],
        }

        rendered = render_post(record)
        issues = validate_post(rendered, record)

        self.assertIn("https://github.com/vosslab/active-without-event", rendered)
        self.assertNotIn("article omits active repository: vosslab/active-without-event", issues)

    def test_adds_ordinary_coverage_for_every_active_repository(self) -> None:
        packet = {
            "repositories": [
                {
                    "repo": "vosslab/secure-agent-playbook-generic",
                    "repository_url": "https://github.com/vosslab/secure-agent-playbook-generic",
                    "commits": [{"subject": "updated for codex"}],
                },
                {
                    "repo": "vosslab/ferrum-chemical-forge",
                    "repository_url": "https://github.com/vosslab/ferrum-chemical-forge",
                    "commits": [{"subject": "Corrected document authority"}],
                },
            ]
        }

        covered = ensure_repository_coverage("# Existing work\n", packet)

        self.assertIn("## Project coverage", covered)
        self.assertIn("https://github.com/vosslab/secure-agent-playbook-generic", covered)
        self.assertIn("https://github.com/vosslab/ferrum-chemical-forge", covered)
        self.assertIn("updated for codex", covered)
        self.assertIn("Corrected document authority", covered)
        self.assertNotIn("Forked project work", covered)

    def test_extracts_readme_context_and_exact_dated_changelog_block(self) -> None:
        readme = "# Example Project\n\nA concise project description for readers.\n\n## Install\n"
        changelog = "## 2026-08-21\n- tomorrow\n\n## 2026-08-20\n- retained change\n\n## 2026-08-19\n- older change\n"

        context = readme_context(readme)
        entries = changelog_entries_for_date(changelog, date(2026, 8, 20))

        self.assertEqual(context, "A concise project description for readers.")
        self.assertEqual(entries, ["- retained change"])

    def test_reads_document_from_exact_owner_mirror(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            checkout = root / "project"
            (checkout / "docs").mkdir(parents=True)
            (checkout / "README.md").write_text("# Project\n\nMirror context.\n", encoding="utf-8")
            (checkout / "docs" / "CHANGELOG.md").write_text("## 2026-08-20\n- mirrored change\n", encoding="utf-8")
            for command in (
                ["git", "init", str(checkout)],
                ["git", "-C", str(checkout), "config", "user.email", "test@example.invalid"],
                ["git", "-C", str(checkout), "config", "user.name", "Test"],
                ["git", "-C", str(checkout), "remote", "add", "origin", "https://github.com/vosslab/project.git"],
                ["git", "-C", str(checkout), "add", "."],
                ["git", "-C", str(checkout), "commit", "-m", "snapshot"],
            ):
                subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            head = subprocess.run(
                ["git", "-C", str(checkout), "rev-parse", "HEAD"],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).stdout.strip()
            (checkout / "docs" / "CHANGELOG.md").write_text("## 2026-08-21\n- later text\n", encoding="utf-8")
            with patch.dict("os.environ", {"VOSSLAB_MIRROR_ROOT": str(root)}):
                resolved = resolve_repo_checkout("vosslab/project")
            document = read_mirror_document(checkout, "docs/CHANGELOG.md", head)

        self.assertEqual(resolved, checkout)
        self.assertEqual(document["path"], "docs/CHANGELOG.md")
        self.assertEqual(document["text"], "## 2026-08-20\n- mirrored change\n")
        self.assertEqual(document["commit"], head)
        self.assertTrue(document["sha"])

    def test_enrichment_keeps_readme_and_dated_changelog_provenance(self) -> None:
        target = date(2026, 8, 20)
        timezone = ZoneInfo("America/Chicago")

        def document_for(_repo: str, path: str, _ref: str) -> dict[str, str]:
            if path == "README.md":
                return {"path": path, "sha": "readme-sha", "text": "# Project\n\nReader context.\n"}
            return {"path": path, "sha": "changelog-sha", "text": "## 2026-08-20\n- evidence detail\n"}

        with (
            patch("scripts.collect_github_events.request_repo_info", return_value={"default_branch": "main"}),
            patch("scripts.collect_github_events.request_repo_commits", return_value=("commits-url", [{"subject": "changed"}])),
            patch("scripts.collect_github_events.request_repo_document", side_effect=document_for),
        ):
            repositories, errors = build_repository_evidence([], "vosslab", target, timezone, owned_repos=["vosslab/project"])

        self.assertEqual(errors, [])
        self.assertEqual(repositories[0]["readme"], {"path": "README.md", "sha": "readme-sha", "summary": "Reader context.", "source": "github_api", "commit": ""})
        self.assertEqual(repositories[0]["changelog"], {"path": "docs/CHANGELOG.md", "sha": "changelog-sha", "entries": ["- evidence detail"], "source": "github_api", "commit": ""})

    def test_claim_packet_carries_document_context_with_provenance(self) -> None:
        evidence = {
            "report_date": "2026-08-20",
            "timezone": "America/Chicago",
            "source_url": "https://api.github.com/users/vosslab/events/public?per_page=100&page=1",
            "coverage_note": "bounded",
            "events": [],
            "commit_enrichment_errors": [],
            "screenshots": [],
            "repositories": [{
                "repo": "vosslab/project",
                "readme": {"path": "README.md", "sha": "readme-sha", "summary": "Context."},
                "changelog": {"path": "docs/CHANGELOG.md", "sha": "change-sha", "entries": ["- dated change"]},
                "commits": [],
            }],
        }

        packet = claim_packet(evidence)

        self.assertEqual(packet["repositories"][0]["readme"]["sha"], "readme-sha")
        self.assertEqual(packet["repositories"][0]["changelog"]["entries"], ["- dated change"])

    def test_finalization_places_escaped_coverage_before_canonical_footer(self) -> None:
        packet = {
            "public_events_source": "https://api.github.com/users/vosslab/events/public?per_page=100&page=1",
            "repositories": [
                {
                    "repo": "vosslab/active-project",
                    "commits": [{"subject": "fixed [unsafe](https://example.invalid)"}],
                }
            ],
        }
        article = "# Existing work\n\nA bounded account.\n\nReconstructed from [public GitHub activity](https://other.invalid).\nIt is a bounded snapshot, not complete commit history.\n"

        finalized = finalize_article(article, packet)

        self.assertIn("fixed \\[unsafe\\]", finalized)
        self.assertNotIn("https://example.invalid", finalized)
        self.assertLess(
            finalized.index("## Project coverage"),
            finalized.index("Reconstructed from [public GitHub activity]"),
        )
        self.assertTrue(
            finalized.endswith(
                "It is a bounded snapshot, not complete commit history.\n"
            )
        )
        self.assertEqual(finalize_article(finalized, packet).count("## Project coverage"), 1)

    def test_coverage_words_do_not_consume_the_narrative_word_budget(self) -> None:
        evidence = {
            "report_date": "2026-08-20",
            "source_url": "https://api.github.com/users/vosslab/events/public?per_page=100&page=1",
            "events": [{"repo": "vosslab/active-project"}],
            "repositories": [{"repo": "vosslab/active-project", "commits": []}],
            "screenshots": [],
        }
        coverage = "coverage " * 1_100
        candidate = f"""---
date:
  created: 2026-08-20
slug: coverage
---

# Coverage matters

I recorded a bounded work log with a deliberately compact narrative.
<!-- more -->

## What changed

I kept the narrative focused on the day's evidence instead of expanding it into a complete history.

## Where the work stands

The result remains bounded and not complete commit history, while the repository record stays comprehensive.

## Project coverage

{coverage}

Reconstructed from [public GitHub activity](https://api.github.com/users/vosslab/events/public?per_page=100&page=1).
It is a bounded snapshot, not complete commit history.
"""

        issues = validate_post(candidate, evidence)

        self.assertNotIn("article must remain concise for a general reader", issues)

    def test_includes_owned_repository_with_dated_commit_without_event(self) -> None:
        target = date(2026, 8, 20)
        timezone = ZoneInfo("America/Chicago")

        def commits_for(repo: str, *_args: object) -> tuple[str, list[dict[str, str]]]:
            commits = []
            if repo == "vosslab/active-without-event":
                commits = [{"subject": "documented activity", "committed_at": "2026-08-20T12:00:00-05:00"}]
            return f"https://api.github.com/repos/{repo}/commits", commits

        with (
            patch("scripts.collect_github_events.request_repo_info", return_value={}),
            patch("scripts.collect_github_events.request_repo_commits", side_effect=commits_for),
            patch("scripts.collect_github_events.request_repo_document", return_value={}),
        ):
            repositories, errors = build_repository_evidence(
                [],
                "vosslab",
                target,
                timezone,
                owned_repos=["vosslab/active-without-event", "vosslab/quiet"],
            )

        self.assertEqual(errors, [])
        self.assertEqual([item["repo"] for item in repositories], ["vosslab/active-without-event"])
        self.assertEqual(repositories[0]["event_count"], 0)


if __name__ == "__main__":
    unittest.main()

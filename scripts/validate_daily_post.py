#!/usr/bin/env python3
"""Validate a source-grounded, paragraph-form daily work-log candidate."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


LINK_RE = re.compile(r"\[[^\]]+\]\((https?://[^)]+)\)")
WORD_RE = re.compile(r"[A-Za-z0-9']+")
THEME_SLUG_RE = re.compile(r"^[a-z]{3,32}$")


def parse_args() -> argparse.Namespace:
    """Parse candidate and evidence paths."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--evidence", required=True)
    return parser.parse_args()


def allowed_urls(evidence: dict[str, object]) -> set[str]:
    """Return source URLs that the evidence packet explicitly supports."""
    urls = {str(evidence.get("source_url", "")).strip()}
    for event in evidence.get("events", []):
        repo = str(event.get("repo", "")).strip()
        if repo:
            urls.add(f"https://github.com/{repo}")
    for repository in evidence.get("repositories", []):
        repo = str(repository.get("repo", "")).strip()
        if repo:
            urls.add(f"https://github.com/{repo}")
        source_url = str(repository.get("commit_source_url", "")).strip()
        if source_url:
            urls.add(source_url)
        for commit in repository.get("commits", []):
            html_url = str(commit.get("html_url", "")).strip()
            if html_url:
                urls.add(html_url)
    urls.discard("")
    return urls


def markdown_body(text: str) -> str:
    """Remove YAML front matter and headings before prose checks."""
    clean = text.strip()
    if clean.startswith("---"):
        parts = clean.split("---", 2)
        if len(parts) == 3:
            clean = parts[2]
    return "\n".join(line for line in clean.splitlines() if not line.startswith("#")).strip()


def media_paths(evidence: dict[str, object]) -> set[str]:
    """Return accepted post-relative and MkDocs source screenshot paths."""
    paths: set[str] = set()
    for item in evidence.get("screenshots", []):
        for key in ("relative_path", "media_path"):
            value = str(item.get(key, "")).strip()
            if value:
                paths.add(value)
    return paths


def validate_post(text: str, evidence: dict[str, object]) -> list[str]:
    """Return all deterministic publication issues in one candidate article."""
    issues = []
    report_date = str(evidence.get("report_date", ""))
    if f"created: {report_date}" not in text:
        issues.append("date front matter does not match evidence")
    slug_match = re.search(r"^slug:\s*([^\s#]+)\s*$", text, flags=re.MULTILINE)
    if not slug_match or not THEME_SLUG_RE.fullmatch(slug_match.group(1)):
        issues.append("article must use one single thematic word as its short slug")
    if len(re.findall(r"^# ", text, flags=re.MULTILINE)) != 1:
        issues.append("article must contain exactly one H1")

    h2_count = len(re.findall(r"^## (?!#)", text, flags=re.MULTILINE))
    if h2_count < 2:
        issues.append("article must use at least two descriptive H2 sections")
    if re.search(r"\]\(https://github\.com/[^)]+/commit/[0-9a-f]{7,40}\)", text):
        issues.append("article exposes developer commit links; use reader-facing prose")

    excerpt_parts = text.split("<!-- more -->")
    if len(excerpt_parts) != 2:
        issues.append("article must define one compact index excerpt")
    else:
        excerpt = excerpt_parts[0]
        if re.search(r"^#{2,6}\s+", excerpt, flags=re.MULTILINE):
            issues.append("index excerpt may not include section headings")
        excerpt_images = len(
            re.findall(r"^!\[[^\]]*\]\([^\n]+\)", excerpt, flags=re.MULTILINE)
        )
        if excerpt_images > 1:
            issues.append("index excerpt may contain at most one image")
        excerpt_body = markdown_body(excerpt)
        excerpt_paragraphs = [
            part.strip()
            for part in re.split(r"\n\s*\n", excerpt_body)
            if part.strip() and not part.lstrip().startswith("!")
        ]
        if len(excerpt_paragraphs) > 1:
            issues.append("index excerpt may contain at most one paragraph")

    body = markdown_body(text)
    narrative = markdown_body(text.split("## Project coverage", 1)[0])
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", body) if part.strip()]
    prose_paragraphs = [part for part in paragraphs if not part.startswith(("- ", "* ", "> "))]
    word_count = len(WORD_RE.findall(narrative))
    if len(prose_paragraphs) < 3 or word_count < 180:
        issues.append("article must be substantial paragraph-form prose")
    if word_count > 1_000:
        issues.append("article must remain concise for a general reader")
    if re.search(r"^\s*[-*]\s+", body, flags=re.MULTILINE):
        issues.append("article contains a raw event-log Markdown list")
    if "PushEvent" in text or "## Observed public activity" in text:
        issues.append("article contains raw event-log labels")
    if not re.search(r"\bI\b|\bmy\b", body, flags=re.IGNORECASE):
        issues.append("article must use a natural first-person work-log voice")
    lower = body.lower()
    if "bounded" not in lower or "not complete commit history" not in lower:
        issues.append("article must preserve the bounded-source statement")
    screenshot_count = len(evidence.get("screenshots", []))
    if screenshot_count > 0:
        paths = media_paths(evidence)
        if not any(path and path in text for path in paths):
            issues.append(
                "article must embed a screenshot path from the evidence packet"
            )

    approved = allowed_urls(evidence)
    for repository in evidence.get("repositories", []):
        repo = str(repository.get("repo", "")).strip()
        if repo and f"https://github.com/{repo}" not in text:
            issues.append(f"article omits active repository: {repo}")
    for url in LINK_RE.findall(text):
        if url not in approved:
            issues.append(f"article contains unsupported URL: {url}")
    if not any(url in text for url in approved if "api.github.com/users/" in url):
        issues.append("article must link the public GitHub source request")
    return issues


def main() -> int:
    """Validate one candidate and print a promotion-friendly result."""
    args = parse_args()
    evidence = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
    candidate = Path(args.candidate).read_text(encoding="utf-8")
    issues = validate_post(candidate, evidence)
    if issues:
        for issue in issues:
            print(f"ERROR: {issue}", file=sys.stderr)
        return 2
    print("Daily post validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

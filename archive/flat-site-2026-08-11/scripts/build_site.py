#!/usr/bin/env python3
"""Build the standalone Vosslab Daily Blog from validated JSON records."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any


DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ============================================
def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default=None,
        help="Generated-site directory; defaults to <repo>/public.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when the committed/generated public directory is stale.",
    )
    return parser.parse_args()


# ============================================
def load_json(path: Path) -> dict[str, Any]:
    """Load one required JSON object, with a useful failure message."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Cannot load JSON from {path}: {error}") from error
    if not isinstance(data, dict):
        raise RuntimeError(f"JSON root must be an object: {path}")
    return data


# ============================================
def required_text(data: dict[str, Any], key: str, source: Path) -> str:
    """Return a non-empty string field from a content object."""
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"{source}: {key!r} must be a non-empty string")
    return value.strip()


# ============================================
def safe_href(url: str, source: Path) -> str:
    """Accept ordinary HTTPS sources and site-relative navigation paths only."""
    if url.startswith("https://") or url.startswith("/"):
        return url
    raise RuntimeError(f"{source}: unsupported link URL {url!r}")


# ============================================
def validate_site(data: dict[str, Any], source: Path) -> dict[str, Any]:
    """Validate the site-level content contract."""
    for key in ("title", "subtitle", "hostname", "content_updated_at", "collection_status"):
        required_text(data, key, source)
    port = data.get("port")
    if not isinstance(port, int) or not 1 <= port <= 65535:
        raise RuntimeError(f"{source}: port must be an integer from 1 to 65535")
    return data


# ============================================
def validate_post(data: dict[str, Any], source: Path) -> dict[str, Any]:
    """Validate a dated post and its externally cited source records."""
    date_text = required_text(data, "date", source)
    if not DATE_RE.fullmatch(date_text):
        raise RuntimeError(f"{source}: date must use YYYY-MM-DD")
    try:
        dt.date.fromisoformat(date_text)
    except ValueError as error:
        raise RuntimeError(f"{source}: date is not a real calendar day") from error
    if source.stem != date_text:
        raise RuntimeError(f"{source}: filename must match date field {date_text}")

    required_text(data, "title", source)
    required_text(data, "summary", source)
    sections = data.get("sections")
    if not isinstance(sections, list) or not sections:
        raise RuntimeError(f"{source}: sections must be a non-empty list")
    for section in sections:
        if not isinstance(section, dict):
            raise RuntimeError(f"{source}: each section must be an object")
        required_text(section, "heading", source)
        paragraphs = section.get("paragraphs", [])
        bullets = section.get("bullets", [])
        if not isinstance(paragraphs, list) or not isinstance(bullets, list):
            raise RuntimeError(f"{source}: section paragraphs and bullets must be lists")
        for paragraph in paragraphs:
            if not isinstance(paragraph, str) or not paragraph.strip():
                raise RuntimeError(f"{source}: every paragraph must be non-empty text")
        for bullet in bullets:
            if not isinstance(bullet, dict):
                raise RuntimeError(f"{source}: every bullet must be an object")
            required_text(bullet, "text", source)
            safe_href(required_text(bullet, "url", source), source)

    sources = data.get("sources", [])
    if not isinstance(sources, list):
        raise RuntimeError(f"{source}: sources must be a list")
    for item in sources:
        if not isinstance(item, dict):
            raise RuntimeError(f"{source}: every source must be an object")
        required_text(item, "label", source)
        safe_href(required_text(item, "url", source), source)
    return data


# ============================================
def esc(value: str) -> str:
    """Escape one text value for HTML output."""
    return html.escape(value, quote=True)


# ============================================
def page_shell(site: dict[str, Any], page_title: str, content: str, prefix: str) -> str:
    """Wrap one rendered page in the shared accessible HTML shell."""
    home_href = f"{prefix}index.html"
    archive_href = f"{prefix}archive/index.html"
    style_href = f"{prefix}assets/style.css"
    favicon_href = f"{prefix}assets/favicon.svg"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="dark">
  <meta name="description" content="{esc(site['subtitle'])}">
  <title>{esc(page_title)} · {esc(site['title'])}</title>
  <link rel="icon" href="{favicon_href}" type="image/svg+xml">
  <link rel="stylesheet" href="{style_href}">
</head>
<body>
  <header>
    <div class="banner">
      <p class="eyebrow">Private LAN · {esc(site['hostname'])}:{site['port']}</p>
      <p class="site-name"><a href="{home_href}">{esc(site['title'])}</a></p>
      <nav aria-label="Primary"><a href="{home_href}">Latest</a><a href="{archive_href}">Archive</a><a href="{prefix}status.json">Status JSON</a></nav>
    </div>
  </header>
  <main>{content}</main>
  <footer>Static local site. Source citations identify evidence; no browser analytics, remote assets, or scripts are loaded.</footer>
</body>
</html>
"""


# ============================================
def render_post_body(post: dict[str, Any]) -> str:
    """Render an article body from one validated post record."""
    parts = [
        "<article>",
        f"<p class=\"post-date\">{esc(post['date'])}</p>",
        f"<h1>{esc(post['title'])}</h1>",
        f"<p class=\"meta\">{esc(post['summary'])}</p>",
    ]
    for section in post["sections"]:
        parts.append(f"<h2>{esc(section['heading'])}</h2>")
        for paragraph in section.get("paragraphs", []):
            parts.append(f"<p>{esc(paragraph)}</p>")
        bullets = section.get("bullets", [])
        if bullets:
            parts.append("<ul>")
            for bullet in bullets:
                parts.append(
                    f"<li><a href=\"{esc(bullet['url'])}\">{esc(bullet['text'])}</a></li>"
                )
            parts.append("</ul>")
    sources = post.get("sources", [])
    if sources:
        parts.append("<section class=\"sources\"><h2>Sources</h2><ul>")
        for source in sources:
            parts.append(
                f"<li><a href=\"{esc(source['url'])}\">{esc(source['label'])}</a></li>"
            )
        parts.append("</ul></section>")
    parts.append("</article>")
    return "\n".join(parts)


# ============================================
def render_post_card(post: dict[str, Any]) -> str:
    """Render a navigable summary card for one post."""
    date_text = post["date"]
    return f"""<a class="post-card" href="posts/{date_text}/index.html">
  <p class="post-date">{esc(date_text)}</p>
  <h2>{esc(post['title'])}</h2>
  <p>{esc(post['summary'])}</p>
</a>"""


# ============================================
def write_text(path: Path, text: str) -> None:
    """Write UTF-8 text, creating parents as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# ============================================
def build_tree(root: Path, output: Path) -> None:
    """Render the entire static site into an empty output directory."""
    site = validate_site(load_json(root / "content" / "site.json"), root / "content" / "site.json")
    post_paths = sorted((root / "content" / "posts").glob("*.json"), reverse=True)
    if not post_paths:
        raise RuntimeError("No post records found under content/posts/")
    posts = [validate_post(load_json(path), path) for path in post_paths]
    shutil.copytree(root / "site-assets", output / "assets")

    status = {
        "site_title": site["title"],
        "content_updated_at": site["content_updated_at"],
        "post_count": len(posts),
        "latest_post": posts[0]["date"],
        "collection_status": site["collection_status"],
    }
    write_text(output / "status.json", json.dumps(status, indent=2) + "\n")

    status_html = (
        "<section class=\"status\"><strong>Collection status</strong><br>"
        f"{esc(site['collection_status'])}<br><span class=\"meta\">"
        f"Content version {esc(site['content_updated_at'])} · {len(posts)} post(s)</span></section>"
    )
    latest = "\n".join(render_post_card(post) for post in posts[:5])
    home_body = f"""<section>
  <p class="eyebrow">Latest note</p>
  <h1>{esc(site['title'])}</h1>
  <p class="subtitle">{esc(site['subtitle'])}</p>
</section>
{status_html}
<section class="post-list" aria-label="Latest posts">{latest}</section>"""
    write_text(output / "index.html", page_shell(site, "Latest", home_body, ""))

    archive_cards = "\n".join(render_post_card(post) for post in posts)
    archive_body = f"""<section>
  <p class="eyebrow">All dated notes</p>
  <h1>Archive</h1>
  <div class="post-list">{archive_cards}</div>
</section>"""
    write_text(output / "archive" / "index.html", page_shell(site, "Archive", archive_body, "../"))

    for post in posts:
        body = render_post_body(post)
        output_path = output / "posts" / post["date"] / "index.html"
        write_text(output_path, page_shell(site, post["title"], body, "../../"))


# ============================================
def tree_files(path: Path) -> dict[Path, bytes]:
    """Return a relative file-to-bytes map for deterministic tree comparison."""
    if not path.is_dir():
        return {}
    return {
        item.relative_to(path): item.read_bytes()
        for item in sorted(path.rglob("*"))
        if item.is_file()
    }


# ============================================
def build_or_check(root: Path, output: Path, check: bool) -> int:
    """Build atomically, or verify that the existing generated site is current."""
    with tempfile.TemporaryDirectory(prefix="vosslab-blog-", dir=root) as temp_dir:
        staged = Path(temp_dir) / "public"
        build_tree(root, staged)
        if check:
            expected = tree_files(staged)
            actual = tree_files(output)
            if expected == actual:
                print(f"Generated site is current: {output}")
                return 0
            missing = sorted(str(path) for path in expected.keys() - actual.keys())
            extra = sorted(str(path) for path in actual.keys() - expected.keys())
            changed = sorted(
                str(path)
                for path in expected.keys() & actual.keys()
                if expected[path] != actual[path]
            )
            print("Generated site is stale.")
            for label, entries in (("missing", missing), ("extra", extra), ("changed", changed)):
                if entries:
                    print(f"{label}: {', '.join(entries)}")
            return 1

        replacement = root / ".public-replacement"
        backup = root / ".public-previous"
        shutil.rmtree(replacement, ignore_errors=True)
        shutil.rmtree(backup, ignore_errors=True)
        shutil.copytree(staged, replacement)
        if output.exists():
            output.rename(backup)
        replacement.rename(output)
        shutil.rmtree(backup, ignore_errors=True)
        print(f"Built {len(tree_files(output))} files in {output}")
        return 0


# ============================================
def main() -> int:
    """Build or validate the site."""
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    output = Path(args.output).resolve() if args.output else root / "public"
    try:
        return build_or_check(root, output, args.check)
    except RuntimeError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

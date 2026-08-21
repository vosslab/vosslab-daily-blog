#!/usr/bin/env python3
"""Collect one day's public Vosslab GitHub activity with full commit messages,
repository metadata, and screenshots directory awareness."""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from zoneinfo import ZoneInfo


API_URL = "https://api.github.com/users/{username}/events/public"
COMMITS_API_URL = "https://api.github.com/repos/{repo}/commits"
COMMIT_API_URL = "https://api.github.com/repos/{repo}/commits/{sha}"
REPO_API_URL = "https://api.github.com/repos/{repo}"
USER_REPOS_API_URL = "https://api.github.com/users/{username}/repos"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MD_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]+\)")
MD_BACKTICK_RE = re.compile(r"`([^`]+)`")
CHANGELOG_HEADING_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\b")


# ============================================
def parse_args() -> argparse.Namespace:
    """Parse one optional report date and collection settings."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="Local report date in YYYY-MM-DD; default is yesterday.")
    parser.add_argument(
        "--username",
        default=os.environ.get("VOSSLAB_GITHUB_USERNAME", "vosslab"),
    )
    parser.add_argument(
        "--timezone",
        default=os.environ.get("VOSSLAB_TIMEZONE", "America/Chicago"),
    )
    parser.add_argument("--max-pages", type=int, default=3)
    return parser.parse_args()


# ============================================
def report_date(
    value: str | None,
    timezone: ZoneInfo,
    now: dt.datetime | None = None,
) -> dt.date:
    """Return a completed local day; reject current and future publication dates."""
    local_today = (now or dt.datetime.now(timezone)).astimezone(timezone).date()
    if value:
        if not DATE_RE.fullmatch(value):
            raise RuntimeError("--date must use YYYY-MM-DD")
        requested = dt.date.fromisoformat(value)
        if requested >= local_today:
            raise RuntimeError(
                "--date must name a complete local calendar day; choose yesterday or earlier"
            )
        return requested
    return local_today - dt.timedelta(days=1)


def require_https_url(url: str) -> str:
    """Validate an outbound GitHub resource URL before opening it."""
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise RuntimeError("GitHub resource URL must use HTTPS")
    return url


# ============================================
def http_get_json(url: str, purpose: str) -> object:
    """Issue one GitHub API GET request and parse the JSON body.

    A configured ``GITHUB_TOKEN`` is sent only as a Bearer authorization
    header; it is never written to the evidence packet or command output.
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "vosslab-daily-blog/2.0",
    }
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required for authenticated collection")
    headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(require_https_url(url), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310: HTTPS checked above
            return json.loads(resp.read().decode("utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"GitHub request failed for {purpose}: {error}") from error


# ============================================
def request_events(username: str, page: int) -> list[dict[str, object]]:
    """Fetch one bounded authenticated request to the public Events endpoint."""
    query = urllib.parse.urlencode({"per_page": "100", "page": str(page)})
    url = API_URL.format(username=urllib.parse.quote(username, safe="")) + "?" + query
    payload = http_get_json(url, f"events page {page}")
    if not isinstance(payload, list):
        raise RuntimeError("GitHub events response was not a list")
    return [item for item in payload if isinstance(item, dict)]


# ============================================
def request_owned_repositories(username: str) -> list[str]:
    """Return every public repository owned by the account, across all pages."""
    repositories: list[str] = []
    page = 1
    while True:
        query = urllib.parse.urlencode(
            {"type": "owner", "per_page": "100", "page": str(page)}
        )
        url = (
            USER_REPOS_API_URL.format(username=urllib.parse.quote(username, safe=""))
            + "?"
            + query
        )
        payload = http_get_json(url, f"owned repositories page {page}")
        if not isinstance(payload, list):
            raise RuntimeError("GitHub owned-repositories response was not a list")
        page_repositories = [
            str(item.get("full_name", "")).strip()
            for item in payload
            if isinstance(item, dict) and str(item.get("full_name", "")).strip()
        ]
        repositories.extend(page_repositories)
        if len(payload) < 100:
            break
        page += 1
    return list(dict.fromkeys(repositories))


# ============================================
def event_local_date(event: dict[str, object], timezone: ZoneInfo) -> dt.date | None:
    """Parse a GitHub UTC event timestamp into the configured local day."""
    value = event.get("created_at")
    if not isinstance(value, str):
        return None
    try:
        stamp = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return stamp.astimezone(timezone).date()


# ============================================
def normalize_event(event: dict[str, object], timezone: ZoneInfo) -> dict[str, object]:
    """Keep only fields needed for sourced daily prose and links."""
    repo_data = event.get("repo") if isinstance(event.get("repo"), dict) else {}
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    repo = str(repo_data.get("name", "unknown repository"))
    commits = []
    payload_commits = payload.get("commits")
    if isinstance(payload_commits, list):
        for commit in payload_commits:
            if not isinstance(commit, dict):
                continue
            sha = str(commit.get("sha", "")).strip()
            if sha:
                commits.append({"sha": sha})
    return {
        "id": str(event.get("id", "")),
        "type": str(event.get("type", "unknown")),
        "created_at": str(event.get("created_at", "")),
        "local_time": dt.datetime.fromisoformat(
            str(event["created_at"]).replace("Z", "+00:00")
        )
        .astimezone(timezone)
        .isoformat(),
        "repo": repo,
        "ref": str(payload.get("ref", "")).strip(),
    }


# ============================================
def strip_changelog_noise(text: str) -> str:
    """Remove markdown links and backticked file paths to save token budget."""
    text = MD_LINK_RE.sub(r"\1", text)
    text = MD_BACKTICK_RE.sub(
        lambda m: m.group(1).rsplit("/", 1)[-1], text
    )
    return text


# ============================================
def readme_context(text: str) -> str:
    """Return the first prose paragraph from a repository README."""
    lines = text.splitlines()
    start = 0
    for index, line in enumerate(lines):
        if line.startswith("# "):
            start = index + 1
            break
    paragraphs = [
        part.strip()
        for part in re.split(r"\n\s*\n", "\n".join(lines[start:]))
        if part.strip() and not part.lstrip().startswith(("[!", "!", "["))
    ]
    return strip_changelog_noise(paragraphs[0]) if paragraphs else ""


# ============================================
def changelog_entries_for_date(text: str, target: dt.date) -> list[str]:
    """Return normalized blocks headed by the exact requested changelog date."""
    lines = text.splitlines()
    entries: list[str] = []
    for index, line in enumerate(lines):
        match = CHANGELOG_HEADING_RE.match(line.strip())
        if not match or match.group(1) != target.isoformat():
            continue
        end = next(
            (
                next_index
                for next_index in range(index + 1, len(lines))
                if lines[next_index].strip().startswith("## ")
            ),
            len(lines),
        )
        entry = strip_changelog_noise("\n".join(lines[index + 1 : end]).strip())
        if entry:
            entries.append(entry)
    return entries


# ============================================
def normalize_repo_commit(
    payload: dict[str, object],
    username: str,
    target: dt.date,
    timezone: ZoneInfo,
) -> dict[str, str] | None:
    """Normalize one commit linked to the configured account on the target local day.

    Preserves the complete multi-line commit message for richer editorial context.
    """
    author_raw = payload.get("author")
    committer_raw = payload.get("committer")
    author: dict[str, object] = dict(author_raw) if isinstance(author_raw, dict) else {}
    committer: dict[str, object] = (
        dict(committer_raw) if isinstance(committer_raw, dict) else {}
    )
    linked_logins = {
        str(author.get("login", "")).lower(),
        str(committer.get("login", "")).lower(),
    }
    if username.lower() not in linked_logins:
        return None
    commit_raw = payload.get("commit")
    commit: dict[str, object] = dict(commit_raw) if isinstance(commit_raw, dict) else {}
    commit_author_raw = commit.get("author")
    commit_author: dict[str, object] = (
        dict(commit_author_raw) if isinstance(commit_author_raw, dict) else {}
    )
    commit_committer_raw = commit.get("committer")
    commit_committer: dict[str, object] = (
        dict(commit_committer_raw)
        if isinstance(commit_committer_raw, dict)
        else {}
    )
    stamp_text = str(
        commit_author.get("date") or commit_committer.get("date") or ""
    )
    try:
        stamp = dt.datetime.fromisoformat(stamp_text.replace("Z", "+00:00"))
    except ValueError:
        return None
    local_stamp = stamp.astimezone(timezone)
    if local_stamp.date() != target:
        return None
    sha = str(payload.get("sha", "")).strip()
    html_url = str(payload.get("html_url", "")).strip()
    if not sha or not html_url:
        return None
    # Preserve the full commit message - first line as subject, remainder as body
    full_message = str(commit.get("message", "")).strip()
    lines = full_message.splitlines()
    subject = lines[0] if lines else ""
    body = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
    return {
        "sha": sha,
        "subject": subject,
        "body": body,
        "full_message": full_message,
        "html_url": html_url,
        "committed_at": local_stamp.isoformat(),
        "account_login": username,
    }


# ============================================
def request_repo_commits(
    repo: str,
    username: str,
    target: dt.date,
    timezone: ZoneInfo,
) -> tuple[str, list[dict[str, str]]]:
    """Fetch commits linked to the account for one repository and completed local day."""
    local_start = dt.datetime.combine(target, dt.time.min, tzinfo=timezone)
    local_end = local_start + dt.timedelta(days=1)
    base_query = {
        "since": local_start.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "until": local_end.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "per_page": "100",
    }
    endpoint = COMMITS_API_URL.format(repo=urllib.parse.quote(repo, safe="/"))
    commits = []
    page = 1
    first_url = ""
    while True:
        query = urllib.parse.urlencode({**base_query, "page": str(page)})
        url = endpoint + "?" + query
        if not first_url:
            first_url = url
        payload = http_get_json(url, f"commits for {repo} page {page}")
        if not isinstance(payload, list):
            raise RuntimeError(f"GitHub commits response was not a list for {repo}")
        for item in payload:
            if not isinstance(item, dict):
                continue
            normalized = normalize_repo_commit(item, username, target, timezone)
            if normalized is not None:
                commits.append(normalized)
        if len(payload) < 100:
            break
        page += 1
    commits.sort(key=lambda item: item["committed_at"])
    return first_url, commits


# ============================================
def request_repo_info(repo: str) -> dict[str, object]:
    """Fetch public repository description, language, and topics."""
    url = REPO_API_URL.format(repo=urllib.parse.quote(repo, safe="/"))
    payload = http_get_json(url, f"repo info for {repo}")
    if not isinstance(payload, dict):
        return {}
    return {
        "description": str(payload.get("description") or ""),
        "language": str(payload.get("language") or ""),
        "topics": [
            str(t)
            for t in (payload.get("topics") or [])
            if isinstance(t, str)
        ],
        "stars": int(payload.get("stargazers_count") or 0),
        "default_branch": str(payload.get("default_branch") or ""),
    }


# ============================================
def request_repo_document(repo: str, path: str, ref: str) -> dict[str, str]:
    """Fetch one optional UTF-8 GitHub document with revision provenance."""
    encoded_repo = urllib.parse.quote(repo, safe="/")
    encoded_path = urllib.parse.quote(path, safe="/")
    query = urllib.parse.urlencode({"ref": ref}) if ref else ""
    url = f"https://api.github.com/repos/{encoded_repo}/contents/{encoded_path}"
    if query:
        url += "?" + query
    try:
        payload = http_get_json(url, f"{path} for {repo}")
    except RuntimeError as error:
        if "404" in str(error):
            return {}
        raise
    if not isinstance(payload, dict) or payload.get("encoding") != "base64":
        return {}
    try:
        encoded_content = re.sub(r"\s+", "", str(payload.get("content", "")))
        text = base64.b64decode(encoded_content, validate=True).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as error:
        raise RuntimeError(f"{path} for {repo} is not valid UTF-8 base64 content: {error}") from error
    return {
        "path": str(payload.get("path") or path),
        "sha": str(payload.get("sha") or ""),
        "text": text,
    }


# ============================================
def request_commit_screenshot_files(
    repo: str, commits: list[dict[str, object]]
) -> list[dict[str, str]]:
    """Return public screenshot files changed by the day's account-linked commits."""
    files: dict[str, dict[str, str]] = {}
    for commit in commits:
        sha = str(commit.get("sha", "")).strip()
        if not sha:
            continue
        url = COMMIT_API_URL.format(
            repo=urllib.parse.quote(repo, safe="/"),
            sha=urllib.parse.quote(sha, safe=""),
        )
        payload = http_get_json(url, f"changed files for {repo}@{sha[:12]}")
        if not isinstance(payload, dict):
            continue
        changed = payload.get("files")
        if not isinstance(changed, list):
            continue
        for item in changed:
            if not isinstance(item, dict):
                continue
            filename = str(item.get("filename", ""))
            if not filename.startswith("docs/screenshots/"):
                continue
            if Path(filename).suffix.lower() not in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
                continue
            commit_url = (
                "https://raw.githubusercontent.com/"
                + repo
                + "/"
                + sha
                + "/"
                + filename
            )
            files[filename] = {"filename": filename, "url": commit_url, "commit": sha}
    return [files[name] for name in sorted(files)]


def download_file(url: str, destination: Path) -> None:
    """Download one public screenshot to a local MkDocs source path."""
    req = urllib.request.Request(require_https_url(url), headers={"User-Agent": "vosslab-daily-blog/2.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:  # nosec B310: HTTPS checked above
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(response.read())
    except OSError as error:
        raise RuntimeError(f"screenshot download failed for {url}: {error}") from error


# ============================================
def mirror_root() -> Path:
    """Return the root containing collector-owned shallow repository checkouts."""
    return Path(os.environ.get("VOSSLAB_MIRROR_ROOT", "/home/vosslab/repo-mirrors/vosslab"))


def ensure_mirror_commit(checkout: Path, commit: str) -> None:
    """Ensure a depth-1 checkout has the exact commit needed for dated evidence."""
    exists = subprocess.run(
        ["git", "-C", str(checkout), "cat-file", "-e", f"{commit}^{{commit}}"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).returncode == 0
    if not exists:
        subprocess.run(
            ["git", "-C", str(checkout), "fetch", "--depth=1", "origin", commit],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )


def read_mirror_document(checkout: Path, path: str, commit: str) -> dict[str, str]:
    """Read one UTF-8 document and blob SHA from one exact mirror commit."""
    ensure_mirror_commit(checkout, commit)
    blob = subprocess.run(
        ["git", "-C", str(checkout), "rev-parse", f"{commit}:{path}"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if blob.returncode:
        return {}
    content = subprocess.run(
        ["git", "-C", str(checkout), "show", f"{commit}:{path}"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.decode("utf-8")
    return {"path": path, "sha": blob.stdout.strip(), "text": content, "commit": commit}


def read_mirror_bytes(checkout: Path, path: str, commit: str) -> bytes | None:
    """Read one exact binary blob from a mirror commit."""
    ensure_mirror_commit(checkout, commit)
    result = subprocess.run(
        ["git", "-C", str(checkout), "show", f"{commit}:{path}"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout if result.returncode == 0 else None


# ============================================
def resolve_repo_checkout(repo: str) -> Path | None:
    """Return the exact matching collector-owned repository mirror checkout."""
    name = repo.rsplit("/", 1)[-1]
    checkout = mirror_root() / name
    if not (checkout / ".git").is_dir():
        return None
    remote = subprocess.run(
        ["git", "-C", str(checkout), "remote", "get-url", "origin"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip().removesuffix(".git")
    expected = f"https://github.com/{repo}"
    return checkout if remote == expected else None


def collect_repository_screenshots(
    repos: list[str],
    target: dt.date,
    destination: Path,
    root: Path,
    commits_by_repo: dict[str, list[dict[str, object]]] | None = None,
) -> list[dict[str, str]]:
    """Copy commit-selected ``docs/screenshots`` images into the blog source tree.

    The collector finds image paths from files changed by the report date's
    account-linked commits. It reads matching mirror blobs at those exact
    commits, or downloads the commit-addressed public blob when no mirror is
    available. Every selected source is required evidence: acquisition errors
    stop collection rather than silently omitting an image.
    """
    destination.mkdir(parents=True, exist_ok=True)
    discovered: list[dict[str, str]] = []
    for repo in repos:
        repo_slug = repo.rsplit("/", 1)[-1]
        checkout = resolve_repo_checkout(repo)
        for source in request_commit_screenshot_files(
            repo, (commits_by_repo or {}).get(repo, [])
        ):
            relative_source = Path(source["filename"]).relative_to("docs/screenshots")
            destination_name = f"{repo_slug}-{'-'.join(relative_source.parts)}"
            copied = destination / destination_name
            commit = str(source["commit"])
            mirror_bytes = (
                read_mirror_bytes(checkout, source["filename"], commit)
                if checkout is not None
                else None
            )
            if mirror_bytes is not None:
                copied.write_bytes(mirror_bytes)
                source_path = f"{checkout}@{commit}:{source['filename']}"
            else:
                download_file(source["url"], copied)
                source_path = source["url"]
            discovered.append(
                {
                    "filename": relative_source.name,
                    "repo": repo,
                    "source_path": source_path,
                    "relative_path": str(
                        Path("../../assets/screenshots") / target.isoformat() / destination_name
                    ),
                    "media_path": str(copied.relative_to(root / "docs")),
                }
            )
    return discovered


# ============================================
def scan_screenshots(report_date_str: str) -> list[dict[str, str]]:
    """Copy legacy dated blog captures into the MkDocs media tree.

    Repository screenshots are the primary source.  This retains the existing
    ``data/screenshots/YYYY-MM-DD`` convention as a compatible local source.
    """
    root = Path(__file__).resolve().parents[1]
    screenshot_dir = root / "data" / "screenshots" / report_date_str
    if not screenshot_dir.is_dir():
        return []
    destination = root / "docs" / "assets" / "screenshots" / report_date_str
    found: list[dict[str, str]] = []
    for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
        for path in sorted(screenshot_dir.glob(f"*{ext}")):
            copied = destination / path.name
            copied.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, copied)
            found.append(
                {
                    "filename": path.name,
                    "repo": "daily capture",
                    "source_path": str(path),
                    "relative_path": str(
                        Path("../../assets/screenshots") / report_date_str / path.name
                    ),
                    "media_path": str(copied.relative_to(root / "docs")),
                }
            )
    return found


# ============================================
def build_repository_evidence(
    events: list[dict[str, object]],
    username: str,
    target: dt.date,
    timezone: ZoneInfo,
    owned_repos: list[str] | None = None,
) -> tuple[list[dict[str, object]], list[str]]:
    """Enrich event and owned repositories with dated account-linked commits."""
    event_repos = list(dict.fromkeys(str(event["repo"]) for event in events))
    repos = list(dict.fromkeys(event_repos + (owned_repos or [])))
    if not repos:
        return [], []

    def _enrich_one(repo: str) -> tuple[dict[str, object], list[str]]:
        local_errors: list[str] = []
        event_count = sum(1 for e in events if e["repo"] == repo)
        result: dict[str, object] = {
            "repo": repo,
            "event_count": event_count,
            "description": "",
            "language": "",
            "topics": [],
            "stars": 0,
            "readme": {},
            "changelog": {},
            "commit_source_url": "",
            "commits": [],
        }
        try:
            info = request_repo_info(repo)
            result["description"] = info.get("description", "")
            result["language"] = info.get("language", "")
            result["topics"] = info.get("topics", [])
            result["stars"] = info.get("stars", 0)
            result["default_branch"] = str(info.get("default_branch", ""))
        except RuntimeError as exc:
            local_errors.append(f"repo info {repo}: {exc}")
        try:
            source_url, commits = request_repo_commits(
                repo, username, target, timezone
            )
            result["commit_source_url"] = source_url
            result["commits"] = commits
        except RuntimeError as exc:
            local_errors.append(f"commits {repo}: {exc}")
        if result["commits"] or event_count:
            try:
                checkout = resolve_repo_checkout(repo)
                default_branch = str(result.get("default_branch", ""))
                evidence_commit = str(result["commits"][-1].get("sha", "")) if result["commits"] else ""
                readme = (
                    read_mirror_document(checkout, "README.md", evidence_commit)
                    if checkout is not None and evidence_commit
                    else request_repo_document(repo, "README.md", default_branch)
                )
                if readme:
                    summary = readme_context(readme["text"])
                    if summary:
                        result["readme"] = {
                            "path": readme["path"],
                            "sha": readme["sha"],
                            "summary": summary,
                            "source": "mirror" if checkout is not None else "github_api",
                            "commit": readme.get("commit", evidence_commit),
                        }
                changelog = (
                    read_mirror_document(checkout, "docs/CHANGELOG.md", evidence_commit)
                    if checkout is not None and evidence_commit
                    else request_repo_document(repo, "docs/CHANGELOG.md", default_branch)
                )
                if changelog:
                    entries = changelog_entries_for_date(changelog["text"], target)
                    if entries:
                        result["changelog"] = {
                            "path": changelog["path"],
                            "sha": changelog["sha"],
                            "entries": entries,
                            "source": "mirror" if checkout is not None else "github_api",
                            "commit": changelog.get("commit", evidence_commit),
                        }
            except (RuntimeError, subprocess.CalledProcessError) as exc:
                local_errors.append(f"repository context {repo}: {exc}")
        return result, local_errors

    with ThreadPoolExecutor(max_workers=min(len(repos), 6)) as executor:
        future_to_repo = {
            executor.submit(_enrich_one, repo): repo for repo in repos
        }
        repo_results: dict[str, dict[str, object]] = {}
        repo_errors: dict[str, list[str]] = {}
        for future in as_completed(future_to_repo):
            repo = future_to_repo[future]
            result, local_errors = future.result()
            repo_results[repo] = result
            repo_errors[repo] = local_errors
    errors = [message for repo in repos for message in repo_errors[repo]]
    repository_evidence = [
        repo_results[repo]
        for repo in repos
        if repo in repo_results
        and (repo in event_repos or repo_results[repo].get("commits"))
    ]
    # stabilise order
    repo_order = {repo: idx for idx, repo in enumerate(repos)}
    repository_evidence.sort(key=lambda item: repo_order.get(item["repo"], 9999))
    return repository_evidence, errors


# ============================================
def markdown_safe(value: str) -> str:
    """Escape characters that could break Markdown rendering."""
    return value.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


# ============================================
def article_slug(report_date: str) -> str:
    """Return the deterministic fallback one-word slug before frontier editing."""
    dt.date.fromisoformat(report_date)  # Validate the report-date contract.
    return "work"


# ============================================
def render_post(record: dict[str, object]) -> str:
    """Render a source-limited daily blog entry as concise prose paragraphs."""
    date_text = record["report_date"]
    display_date = (
        dt.date.fromisoformat(date_text)
        .strftime("%B %d, %Y")
        .replace(" 0", " ")
    )
    events = record["events"]

    def join_words(values: list[str]) -> str:
        if len(values) == 1:
            return values[0]
        if len(values) == 2:
            return f"{values[0]} and {values[1]}"
        return ", ".join(values[:-1]) + f", and {values[-1]}"

    lines = [
        "---",
        "date:",
        f"  created: {date_text}",
        f"slug: {article_slug(date_text)}",
        "---",
        "",
        f"# Vosslab work log - {display_date}",
        "",
    ]
    repository_evidence = record.get("repositories", [])
    has_repository_activity = any(
        repository.get("commits") for repository in repository_evidence
    )
    if not events and not has_repository_activity:
        lines.extend(
            [
                "I found no qualifying public GitHub activity for " + display_date + ", so I am recording the source boundary rather than inventing a work narrative or treating the quiet snapshot as proof that no work occurred.",
                "",
                "<!-- more -->",
                "",
                "## What the snapshot shows",
                "",
                "The retrieved public GitHub Events API pages did not return qualifying activity for this date. That is a limited observation about a public activity feed, not a complete accounting of repositories, local work, private work, or every commit associated with my account.",
                "",
                "## What I recorded",
                "",
                "I am leaving this as a quiet daily entry so the chronology stays honest and the next published update does not silently skip a date. A useful work log should distinguish unavailable public evidence from a claim about what did or did not happen, especially when the source is intentionally bounded.",
                "",
            ]
        )
    else:
        lines.extend(["<!-- more -->", ""])
        repo_names = list(
            dict.fromkeys(
                str(event["repo"]) for event in events
            ) or dict.fromkeys(str(repository["repo"]) for repository in repository_evidence)
        )
        repo_links = [
            f"[{markdown_safe(repo)}](https://github.com/{repo})"
            for repo in repo_names
        ]
        lines.extend(
            [
                "## What changed",
                "",
                f"On {display_date}, the public GitHub activity snapshot showed work across {join_words(repo_links)}.",
                "",
            ]
        )
        rendered_repository_detail = False
        for repository in repository_evidence:
            repo = str(repository["repo"])
            commits = repository.get("commits", [])
            if not commits:
                continue
            subjects = [
                markdown_safe(str(commit.get("subject", commit.get("message", ""))))
                for commit in commits
                if str(commit.get("subject", commit.get("message", ""))).strip()
            ]
            description = markdown_safe(str(repository.get("description", "")).strip())
            context = f" {description}" if description else ""
            if subjects:
                rendered_repository_detail = True
                quoted_subjects = ['"' + subject + '"' for subject in subjects]
                work_summary = join_words(quoted_subjects)
                lines.extend(
                    [
                        f"In [{markdown_safe(repo)}](https://github.com/{repo}), I worked on {work_summary}.{context}",
                        "",
                    ]
                )
        if not rendered_repository_detail:
            descriptions = [
                markdown_safe(str(item.get("description", "")).strip())
                for item in repository_evidence
                if str(item.get("description", "")).strip()
            ]
            context = f" The repository description identifies it as {descriptions[0]}" if descriptions else ""
            lines.extend(
                [
                    f"I saw {len(events)} public activity record(s) across {join_words(repo_links)}, but the retrieved account-linked commit endpoint did not supply enough detail to describe a specific code change responsibly.{context}",
                    "",
                    "That makes this a useful pointer to the active project, not a basis for reconstructing implementation decisions, outcomes, or unfinished work. I am keeping the distinction explicit so a sparse public signal does not become a more confident story than the evidence supports.",
                    "",
                    "I am publishing this source-limited fallback rather than silently omitting the day. It preserves a readable chronology while leaving the next fully evidenced update free to explain the work in its proper context.",
                    "",
                ]
            )

    screenshots = record.get("screenshots", [])
    if screenshots:
        lines.extend(["## Supporting views", ""])
        for shot in screenshots[:3]:
            lines.append(
                f"![{shot['filename']} - {shot.get('repo', 'daily capture')}]({shot['relative_path']})"
            )
            lines.append("")

    lines.extend(
        [
            "## Where the work stands",
            "",
            "This entry keeps the development record readable by linking projects rather than individual source-control records.",
            "",
            f"This entry is reconstructed from the [public GitHub Events API]({record['source_url']}) "
            f"for {record['timezone']} and retrieved {record['pages_fetched']} of at most "
            f"{record['max_pages']} pages. It is a bounded snapshot, not complete commit history.",
            "",
        ]
    )
    return "\n".join(lines)


# ============================================
def write_json(path: Path, value: dict[str, object]) -> None:
    """Write one stable, readable JSON artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


# ============================================
def main() -> int:
    """Collect, normalize, persist, and render one daily fallback entry."""
    args = parse_args()
    if args.max_pages < 1 or args.max_pages > 10:
        raise RuntimeError("--max-pages must be between 1 and 10")
    timezone = ZoneInfo(args.timezone)
    target = report_date(args.date, timezone)
    username = args.username.strip().lower()
    if not username:
        raise RuntimeError("--username must not be empty")

    matching = []
    pages_fetched = 0
    for page in range(1, args.max_pages + 1):
        events = request_events(username, page)
        pages_fetched += 1
        if not events:
            break
        for event in events:
            actor = (
                event.get("actor")
                if isinstance(event.get("actor"), dict)
                else {}
            )
            if str(actor.get("login", "")).lower() != username:
                continue
            if event_local_date(event, timezone) == target:
                matching.append(normalize_event(event, timezone))
        oldest = event_local_date(events[-1], timezone)
        if oldest and oldest < target:
            break

    matching.sort(key=lambda item: item["created_at"])
    owned_repos = request_owned_repositories(username)
    repositories, enrichment_errors = build_repository_evidence(
        matching, username, target, timezone, owned_repos
    )
    root = Path(__file__).resolve().parents[1]
    source_url = (
        API_URL.format(username=urllib.parse.quote(username, safe=""))
        + "?per_page=100&page=1"
    )
    screenshots = scan_screenshots(target.isoformat())
    screenshot_destination = (
        root / "docs" / "assets" / "screenshots" / target.isoformat()
    )
    screenshots.extend(
        collect_repository_screenshots(
            [item["repo"] for item in repositories],
            target,
            screenshot_destination,
            root,
            {item["repo"]: item.get("commits", []) for item in repositories},
        )
    )
    screenshots.sort(key=lambda item: (item.get("repo", ""), item["filename"]))
    record: dict[str, object] = {
        "schema_version": 3,
        "report_date": target.isoformat(),
        "timezone": args.timezone,
        "username": username,
        "source_url": source_url,
        "source_mode": "github_public_events_owned_repository_commits_and_docs",
        "coverage_note": (
            "Public GitHub Events API is bounded; every public repository owned by the account is checked for account-linked commits, README context, and dated docs/CHANGELOG.md entries when available."
        ),
        "retrieved_at": dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat(),
        "pages_fetched": pages_fetched,
        "max_pages": args.max_pages,
        "events": matching,
        "repositories": repositories,
        "commit_enrichment_errors": enrichment_errors,
        "screenshots": screenshots,
    }
    dated_source = root / "data" / "daily" / f"{target.isoformat()}.json"
    write_json(dated_source, record)
    write_json(
        root / "data" / "daily" / "latest.json",
        {
            "report_date": target.isoformat(),
            "source_path": str(dated_source.relative_to(root)),
            "post_path": f"docs/blog/posts/{target.isoformat()}.md",
            "source_mode": record["source_mode"],
            "event_count": len(matching),
            "repository_count": len(repositories),
            "commit_count": sum(
                len(item["commits"]) for item in repositories
            ),
            "commit_enrichment_error_count": len(enrichment_errors),
            "screenshot_count": len(screenshots),
        },
    )
    print(
        f"Collected {len(matching)} public activity record(s) for "
        f"{target.isoformat()} into {dated_source}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(2)

#!/usr/bin/env python3
"""Collect and publish the deterministic canonical Vosslab daily post."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import collect_github_events as collector
import publication_state as publication


ROOT = Path(__file__).resolve().parents[1]
VENV_PYTHON = ROOT / ".venv" / "bin" / "python"
SCRIPTS = ROOT / "scripts"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="Completed America/Chicago report date (YYYY-MM-DD).")
    return parser.parse_args()


def validate_post(post_path: Path, evidence_path: Path) -> None:
    """Run the repository's deterministic article validator."""
    subprocess.run(
        [
            str(VENV_PYTHON),
            str(SCRIPTS / "validate_daily_post.py"),
            "--candidate",
            str(post_path),
            "--evidence",
            str(evidence_path),
        ],
        cwd=ROOT,
        check=True,
    )


def publish_status(label: str) -> str:
    """Publish the current durable-state view through an atomic site release."""
    publication.write_status(ROOT)
    return publication.build_and_promote(label, ROOT)


def collection_failure(report_date: str, failure_kind: str) -> int:
    """Persist and publish a bounded source-collection failure."""
    state = publication.load_state(report_date, ROOT)
    publication.collection_failed(state, failure_kind)
    publication.save_state(state, ROOT)
    publish_status(f"collection-failed-{report_date}")
    print(f"Collection failed for {report_date}; publication status updated.", file=sys.stderr)
    return 2


def main() -> int:
    args = parse_args()
    timezone = ZoneInfo("America/Chicago")
    report_date = collector.report_date(args.date, timezone).isoformat()
    collect_command = [str(VENV_PYTHON), str(SCRIPTS / "collect_github_events.py"), "--date", report_date]
    result = subprocess.run(
        collect_command,
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        failure_kind = (
            "github_authentication_failed"
            if "401" in result.stderr or "GITHUB_TOKEN" in result.stderr
            else "collector_command_failed"
        )
        return collection_failure(report_date, failure_kind)

    evidence_path = ROOT / "data" / "daily" / f"{report_date}.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    if evidence.get("commit_enrichment_errors"):
        return collection_failure(report_date, "repository_enrichment_failed")
    state = publication.load_state(report_date, ROOT)
    publication.collection_ready(state, evidence_path, evidence)
    publication.save_state(state, ROOT)

    post_path = ROOT / "docs" / "blog" / "posts" / f"{report_date}.md"
    post_path.write_text(collector.render_post(evidence), encoding="utf-8")
    publication.canonical_staging(state, post_path)
    publication.save_state(state, ROOT)
    publication.write_status(ROOT)

    try:
        validate_post(post_path, evidence_path)
        release_id = publication.build_and_promote(f"canonical-{report_date}", ROOT)
    except subprocess.CalledProcessError as error:
        print(f"Canonical build failed for {report_date}: {error}", file=sys.stderr)
        return error.returncode or 2

    publication.canonical_published(state, release_id)
    publication.save_state(state, ROOT)
    publish_status(f"publication-status-{report_date}")
    print(f"Canonical daily post published for {report_date}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

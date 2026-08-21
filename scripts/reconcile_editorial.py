#!/usr/bin/env python3
"""Reconcile durable editorial revisions for already-published daily posts."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import publication_state as publication
from daily_publish import validate_post


ROOT = Path(__file__).resolve().parents[1]
VENV_PYTHON = ROOT / ".venv" / "bin" / "python"
SCRIPTS = ROOT / "scripts"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="Reconcile one completed report date.")
    parser.add_argument("--limit", type=int, default=1, help="Maximum eligible dates per invocation.")
    return parser.parse_args()


def publish_status(label: str) -> None:
    publication.write_status(ROOT)
    publication.build_and_promote(label, ROOT)


def eligible_records(report_date: str | None, limit: int) -> list[dict[str, object]]:
    records = publication.all_states(ROOT)
    if report_date:
        records = [record for record in records if record["report_date"] == report_date]
    return [
        record
        for record in records
        if record["canonical"]["state"] == "published"
        and record["editorial"]["state"] in {"pending", "degraded", "staging"}
    ][:limit]


def degrade(record: dict[str, object], failure_kind: str) -> None:
    publication.editorial_degraded(record, failure_kind)
    publication.save_state(record, ROOT)
    publish_status(f"editorial-degraded-{record['report_date']}")


def reconcile(record: dict[str, object]) -> None:
    report_date = record["report_date"]
    evidence_path = ROOT / record["evidence_path"]
    candidate_path = ROOT / "data" / "editorial" / "candidates" / f"{report_date}.md"
    manifest_path = ROOT / "data" / "editorial" / "manifests" / f"{report_date}.json"
    publication.editorial_staging(record)
    publication.save_state(record, ROOT)
    publish_status(f"editorial-staging-{report_date}")

    command = [
        str(VENV_PYTHON),
        str(SCRIPTS / "run_layered_editorial.py"),
        "--evidence",
        str(evidence_path),
        "--candidate",
        str(candidate_path),
        "--manifest",
        str(manifest_path),
    ]
    try:
        subprocess.run(command, cwd=ROOT, check=True)
        validate_post(candidate_path, evidence_path)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        degrade(record, "editorial_command_failed")
        return

    post_path = ROOT / "docs" / "blog" / "posts" / f"{report_date}.md"
    canonical_text = post_path.read_text(encoding="utf-8")
    post_path.write_text(candidate_path.read_text(encoding="utf-8"), encoding="utf-8")
    release_id = ""
    try:
        try:
            release_id = publication.build_and_promote(f"editorial-{report_date}", ROOT)
        finally:
            if not release_id:
                post_path.write_text(canonical_text, encoding="utf-8")
    except subprocess.CalledProcessError:
        degrade(record, "editorial_release_failed")
        return

    publication.editorial_promoted(record, release_id, candidate_path)
    publication.save_state(record, ROOT)
    publish_status(f"editorial-status-{report_date}")
    print(f"Editorial revision published for {report_date}.")


def main() -> int:
    args = parse_args()
    if args.limit < 1:
        raise RuntimeError("--limit must be at least one")
    records = eligible_records(args.date, args.limit)
    if not records:
        print("No eligible editorial revisions.")
        return 0
    for record in records:
        reconcile(record)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(2)

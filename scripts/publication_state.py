"""Durable state and atomic release helpers for the Vosslab Daily Blog."""

from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / "data" / "publications"
RELEASES_DIR = ROOT / "generated" / "releases"
STAGING_DIR = ROOT / "generated" / "staging"
SITE_LINK = ROOT / "site"
VENV_PYTHON = ROOT / ".venv" / "bin" / "python"


COLLECTION_STATES = {"pending", "empty", "ready", "failed"}
CANONICAL_STATES = {"pending", "staging", "published"}
EDITORIAL_STATES = {"pending", "staging", "promoted", "degraded"}


def utc_now() -> str:
    """Return a stable ISO-8601 UTC timestamp without microseconds."""
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def state_path(report_date: str, root: Path = ROOT) -> Path:
    """Return the durable publication-state location for one report date."""
    return root / "data" / "publications" / f"{report_date}.json"


def atomic_write_json(path: Path, value: dict[str, object]) -> None:
    """Atomically replace one JSON record on the same filesystem."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def load_state(report_date: str, root: Path = ROOT) -> dict[str, object]:
    """Load one publication record, initializing its legal starting state."""
    path = state_path(report_date, root)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "schema_version": 1,
        "report_date": report_date,
        "updated_at": utc_now(),
        "evidence_path": "",
        "collection": {"state": "pending", "updated_at": utc_now()},
        "canonical": {"state": "pending", "updated_at": utc_now()},
        "editorial": {"state": "pending", "updated_at": utc_now(), "attempts": []},
    }


def save_state(record: dict[str, object], root: Path = ROOT) -> None:
    """Persist one publication record after validating its state vocabulary."""
    if record["collection"]["state"] not in COLLECTION_STATES:
        raise RuntimeError("invalid collection state")
    if record["canonical"]["state"] not in CANONICAL_STATES:
        raise RuntimeError("invalid canonical state")
    if record["editorial"]["state"] not in EDITORIAL_STATES:
        raise RuntimeError("invalid editorial state")
    record["updated_at"] = utc_now()
    atomic_write_json(state_path(record["report_date"], root), record)


def collection_ready(record: dict[str, object], evidence_path: Path, evidence: dict[str, object]) -> None:
    """Record a re-creatable collection result ready for canonical rendering."""
    record["evidence_path"] = str(evidence_path.relative_to(ROOT))
    has_commit_activity = any(repository.get("commits") for repository in evidence["repositories"])
    record["collection"] = {
        "state": "ready" if evidence["events"] or has_commit_activity else "empty",
        "updated_at": utc_now(),
        "event_count": len(evidence.get("events", [])),
        "repository_count": len(evidence.get("repositories", [])),
    }
    record["canonical"] = {"state": "pending", "updated_at": utc_now()}
    record["editorial"] = {"state": "pending", "updated_at": utc_now(), "attempts": []}


def collection_failed(record: dict[str, object], failure_kind: str) -> None:
    """Record a bounded collection failure without exposing provider details."""
    record["collection"] = {
        "state": "failed",
        "updated_at": utc_now(),
        "failure_kind": failure_kind,
    }


def canonical_staging(record: dict[str, object], post_path: Path) -> None:
    """Record a validated canonical post awaiting atomic release promotion."""
    record["canonical"] = {
        "state": "staging",
        "updated_at": utc_now(),
        "post_path": str(post_path.relative_to(ROOT)),
    }


def canonical_published(record: dict[str, object], release_id: str) -> None:
    """Record the release that made the canonical post visible."""
    record["canonical"].update(
        {"state": "published", "updated_at": utc_now(), "release_id": release_id}
    )


def editorial_staging(record: dict[str, object]) -> None:
    """Record that an editorial reconciliation attempt owns the date."""
    record["editorial"]["state"] = "staging"
    record["editorial"]["updated_at"] = utc_now()


def editorial_degraded(record: dict[str, object], failure_kind: str) -> None:
    """Record a bounded editorial result while preserving canonical publication."""
    attempts = list(record["editorial"].get("attempts", []))
    attempts.append({"at": utc_now(), "result": "degraded", "failure_kind": failure_kind})
    record["editorial"] = {
        "state": "degraded",
        "updated_at": utc_now(),
        "attempts": attempts[-20:],
    }


def editorial_promoted(record: dict[str, object], release_id: str, candidate_path: Path) -> None:
    """Record the release that promoted a validated editorial revision."""
    attempts = list(record["editorial"].get("attempts", []))
    attempts.append({"at": utc_now(), "result": "promoted"})
    record["editorial"] = {
        "state": "promoted",
        "updated_at": utc_now(),
        "release_id": release_id,
        "candidate_path": str(candidate_path.relative_to(ROOT)),
        "attempts": attempts[-20:],
    }


def all_states(root: Path = ROOT) -> list[dict[str, object]]:
    """Load publication records in descending report-date order."""
    directory = root / "data" / "publications"
    if not directory.exists():
        return []
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(directory.glob("*.json"), reverse=True)
    ]


def render_status(root: Path = ROOT) -> str:
    """Render reader-visible publication status from durable state records."""
    records = all_states(root)
    if not records:
        return "# Publication status\n\nNo completed collection has been recorded yet.\n"
    rows = []
    for record in records[:14]:
        collection = record["collection"]["state"]
        canonical = record["canonical"]["state"]
        editorial = record["editorial"]["state"]
        rows.append(
            f"| {record['report_date']} | {collection} | {canonical} | {editorial} |"
        )
    latest = records[0]
    return "\n".join(
        [
            "# Publication status",
            "",
            f"Latest tracked report date: `{latest['report_date']}`.",
            "",
            "| Report date | Collection | Canonical post | Editorial revision |",
            "| --- | --- | --- | --- |",
            *rows,
            "",
            "The canonical post is the reader-visible daily record. Editorial revisions promote after their own validated release succeeds.",
            "",
        ]
    )


def write_status(root: Path = ROOT) -> None:
    """Write the status source page from durable publication state."""
    (root / "docs" / "status.md").write_text(render_status(root), encoding="utf-8")


def build_and_promote(label: str, root: Path = ROOT) -> str:
    """Build MkDocs into a staged release and atomically switch the served pointer."""
    release_id = f"{label}-{utc_now().replace(':', '').replace('+00:00', 'Z')}-{uuid.uuid4().hex[:8]}"
    stage = root / "generated" / "staging" / release_id
    release = root / "generated" / "releases" / release_id
    stage.parent.mkdir(parents=True, exist_ok=True)
    release.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            [str(root / ".venv" / "bin" / "mkdocs"), "build", "--strict", "--site-dir", str(stage)],
            cwd=root,
            check=True,
        )
        os.replace(stage, release)
        link = root / f".site-next-{uuid.uuid4().hex}"
        link.symlink_to(release.relative_to(root))
        if (root / "site").exists() and not (root / "site").is_symlink():
            legacy = root / "generated" / "releases" / f"legacy-{utc_now().replace(':', '').replace('+00:00', 'Z')}"
            os.replace(root / "site", legacy)
        os.replace(link, root / "site")
        return release_id
    finally:
        if stage.exists():
            shutil.rmtree(stage)

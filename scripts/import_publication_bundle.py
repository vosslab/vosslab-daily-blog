#!/usr/bin/env python3
"""Validate and atomically import one producer-owned daily publication bundle."""

# Standard Library
import os
import json
import uuid
import shutil
import hashlib
import pathlib
import argparse
import subprocess
import datetime
import zoneinfo
import re

# local repo modules
import scripts.validate_daily_post


#============================================
def repository_root(start_path: str) -> str:
	"""Resolve the publisher repository root through Git."""
	start = os.path.dirname(os.path.abspath(start_path))
	result = subprocess.run(
		["git", "-C", start, "rev-parse", "--show-toplevel"],
		check=False,
		text=True,
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE,
		timeout=60,
	)
	if result.returncode:
		message = result.stderr.strip() or result.stdout.strip()
		raise RuntimeError(f"Publisher repository root is unavailable: {message}")
	root = result.stdout.strip()
	if not os.path.isabs(root):
		raise RuntimeError("Publisher repository root must be absolute.")
	return root


REPO_ROOT = repository_root(__file__)
BUNDLE_SCHEMA_VERSION = "vosslab.daily-blog.bundle.v1"
EVIDENCE_SCHEMA_VERSION = "vosslab.daily-blog.evidence.v2"
PUBLICATION_SCHEMA_VERSION = "vosslab.daily-blog.publication.v1"
AUTHORITY_ORDER = {
	"dated_changelog": 600,
	"changed_documentation": 500,
	"diff": 400,
	"readme_context": 300,
	"screenshot": 200,
	"commit_metadata": 100,
}
AUTHORITY_LEVELS = {
	"dated_changelog": "primary_narrative",
	"changed_documentation": "strong_support",
	"diff": "technical_support",
	"readme_context": "repository_context",
	"screenshot": "visual_support",
	"commit_metadata": "locator_provenance",
}
GENERATOR_VERSION = "daily-blog-generator-v1"
PROMPT_VERSION = "daily-blog-prompts-v2"
RUBRIC_VERSION = "daily-blog-rubric-v2"
HEX_DIGITS = frozenset("0123456789abcdef")
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


#============================================
def parse_args() -> argparse.Namespace:
	"""Parse the one public bundle-import command."""
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument(
		"-b",
		"--bundle",
		dest="bundle_path",
		required=True,
		help="Complete producer publication-bundle directory.",
	)
	args = parser.parse_args()
	return args


#============================================
def utc_now() -> str:
	"""Return a stable UTC timestamp without microseconds."""
	moment = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
	text = moment.isoformat().replace("+00:00", "Z")
	return text


#============================================
def canonical_json_bytes(value: object) -> bytes:
	"""Return deterministic UTF-8 JSON bytes for hashing."""
	text = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
	return text.encode("utf-8")


#============================================
def sha256_bytes(contents: bytes) -> str:
	"""Return one lowercase SHA-256 digest."""
	digest = hashlib.sha256(contents).hexdigest()
	return digest


#============================================
def hash_value(value: object) -> str:
	"""Hash one JSON-compatible value canonically."""
	return sha256_bytes(canonical_json_bytes(value))


#============================================
def _is_lower_hex(value: object, lengths: set[int]) -> bool:
	"""Return whether a value is one lowercase hexadecimal identity."""
	if not isinstance(value, str) or len(value) not in lengths:
		return False
	return set(value) <= HEX_DIGITS


#============================================
def _require_keys(value: dict, required: set[str], label: str) -> None:
	"""Require every named contract field in one JSON object."""
	missing = sorted(required - set(value))
	if missing:
		raise RuntimeError(f"{label} is missing required fields: {', '.join(missing)}")


#============================================
def _validate_report_identity(bundle: dict) -> None:
	"""Validate date, timezone, creation time, generator, and contract versions."""
	try:
		datetime.date.fromisoformat(bundle["report_date"])
	except (TypeError, ValueError) as error:
		raise RuntimeError("Bundle report date must use YYYY-MM-DD.") from error
	try:
		zoneinfo.ZoneInfo(bundle["timezone"])
	except (TypeError, zoneinfo.ZoneInfoNotFoundError) as error:
		raise RuntimeError("Bundle timezone must name an available IANA timezone.") from error
	try:
		created_at = datetime.datetime.fromisoformat(bundle["created_at"].replace("Z", "+00:00"))
	except (AttributeError, TypeError, ValueError) as error:
		raise RuntimeError("Bundle creation time must be an ISO-8601 timestamp.") from error
	if created_at.tzinfo is None:
		raise RuntimeError("Bundle creation time must include a timezone.")
	generator = bundle["generator"]
	if not isinstance(generator, dict):
		raise RuntimeError("Bundle generator metadata must be an object.")
	_require_keys(generator, {"run_id", "revision", "version"}, "Bundle generator metadata")
	if not isinstance(generator["run_id"], str) or not RUN_ID_RE.fullmatch(generator["run_id"]):
		raise RuntimeError("Bundle generator run ID must use a safe bounded identifier.")
	if not _is_lower_hex(generator["revision"], {40, 64}):
		raise RuntimeError("Bundle generator revision must be an exact Git object ID.")
	if generator["version"] != GENERATOR_VERSION:
		raise RuntimeError("Unsupported generator version.")
	contracts = bundle["contracts"]
	if not isinstance(contracts, dict):
		raise RuntimeError("Bundle contracts metadata must be an object.")
	_require_keys(
		contracts,
		{"evidence_schema", "prompt_version", "rubric_version"},
		"Bundle contracts metadata",
	)
	expected = {
		"evidence_schema": EVIDENCE_SCHEMA_VERSION,
		"prompt_version": PROMPT_VERSION,
		"rubric_version": RUBRIC_VERSION,
	}
	if any(contracts[key] != expected[key] for key in expected):
		raise RuntimeError("Bundle contract versions are unsupported.")


#============================================
def _validate_editorial_manifest(bundle: dict) -> None:
	"""Validate anonymous candidate summaries and the structured referee result."""
	candidates = bundle["candidates"]
	if not isinstance(candidates, list) or len(candidates) != 2:
		raise RuntimeError("Bundle must contain exactly two candidate validation summaries.")
	for index, candidate in enumerate(candidates, start=1):
		if not isinstance(candidate, dict):
			raise RuntimeError("Bundle candidate summaries must be objects.")
		_require_keys(
			candidate,
			{"candidate_id", "post_hash", "valid", "issues"},
			"Bundle candidate summary",
		)
		if candidate["candidate_id"] != f"candidate_{index}":
			raise RuntimeError("Bundle candidate IDs must use canonical anonymous ordering.")
		if not _is_lower_hex(candidate["post_hash"], {64}):
			raise RuntimeError("Bundle candidate post hash must be SHA-256.")
		if type(candidate["valid"]) is not bool:
			raise RuntimeError("Bundle candidate validity must be Boolean.")
		if not isinstance(candidate["issues"], list) or not all(
			isinstance(issue, str) for issue in candidate["issues"]
		):
			raise RuntimeError("Bundle candidate issues must be a list of strings.")
		if len(candidate["issues"]) > 50 or any(len(issue) > 1000 for issue in candidate["issues"]):
			raise RuntimeError("Bundle candidate issues exceed the bounded validation summary.")
		if candidate["valid"] == bool(candidate["issues"]):
			raise RuntimeError("Bundle candidate validity and issues are inconsistent.")
	referee = bundle["referee"]
	if not isinstance(referee, dict):
		raise RuntimeError("Bundle referee result must be an object.")
	_require_keys(
		referee,
		{"winner", "reason", "evidence_quality", "confidence", "anonymous_mapping"},
		"Bundle referee result",
	)
	if referee["winner"] not in {"A", "B", "NONE"}:
		raise RuntimeError("Bundle referee winner is unsupported.")
	if not isinstance(referee["reason"], str) or not 0 < len(referee["reason"].strip()) <= 500:
		raise RuntimeError("Bundle referee reason must be concise and non-empty.")
	if referee["evidence_quality"] not in {"high", "medium", "low"}:
		raise RuntimeError("Bundle referee evidence quality is unsupported.")
	confidence = referee["confidence"]
	if type(confidence) not in {int, float} or not 0 <= confidence <= 1:
		raise RuntimeError("Bundle referee confidence must be a number from zero through one.")
	mapping = referee["anonymous_mapping"]
	if not isinstance(mapping, dict) or set(mapping) - {"A", "B"}:
		raise RuntimeError("Bundle referee mapping must contain anonymous A/B labels.")
	if len(set(mapping.values())) != len(mapping) or any(
		value not in {"candidate_1", "candidate_2"} for value in mapping.values()
	):
		raise RuntimeError("Bundle referee mapping must identify distinct candidate summaries.")
	if referee["winner"] in {"A", "B"}:
		selected_id = mapping.get(referee["winner"])
		selected = next(
			(candidate for candidate in candidates if candidate["candidate_id"] == selected_id),
			None,
		)
		if selected is None or selected["valid"] is not True:
			raise RuntimeError("Bundle referee winner must map to a valid candidate.")
		if selected["post_hash"] != bundle["post"].get("sha256"):
			raise RuntimeError("Bundle final post is not the exact referee-selected candidate.")


#============================================
def stable_json_text(value: object) -> str:
	"""Render inspectable stable JSON with one final newline."""
	text = json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
	return text


#============================================
def atomic_write_text(path: str, text: str) -> None:
	"""Atomically replace one UTF-8 text file."""
	parent = os.path.dirname(os.path.abspath(path))
	os.makedirs(parent, exist_ok=True)
	temporary = os.path.join(parent, f".{os.path.basename(path)}.{uuid.uuid4().hex}.tmp")
	with open(temporary, "w", encoding="utf-8") as handle:
		handle.write(text)
	os.replace(temporary, path)


#============================================
def read_json_object(path: str) -> dict:
	"""Read one required JSON object."""
	with open(path, "r", encoding="utf-8") as handle:
		value = json.load(handle)
	if not isinstance(value, dict):
		raise RuntimeError(f"Expected one JSON object: {path}")
	return value


#============================================
def secure_bundle_dir(path: str) -> str:
	"""Return one physical bundle directory and reject link-based indirection."""
	resolved = os.path.abspath(path)
	if not os.path.isdir(resolved):
		raise RuntimeError("Publication bundle directory does not exist.")
	if os.path.islink(resolved):
		raise RuntimeError("Publication bundle directory must be physical.")
	return resolved


#============================================
def secure_child(bundle_dir: str, relative_path: str) -> str:
	"""Return one regular bundle file confined below the physical bundle root."""
	pure = pathlib.PurePosixPath(relative_path)
	if pure.is_absolute() or ".." in pure.parts or "." in pure.parts:
		raise RuntimeError(f"Bundle path is not confined: {relative_path}")
	path = os.path.abspath(os.path.join(bundle_dir, *pure.parts))
	if os.path.commonpath((bundle_dir, path)) != bundle_dir:
		raise RuntimeError(f"Bundle path escapes its root: {relative_path}")
	if not os.path.isfile(path) or os.path.islink(path):
		raise RuntimeError(f"Bundle artifact must be one regular file: {relative_path}")
	if os.path.commonpath((bundle_dir, os.path.realpath(path))) != bundle_dir:
		raise RuntimeError(f"Bundle artifact resolves outside its root: {relative_path}")
	return path


#============================================
def bundle_identity(bundle: dict) -> str:
	"""Recompute producer bundle identity independently."""
	content = dict(bundle)
	content.pop("bundle_id", None)
	return hash_value(content)


#============================================
def evidence_item_identity(item: dict) -> str:
	"""Recompute one producer evidence identity independently."""
	value = {
		"kind": item["kind"],
		"repository": item["repository"],
		"commit": item["commit"],
		"path": item["path"],
		"blob_hash": item["blob_hash"],
		"content_hash": item["content_hash"],
	}
	return "ev-" + hash_value(value)[:16]


#============================================
def _is_iso_timestamp(value: object) -> bool:
	"""Return whether a value is one timezone-aware ISO-8601 timestamp."""
	if not isinstance(value, str):
		return False
	try:
		moment = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
	except ValueError:
		return False
	return moment.tzinfo is not None


#============================================
def _validate_provenance_records(evidence: dict) -> dict[str, set[str]]:
	"""Validate typed mirror and activity records and return commit IDs by repository."""
	mirrors_by_repository = {}
	for mirror in evidence["mirrors"]:
		if not isinstance(mirror, dict):
			raise RuntimeError("Evidence mirror records must be objects.")
		_require_keys(
			mirror,
			{
				"repository", "repository_url", "cache_path",
				"refresh_result", "refresh_error", "default_revision",
				"object_available", "ref_fingerprint", "refreshed_at",
			},
			"Evidence mirror record",
		)
		repository = mirror["repository"]
		if not isinstance(repository, str) or not repository:
			raise RuntimeError("Evidence mirror repository must be non-empty.")
		if repository in mirrors_by_repository:
			raise RuntimeError("Evidence mirrors contain duplicate repositories.")
		if not isinstance(mirror["repository_url"], str) or not mirror[
			"repository_url"
		].startswith("https://github.com/"):
			raise RuntimeError("Evidence mirror origin must be one HTTPS GitHub URL.")
		if not isinstance(mirror["cache_path"], str) or not os.path.isabs(mirror["cache_path"]):
			raise RuntimeError("Evidence mirror cache path must be absolute.")
		if mirror["refresh_result"] not in {"refreshed", "skipped"}:
			raise RuntimeError("Evidence mirror refresh must be complete.")
		if mirror["refresh_error"] != "" or mirror["object_available"] is not True:
			raise RuntimeError("Evidence mirror object availability is incomplete.")
		if not _is_lower_hex(mirror["default_revision"], {40, 64}):
			raise RuntimeError("Evidence mirror default revision must be an exact Git object ID.")
		if not _is_lower_hex(mirror["ref_fingerprint"], {64}):
			raise RuntimeError("Evidence mirror ref fingerprint must be SHA-256.")
		if not _is_iso_timestamp(mirror["refreshed_at"]):
			raise RuntimeError("Evidence mirror refresh time must be timezone-aware.")
		mirrors_by_repository[repository] = mirror
	commits_by_repository = {}
	for activity in evidence["activity"]:
		if not isinstance(activity, dict):
			raise RuntimeError("Evidence activity records must be objects.")
		_require_keys(
			activity,
			{
				"repository", "repository_url", "cache_path", "default_revision",
				"commits", "revision_ranges", "snapshot_commits",
			},
			"Evidence activity record",
		)
		repository = activity["repository"]
		mirror = mirrors_by_repository.get(repository)
		if mirror is None:
			raise RuntimeError("Evidence activity has no matching mirror record.")
		for key in ("repository_url", "cache_path", "default_revision"):
			if activity[key] != mirror[key]:
				raise RuntimeError("Evidence activity does not match its mirror provenance.")
		commits = activity["commits"]
		if not isinstance(commits, list) or not commits:
			raise RuntimeError("Evidence activity requires attributed commits.")
		commit_ids = set()
		commit_parents = {}
		for commit in commits:
			if not isinstance(commit, dict):
				raise RuntimeError("Evidence commit records must be objects.")
			_require_keys(
				commit,
				{
					"sha", "parents", "author_name", "author_email",
					"author_timestamp", "committer_timestamp", "message",
				},
				"Evidence commit record",
			)
			if not _is_lower_hex(commit["sha"], {40, 64}):
				raise RuntimeError("Evidence commit SHA must be an exact Git object ID.")
			if not isinstance(commit["parents"], list) or not all(
				_is_lower_hex(parent, {40, 64}) for parent in commit["parents"]
			):
				raise RuntimeError("Evidence commit parents must be exact Git object IDs.")
			if not _is_iso_timestamp(commit["author_timestamp"]) or not _is_iso_timestamp(
				commit["committer_timestamp"]
			):
				raise RuntimeError("Evidence commit timestamps must be timezone-aware.")
			if not all(
				isinstance(commit[key], str) and commit[key]
				for key in ("author_name", "author_email", "message")
			):
				raise RuntimeError("Evidence commit attribution and message must be non-empty.")
			commit_ids.add(commit["sha"])
			commit_parents[commit["sha"]] = tuple(commit["parents"])
		if len(commit_ids) != len(commits):
			raise RuntimeError("Evidence activity commit identities are inconsistent.")
		ranges = activity["revision_ranges"]
		if not isinstance(ranges, list) or not ranges:
			raise RuntimeError("Evidence activity requires exact revision ranges.")
		actual_ranges = set()
		for revision in ranges:
			if not isinstance(revision, dict):
				raise RuntimeError("Evidence revision ranges must be objects.")
			_require_keys(
				revision,
				{"base_commit", "final_commit"},
				"Evidence revision range",
			)
			base_commit = revision["base_commit"]
			final_commit = revision["final_commit"]
			if base_commit and not _is_lower_hex(base_commit, {40, 64}):
				raise RuntimeError("Evidence revision base must be an exact Git object ID.")
			if not _is_lower_hex(final_commit, {40, 64}):
				raise RuntimeError("Evidence revision final must be an exact Git object ID.")
			actual_ranges.add((base_commit, final_commit))
		expected_ranges = {
			(base_commit, commit_id)
			for commit_id, parents in commit_parents.items()
			for base_commit in (parents or ("",))
		}
		if len(actual_ranges) != len(ranges) or actual_ranges != expected_ranges:
			raise RuntimeError("Evidence revision ranges do not match attributed commit parents.")
		snapshots = activity["snapshot_commits"]
		if (
			not isinstance(snapshots, list)
			or not snapshots
			or len(set(snapshots)) != len(snapshots)
			or any(commit not in commit_ids for commit in snapshots)
		):
			raise RuntimeError("Evidence snapshot commits must be unique attributed commits.")
		if repository in commits_by_repository:
			raise RuntimeError("Evidence activity contains duplicate repositories.")
		commits_by_repository[repository] = commit_ids
	return commits_by_repository


#============================================
def validate_evidence(evidence: dict, bundle: dict) -> dict[str, dict]:
	"""Verify evidence schema, packet identity, authority, and item hashes."""
	_require_keys(
		evidence,
		{
			"schema_version", "report_date", "timezone", "complete", "budgets",
			"mirrors", "activity", "items", "packet_id",
		},
		"Evidence packet",
	)
	if evidence.get("schema_version") != EVIDENCE_SCHEMA_VERSION:
		raise RuntimeError("Unsupported evidence packet schema.")
	if evidence.get("report_date") != bundle["report_date"]:
		raise RuntimeError("Evidence report date does not match the bundle.")
	if evidence.get("timezone") != bundle["timezone"]:
		raise RuntimeError("Evidence timezone does not match the bundle.")
	if evidence.get("complete") is not True:
		raise RuntimeError("Publication bundle evidence must be complete.")
	if not isinstance(evidence["budgets"], dict):
		raise RuntimeError("Evidence budgets must be an object.")
	if not isinstance(evidence["mirrors"], list) or not isinstance(evidence["activity"], list):
		raise RuntimeError("Evidence mirrors and activity must be lists.")
	commits_by_repository = _validate_provenance_records(evidence)
	packet_content = dict(evidence)
	packet_id = packet_content.pop("packet_id", None)
	if hash_value(packet_content) != packet_id:
		raise RuntimeError("Evidence packet identity does not match its content.")
	if packet_id != bundle["evidence"]["packet_id"]:
		raise RuntimeError("Bundle evidence identity does not match evidence.json.")
	items = evidence.get("items")
	if not isinstance(items, list) or not items:
		raise RuntimeError("Evidence packet requires at least one evidence item.")
	items_by_id = {}
	previous_rank = None
	for item in items:
		if not isinstance(item, dict):
			raise RuntimeError("Evidence items must be JSON objects.")
		_require_keys(
			item,
			{
				"evidence_id", "kind", "authority_level", "authority_rank",
				"repository", "commit", "path", "blob_hash", "content", "content_hash",
				"acquisition_source", "truncated", "asset_path", "publish_path",
			},
			"Evidence item",
		)
		kind = item.get("kind")
		if kind not in AUTHORITY_ORDER:
			raise RuntimeError(f"Unsupported evidence kind: {kind}")
		for key in (
			"evidence_id",
			"authority_level",
			"repository",
			"commit",
			"path",
			"blob_hash",
			"content_hash",
			"acquisition_source",
			"asset_path",
			"publish_path",
		):
			if not isinstance(item[key], str):
				raise RuntimeError(f"Evidence item field must be text: {key}")
		if not item["repository"] or not item["acquisition_source"]:
			raise RuntimeError("Evidence repository and acquisition source must be non-empty.")
		if item["commit"] and not _is_lower_hex(item["commit"], {40, 64}):
			raise RuntimeError("Evidence item commit must be an exact Git object ID.")
		if item["path"] and not _is_lower_hex(item["blob_hash"], {40, 64}):
			raise RuntimeError("Path evidence must identify an exact Git blob.")
		if not item["path"] and item["blob_hash"]:
			raise RuntimeError("Evidence without a path cannot declare a Git blob.")
		if commits_by_repository:
			if item["repository"] not in commits_by_repository:
				raise RuntimeError("Evidence item repository has no activity provenance.")
			if item["commit"] not in commits_by_repository[item["repository"]]:
				raise RuntimeError("Evidence item commit has no activity provenance.")
		if item.get("authority_rank") != AUTHORITY_ORDER[kind]:
			raise RuntimeError("Evidence authority rank does not match its kind.")
		if item.get("authority_level") != AUTHORITY_LEVELS[kind]:
			raise RuntimeError("Evidence authority level does not match its kind.")
		if previous_rank is not None and item["authority_rank"] > previous_rank:
			raise RuntimeError("Evidence items are not ordered by authority.")
		previous_rank = item["authority_rank"]
		if not isinstance(item["content"], str):
			raise RuntimeError("Evidence content must be text.")
		if type(item["truncated"]) is not bool:
			raise RuntimeError("Evidence truncation state must be Boolean.")
		content = item["content"]
		if sha256_bytes(content.encode("utf-8")) != item.get("content_hash"):
			raise RuntimeError("Evidence content hash does not match its content.")
		if evidence_item_identity(item) != item.get("evidence_id"):
			raise RuntimeError("Evidence item identity does not match its provenance.")
		identifier = item["evidence_id"]
		if identifier in items_by_id:
			raise RuntimeError("Evidence packet contains duplicate evidence IDs.")
		items_by_id[identifier] = item
	return items_by_id


#============================================
def _listed_asset_files(bundle_dir: str) -> set[str]:
	"""Return every physical asset file while rejecting directory symlinks."""
	asset_root = os.path.join(bundle_dir, "assets")
	if not os.path.isdir(asset_root) or os.path.islink(asset_root):
		raise RuntimeError("Bundle assets must use one physical assets directory.")
	paths = set()
	for current_root, directories, files in os.walk(asset_root):
		for name in directories:
			if os.path.islink(os.path.join(current_root, name)):
				raise RuntimeError("Bundle asset directories must be physical.")
		for name in files:
			path = os.path.join(current_root, name)
			if os.path.islink(path):
				raise RuntimeError("Bundle assets must be regular files.")
			relative = os.path.relpath(path, bundle_dir).replace(os.sep, "/")
			paths.add(relative)
	return paths


#============================================
def validate_assets(bundle_dir: str, bundle: dict, items_by_id: dict[str, dict]) -> None:
	"""Verify asset hashes, paths, and evidence provenance."""
	assets = bundle.get("assets")
	if not isinstance(assets, list):
		raise RuntimeError("Bundle assets must be a list.")
	manifest_paths = set()
	for asset in assets:
		if not isinstance(asset, dict):
			raise RuntimeError("Bundle asset entries must be objects.")
		path = str(asset.get("path") or "")
		pure = pathlib.PurePosixPath(path)
		if len(pure.parts) != 2 or pure.parts[0] != "assets":
			raise RuntimeError(f"Bundle asset path must be assets/<name>: {path}")
		asset_path = secure_child(bundle_dir, path)
		with open(asset_path, "rb") as handle:
			contents = handle.read()
		if sha256_bytes(contents) != asset.get("sha256"):
			raise RuntimeError(f"Bundle asset hash mismatch: {path}")
		evidence_id = str(asset.get("evidence_id") or "")
		if evidence_id not in items_by_id:
			raise RuntimeError(f"Bundle asset has unknown evidence ID: {path}")
		item = items_by_id[evidence_id]
		if item.get("kind") != "screenshot" or item.get("asset_path") != path:
			raise RuntimeError(f"Bundle asset does not match screenshot evidence: {path}")
		if item.get("blob_hash") != asset.get("git_blob_hash"):
			raise RuntimeError(f"Bundle asset Git blob provenance mismatch: {path}")
		expected_publish_path = f"../../assets/publications/{bundle['report_date']}/{pure.name}"
		if asset.get("publish_path") != expected_publish_path:
			raise RuntimeError(f"Bundle asset publication path mismatch: {path}")
		if item.get("publish_path") != expected_publish_path:
			raise RuntimeError(f"Evidence publication path mismatch: {path}")
		manifest_paths.add(path)
	if len(manifest_paths) != len(assets):
		raise RuntimeError("Bundle asset manifest contains duplicate paths.")
	evidence_asset_paths = {item["asset_path"] for item in items_by_id.values() if item["asset_path"]}
	if evidence_asset_paths != manifest_paths:
		raise RuntimeError("Screenshot evidence and bundle assets do not match.")
	if _listed_asset_files(bundle_dir) != manifest_paths:
		raise RuntimeError("Bundle assets directory does not match its manifest.")


#============================================
def validate_bundle(bundle_path: str) -> tuple[dict, dict, str]:
	"""Validate the complete current bundle contract and return its core artifacts."""
	bundle_dir = secure_bundle_dir(bundle_path)
	bundle_file = secure_child(bundle_dir, "bundle.json")
	evidence_file = secure_child(bundle_dir, "evidence.json")
	post_file = secure_child(bundle_dir, "post.md")
	bundle = read_json_object(bundle_file)
	evidence = read_json_object(evidence_file)
	with open(post_file, "r", encoding="utf-8") as handle:
		post = handle.read()
	_require_keys(
		bundle,
		{
			"schema_version", "bundle_id", "report_date", "timezone",
			"publication_quality", "created_at", "generator", "contracts",
			"evidence", "post", "assets", "candidates", "referee",
		},
		"Publication bundle",
	)
	if bundle.get("schema_version") != BUNDLE_SCHEMA_VERSION:
		raise RuntimeError("Unsupported publication bundle schema.")
	if bundle_identity(bundle) != bundle.get("bundle_id"):
		raise RuntimeError("Publication bundle identity does not match its manifest.")
	if not isinstance(bundle["post"], dict) or not isinstance(bundle["evidence"], dict):
		raise RuntimeError("Bundle post and evidence manifests must be objects.")
	_validate_report_identity(bundle)
	_validate_editorial_manifest(bundle)
	if bundle.get("publication_quality") not in {"final", "provisional"}:
		raise RuntimeError("Unsupported publication quality.")
	if bundle["publication_quality"] == "final" and bundle["referee"].get("winner") not in {"A", "B"}:
		raise RuntimeError("Final bundles require an approved anonymous candidate.")
	if bundle["publication_quality"] == "provisional" and bundle["referee"].get("winner") != "NONE":
		raise RuntimeError("Provisional bundles require a NONE referee result.")
	if bundle.get("post", {}).get("path") != "post.md":
		raise RuntimeError("Bundle post path must name post.md.")
	if bundle.get("evidence", {}).get("path") != "evidence.json":
		raise RuntimeError("Bundle evidence path must name evidence.json.")
	if hash_value(evidence) != bundle["evidence"].get("sha256"):
		raise RuntimeError("Bundle evidence hash does not match evidence.json.")
	if not _is_lower_hex(bundle["evidence"].get("sha256"), {64}):
		raise RuntimeError("Bundle evidence hash must be SHA-256.")
	if sha256_bytes(post.encode("utf-8")) != bundle["post"].get("sha256"):
		raise RuntimeError("Bundle post hash does not match post.md.")
	if not _is_lower_hex(bundle["post"].get("sha256"), {64}):
		raise RuntimeError("Bundle post hash must be SHA-256.")
	items_by_id = validate_evidence(evidence, bundle)
	validate_assets(bundle_dir, bundle, items_by_id)
	post_issues = scripts.validate_daily_post.validate_post(post, evidence, bundle)
	if post_issues:
		raise RuntimeError("Bundle post validation failed: " + "; ".join(post_issues))
	return bundle, evidence, post


#============================================
def _publication_record_path(root: str, report_date: str) -> str:
	"""Return the current publisher-owned record for one date."""
	return os.path.join(root, "data", "publications", f"{report_date}.json")


#============================================
def _load_current_record(root: str, report_date: str) -> dict | None:
	"""Load the current date record when present."""
	path = _publication_record_path(root, report_date)
	if not os.path.isfile(path):
		return None
	if os.path.islink(path):
		raise RuntimeError("Current publication record must be one physical file.")
	return read_json_object(path)


#============================================
def _quality_rank(value: dict) -> int:
	"""Return replacement precedence for one bundle or publication record."""
	quality = value.get("publication_quality")
	return {"provisional": 1, "final": 2}.get(quality, 0)


#============================================
def _read_publication_records(root: str, proposed: dict) -> list[dict]:
	"""Read publication records and replace the proposed date in memory."""
	directory = os.path.join(root, "data", "publications")
	records_by_date = {}
	if os.path.isdir(directory):
		for name in os.listdir(directory):
			if not name.endswith(".json"):
				continue
			path = os.path.join(directory, name)
			if os.path.islink(path) or not os.path.isfile(path):
				continue
			record = read_json_object(path)
			date_text = str(record.get("report_date") or name[:-5])
			records_by_date[date_text] = record
	records_by_date[proposed["report_date"]] = proposed
	records = [records_by_date[key] for key in sorted(records_by_date, reverse=True)]
	return records


#============================================
def render_status(records: list[dict]) -> str:
	"""Render the local status page from current and historical records."""
	lines = [
		"# Publication status",
		"",
		"| Report date | Quality | Generator run | Bundle |",
		"| --- | --- | --- | --- |",
	]
	for record in records[:30]:
		date_text = str(record.get("report_date") or "unknown")
		if record.get("schema_version") == PUBLICATION_SCHEMA_VERSION:
			quality = str(record["publication_quality"])
			run_id = str(record["generator_run"])
			bundle_id = str(record["bundle_id"])[:12]
		else:
			quality = "legacy"
			run_id = "historical"
			bundle_id = "historical"
		lines.append(f"| {date_text} | {quality} | {run_id} | {bundle_id} |")
	lines.extend(
		[
			"",
			"A final bundle may supersede a provisional bundle for the same report date. "
			+ "Bundle validation and strict staged builds complete before this page changes.",
			"",
		]
	)
	return "\n".join(lines)


#============================================
def _reject_tree_symlinks(root: str) -> None:
	"""Reject symlinks before staging a complete source tree."""
	for current_root, directories, files in os.walk(root):
		for name in directories + files:
			if os.path.islink(os.path.join(current_root, name)):
				raise RuntimeError(f"MkDocs source tree contains a symlink: {name}")


#============================================
def strict_mkdocs_build(stage_root: str, site_dir: str, root: str) -> None:
	"""Run one strict MkDocs build against the complete staged source tree."""
	venv_mkdocs = os.path.join(root, ".venv", "bin", "mkdocs")
	mkdocs = venv_mkdocs if os.path.isfile(venv_mkdocs) else shutil.which("mkdocs")
	if not mkdocs:
		raise RuntimeError("MkDocs executable is unavailable.")
	result = subprocess.run(
		[
			mkdocs,
			"build",
			"--strict",
			"--config-file",
			os.path.join(stage_root, "mkdocs.yml"),
			"--site-dir",
			site_dir,
		],
		cwd=stage_root,
		check=False,
		text=True,
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE,
		timeout=600,
	)
	if result.returncode:
		message = result.stderr.strip() or result.stdout.strip()
		raise RuntimeError(f"Strict staged MkDocs build failed: {message}")


#============================================
def _publication_record(bundle: dict) -> dict:
	"""Build the current publisher-owned record from one validated bundle."""
	bundle_id = bundle["bundle_id"]
	record = {
		"schema_version": PUBLICATION_SCHEMA_VERSION,
		"report_date": bundle["report_date"],
		"timezone": bundle["timezone"],
		"publication_quality": bundle["publication_quality"],
		"bundle_id": bundle_id,
		"generator_run": bundle["generator"]["run_id"],
		"generator_revision": bundle["generator"]["revision"],
		"evidence_manifest": f"data/publication_bundles/{bundle_id}/evidence.json",
		"post_path": f"docs/blog/posts/{bundle['report_date']}.md",
		"release_id": bundle_id,
		"imported_at": utc_now(),
	}
	return record


#============================================
def _copy_bundle_archive(bundle_dir: str, archive_stage: str) -> None:
	"""Stage the durable manifest, evidence, and exact selected post."""
	os.makedirs(archive_stage)
	for name in ("bundle.json", "evidence.json", "post.md"):
		shutil.copy2(secure_child(bundle_dir, name), os.path.join(archive_stage, name))


#============================================
def _is_idempotent(root: str, bundle: dict, post: str) -> bool:
	"""Return whether the exact bundle is already the complete installed release."""
	record = _load_current_record(root, bundle["report_date"])
	if not record or record.get("bundle_id") != bundle["bundle_id"]:
		return False
	bundle_id = bundle["bundle_id"]
	release = os.path.join(root, "generated", "releases", bundle_id)
	archive = os.path.join(root, "data", "publication_bundles", bundle_id)
	post_path = os.path.join(root, "docs", "blog", "posts", f"{bundle['report_date']}.md")
	if not os.path.isdir(release) or not os.path.isdir(archive) or not os.path.isfile(post_path):
		raise RuntimeError("Existing identical publication record is incomplete.")
	with open(post_path, "r", encoding="utf-8") as handle:
		installed_post = handle.read()
	if installed_post != post:
		raise RuntimeError("Existing identical publication record has different post content.")
	return True


#============================================
def _prepare_stage(
	root: str,
	stage_root: str,
	bundle_dir: str,
	bundle: dict,
	evidence: dict,
	post: str,
	build_function: object,
) -> tuple[str, dict]:
	"""Stage complete source, record, archive, validation, and strict build outputs."""
	proposed_docs = os.path.join(stage_root, "docs")
	_reject_tree_symlinks(os.path.join(root, "docs"))
	shutil.copytree(os.path.join(root, "docs"), proposed_docs)
	shutil.copy2(os.path.join(root, "mkdocs.yml"), os.path.join(stage_root, "mkdocs.yml"))
	post_path = os.path.join(proposed_docs, "blog", "posts", f"{bundle['report_date']}.md")
	os.makedirs(os.path.dirname(post_path), exist_ok=True)
	atomic_write_text(post_path, post)
	for asset in bundle["assets"]:
		name = pathlib.PurePosixPath(asset["path"]).name
		destination = os.path.join(
			proposed_docs,
			"assets",
			"publications",
			bundle["report_date"],
			name,
		)
		os.makedirs(os.path.dirname(destination), exist_ok=True)
		shutil.copy2(secure_child(bundle_dir, asset["path"]), destination)
	record = _publication_record(bundle)
	status = render_status(_read_publication_records(root, record))
	atomic_write_text(os.path.join(proposed_docs, "status.md"), status)
	post_issues = scripts.validate_daily_post.validate_post(post, evidence, bundle)
	if post_issues:
		raise RuntimeError("Staged article validation failed: " + "; ".join(post_issues))
	archive_stage = os.path.join(stage_root, "publication_archive")
	_copy_bundle_archive(bundle_dir, archive_stage)
	atomic_write_text(os.path.join(stage_root, "publication.json"), stable_json_text(record))
	site_dir = os.path.join(stage_root, "site")
	build_function(stage_root, site_dir, root)
	if not os.path.isfile(os.path.join(site_dir, "index.html")):
		raise RuntimeError("Strict build did not produce a site index.")
	return stage_root, record


#============================================
def _new_stage_root(root: str, bundle_id: str) -> str:
	"""Create and return one unique publisher-owned staging directory."""
	stage_parent = os.path.join(root, "generated", "staging")
	os.makedirs(stage_parent, exist_ok=True)
	stage_root = os.path.join(stage_parent, f"import-{bundle_id}-{uuid.uuid4().hex}")
	os.makedirs(stage_root)
	return stage_root


#============================================
def _commit_stage(root: str, stage_root: str, record: dict) -> None:
	"""Install source, records, archive, release, and served pointer transactionally."""
	bundle_id = record["bundle_id"]
	report_date = record["report_date"]
	release = os.path.join(root, "generated", "releases", bundle_id)
	archive = os.path.join(root, "data", "publication_bundles", bundle_id)
	record_path = _publication_record_path(root, report_date)
	docs_path = os.path.join(root, "docs")
	site_link = os.path.join(root, "site")
	if os.path.lexists(release) or os.path.lexists(archive):
		raise RuntimeError("Immutable release or publication archive already exists.")
	os.makedirs(os.path.dirname(release), exist_ok=True)
	os.makedirs(os.path.dirname(archive), exist_ok=True)
	os.makedirs(os.path.dirname(record_path), exist_ok=True)
	previous_docs = os.path.join(stage_root, "previous_docs")
	previous_record = os.path.join(stage_root, "previous_publication.json")
	previous_site = os.path.join(stage_root, "previous_site")
	release_installed = False
	archive_installed = False
	docs_installed = False
	record_installed = False
	site_moved = False
	previous_docs_moved = False
	previous_record_moved = False
	try:
		os.replace(os.path.join(stage_root, "site"), release)
		release_installed = True
		os.replace(os.path.join(stage_root, "publication_archive"), archive)
		archive_installed = True
		if os.path.exists(record_path):
			os.replace(record_path, previous_record)
			previous_record_moved = True
		os.replace(os.path.join(stage_root, "publication.json"), record_path)
		record_installed = True
		os.replace(docs_path, previous_docs)
		previous_docs_moved = True
		os.replace(os.path.join(stage_root, "docs"), docs_path)
		docs_installed = True
		if os.path.lexists(site_link) and not os.path.islink(site_link):
			os.replace(site_link, previous_site)
			site_moved = True
		next_link = os.path.join(root, f".site-next-{uuid.uuid4().hex}")
		os.symlink(os.path.relpath(release, root), next_link)
		os.replace(next_link, site_link)
	except Exception:
		if docs_installed and os.path.exists(docs_path):
			shutil.rmtree(docs_path)
		if previous_docs_moved and os.path.exists(previous_docs):
			os.replace(previous_docs, docs_path)
		if record_installed and os.path.exists(record_path):
			os.unlink(record_path)
		if previous_record_moved and os.path.exists(previous_record):
			os.replace(previous_record, record_path)
		if site_moved and os.path.exists(previous_site):
			os.replace(previous_site, site_link)
		if archive_installed and os.path.exists(archive):
			shutil.rmtree(archive)
		if release_installed and os.path.exists(release):
			shutil.rmtree(release)
		raise
	if os.path.exists(previous_docs):
		shutil.rmtree(previous_docs)
	if os.path.exists(previous_record):
		os.unlink(previous_record)
	if os.path.exists(previous_site):
		shutil.rmtree(previous_site)


#============================================
def import_publication_bundle(
	bundle_path: str,
	root: str = REPO_ROOT,
	build_function: object = strict_mkdocs_build,
) -> dict:
	"""Validate, stage, strictly build, and atomically install one bundle."""
	bundle_dir = secure_bundle_dir(bundle_path)
	bundle, evidence, post = validate_bundle(bundle_dir)
	if _is_idempotent(root, bundle, post):
		return {
			"status": "idempotent",
			"bundle_id": bundle["bundle_id"],
			"report_date": bundle["report_date"],
		}
	current = _load_current_record(root, bundle["report_date"])
	if current and _quality_rank(bundle) < _quality_rank(current):
		raise RuntimeError("A provisional bundle cannot supersede a final publication.")
	if current and _quality_rank(current) == 2:
		raise RuntimeError("A different bundle cannot supersede an existing final publication.")
	stage_root = _new_stage_root(root, bundle["bundle_id"])
	try:
		stage_root, record = _prepare_stage(
			root,
			stage_root,
			bundle_dir,
			bundle,
			evidence,
			post,
			build_function,
		)
		_commit_stage(root, stage_root, record)
	except Exception:
		if stage_root and os.path.exists(stage_root):
			shutil.rmtree(stage_root)
		raise
	if os.path.exists(stage_root):
		shutil.rmtree(stage_root)
	result = {
		"status": "imported",
		"bundle_id": bundle["bundle_id"],
		"report_date": bundle["report_date"],
		"publication_quality": bundle["publication_quality"],
		"release_id": bundle["bundle_id"],
	}
	return result


#============================================
def main() -> None:
	"""Run the publisher's sole generator-facing import command."""
	args = parse_args()
	result = import_publication_bundle(args.bundle_path)
	print(stable_json_text(result), end="")


if __name__ == "__main__":
	main()

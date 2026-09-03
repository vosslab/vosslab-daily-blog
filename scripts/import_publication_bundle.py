#!/usr/bin/env python3
"""Validate and atomically import one producer-owned daily publication bundle."""

# Standard Library
import os
import json
import uuid
import shutil
import hashlib
import pathlib
import subprocess
import datetime
import zoneinfo
import re
import sys

# local repo modules
import scripts.publication_record
import scripts.validate_daily_post
import scripts.site_deployment
import scripts.validate_editorial_projection
import scripts.validate_repository_lifecycle
import scripts.validate_repository_roster
import scripts.publication_transaction
import scripts.publication_import_cli
import scripts.repository_paths
import scripts.maker_activation
import scripts.bundle_snapshot
import scripts.publication_staging
import scripts.canonical_json
import scripts.publication_source_safety
import scripts.publication_import_protocol
import scripts.publication_surface


REPO_ROOT = scripts.repository_paths.repository_root(__file__)
BUNDLE_SCHEMA_VERSION = "vosslab.daily-blog.bundle.v9"
EVIDENCE_SCHEMA_VERSION = "vosslab.daily-blog.evidence.v4"
EDITORIAL_PROJECTION_SCHEMA_VERSION = (
	scripts.validate_editorial_projection.EDITORIAL_PROJECTION_SCHEMA_VERSION
)
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
GENERATOR_VERSION = "daily-blog-generator-v2"
HEX_DIGITS = frozenset("0123456789abcdef")
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
REPOSITORY_RE = re.compile(r"^(?P<owner>[A-Za-z0-9-]+)/(?P<name>[A-Za-z0-9._-]+)$")
ARTIFACT_ID_RE = re.compile(r"^artifact-[0-9a-f]{24}$")


#============================================
def utc_now() -> str:
	"""Return a stable UTC timestamp without microseconds."""
	moment = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
	text = moment.isoformat().replace("+00:00", "Z")
	return text


#============================================
def canonical_json_bytes(value: object) -> bytes:
	"""Return deterministic UTF-8 JSON bytes for hashing."""
	contents = scripts.canonical_json.compact_json_bytes(value)
	return contents


#============================================
def sha256_bytes(contents: bytes) -> str:
	"""Return one lowercase SHA-256 digest."""
	digest = hashlib.sha256(contents).hexdigest()
	return digest


#============================================
def hash_value(value: object) -> str:
	"""Hash one JSON-compatible value canonically."""
	return scripts.canonical_json.hash_value(value)


#============================================
def _is_lower_hex(value: object, lengths: set[int]) -> bool:
	"""Return whether a value is one lowercase hexadecimal identity."""
	if not isinstance(value, str) or len(value) not in lengths:
		return False
	return set(value) <= HEX_DIGITS


#============================================
def _require_keys(value: dict, required: set[str], label: str) -> None:
	"""Require the exact named contract fields in one JSON object."""
	missing = sorted(required - set(value))
	if missing:
		raise RuntimeError(f"{label} is missing required fields: {', '.join(missing)}")
	extra = sorted(set(value) - required)
	if extra:
		raise RuntimeError(f"{label} has unsupported fields: {', '.join(extra)}")


#============================================
def _validate_report_identity(bundle: dict) -> None:
	"""Validate date, timezone, creation time, generator, and contract versions."""
	receipt = scripts.maker_activation.validate_bundle_activation(bundle)
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
	if not _is_lower_hex(generator["revision"], {64}):
		raise RuntimeError("Bundle generator revision must be a 64-hex source/config fingerprint.")
	if generator["version"] != GENERATOR_VERSION:
		raise RuntimeError("Unsupported generator version.")
	contracts = bundle["contracts"]
	if not isinstance(contracts, dict):
		raise RuntimeError("Bundle contracts metadata must be an object.")
	_require_keys(
		contracts,
		{
			"evidence_schema", "editorial_projection_schema",
			"prompt_version", "rubric_version", "candidate_validation",
			"publication_source_safety",
		},
		"Bundle contracts metadata",
	)
	prompt_contract = receipt["editorial_prompt_contract"]
	if not isinstance(prompt_contract, dict):
		raise RuntimeError("Maker activation prompt contract is invalid.")
	expected = {
		"evidence_schema": EVIDENCE_SCHEMA_VERSION,
		"editorial_projection_schema": EDITORIAL_PROJECTION_SCHEMA_VERSION,
		"prompt_version": prompt_contract.get("prompt_version"),
		"rubric_version": prompt_contract.get("rubric_version"),
		"candidate_validation": receipt["candidate_validation"],
		"publication_source_safety": scripts.publication_source_safety.policy_identity(),
	}
	if any(contracts[key] != expected[key] for key in expected):
		raise RuntimeError("Bundle contract versions are unsupported.")

#============================================
def stable_json_text(value: object) -> str:
	"""Render inspectable stable JSON with one final newline."""
	text = scripts.canonical_json.stable_json_bytes(value).decode("utf-8")
	return text

#============================================
def read_json_object(path: str) -> dict:
	"""Read one required JSON object."""
	with open(path, "r", encoding="utf-8") as handle:
		value = json.load(handle)
	if not isinstance(value, dict):
		raise RuntimeError(f"Expected one JSON object: {path}")
	return value

#============================================
def bundle_sha256(bundle: dict) -> str:
	"""Recompute the producer bundle checksum independently."""
	content = dict(bundle)
	content.pop("bundle_sha256", None)
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
def _is_canonical_utc_timestamp(value: object) -> bool:
	"""Return whether a value is one canonical whole-second UTC timestamp."""
	if not _is_iso_timestamp(value):
		return False
	moment = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
	canonical = moment.astimezone(datetime.timezone.utc).replace(microsecond=0)
	return value == canonical.isoformat().replace("+00:00", "Z")


#============================================
def _validate_provenance_records(evidence: dict) -> dict[str, set[str]]:
	"""Validate typed mirror and activity records and return commit IDs by repository."""
	mirrors_by_repository = {}
	roster_ids = set()
	for mirror in evidence["mirrors"]:
		if not isinstance(mirror, dict):
			raise RuntimeError("Evidence mirror records must be objects.")
		_require_keys(
			mirror,
			{
				"repository", "repository_url", "clone_url", "created_at", "is_fork",
				"roster_id", "cache_path",
				"refresh_result", "refresh_error", "default_revision",
				"object_available", "ref_fingerprint", "refreshed_at",
			},
			"Evidence mirror record",
		)
		repository = mirror["repository"]
		match = REPOSITORY_RE.fullmatch(repository) if isinstance(repository, str) else None
		if match is None or ".." in match.group("name"):
			raise RuntimeError("Evidence mirror repository must be non-empty.")
		if repository in mirrors_by_repository:
			raise RuntimeError("Evidence mirrors contain duplicate repositories.")
		expected_page = f"https://github.com/{repository}"
		if mirror["repository_url"] != expected_page or mirror["clone_url"] != expected_page + ".git":
			raise RuntimeError("Evidence mirror URLs must use canonical HTTPS GitHub identity.")
		if not _is_canonical_utc_timestamp(mirror["created_at"]):
			raise RuntimeError("Evidence mirror creation time must be canonical UTC.")
		if type(mirror["is_fork"]) is not bool:
			raise RuntimeError("Evidence mirror fork state must be Boolean.")
		if not _is_lower_hex(mirror["roster_id"], {64}):
			raise RuntimeError("Evidence mirror roster identity must be SHA-256.")
		roster_ids.add(mirror["roster_id"])
		if not isinstance(mirror["cache_path"], str) or not os.path.isabs(mirror["cache_path"]):
			raise RuntimeError("Evidence mirror cache path must be absolute.")
		if tuple(pathlib.PurePath(mirror["cache_path"]).parts[-2:]) != (
			match.group("owner"), match.group("name")
		):
			raise RuntimeError("Evidence mirror cache path must be owner-qualified.")
		refresh_result = mirror["refresh_result"]
		if refresh_result not in {"refreshed", "skipped"}:
			raise RuntimeError("Evidence mirror refresh must be complete.")
		if mirror["refresh_error"] != "" or mirror["object_available"] is not True:
			raise RuntimeError("Evidence mirror object availability is incomplete.")
		if not _is_lower_hex(mirror["default_revision"], {40, 64}):
			raise RuntimeError("Evidence mirror default revision must be an exact Git object ID.")
		if not _is_lower_hex(mirror["ref_fingerprint"], {64}):
			raise RuntimeError("Evidence mirror ref fingerprint must be SHA-256.")
		if refresh_result == "refreshed" and not _is_iso_timestamp(mirror["refreshed_at"]):
			raise RuntimeError("Evidence mirror refresh time must be timezone-aware.")
		if refresh_result == "skipped" and mirror["refreshed_at"] != "" and not _is_iso_timestamp(
			mirror["refreshed_at"]
		):
			raise RuntimeError("Skipped mirror inspection time must be empty or timezone-aware.")
		mirrors_by_repository[repository] = mirror
	if len(roster_ids) != 1:
		raise RuntimeError("Evidence mirrors must share one repository roster identity.")
	commits_by_repository = {}
	for activity in evidence["activity"]:
		if not isinstance(activity, dict):
			raise RuntimeError("Evidence activity records must be objects.")
		_require_keys(
			activity,
			{
				"repository", "repository_url", "cache_path", "default_revision",
				"commits", "revision_ranges", "snapshot_commits", "is_fork",
				"lifecycle_events",
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
		scripts.validate_repository_lifecycle.validate_activity_lifecycle(
			activity,
			mirror,
			evidence["report_date"],
			evidence["timezone"],
		)
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
			"schema_version", "report_date", "timezone", "complete", "collection_limits",
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
	if not isinstance(evidence["collection_limits"], dict):
		raise RuntimeError("Evidence collection limits must be an object.")
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
def declared_asset_paths(bundle: dict) -> set[str]:
	"""Validate manifest direct asset names before retaining their bytes."""
	assets = bundle.get("assets")
	if not isinstance(assets, list):
		raise RuntimeError("Bundle assets must be a list.")
	paths = set()
	for asset in assets:
		if not isinstance(asset, dict):
			raise RuntimeError("Bundle asset entries must be objects.")
		path = scripts.publication_surface.validate_direct_asset_path(asset.get("path"))
		paths.add(path)
	if len(paths) != len(assets):
		raise RuntimeError("Bundle asset manifest contains duplicate paths.")
	return paths

#============================================
def validate_assets(
	contents_by_path: dict[str, bytes],
	bundle: dict,
	items_by_id: dict[str, dict],
	surface: dict,
) -> dict[str, bytes]:
	"""Verify asset hashes, paths, and evidence provenance, then seal their bytes."""
	assets = bundle.get("assets")
	if not isinstance(assets, list):
		raise RuntimeError("Bundle assets must be a list.")
	manifest_paths = declared_asset_paths(bundle)
	for asset in assets:
		path = asset["path"]
		pure = pathlib.PurePosixPath(path)
		if path not in contents_by_path:
			raise RuntimeError(f"Bundle artifact must be regular: {path}")
		contents = contents_by_path[path]
		if sha256_bytes(contents) != asset.get("sha256"):
			raise RuntimeError(f"Bundle asset hash mismatch: {path}")
		contents_by_path[path] = contents
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
	# ASVS 2.3.1: stage precisely the survivor scope, not every aggregate screenshot.
	if scripts.publication_surface.allowed_asset_paths(surface) != manifest_paths:
		raise RuntimeError("Bundle assets do not exactly match publication surface images.")
	if set(contents_by_path) != manifest_paths:
		raise RuntimeError("Bundle assets directory does not match its manifest.")
	return contents_by_path

#============================================
def _receive_snapshot(
	snapshot: scripts.bundle_snapshot.BundleSnapshot,
) -> tuple[dict, dict, dict, dict, bytes, dict[str, bytes]]:
	"""Receive producer-authoritative bytes and validate only routing mechanics."""
	sealed_contents = {"bundle.json": snapshot.read("bundle.json")}
	bundle = scripts.canonical_json.load_stable_json(
		sealed_contents["bundle.json"], "Publication bundle routing manifest",
	)
	if not isinstance(bundle, dict):
		raise RuntimeError("Publication bundle routing manifest must be an object.")
	assets = bundle.get("assets")
	if not isinstance(assets, list):
		raise RuntimeError("Publication transfer asset routing is invalid.")
	asset_paths = declared_asset_paths(bundle)
	sealed_contents.update(snapshot.read_declared_assets(asset_paths))
	_validate_report_identity(bundle)
	if snapshot.transfer_header is not None and (
		snapshot.transfer_header["bundle_sha256"] != bundle.get("bundle_sha256")
		or snapshot.transfer_header["report_date"] != bundle.get("report_date")
	):
		raise RuntimeError("Publication transfer routing identity is inconsistent.")
	post_manifest = bundle.get("post")
	if not isinstance(post_manifest, dict) or post_manifest.get("path") != "post.md":
		raise RuntimeError("Publication transfer has no fixed post destination.")
	for name in (
		"evidence.json", "repository_roster.json", "daily_active_roster.json",
		"editorial_projection.json", "publication_surface.json", "post.md",
	):
		sealed_contents[name] = snapshot.read(name)
	# Evidence, roster, projection, surface, and Markdown meaning belong to the
	# producer. The renderer preserves these bytes without independently
	# parsing, scoring, or admitting their contents.
	return bundle, {}, {}, {}, sealed_contents["post.md"], sealed_contents


#============================================
def validate_bundle(bundle_path: str) -> tuple[dict, dict, dict, dict, bytes, dict[str, bytes]]:
	"""Validate a bundle and retain the accepted bytes for all later staging."""
	try:
		with scripts.bundle_snapshot.BundleSnapshot(bundle_path) as snapshot:
			result = validate_snapshot(snapshot)
		return result
	except scripts.publication_import_protocol.ImportProtocolError:
		raise
	except (RuntimeError, UnicodeDecodeError) as error:
		raise scripts.publication_import_protocol.ImportProtocolError(
			"snapshot_rejected", "validate", str(error),
		) from error


#============================================
def validate_snapshot(
	snapshot: scripts.bundle_snapshot.BundleSnapshot,
) -> tuple[dict, dict, dict, dict, bytes, dict[str, bytes]]:
	"""Validate one held bundle snapshot before source access can be released."""
	try:
		return _receive_snapshot(snapshot)
	except scripts.publication_import_protocol.ImportProtocolError:
		raise
	except (RuntimeError, UnicodeDecodeError) as error:
		raise scripts.publication_import_protocol.ImportProtocolError(
			"snapshot_rejected", "validate", str(error),
		) from error


#============================================
def _validate_snapshot(
	snapshot: scripts.bundle_snapshot.BundleSnapshot,
) -> tuple[dict, dict, dict, dict, str, dict[str, bytes]]:
	"""Perform the deterministic contract checks for one sealed snapshot."""
	sealed_contents = {"bundle.json": snapshot.read("bundle.json")}
	bundle = scripts.canonical_json.load_stable_json(
		sealed_contents["bundle.json"], "Publication bundle JSON",
	)
	if not isinstance(bundle, dict):
		raise RuntimeError("Publication bundle JSON must be an object.")
	asset_contents = snapshot.read_declared_assets(declared_asset_paths(bundle))
	for name in (
		"evidence.json", "repository_roster.json", "daily_active_roster.json",
		"editorial_projection.json", "publication_surface.json", "post.md",
	):
		sealed_contents[name] = snapshot.read(name)
	evidence = scripts.canonical_json.load_stable_json(
		sealed_contents["evidence.json"], "Publication evidence JSON",
	)
	roster = scripts.canonical_json.load_stable_json(
		sealed_contents["repository_roster.json"], "Publication repository roster JSON",
	)
	active_roster = scripts.canonical_json.load_stable_json(
		sealed_contents["daily_active_roster.json"], "Publication daily active roster JSON",
	)
	projection = scripts.canonical_json.load_stable_json(
		sealed_contents["editorial_projection.json"], "Publication editorial projection JSON",
	)
	surface = scripts.canonical_json.load_stable_json(
		sealed_contents["publication_surface.json"], "Publication surface JSON",
	)
	post = sealed_contents["post.md"]
	if not all(isinstance(value, dict) for value in (bundle, evidence, roster, active_roster, projection, surface)):
		raise RuntimeError("Bundle JSON artifacts must be objects.")
	_require_keys(
		bundle,
		{
			"schema_version", "bundle_sha256", "best_artifact_id", "report_date", "timezone",
			"created_at", "generator", "contracts", "evidence", "repository_roster",
			"daily_active_roster",
			"editorial_projection", "publication_surface", "post", "assets",
			"maker_activation", "editorial_prompt_contract",
		},
		"Publication bundle",
	)
	if bundle.get("schema_version") != BUNDLE_SCHEMA_VERSION:
		raise RuntimeError("Unsupported publication bundle schema.")
	if bundle_sha256(bundle) != bundle.get("bundle_sha256"):
		raise RuntimeError("Publication bundle checksum does not match its manifest.")
	if snapshot.transfer_header is not None:
		if snapshot.transfer_header["bundle_sha256"] != bundle["bundle_sha256"]:
			raise RuntimeError("Publication bundle transfer checksum does not match its manifest.")
		if snapshot.transfer_header["report_date"] != bundle["report_date"]:
			raise RuntimeError("Publication bundle transfer report date does not match its manifest.")
	if not all(
		isinstance(bundle[key], dict)
		for key in ("post", "evidence", "repository_roster", "editorial_projection", "publication_surface")
	):
		raise RuntimeError("Bundle artifact manifests must be objects.")
	_validate_report_identity(bundle)
	# ASVS 2.2.1/2.2.3: bind the admitted post to one allowlisted artifact identity.
	_require_keys(bundle["post"], {"path", "sha256", "artifact_id"}, "Bundle post manifest")
	if bundle["post"]["path"] != "post.md":
		raise RuntimeError("Bundle post path must name post.md.")
	if not isinstance(bundle["best_artifact_id"], str) or ARTIFACT_ID_RE.fullmatch(
		bundle["best_artifact_id"]
	) is None:
		raise RuntimeError("Bundle best artifact identity is invalid.")
	if bundle["post"]["artifact_id"] != bundle["best_artifact_id"]:
		raise RuntimeError("Bundle selected post artifact identity does not match the best artifact.")
	if bundle.get("evidence", {}).get("path") != "evidence.json":
		raise RuntimeError("Bundle evidence path must name evidence.json.")
	if bundle["editorial_projection"].get("path") != "editorial_projection.json":
		raise RuntimeError("Bundle projection path must name editorial_projection.json.")
	if bundle["publication_surface"].get("path") != "publication_surface.json":
		raise RuntimeError("Bundle surface path must name publication_surface.json.")
	if hash_value(evidence) != bundle["evidence"].get("sha256"):
		raise RuntimeError("Bundle evidence hash does not match evidence.json.")
	if not _is_lower_hex(bundle["evidence"].get("sha256"), {64}):
		raise RuntimeError("Bundle evidence hash must be SHA-256.")
	if hash_value(projection) != bundle["editorial_projection"].get("sha256"):
		raise RuntimeError("Bundle projection hash does not match editorial_projection.json.")
	if not _is_lower_hex(bundle["editorial_projection"].get("sha256"), {64}):
		raise RuntimeError("Bundle projection hash must be SHA-256.")
	if hash_value(surface) != bundle["publication_surface"].get("sha256"):
		raise RuntimeError("Bundle surface hash does not match publication_surface.json.")
	if bundle["publication_surface"].get("surface_id") != surface.get("surface_id"):
		raise RuntimeError("Bundle surface identity does not match publication_surface.json.")
	if sha256_bytes(post) != bundle["post"].get("sha256"):
		raise RuntimeError("Bundle post hash does not match post.md.")
	if not _is_lower_hex(bundle["post"].get("sha256"), {64}):
		raise RuntimeError("Bundle post hash must be SHA-256.")
	items_by_id = validate_evidence(evidence, bundle)
	scripts.validate_repository_roster.validate_repository_roster(bundle, evidence, roster)
	# ASVS 1.5.2, 2.2.1, 2.2.3, and 11.4.3: independently validate
	# the allowlisted report-day provenance object and its SHA-256 binding.
	scripts.validate_repository_roster.validate_daily_active_roster(bundle, roster, active_roster)
	scripts.validate_editorial_projection.validate_projection(projection, evidence, bundle)
	surface = scripts.publication_surface.validate_surface(surface, evidence, projection, bundle)
	asset_contents = validate_assets(asset_contents, bundle, items_by_id, surface)
	sealed_contents.update(asset_contents)
	return bundle, evidence, projection, surface, post, sealed_contents


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
def _is_idempotent(
	root: str,
	bundle: dict,
	post: bytes,
	sealed_contents: dict[str, bytes],
) -> bool:
	"""Return whether the exact bundle is already the complete installed release."""
	record = _load_current_record(root, bundle["report_date"])
	if not record or record.get("bundle_sha256") != bundle["bundle_sha256"]:
		return False
	report_date = bundle["report_date"]
	release = os.path.join(root, "generated", "releases", report_date)
	archive = os.path.join(root, "data", "publication_bundles", report_date)
	post_path = os.path.join(root, "docs", "blog", "posts", f"{report_date}.md")
	if not os.path.isdir(release) or not os.path.isdir(archive) or not os.path.isfile(post_path):
		raise RuntimeError("Existing identical publication record is incomplete.")
	if not scripts.site_deployment.site_serves_publication(root, report_date):
		raise RuntimeError("Existing identical publication record is incomplete.")
	names = (
		"bundle.json", "evidence.json", "repository_roster.json", "daily_active_roster.json",
		"editorial_projection.json", "publication_surface.json", "post.md",
	)
	for name in names + tuple(asset["path"] for asset in bundle["assets"]):
		archived_path = os.path.join(archive, name)
		if not os.path.isfile(archived_path):
			raise RuntimeError("Existing identical publication archive is incomplete.")
		source_contents = sealed_contents[name]
		with open(archived_path, "rb") as handle:
			archived_contents = handle.read()
		if source_contents != archived_contents:
			raise RuntimeError("Existing identical publication archive has different content.")
	with open(post_path, "rb") as handle:
		installed_post = handle.read()
	if installed_post != post:
		raise RuntimeError("Existing identical publication record has different post content.")
	return True


#============================================
def _new_stage_root(root: str, report_date: str) -> str:
	"""Create and return one unique publisher-owned staging directory."""
	stage_parent = os.path.join(root, "generated", "staging")
	os.makedirs(stage_parent, exist_ok=True)
	stage_root = os.path.join(stage_parent, f"import-{report_date}-{uuid.uuid4().hex}")
	os.makedirs(stage_root)
	return stage_root


#============================================
def _commit_stage(root: str, stage_root: str, record: dict) -> None:
	"""Install one prepared stage through the durable transaction helper."""
	scripts.publication_transaction.commit_stage(root, stage_root, record)


#============================================
def import_publication_bundle(
	bundle_path: str,
	root: str = REPO_ROOT,
	build_function: object = strict_mkdocs_build,
	replace_existing: bool = False,
) -> dict:
	"""Validate, stage, strictly build, and atomically install one bundle.

	Args:
		bundle_path: Physical producer bundle directory.
		root: Physical publisher repository root.
		build_function: Strict staged-site build implementation.
		replace_existing: Whether to replace the current publication for this report date.

	Returns:
		A typed imported, idempotent, or replaced publisher result.

	Raises:
		RuntimeError: Bundle validation, replacement authorization, build, or commit fails.
	"""
	bundle, evidence, projection, surface, post, sealed_contents = validate_bundle(bundle_path)
	return _import_validated_bundle(
		bundle,
		evidence,
		projection,
		surface,
		post,
		sealed_contents,
		root,
		build_function,
		replace_existing,
	)


#============================================
def import_publication_snapshot(
	snapshot: scripts.bundle_snapshot.BundleSnapshot,
	root: str = REPO_ROOT,
	build_function: object = strict_mkdocs_build,
	replace_existing: bool = False,
) -> dict:
	"""Validate and install one already-sealed producer transfer snapshot."""
	bundle, evidence, projection, surface, post, sealed_contents = validate_snapshot(snapshot)
	return _import_validated_bundle(
		bundle,
		evidence,
		projection,
		surface,
		post,
		sealed_contents,
		root,
		build_function,
		replace_existing,
	)


#============================================
def _import_validated_bundle(
	bundle: dict,
	evidence: dict,
	projection: dict,
	surface: dict,
	post: bytes,
	sealed_contents: dict[str, bytes],
	root: str,
	build_function: object,
	replace_existing: bool,
) -> dict:
	"""Install one validated byte snapshot without reopening producer paths."""
	if type(replace_existing) is not bool:
		raise RuntimeError("Replace-existing state must be Boolean.")
	with scripts.publication_transaction.publisher_lock(root):
		scripts.publication_transaction.reconcile_interrupted_staging(root)
		if _is_idempotent(root, bundle, post, sealed_contents):
			return {
				"status": "idempotent",
				"bundle_sha256": bundle["bundle_sha256"],
				"report_date": bundle["report_date"],
			}
		current = _load_current_record(root, bundle["report_date"])
		if current:
			scripts.publication_record.validate_existing_publication_record(current)
			if not replace_existing:
				raise scripts.publication_import_protocol.ImportProtocolError(
					"publication_conflict", "preflight",
					"A different bundle cannot replace an already-published report date."
				)
		stage_root = _new_stage_root(root, bundle["report_date"])
		try:
			try:
				stage_root, record = scripts.publication_staging.prepare_stage(
					root,
					stage_root,
					bundle,
					evidence,
					projection,
					surface,
					post,
					sealed_contents,
					build_function,
					utc_now(),
				)
			except RuntimeError as error:
				raise scripts.publication_import_protocol.ImportProtocolError(
					"staged_build_failed", "stage", str(error),
				) from error
			try:
				_commit_stage(root, stage_root, record)
			except RuntimeError as error:
				raise scripts.publication_import_protocol.ImportProtocolError(
					"commit_failed", "commit", str(error),
				) from error
		finally:
			exception_type, _exception, _traceback = sys.exc_info()
			# Ordinary failures remove the uncommitted stage; non-Exception control
			# flow leaves it available for the transaction recovery contract.
			if (
				exception_type is None or issubclass(exception_type, Exception)
			) and stage_root and os.path.exists(stage_root):
				shutil.rmtree(stage_root)
		result = {
			"status": "replaced" if current else "imported",
			"bundle_sha256": bundle["bundle_sha256"],
			"report_date": bundle["report_date"],
		}
		return result


#============================================
def main() -> None:
	"""Run the publisher's sole generator-facing import command."""
	args = scripts.publication_import_cli.parse_args()
	try:
		if args.bundle_stdin:
			try:
				snapshot = scripts.bundle_snapshot.BundleSnapshot.from_stream(sys.stdin.buffer)
			except RuntimeError as error:
				raise scripts.publication_import_protocol.ImportProtocolError(
					"snapshot_rejected", "receive", str(error),
				) from error
			result = import_publication_snapshot(snapshot, replace_existing=args.replace_existing)
		else:
			result = import_publication_bundle(
				args.bundle_path,
				replace_existing=args.replace_existing,
			)
	except (RuntimeError, UnicodeDecodeError) as error:
		sys.stderr.buffer.write(scripts.publication_import_protocol.failure_envelope(error))
		raise SystemExit(1) from error
	print(scripts.publication_import_protocol.stable_success_text(result), end="")


if __name__ == "__main__":
	main()

#!/usr/bin/env python3
"""Build and atomically promote the current MkDocs presentation source."""

# Standard Library
import os
import re
import sys
import json
import uuid
import shutil
import hashlib
import datetime
import subprocess

# local repo modules
import scripts.publication_record
import scripts.render_publication_status


DEPLOYMENT_SCHEMA_VERSION = "vosslab.daily-blog.site-deployment.v1"
DEPLOYMENT_RECORD_FIELDS = frozenset(
	{
		"base_bundle_id",
		"built_at",
		"release_id",
		"schema_version",
		"source_identity",
	}
)
LOWER_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SITE_RELEASE_PREFIX = "site-"
SUPPORTED_PYTHON = (3, 13)


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


#============================================
def utc_now() -> str:
	"""Return a canonical whole-second UTC timestamp."""
	moment = datetime.datetime.now(datetime.UTC).replace(microsecond=0)
	text = moment.isoformat().replace("+00:00", "Z")
	return text


#============================================
def stable_json_text(value: object) -> str:
	"""Return deterministic pretty JSON with one trailing newline."""
	text = json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
	return text


#============================================
def _read_publication_records(root: str) -> list[dict]:
	"""Read every validated installed publication record newest first."""
	directory = os.path.join(root, "data", "publications")
	if not os.path.isdir(directory):
		return []
	records = []
	for name in sorted(os.listdir(directory), reverse=True):
		if not name.endswith(".json"):
			continue
		path = os.path.join(directory, name)
		if os.path.islink(path) or not os.path.isfile(path):
			raise RuntimeError(f"Publication record path is not a physical file: {path}")
		with open(path, "r", encoding="utf-8") as handle:
			record = scripts.publication_record.validate_publication_record(json.load(handle))
		expected_date = os.path.splitext(name)[0]
		if record["report_date"] != expected_date:
			raise RuntimeError("Publication record date does not match its path.")
		records.append(record)
	return records


#============================================
def _verify_imported_source(root: str, records: list[dict]) -> None:
	"""Reject drift in importer-owned posts and the derived status page."""
	for record in records:
		bundle_id = record["bundle_id"]
		report_date = record["report_date"]
		post_path = os.path.join(root, "docs", "blog", "posts", f"{report_date}.md")
		archive_path = os.path.join(
			root,
			"data",
			"publication_bundles",
			bundle_id,
			"post.md",
		)
		if not os.path.isfile(post_path) or not os.path.isfile(archive_path):
			raise RuntimeError("Imported post receipt is incomplete.")
		with open(post_path, "rb") as handle:
			post_bytes = handle.read()
		with open(archive_path, "rb") as handle:
			archive_bytes = handle.read()
		if post_bytes != archive_bytes:
			raise RuntimeError(f"Imported post has drifted from its bundle: {report_date}")
	status_path = os.path.join(root, "docs", "status.md")
	expected_status = scripts.render_publication_status.render_status(records)
	with open(status_path, "r", encoding="utf-8") as handle:
		installed_status = handle.read()
	if installed_status != expected_status:
		raise RuntimeError("Publication status has drifted from installed records.")


#============================================
def _reject_tree_symlinks(root: str) -> None:
	"""Require a physical MkDocs source tree before taking a snapshot."""
	for directory, names, files in os.walk(root):
		for name in names + files:
			path = os.path.join(directory, name)
			if os.path.islink(path):
				raise RuntimeError(f"MkDocs source tree contains a symlink: {path}")


#============================================
def _snapshot_source(root: str, stage_root: str) -> None:
	"""Copy one complete physical MkDocs source snapshot into staging."""
	docs_source = os.path.join(root, "docs")
	config_source = os.path.join(root, "mkdocs.yml")
	_reject_tree_symlinks(docs_source)
	if os.path.islink(config_source) or not os.path.isfile(config_source):
		raise RuntimeError("mkdocs.yml must be one physical file.")
	shutil.copytree(docs_source, os.path.join(stage_root, "docs"))
	shutil.copy2(config_source, os.path.join(stage_root, "mkdocs.yml"))


#============================================
def source_identity(stage_root: str) -> str:
	"""Hash the staged MkDocs configuration, paths, and file bytes."""
	paths = ["mkdocs.yml"]
	for directory, names, files in os.walk(os.path.join(stage_root, "docs")):
		names.sort()
		for name in sorted(files):
			path = os.path.join(directory, name)
			relative = os.path.relpath(path, stage_root).replace(os.sep, "/")
			paths.append(relative)
	hasher = hashlib.sha256()
	for relative in sorted(paths):
		path = os.path.join(stage_root, *relative.split("/"))
		with open(path, "rb") as handle:
			contents = handle.read()
		hasher.update(relative.encode("utf-8"))
		hasher.update(b"\0")
		hasher.update(hashlib.sha256(contents).digest())
	identity = hasher.hexdigest()
	return identity


#============================================
def strict_mkdocs_build(stage_root: str, site_dir: str, _root: str) -> None:
	"""Build the staged source with the active Python environment."""
	result = subprocess.run(
		[
			sys.executable,
			"-m",
			"mkdocs",
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
def require_supported_python(version_info: tuple[int, ...]) -> None:
	"""Require the repository's exact Python publication runtime."""
	if tuple(version_info[:2]) != SUPPORTED_PYTHON:
		required = ".".join(str(part) for part in SUPPORTED_PYTHON)
		raise RuntimeError(f"Site publication requires Python {required}.")


#============================================
def validate_deployment_record(record: object) -> dict:
	"""Validate one exact manual site-deployment receipt."""
	if not isinstance(record, dict):
		raise RuntimeError("Site deployment receipt must be one JSON object.")
	if record.get("schema_version") != DEPLOYMENT_SCHEMA_VERSION:
		raise RuntimeError("Unsupported site deployment receipt schema.")
	if set(record) != DEPLOYMENT_RECORD_FIELDS:
		raise RuntimeError("Site deployment receipt fields are unsupported.")
	source_identity_value = record["source_identity"]
	if (
		not isinstance(source_identity_value, str)
		or LOWER_SHA256_RE.fullmatch(source_identity_value) is None
	):
		raise RuntimeError("Site deployment source identity is invalid.")
	expected_release = f"{SITE_RELEASE_PREFIX}{source_identity_value}"
	if record["release_id"] != expected_release:
		raise RuntimeError("Site deployment release identity is inconsistent.")
	base_bundle_id = record["base_bundle_id"]
	if base_bundle_id != "" and (
		not isinstance(base_bundle_id, str)
		or LOWER_SHA256_RE.fullmatch(base_bundle_id) is None
	):
		raise RuntimeError("Site deployment base bundle identity is invalid.")
	built_at = record["built_at"]
	if not isinstance(built_at, str) or not built_at.endswith("Z"):
		raise RuntimeError("Site deployment timestamp is invalid.")
	moment = datetime.datetime.fromisoformat(built_at.replace("Z", "+00:00"))
	canonical = moment.astimezone(datetime.UTC).replace(microsecond=0)
	if moment.microsecond or canonical.isoformat().replace("+00:00", "Z") != built_at:
		raise RuntimeError("Site deployment timestamp is invalid.")
	return record


#============================================
def _read_deployment_record(release: str) -> dict:
	"""Read and validate the receipt carried by one site release."""
	path = os.path.join(release, ".deployment.json")
	if not os.path.isfile(path) or os.path.islink(path):
		raise RuntimeError("Site release deployment receipt is missing.")
	with open(path, "r", encoding="utf-8") as handle:
		record = validate_deployment_record(json.load(handle))
	return record


#============================================
def site_serves_bundle(root: str, bundle_id: str) -> bool:
	"""Return whether site serves the bundle directly or through a derived release."""
	site_link = os.path.join(root, "site")
	if not os.path.islink(site_link):
		return False
	expected_release = os.path.join(root, "generated", "releases", bundle_id)
	if os.path.realpath(site_link) == os.path.realpath(expected_release):
		return True
	target = os.path.realpath(site_link)
	release_root = os.path.realpath(os.path.join(root, "generated", "releases"))
	if os.path.commonpath((release_root, target)) != release_root:
		raise RuntimeError("Served site release escapes generated/releases.")
	release_name = os.path.basename(target)
	if not release_name.startswith(SITE_RELEASE_PREFIX):
		return False
	record = _read_deployment_record(target)
	if record["release_id"] != release_name:
		raise RuntimeError("Served site release path disagrees with its receipt.")
	if not os.path.isfile(os.path.join(target, "index.html")):
		raise RuntimeError("Served site release has no index.")
	serves_bundle = record["base_bundle_id"] == bundle_id
	return serves_bundle


#============================================
def _clear_stale_site_staging(root: str) -> str:
	"""Remove abandoned manual stages while the publisher lock is held."""
	stage_parent = os.path.join(root, "generated", "site-staging")
	os.makedirs(stage_parent, exist_ok=True)
	for name in os.listdir(stage_parent):
		path = os.path.join(stage_parent, name)
		if os.path.islink(path) or not os.path.isdir(path):
			os.unlink(path)
		else:
			shutil.rmtree(path)
	return stage_parent


#============================================
def _switch_site_pointer(root: str, release: str) -> None:
	"""Atomically point site at one complete immutable release."""
	site_link = os.path.join(root, "site")
	if os.path.lexists(site_link) and not os.path.islink(site_link):
		raise RuntimeError("Served site path must be a symlink.")
	next_link = os.path.join(root, f".site-next-publish-{uuid.uuid4().hex}")
	os.symlink(os.path.relpath(release, root), next_link)
	os.replace(next_link, site_link)


#============================================
def _promote_release(
	root: str,
	stage_site: str,
	source_identity_value: str,
	base_bundle_id: str,
) -> dict:
	"""Install or reuse one immutable presentation release and switch site."""
	release_id = f"{SITE_RELEASE_PREFIX}{source_identity_value}"
	release = os.path.join(root, "generated", "releases", release_id)
	record = {
		"schema_version": DEPLOYMENT_SCHEMA_VERSION,
		"base_bundle_id": base_bundle_id,
		"built_at": utc_now(),
		"release_id": release_id,
		"source_identity": source_identity_value,
	}
	status = "published"
	if os.path.lexists(release):
		if not os.path.isdir(release) or os.path.islink(release):
			raise RuntimeError("Immutable site release path is invalid.")
		installed_record = _read_deployment_record(release)
		if installed_record["source_identity"] != source_identity_value:
			raise RuntimeError("Immutable site release identity has different content.")
		if installed_record["base_bundle_id"] != base_bundle_id:
			raise RuntimeError("Immutable site release covers a different base bundle.")
		status = "idempotent"
	else:
		os.makedirs(os.path.dirname(release), exist_ok=True)
		with open(os.path.join(stage_site, ".deployment.json"), "w", encoding="utf-8") as handle:
			handle.write(stable_json_text(record))
		os.replace(stage_site, release)
	_switch_site_pointer(root, release)
	result = {
		"status": status,
		"release_id": release_id,
		"source_identity": source_identity_value,
		"base_bundle_id": base_bundle_id,
		"site": os.path.relpath(release, root),
	}
	return result


#============================================
def publish_site(root: str, build_function: object) -> dict:
	"""Snapshot, strictly build, and atomically promote the current presentation."""
	# Import here so publication_transaction can use site_serves_bundle without a cycle.
	import scripts.publication_transaction

	with scripts.publication_transaction.publisher_lock(root):
		scripts.publication_transaction.reconcile_interrupted_staging(root)
		records = _read_publication_records(root)
		_verify_imported_source(root, records)
		stage_parent = _clear_stale_site_staging(root)
		stage_root = os.path.join(stage_parent, f"publish-{uuid.uuid4().hex}")
		os.makedirs(stage_root)
		try:
			_snapshot_source(root, stage_root)
			source_identity_value = source_identity(stage_root)
			stage_site = os.path.join(stage_root, "site")
			build_function(stage_root, stage_site, root)
			if not os.path.isfile(os.path.join(stage_site, "index.html")):
				raise RuntimeError("Strict build did not produce a site index.")
			base_bundle_id = records[0]["bundle_id"] if records else ""
			result = _promote_release(
				root,
				stage_site,
				source_identity_value,
				base_bundle_id,
			)
		finally:
			if os.path.isdir(stage_root):
				shutil.rmtree(stage_root)
	return result


#============================================
def main() -> None:
	"""Publish current repository presentation source to the served site pointer."""
	require_supported_python(sys.version_info)
	result = publish_site(REPO_ROOT, strict_mkdocs_build)
	print(stable_json_text(result), end="")


if __name__ == "__main__":
	main()

"""Durable locking, commit ordering, and recovery for publisher imports."""

# Standard Library
import os
import json
import fcntl
import shutil
import hashlib
import contextlib
import collections.abc

# local repo modules
import scripts.atomic_paths
import scripts.site_deployment
import scripts.publication_record


#============================================
@contextlib.contextmanager
def publisher_lock(root: str) -> collections.abc.Iterator[None]:
	"""Hold the publisher-wide filesystem lock for one import transaction."""
	lock_directory = os.path.join(root, "generated")
	lock_path = os.path.join(lock_directory, "publisher.lock")
	os.makedirs(lock_directory, exist_ok=True)
	with open(lock_path, "a+", encoding="utf-8") as handle:
		fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
		try:
			yield
		finally:
			fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


#============================================
def _remove_path(path: str) -> None:
	"""Remove one file, link, or directory when present."""
	if not os.path.lexists(path):
		return
	if os.path.islink(path) or not os.path.isdir(path):
		os.unlink(path)
		return
	shutil.rmtree(path)


#============================================
def _record_path(root: str, report_date: str) -> str:
	"""Return the publication record path for one report date."""
	return os.path.join(root, "data", "publications", f"{report_date}.json")


#============================================
def _release_path(root: str, report_date: str) -> str:
	"""Return the stable built release path for one report date."""
	return os.path.join(root, "generated", "releases", report_date)


#============================================
def _archive_path(root: str, report_date: str) -> str:
	"""Return the stable validated bundle archive path for one report date."""
	return os.path.join(root, "data", "publication_bundles", report_date)


#============================================
def _site_points_to(root: str, release: str) -> bool:
	"""Return whether the physical served pointer resolves to the expected release."""
	site_link = os.path.join(root, "site")
	return os.path.islink(site_link) and os.path.realpath(site_link) == os.path.realpath(release)


#============================================
def _read_marker(stage_root: str) -> dict:
	"""Read one staged transaction marker."""
	marker_path = os.path.join(stage_root, "transaction.json")
	with open(marker_path, "r", encoding="utf-8") as handle:
		marker = json.load(handle)
	if not isinstance(marker, dict):
		raise RuntimeError("Publication transaction marker must be an object.")
	return marker


#============================================
def write_transaction_marker(stage_root: str, record: dict, expected: dict | None = None) -> None:
	"""Persist the intended commit before moving any installed paths."""
	marker = {"record": record}
	if expected is not None:
		marker["expected"] = expected
	marker_path = os.path.join(stage_root, "transaction.json")
	temporary = f"{marker_path}.tmp"
	with open(temporary, "w", encoding="utf-8") as handle:
		json.dump(marker, handle, ensure_ascii=True, indent=2, sort_keys=True)
		handle.write("\n")
	os.replace(temporary, marker_path)


#============================================
def _marker_record(marker: dict) -> dict:
	"""Return the required publication record from one marker."""
	if set(marker) not in ({"record"}, {"record", "expected"}):
		raise RuntimeError("Publication transaction marker fields are unsupported.")
	return scripts.publication_record.validate_publication_record(marker["record"])


#============================================
def _directory_sha256(path: str) -> str:
	"""Hash one physical directory tree for crash-recovery state detection."""
	if not os.path.isdir(path) or os.path.islink(path):
		raise RuntimeError("Publication transaction directory is unavailable.")
	hasher = hashlib.sha256()
	for current_root, directories, files in os.walk(path):
		directories.sort()
		for name in directories:
			child = os.path.join(current_root, name)
			if os.path.islink(child):
				raise RuntimeError("Publication transaction directories must be physical.")
			relative = os.path.relpath(child, path).replace(os.sep, "/")
			hasher.update(f"D:{relative}\n".encode("utf-8"))
		for name in sorted(files):
			child = os.path.join(current_root, name)
			if os.path.islink(child) or not os.path.isfile(child):
				raise RuntimeError("Publication transaction files must be physical.")
			relative = os.path.relpath(child, path).replace(os.sep, "/")
			hasher.update(f"F:{relative}\n".encode("utf-8"))
			with open(child, "rb") as handle:
				while chunk := handle.read(64 * 1024):
					hasher.update(chunk)
	digest = hasher.hexdigest()
	return digest


#============================================
def _transaction_expected(stage_root: str, record: dict) -> dict:
	"""Capture immutable staged identities before any stable path is exchanged."""
	expected = {
		"archive_bundle_sha256": record["bundle_sha256"],
		"docs_tree_sha256": _directory_sha256(os.path.join(stage_root, "docs")),
		"release_tree_sha256": _directory_sha256(os.path.join(stage_root, "site")),
	}
	return expected


#============================================
def _marker_expected(marker: dict) -> dict:
	"""Return exact staged identities used to recover an interrupted exchange."""
	expected = marker.get("expected")
	if not isinstance(expected, dict) or set(expected) != {
		"archive_bundle_sha256", "docs_tree_sha256", "release_tree_sha256"
	}:
		raise RuntimeError("Publication transaction recovery marker is incomplete.")
	for value in expected.values():
		if not isinstance(value, str) or len(value) != 64:
			raise RuntimeError("Publication transaction recovery marker is invalid.")
	return expected


#============================================
def _publication_is_coherent(root: str, record: dict) -> bool:
	"""Return whether crash-recovery outputs match one exact installed receipt."""
	report_date = record["report_date"]
	release = _release_path(root, report_date)
	archive = _archive_path(root, report_date)
	record_path = _record_path(root, report_date)
	post_path = os.path.join(root, "docs", "blog", "posts", f"{report_date}.md")
	if not os.path.isfile(record_path) or os.path.islink(record_path):
		return False
	with open(record_path, "r", encoding="utf-8") as handle:
		installed_record = json.load(handle)
	if installed_record != record:
		return False
	if not os.path.isdir(release) or not os.path.isfile(os.path.join(release, "index.html")):
		return False
	if not os.path.isdir(archive):
		return False
	if not all(
		os.path.isfile(os.path.join(archive, name))
		for name in (
			"bundle.json", "evidence.json", "repository_roster.json",
			"editorial_projection.json", "publication_surface.json", "post.md",
		)
	):
		return False
	if not os.path.isfile(post_path) or not scripts.site_deployment.site_serves_publication(
		root, report_date
	):
		return False
	with open(os.path.join(archive, "post.md"), "r", encoding="utf-8") as handle:
		archived_post = handle.read()
	with open(post_path, "r", encoding="utf-8") as handle:
		installed_post = handle.read()
	if archived_post != installed_post:
		return False
	return True


#============================================
def _cleanup_backups(stage_root: str) -> None:
	"""Remove transaction backup paths after commit completion."""
	for name in ("previous_site_target",):
		_remove_path(os.path.join(stage_root, name))


#============================================
def _archive_is_staged(path: str, expected: dict) -> bool:
	"""Return whether one archive directory still holds the staged new bundle."""
	manifest = os.path.join(path, "bundle.json")
	if not os.path.isfile(manifest):
		return False
	with open(manifest, "r", encoding="utf-8") as handle:
		bundle = json.load(handle)
	value = isinstance(bundle, dict) and bundle.get("bundle_sha256")
	return value == expected["archive_bundle_sha256"]


#============================================
def _restore_directory(stable: str, staged: str, staged_is_new: bool) -> None:
	"""Restore one path after an exchange without making an existing path disappear."""
	if os.path.lexists(staged):
		if staged_is_new:
			return
		scripts.atomic_paths.exchange_directories(stable, staged)
		return
	# A missing staged name means a first install completed before the process ended.
	_remove_path(stable)


#============================================
def _restore_site_link(root: str, stage_root: str) -> None:
	"""Restore the prior served link with one atomic file replacement."""
	site_link = os.path.join(root, "site")
	previous_target = os.path.join(stage_root, "previous_site_target")
	if not os.path.isfile(previous_target):
		return
	with open(previous_target, "r", encoding="utf-8") as handle:
		target = handle.read()
	if not target or "\n" in target:
		raise RuntimeError("Publication transaction previous site target is invalid.")
	temporary = os.path.join(root, f".site-rollback-{os.path.basename(stage_root)}")
	os.symlink(target, temporary)
	os.replace(temporary, site_link)


#============================================
def _rollback(root: str, stage_root: str, record: dict, expected: dict) -> None:
	"""Restore an interrupted exchange from staged identities and stable paths."""
	report_date = record["report_date"]
	release = _release_path(root, report_date)
	archive = _archive_path(root, report_date)
	docs_path = os.path.join(root, "docs")
	staged_release = os.path.join(stage_root, "site")
	staged_archive = os.path.join(stage_root, "publication_archive")
	staged_docs = os.path.join(stage_root, "docs")
	if os.path.lexists(staged_docs):
		docs_is_new = _directory_sha256(staged_docs) == expected["docs_tree_sha256"]
	else:
		docs_is_new = False
	_restore_directory(docs_path, staged_docs, docs_is_new)
	archive_is_new = _archive_is_staged(staged_archive, expected)
	_restore_directory(archive, staged_archive, archive_is_new)
	if os.path.lexists(staged_release):
		release_is_new = _directory_sha256(staged_release) == expected["release_tree_sha256"]
	else:
		release_is_new = False
	_restore_directory(release, staged_release, release_is_new)
	_restore_site_link(root, stage_root)


#============================================
def reconcile_interrupted_staging(root: str) -> None:
	"""Rollback interrupted staging left by a crashed publisher process."""
	stage_parent = os.path.join(root, "generated", "staging")
	if os.path.isdir(stage_parent):
		for name in sorted(os.listdir(stage_parent)):
			stage_root = os.path.join(stage_parent, name)
			if not os.path.isdir(stage_root) or os.path.islink(stage_root):
				_remove_path(stage_root)
				continue
			marker_path = os.path.join(stage_root, "transaction.json")
			if not os.path.isfile(marker_path):
				_remove_path(stage_root)
				continue
			marker = _read_marker(stage_root)
			record = _marker_record(marker)
			if _publication_is_coherent(root, record):
				_cleanup_backups(stage_root)
				_remove_path(stage_root)
				continue
			expected = _marker_expected(marker)
			_rollback(root, stage_root, record, expected)
			_remove_path(stage_root)
	for name in os.listdir(root) if os.path.isdir(root) else []:
		if name.startswith(".site-next-"):
			_remove_path(os.path.join(root, name))


#============================================
def commit_stage(root: str, stage_root: str, record: dict) -> None:
	"""Install the release and pointer before the publication record last."""
	report_date = record["report_date"]
	release = _release_path(root, report_date)
	archive = _archive_path(root, report_date)
	record_path = _record_path(root, report_date)
	docs_path = os.path.join(root, "docs")
	site_link = os.path.join(root, "site")
	os.makedirs(os.path.dirname(release), exist_ok=True)
	os.makedirs(os.path.dirname(archive), exist_ok=True)
	os.makedirs(os.path.dirname(record_path), exist_ok=True)
	next_link = None
	expected = _transaction_expected(stage_root, record)
	write_transaction_marker(stage_root, record, expected)
	try:
		if os.path.lexists(release):
			scripts.atomic_paths.exchange_directories(
				release, os.path.join(stage_root, "site")
			)
		else:
			os.replace(os.path.join(stage_root, "site"), release)
		if os.path.lexists(archive):
			scripts.atomic_paths.exchange_directories(
				archive, os.path.join(stage_root, "publication_archive")
			)
		else:
			os.replace(os.path.join(stage_root, "publication_archive"), archive)
		scripts.atomic_paths.exchange_directories(docs_path, os.path.join(stage_root, "docs"))
		if os.path.lexists(site_link):
			if not os.path.islink(site_link):
				raise RuntimeError("Published site pointer must be a symbolic link.")
			previous_target = os.readlink(site_link)
			with open(os.path.join(stage_root, "previous_site_target"), "w", encoding="utf-8") as handle:
				handle.write(previous_target)
		next_link = os.path.join(root, f".site-next-{os.path.basename(stage_root)}")
		os.symlink(os.path.relpath(release, root), next_link)
		os.replace(next_link, site_link)
		next_link = None
		next_record = os.path.join(stage_root, "publication.json")
		os.replace(next_record, record_path)
	except Exception:
		_rollback(root, stage_root, record, expected)
		raise
	finally:
		if next_link is not None:
			_remove_path(next_link)
	_cleanup_backups(stage_root)

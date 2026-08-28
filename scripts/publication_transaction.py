"""Durable locking, commit ordering, and recovery for publisher imports."""

# Standard Library
import contextlib
import fcntl
import json
import os
import shutil
from collections.abc import Iterator

# local repo modules
import scripts.publication_record
import scripts.site_deployment


#============================================
@contextlib.contextmanager
def publisher_lock(root: str) -> Iterator[None]:
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
def _release_path(root: str, bundle_id: str) -> str:
	"""Return one immutable release path."""
	return os.path.join(root, "generated", "releases", bundle_id)


#============================================
def _archive_path(root: str, bundle_id: str) -> str:
	"""Return one immutable bundle archive path."""
	return os.path.join(root, "data", "publication_bundles", bundle_id)


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
def write_transaction_marker(stage_root: str, record: dict) -> None:
	"""Persist the intended commit before moving any installed paths."""
	marker = {"record": record}
	marker_path = os.path.join(stage_root, "transaction.json")
	temporary = f"{marker_path}.tmp"
	with open(temporary, "w", encoding="utf-8") as handle:
		json.dump(marker, handle, ensure_ascii=True, indent=2, sort_keys=True)
		handle.write("\n")
	os.replace(temporary, marker_path)


#============================================
def _marker_record(marker: dict) -> dict:
	"""Return the required publication record from one marker."""
	if set(marker) != {"record"}:
		raise RuntimeError("Publication transaction marker fields are unsupported.")
	return scripts.publication_record.validate_publication_record(marker["record"])


#============================================
def _publication_is_coherent(root: str, record: dict) -> bool:
	"""Return whether crash-recovery outputs match one exact installed receipt."""
	bundle_id = record["bundle_id"]
	report_date = record["report_date"]
	release = _release_path(root, bundle_id)
	archive = _archive_path(root, bundle_id)
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
		for name in ("bundle.json", "evidence.json", "editorial_projection.json", "post.md")
	):
		return False
	if not os.path.isfile(post_path) or not scripts.site_deployment.site_serves_bundle(
		root, bundle_id
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
	for name in ("previous_docs", "previous_publication.json", "previous_site"):
		_remove_path(os.path.join(stage_root, name))


#============================================
def _rollback(
	root: str,
	stage_root: str,
	record: dict,
	release_installed: bool,
	archive_installed: bool,
	docs_installed: bool,	record_installed: bool,
	site_replaced: bool,
	site_moved: bool,
	previous_record_moved: bool,
) -> None:
	"""Restore every path moved by an interrupted or failed commit."""
	bundle_id = record["bundle_id"]
	report_date = record["report_date"]
	release = _release_path(root, bundle_id)
	archive = _archive_path(root, bundle_id)
	record_path = _record_path(root, report_date)
	docs_path = os.path.join(root, "docs")
	site_link = os.path.join(root, "site")
	previous_docs = os.path.join(stage_root, "previous_docs")
	previous_record = os.path.join(stage_root, "previous_publication.json")
	previous_site = os.path.join(stage_root, "previous_site")
	if record_installed and os.path.lexists(record_path):
		_remove_path(record_path)
	if previous_record_moved and os.path.lexists(previous_record):
		os.replace(previous_record, record_path)
	if site_replaced and os.path.lexists(site_link):
		_remove_path(site_link)
	if site_moved and os.path.lexists(previous_site):
		os.replace(previous_site, site_link)
	if docs_installed and os.path.lexists(docs_path):
		_remove_path(docs_path)
	if os.path.lexists(previous_docs):
		os.replace(previous_docs, docs_path)
	if archive_installed and os.path.lexists(archive):
		_remove_path(archive)
	if release_installed and os.path.lexists(release):
		_remove_path(release)


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
			release = _release_path(root, record["bundle_id"])
			archive = _archive_path(root, record["bundle_id"])
			record_path = _record_path(root, record["report_date"])
			docs_path = os.path.join(root, "docs")
			previous_docs = os.path.join(stage_root, "previous_docs")
			previous_record = os.path.join(stage_root, "previous_publication.json")
			previous_site = os.path.join(stage_root, "previous_site")
			record_installed = os.path.isfile(record_path)
			installed_record = None
			if record_installed:
				with open(record_path, "r", encoding="utf-8") as handle:
					installed_record = json.load(handle)
			record_installed = record_installed and installed_record == record
			_rollback(
				root,
				stage_root,
				record,
				os.path.lexists(release),
				os.path.lexists(archive),
				os.path.isdir(docs_path) and os.path.lexists(previous_docs),
				record_installed,
				_site_points_to(root, release),
				os.path.lexists(previous_site),
				os.path.lexists(previous_record),
			)
			_remove_path(stage_root)
	for name in os.listdir(root) if os.path.isdir(root) else []:
		if name.startswith(".site-next-"):
			_remove_path(os.path.join(root, name))


#============================================
def commit_stage(root: str, stage_root: str, record: dict) -> None:
	"""Install the release and pointer before the publication record last."""
	bundle_id = record["bundle_id"]
	report_date = record["report_date"]
	release = _release_path(root, bundle_id)
	archive = _archive_path(root, bundle_id)
	record_path = _record_path(root, report_date)
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
	site_replaced = False
	site_moved = False
	previous_record_moved = False
	next_link = None
	try:
		os.replace(os.path.join(stage_root, "site"), release)
		release_installed = True
		os.replace(os.path.join(stage_root, "publication_archive"), archive)
		archive_installed = True
		os.replace(docs_path, previous_docs)
		os.replace(os.path.join(stage_root, "docs"), docs_path)
		docs_installed = True
		if os.path.lexists(site_link):
			os.replace(site_link, previous_site)
			site_moved = True
		next_link = os.path.join(root, f".site-next-{os.path.basename(stage_root)}")
		os.symlink(os.path.relpath(release, root), next_link)
		os.replace(next_link, site_link)
		site_replaced = True
		next_link = None
		next_record = os.path.join(stage_root, "publication.json")
		if os.path.lexists(record_path):
			os.replace(record_path, previous_record)
			previous_record_moved = True
		os.replace(next_record, record_path)
		record_installed = True
	except Exception:
		_rollback(
			root,
			stage_root,
			record,
			release_installed,
			archive_installed,
			docs_installed,
			record_installed,
			site_replaced,
			site_moved,
			previous_record_moved,
		)
		raise
	finally:
		if next_link is not None:
			_remove_path(next_link)
	_cleanup_backups(stage_root)

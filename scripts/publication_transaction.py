"""Atomic source and rendered-site installation for producer publications."""

import collections.abc
import contextlib
import fcntl
import hashlib
import json
import os
import shutil

import scripts.atomic_paths
import scripts.site_deployment


@contextlib.contextmanager
def publisher_lock(root: str) -> collections.abc.Iterator[None]:
	"""Hold the renderer-wide filesystem lock for one import transaction."""
	lock_directory = os.path.join(root, "generated")
	os.makedirs(lock_directory, exist_ok=True)
	with open(os.path.join(lock_directory, "publisher.lock"), "a+", encoding="utf-8") as handle:
		fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
		try:
			yield
		finally:
			fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _remove_path(path: str) -> None:
	"""Remove one disposable file, link, or directory when present."""
	if not os.path.lexists(path):
		return
	if os.path.islink(path) or not os.path.isdir(path):
		os.unlink(path)
	else:
		shutil.rmtree(path)


def _release_path(root: str, report_date: str) -> str:
	"""Return the stable rendered release path for one report date."""
	return os.path.join(root, "generated", "releases", report_date)


def _validate_receipt(value: object) -> dict:
	"""Validate the small transaction-local delivery identity."""
	if not isinstance(value, dict) or set(value) != {
		"bundle_sha256", "post_sha256", "report_date"
	}:
		raise RuntimeError("Publication transaction receipt is invalid.")
	for name in ("bundle_sha256", "post_sha256"):
		field = value[name]
		if not isinstance(field, str) or len(field) != 64:
			raise RuntimeError("Publication transaction receipt is invalid.")
	report_date = value["report_date"]
	if not isinstance(report_date, str) or len(report_date) != 10:
		raise RuntimeError("Publication transaction receipt is invalid.")
	return value


def write_transaction_marker(stage_root: str, receipt: dict) -> None:
	"""Persist a disposable recovery marker inside the staging directory."""
	_validate_receipt(receipt)
	path = os.path.join(stage_root, "transaction.json")
	temporary = f"{path}.tmp"
	with open(temporary, "w", encoding="utf-8") as handle:
		json.dump({"receipt": receipt}, handle, ensure_ascii=True, sort_keys=True)
		handle.write("\n")
	os.replace(temporary, path)


def _read_receipt(stage_root: str) -> dict:
	"""Read one transaction-local recovery identity."""
	with open(os.path.join(stage_root, "transaction.json"), "r", encoding="utf-8") as handle:
		marker = json.load(handle)
	if not isinstance(marker, dict) or set(marker) != {"receipt"}:
		raise RuntimeError("Publication transaction marker is invalid.")
	return _validate_receipt(marker["receipt"])


def _post_matches(root: str, receipt: dict) -> bool:
	"""Return whether installed final Markdown matches the delivery receipt."""
	path = os.path.join(root, "docs", "blog", "posts", f"{receipt['report_date']}.md")
	if not os.path.isfile(path) or os.path.islink(path):
		return False
	with open(path, "rb") as handle:
		return hashlib.sha256(handle.read()).hexdigest() == receipt["post_sha256"]


def reconcile_interrupted_staging(root: str) -> None:
	"""Discard disposable import staging left by an interrupted process."""
	stage_parent = os.path.join(root, "generated", "staging")
	if os.path.isdir(stage_parent):
		for name in sorted(os.listdir(stage_parent)):
			if name.startswith("import-"):
				_remove_path(os.path.join(stage_parent, name))
	for name in os.listdir(root) if os.path.isdir(root) else []:
		if name.startswith(".site-next-"):
			_remove_path(os.path.join(root, name))


def commit_stage(root: str, stage_root: str, receipt: dict) -> None:
	"""Install Markdown/assets and rendered output without archiving bundle JSON."""
	receipt = _validate_receipt(receipt)
	if _read_receipt(stage_root) != receipt:
		raise RuntimeError("Publication transaction marker changed during staging.")
	report_date = receipt["report_date"]
	release = _release_path(root, report_date)
	docs_path = os.path.join(root, "docs")
	staged_docs = os.path.join(stage_root, "docs")
	staged_site = os.path.join(stage_root, "site")
	site_link = os.path.join(root, "site")
	os.makedirs(os.path.dirname(release), exist_ok=True)
	next_link = os.path.join(root, f".site-next-{os.path.basename(stage_root)}")
	release_existed = os.path.lexists(release)
	release_installed = False
	docs_installed = False
	previous_site_target = os.readlink(site_link) if os.path.islink(site_link) else None
	try:
		if release_existed:
			scripts.atomic_paths.exchange_directories(release, staged_site)
		else:
			os.replace(staged_site, release)
		release_installed = True
		scripts.atomic_paths.exchange_directories(docs_path, staged_docs)
		docs_installed = True
		os.symlink(os.path.relpath(release, root), next_link)
		os.replace(next_link, site_link)
		if not _post_matches(root, receipt):
			raise RuntimeError("Installed Markdown bytes differ from the producer delivery.")
		if not scripts.site_deployment.site_serves_publication(root, report_date):
			raise RuntimeError("Rendered release does not contain the delivered publication.")
	except BaseException:
		if previous_site_target is not None:
			rollback_link = f"{next_link}-rollback"
			if os.path.lexists(rollback_link):
				os.unlink(rollback_link)
			os.symlink(previous_site_target, rollback_link)
			os.replace(rollback_link, site_link)
		if docs_installed:
			scripts.atomic_paths.exchange_directories(docs_path, staged_docs)
		if release_installed:
			if release_existed:
				scripts.atomic_paths.exchange_directories(release, staged_site)
			else:
				os.replace(release, staged_site)
		raise
	finally:
		if os.path.lexists(next_link):
			os.unlink(next_link)

"""Build one publisher-owned publication stage from sealed bundle bytes."""

# Standard Library
import hashlib
import os
import pathlib
import shutil
import uuid

# local repo modules
import scripts.publication_transaction


#============================================
def _atomic_write_text(path: str, text: str) -> None:
	"""Atomically replace one UTF-8 text file."""
	parent = os.path.dirname(os.path.abspath(path))
	os.makedirs(parent, exist_ok=True)
	temporary = os.path.join(parent, f".{os.path.basename(path)}.{uuid.uuid4().hex}.tmp")
	with open(temporary, "w", encoding="utf-8") as handle:
		handle.write(text)
	os.replace(temporary, path)


#============================================
def _atomic_write_bytes(path: str, contents: bytes) -> None:
	"""Atomically place producer-supplied bytes without interpreting Markdown."""
	parent = os.path.dirname(os.path.abspath(path))
	os.makedirs(parent, exist_ok=True)
	temporary = os.path.join(parent, f".{os.path.basename(path)}.{uuid.uuid4().hex}.tmp")
	with open(temporary, "wb") as handle:
		handle.write(contents)
	os.replace(temporary, path)


#============================================
def _reject_tree_symlinks(root: str) -> None:
	"""Reject symlinks before staging a complete source tree."""
	for current_root, directories, files in os.walk(root):
		for name in directories + files:
			if os.path.islink(os.path.join(current_root, name)):
				raise RuntimeError(f"MkDocs source tree contains a symlink: {name}")


#============================================
def prepare_stage(
	root: str,
	stage_root: str,
	bundle: dict,
	evidence: dict,
	projection: dict,
	surface: dict,
	post: bytes,
	sealed_contents: dict[str, bytes],
	build_function: object,
	imported_at: str,
) -> tuple[str, dict]:
	"""Stage producer bytes and a strict MkDocs build without durable bundle metadata."""
	proposed_docs = os.path.join(stage_root, "docs")
	_reject_tree_symlinks(os.path.join(root, "docs"))
	shutil.copytree(os.path.join(root, "docs"), proposed_docs)
	shutil.copy2(os.path.join(root, "mkdocs.yml"), os.path.join(stage_root, "mkdocs.yml"))
	post_path = os.path.join(proposed_docs, "blog", "posts", f"{bundle['report_date']}.md")
	os.makedirs(os.path.dirname(post_path), exist_ok=True)
	_atomic_write_bytes(post_path, post)
	asset_directory = os.path.join(
		proposed_docs, "blog", "posts", bundle["report_date"]
	)
	if os.path.lexists(asset_directory):
		if os.path.islink(asset_directory) or not os.path.isdir(asset_directory):
			raise RuntimeError("Publication asset destination must be a physical directory.")
		shutil.rmtree(asset_directory)
	for asset in bundle["assets"]:
		name = pathlib.PurePosixPath(asset["path"]).name
		destination = os.path.join(
			proposed_docs,
			"blog",
			"posts",
			bundle["report_date"],
			name,
		)
		os.makedirs(os.path.dirname(destination), exist_ok=True)
		with open(destination, "wb") as handle:
			handle.write(sealed_contents[asset["path"]])
	receipt = {
		"bundle_sha256": bundle["bundle_sha256"],
		"post_sha256": hashlib.sha256(post).hexdigest(),
		"report_date": bundle["report_date"],
	}
	scripts.publication_transaction.write_transaction_marker(stage_root, receipt)
	site_dir = os.path.join(stage_root, "site")
	build_function(stage_root, site_dir, root)
	if not os.path.isfile(os.path.join(site_dir, "index.html")):
		raise RuntimeError("Strict build did not produce a site index.")
	return stage_root, receipt

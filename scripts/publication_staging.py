"""Build one publisher-owned publication stage from sealed bundle bytes."""

# Standard Library
import json
import os
import pathlib
import shutil
import uuid

# local repo modules
import scripts.publication_article_projection
import scripts.publication_record
import scripts.publication_transaction
import scripts.render_publication_status
import scripts.validate_daily_post
import scripts.publication_surface


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
def _reject_tree_symlinks(root: str) -> None:
	"""Reject symlinks before staging a complete source tree."""
	for current_root, directories, files in os.walk(root):
		for name in directories + files:
			if os.path.islink(os.path.join(current_root, name)):
				raise RuntimeError(f"MkDocs source tree contains a symlink: {name}")


#============================================
def _publication_record(
	bundle: dict, surface: dict, article_projection: str, imported_at: str,
) -> dict:
	"""Build the current publisher-owned record from one validated bundle."""
	report_date = bundle["report_date"]
	record = {
		"schema_version": scripts.publication_record.PUBLICATION_SCHEMA_VERSION,
		"report_date": report_date,
		"timezone": bundle["timezone"],
		"bundle_sha256": bundle["bundle_sha256"],
		"article_body_sha256": scripts.publication_article_projection.article_body_sha256(
			article_projection
		),
		"best_artifact_id": bundle["best_artifact_id"],
		"generator_run": bundle["generator"]["run_id"],
		"generator_revision": bundle["generator"]["revision"],
		"evidence_manifest": f"data/publication_bundles/{report_date}/evidence.json",
		"editorial_projection_manifest": (
			f"data/publication_bundles/{report_date}/editorial_projection.json"
		),
		"publication_surface_manifest": (
			f"data/publication_bundles/{report_date}/publication_surface.json"
		),
		"publication_surface_id": surface["surface_id"],
		"publication_surface_sha256": bundle["publication_surface"]["sha256"],
		"post_path": f"docs/blog/posts/{report_date}.md",
		"imported_at": imported_at,
	}
	return record


#============================================
def _copy_bundle_archive(
	archive_stage: str,
	bundle: dict,
	sealed_contents: dict[str, bytes],
) -> None:
	"""Stage every validated manifest artifact at its exact bundle-relative path."""
	os.makedirs(archive_stage)
	names = (
		"bundle.json", "evidence.json", "repository_roster.json",
		"editorial_projection.json", "publication_surface.json", "post.md",
	)
	for name in names + tuple(asset["path"] for asset in bundle["assets"]):
		destination = os.path.join(archive_stage, *pathlib.PurePosixPath(name).parts)
		os.makedirs(os.path.dirname(destination), exist_ok=True)
		if name in sealed_contents:
			with open(destination, "wb") as handle:
				handle.write(sealed_contents[name])
		else:
			raise RuntimeError(f"Validated artifact bytes are unavailable: {name}")


#============================================
def prepare_stage(
	root: str,
	stage_root: str,
	bundle: dict,
	evidence: dict,
	projection: dict,
	surface: dict,
	post: str,
	sealed_contents: dict[str, bytes],
	build_function: object,
	imported_at: str,
) -> tuple[str, dict]:
	"""Stage complete source, record, archive, validation, and strict build outputs."""
	proposed_docs = os.path.join(stage_root, "docs")
	_reject_tree_symlinks(os.path.join(root, "docs"))
	shutil.copytree(os.path.join(root, "docs"), proposed_docs)
	shutil.copy2(os.path.join(root, "mkdocs.yml"), os.path.join(stage_root, "mkdocs.yml"))
	post_path = os.path.join(proposed_docs, "blog", "posts", f"{bundle['report_date']}.md")
	os.makedirs(os.path.dirname(post_path), exist_ok=True)
	_atomic_write_text(post_path, post)
	# ASVS 2.3.1: the sealed surface is the single asset authority for staging.
	for image in surface["allowed_images"]:
		name = pathlib.PurePosixPath(image["asset_path"]).name
		destination = os.path.join(
			proposed_docs,
			"assets",
			"publications",
			bundle["report_date"],
			name,
		)
		os.makedirs(os.path.dirname(destination), exist_ok=True)
		with open(destination, "wb") as handle:
			handle.write(sealed_contents[image["asset_path"]])
	article_projection = scripts.publication_article_projection.source_article_projection(
		post,
		os.path.join(stage_root, "mkdocs.yml"),
	)
	record = _publication_record(bundle, surface, article_projection, imported_at)
	records = scripts.render_publication_status.read_publication_records(root, record)
	status = scripts.render_publication_status.render_status(records)
	_atomic_write_text(os.path.join(proposed_docs, "status.md"), status)
	post_issues = scripts.validate_daily_post.validate_post(
		post,
		evidence,
		projection,
		bundle,
		surface=surface,
		policy=scripts.validate_daily_post.V4_MAKER_POLICY,
	)
	if post_issues:
		raise RuntimeError("Staged article validation failed: " + "; ".join(post_issues))
	archive_stage = os.path.join(stage_root, "publication_archive")
	_copy_bundle_archive(archive_stage, bundle, sealed_contents)
	_atomic_write_text(
		os.path.join(stage_root, "publication.json"),
		json.dumps(record, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
	)
	scripts.publication_transaction.write_transaction_marker(stage_root, record)
	site_dir = os.path.join(stage_root, "site")
	build_function(stage_root, site_dir, root)
	if not os.path.isfile(os.path.join(site_dir, "index.html")):
		raise RuntimeError("Strict build did not produce a site index.")
	scripts.publication_article_projection.verify_built_article(
		site_dir,
		bundle["report_date"],
		article_projection,
		scripts.publication_surface.allowed_publish_paths(surface),
	)
	return stage_root, record

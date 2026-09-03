"""Immutable presentation-release and atomic site-pointer tests."""

# Standard Library
import os
import json
import pathlib

# PIP3 modules
import pytest

# local repo modules
import scripts.publication_record
import scripts.publication_article_projection
import scripts.render_publication_status
import scripts.site_deployment


REPORT_DATE = "2026-08-23"
BUNDLE_SHA256 = "a" * 64


#============================================
def _write_json(path: pathlib.Path, value: dict) -> None:
	"""Write one stable inline JSON test artifact."""
	path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


#============================================
def _initialize_source(root: pathlib.Path) -> None:
	"""Create minimal MkDocs source and one prior served release."""
	(root / "docs" / "blog" / "posts").mkdir(parents=True)
	(root / "docs" / "index.md").write_text("# Current source\n", encoding="utf-8")
	status = scripts.render_publication_status.render_status([])
	(root / "docs" / "status.md").write_text(status, encoding="utf-8")
	(root / "mkdocs.yml").write_text("site_name: Test\n", encoding="utf-8")
	old_release = root / "generated" / "releases" / "old"
	old_release.mkdir(parents=True)
	(old_release / "index.html").write_text("old release", encoding="utf-8")
	(root / "generated" / "staging").mkdir()
	(root / "site").symlink_to("generated/releases/old")


#============================================
def _fake_build(stage_root: str, site_dir: str, _root: str) -> None:
	"""Render deterministic test output from the staged source."""
	os.makedirs(os.path.join(site_dir, "status"))
	with open(os.path.join(stage_root, "docs", "index.md"), encoding="utf-8") as handle:
		index_source = handle.read()
	with open(os.path.join(site_dir, "index.html"), "w", encoding="utf-8") as handle:
		handle.write(index_source)
	with open(os.path.join(site_dir, "status", "index.html"), "w", encoding="utf-8") as handle:
		handle.write("status")
	post_path = os.path.join(stage_root, "docs", "blog", "posts", f"{REPORT_DATE}.md")
	if os.path.isfile(post_path):
		with open(post_path, encoding="utf-8") as handle:
			post = handle.read()
		rendered = scripts.publication_article_projection.render_staged_post_body(
			post,
			os.path.join(stage_root, "mkdocs.yml"),
		)
		article_dir = os.path.join(site_dir, "article")
		os.makedirs(article_dir)
		with open(os.path.join(article_dir, "index.html"), "w", encoding="utf-8") as handle:
			handle.write(
				f'<time datetime="{REPORT_DATE} 00:00:00+00:00"></time>'
				f'<article class="md-content__inner md-typeset">{rendered}</article>'
			)


#============================================
def _install_publication_record(root: pathlib.Path) -> dict:
	"""Install one complete publication receipt and matching source post."""
	post = (
		"---\ndate: 2026-08-23\nslug: imported\n---\n\n"
		"# Imported post\n\nGrounded retained material.\n"
	)
	post_path = root / "docs" / "blog" / "posts" / f"{REPORT_DATE}.md"
	post_path.write_text(post, encoding="utf-8")
	archive = root / "data" / "publication_bundles" / REPORT_DATE
	archive.mkdir(parents=True)
	(archive / "post.md").write_text(post, encoding="utf-8")
	record = {
		"schema_version": scripts.publication_record.PUBLICATION_SCHEMA_VERSION,
		"report_date": REPORT_DATE,
		"timezone": "America/Chicago",
		"bundle_sha256": BUNDLE_SHA256,
		"article_body_sha256": scripts.publication_article_projection.article_body_sha256(
			scripts.publication_article_projection.source_article_projection(
				post,
				str(root / "mkdocs.yml"),
			)
		),
		"best_artifact_id": "artifact-" + "c" * 24,
		"generator_run": "test-run",
		"generator_revision": "b" * 64,
		"evidence_manifest": f"data/publication_bundles/{REPORT_DATE}/evidence.json",
		"editorial_projection_manifest": (
			f"data/publication_bundles/{REPORT_DATE}/editorial_projection.json"
		),
		"publication_surface_manifest": (
			f"data/publication_bundles/{REPORT_DATE}/publication_surface.json"
		),
		"publication_surface_id": "d" * 64,
		"publication_surface_sha256": "e" * 64,
		"post_path": f"docs/blog/posts/{REPORT_DATE}.md",
		"imported_at": "2026-08-24T12:00:00Z",
	}
	record_dir = root / "data" / "publications"
	record_dir.mkdir(parents=True)
	_write_json(record_dir / f"{REPORT_DATE}.json", record)
	status = scripts.render_publication_status.render_status([record])
	(root / "docs" / "status.md").write_text(status, encoding="utf-8")
	return record


#============================================
def test_publish_site_installs_immutable_release_and_switches_pointer(
	tmp_path: pathlib.Path,
) -> None:
	_initialize_source(tmp_path)
	result = scripts.site_deployment.publish_site(str(tmp_path), _fake_build)
	release = pathlib.Path(os.path.realpath(tmp_path / "site"))
	assert result["status"] == "published"
	assert release.name.startswith("site-") and (release / "index.html").is_file()


#============================================
def test_publish_site_is_idempotent_for_unchanged_source(tmp_path: pathlib.Path) -> None:
	_initialize_source(tmp_path)
	first = scripts.site_deployment.publish_site(str(tmp_path), _fake_build)
	second = scripts.site_deployment.publish_site(str(tmp_path), _fake_build)
	assert second["status"] == "idempotent"
	assert second["release_id"] == first["release_id"]


#============================================
def test_publish_site_promotes_changed_source(tmp_path: pathlib.Path) -> None:
	_initialize_source(tmp_path)
	first = scripts.site_deployment.publish_site(str(tmp_path), _fake_build)
	(tmp_path / "docs" / "index.md").write_text("# Revised presentation\n", encoding="utf-8")
	second = scripts.site_deployment.publish_site(str(tmp_path), _fake_build)
	served_release = pathlib.Path(os.path.realpath(tmp_path / "site"))
	assert second["status"] == "published" and second["release_id"] != first["release_id"]
	assert served_release.name == second["release_id"]


#============================================
def test_site_deployment_requires_python_313() -> None:
	scripts.site_deployment.require_supported_python((3, 13, 5))
	with pytest.raises(RuntimeError, match="requires Python 3.13"):
		scripts.site_deployment.require_supported_python((3, 12, 13))
	with pytest.raises(RuntimeError, match="requires Python 3.13"):
		scripts.site_deployment.require_supported_python((3, 14, 0))


#============================================
def test_site_release_preserves_base_report_date(tmp_path: pathlib.Path) -> None:
	_initialize_source(tmp_path)
	record = _install_publication_record(tmp_path)
	legacy = {key: record[key] for key in scripts.publication_record.HISTORICAL_PUBLICATION_RECORD_FIELDS}
	legacy["schema_version"] = scripts.publication_record.HISTORICAL_PUBLICATION_SCHEMA_VERSION
	_write_json(tmp_path / "data" / "publications" / f"{REPORT_DATE}.json", legacy)
	scripts.site_deployment.publish_site(str(tmp_path), _fake_build)
	assert scripts.site_deployment.site_serves_publication(str(tmp_path), REPORT_DATE)
	assert not scripts.site_deployment.site_serves_publication(str(tmp_path), "2026-08-22")


#============================================
def test_publish_site_rejects_imported_post_drift(tmp_path: pathlib.Path) -> None:
	_initialize_source(tmp_path)
	_install_publication_record(tmp_path)
	post_path = tmp_path / "docs" / "blog" / "posts" / f"{REPORT_DATE}.md"
	post_path.write_text("# Edited outside importer\n", encoding="utf-8")

	with pytest.raises(RuntimeError, match="drifted from its bundle"):
		scripts.site_deployment.publish_site(str(tmp_path), _fake_build)


#============================================
def test_failed_build_preserves_served_pointer(tmp_path: pathlib.Path) -> None:
	_initialize_source(tmp_path)
	original_target = os.readlink(tmp_path / "site")

	def failed_build(_stage_root: str, _site_dir: str, _root: str) -> None:
		raise RuntimeError("synthetic build failure")

	with pytest.raises(RuntimeError, match="synthetic build failure"):
		scripts.site_deployment.publish_site(str(tmp_path), failed_build)

	assert os.readlink(tmp_path / "site") == original_target


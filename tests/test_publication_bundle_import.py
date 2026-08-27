"""Bundle validation, idempotency, supersession, and release-preservation tests."""

# Standard Library
import os
import json

# PIP3 modules
import pytest

# local repo modules
import scripts.import_publication_bundle


#============================================
def initialize_site(root) -> None:
	"""Create a minimal publisher-owned source and prior served release."""
	(root / "docs" / "blog" / "posts").mkdir(parents=True)
	(root / "docs" / "assets").mkdir()
	(root / "docs" / "index.md").write_text("# Existing site\n", encoding="utf-8")
	(root / "docs" / "status.md").write_text("# Existing status\n", encoding="utf-8")
	(root / "docs" / "blog" / "index.md").write_text("# Work log\n", encoding="utf-8")
	(root / "mkdocs.yml").write_text("site_name: Test\n", encoding="utf-8")
	(root / "data" / "publications").mkdir(parents=True)
	old_release = root / "generated" / "releases" / "old"
	old_release.mkdir(parents=True)
	(old_release / "index.html").write_text("old release", encoding="utf-8")
	(root / "generated" / "staging").mkdir()
	(root / "site").symlink_to("generated/releases/old")


#============================================
def make_bundle(root, run_id: str, quality: str = "provisional") -> str:
	"""Write one complete inline v1 bundle with no media assets."""
	bundle_dir = root / f"bundle-{run_id}"
	(bundle_dir / "assets").mkdir(parents=True)
	content = "No attributed commits were located for the selected report day."
	content_hash = scripts.import_publication_bundle.sha256_bytes(content.encode("utf-8"))
	item = {
		"evidence_id": "",
		"kind": "commit_metadata",
		"authority_level": "locator_provenance",
		"authority_rank": 100,
		"repository": "vosslab",
		"commit": "",
		"path": "",
		"blob_hash": "",
		"content": content,
		"content_hash": content_hash,
		"acquisition_source": "date-scoped cache activity locator",
		"truncated": False,
		"asset_path": "",
		"publish_path": "",
	}
	item["evidence_id"] = scripts.import_publication_bundle.evidence_item_identity(item)
	evidence = {
		"schema_version": "vosslab.daily-blog.evidence.v2",
		"report_date": "2026-08-23",
		"timezone": "America/Chicago",
		"complete": True,
		"budgets": {},
		"mirrors": [],
		"activity": [],
		"items": [item],
	}
	evidence["packet_id"] = scripts.import_publication_bundle.hash_value(evidence)
	post = (
		"---\n"
		+ "date: 2026-08-23\n"
		+ "slug: exact-evidence\n"
		+ f"publication_quality: {quality}\n"
		+ f"generator_run: {run_id}\n"
		+ "evidence_manifest: evidence.json\n"
		+ "---\n\n"
		+ "# Exact evidence preserves the day\n\n"
		+ f"I kept the account tied to exact objects. <!-- evidence: {item['evidence_id']} -->\n\n"
		+ "<!-- more -->\n\n"
		+ "## Publication state\n\n"
		+ f"I retained a bounded work log. <!-- evidence: {item['evidence_id']} -->\n"
	)
	winner = "A" if quality == "final" else "NONE"
	candidates = [
		{
			"candidate_id": f"candidate_{index}",
			"post_hash": (
				scripts.import_publication_bundle.sha256_bytes(post.encode("utf-8"))
				if quality == "final" and index == 1
				else scripts.import_publication_bundle.sha256_bytes(
					f"candidate {index}".encode("utf-8")
				)
			),
			"valid": quality == "final" and index == 1,
			"issues": [] if quality == "final" and index == 1 else ["not selected"],
		}
		for index in (1, 2)
	]
	bundle = {
		"schema_version": "vosslab.daily-blog.bundle.v1",
		"bundle_id": "",
		"report_date": "2026-08-23",
		"timezone": "America/Chicago",
		"publication_quality": quality,
		"created_at": "2026-08-24T08:00:00Z",
		"generator": {
			"run_id": run_id,
			"revision": "f" * 40,
			"version": "daily-blog-generator-v1",
		},
		"contracts": {
			"evidence_schema": "vosslab.daily-blog.evidence.v2",
			"prompt_version": "daily-blog-prompts-v2",
			"rubric_version": "daily-blog-rubric-v2",
		},
		"evidence": {
			"path": "evidence.json",
			"packet_id": evidence["packet_id"],
			"sha256": scripts.import_publication_bundle.hash_value(evidence),
		},
		"post": {
			"path": "post.md",
			"sha256": scripts.import_publication_bundle.sha256_bytes(post.encode("utf-8")),
		},
		"assets": [],
		"candidates": candidates,
		"referee": {
			"winner": winner,
			"reason": "The selected quality follows deterministic validation.",
			"evidence_quality": "medium",
			"confidence": 0.8,
			"anonymous_mapping": {"A": "candidate_1"} if quality == "final" else {},
		},
	}
	bundle["bundle_id"] = scripts.import_publication_bundle.bundle_identity(bundle)
	(bundle_dir / "evidence.json").write_text(
		json.dumps(evidence, indent=2, sort_keys=True) + "\n",
		encoding="utf-8",
	)
	(bundle_dir / "post.md").write_text(post, encoding="utf-8")
	(bundle_dir / "bundle.json").write_text(
		json.dumps(bundle, indent=2, sort_keys=True) + "\n",
		encoding="utf-8",
	)
	return str(bundle_dir)


#============================================
def fake_build(_stage_root: str, site_dir: str, _root: str) -> None:
	"""Create the minimal built release expected by the transaction."""
	os.makedirs(site_dir)
	with open(os.path.join(site_dir, "index.html"), "w", encoding="utf-8") as handle:
		handle.write("new release")


#============================================
def publication_snapshot(root) -> dict:
	"""Return the source, record, release, archive, and pointer transaction state."""
	post_path = root / "docs" / "blog" / "posts" / "2026-08-23.md"
	record_path = root / "data" / "publications" / "2026-08-23.json"
	archive_root = root / "data" / "publication_bundles"
	release_root = root / "generated" / "releases"
	value = {
		"status": (root / "docs" / "status.md").read_text(encoding="utf-8"),
		"post": post_path.read_text(encoding="utf-8") if post_path.is_file() else "",
		"record": record_path.read_text(encoding="utf-8") if record_path.is_file() else "",
		"site": os.readlink(root / "site"),
		"staging": tuple(sorted(path.name for path in (root / "generated" / "staging").iterdir())),
		"archives": (
			tuple(sorted(path.name for path in archive_root.iterdir()))
			if archive_root.is_dir()
			else ()
		),
		"releases": tuple(sorted(path.name for path in release_root.iterdir())),
	}
	return value


#============================================
def test_import_and_identical_reimport_are_successful(tmp_path) -> None:
	"""A complete import switches release once and accepts the same bundle idempotently."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-one")

	first = scripts.import_publication_bundle.import_publication_bundle(
		bundle_path, str(tmp_path), fake_build
	)
	second = scripts.import_publication_bundle.import_publication_bundle(
		bundle_path, str(tmp_path), fake_build
	)

	assert first["status"] == "imported"
	assert second["status"] == "idempotent"


#============================================
def test_failed_staged_build_preserves_source_and_served_release(tmp_path) -> None:
	"""Build failure leaves both source status and the last-good site pointer unchanged."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-failure")
	original = publication_snapshot(tmp_path)

	def failed_build(_stage_root: str, _site_dir: str, _root: str) -> None:
		raise RuntimeError("synthetic strict build failure")

	with pytest.raises(RuntimeError, match="synthetic strict build failure"):
		scripts.import_publication_bundle.import_publication_bundle(
			bundle_path, str(tmp_path), failed_build
		)

	assert publication_snapshot(tmp_path) == original


#============================================
def test_final_bundle_supersedes_provisional_for_same_date(tmp_path) -> None:
	"""Quality precedence allows the planned provisional-to-final transition."""
	initialize_site(tmp_path)
	provisional = make_bundle(tmp_path, "run-provisional")
	final = make_bundle(tmp_path, "run-final", quality="final")

	scripts.import_publication_bundle.import_publication_bundle(
		provisional, str(tmp_path), fake_build
	)
	result = scripts.import_publication_bundle.import_publication_bundle(
		final, str(tmp_path), fake_build
	)

	assert result["publication_quality"] == "final"


#============================================
def test_provisional_bundle_cannot_replace_final(tmp_path) -> None:
	"""Quality precedence preserves an already final date."""
	initialize_site(tmp_path)
	final = make_bundle(tmp_path, "run-final", quality="final")
	provisional = make_bundle(tmp_path, "run-later-provisional")
	scripts.import_publication_bundle.import_publication_bundle(
		final, str(tmp_path), fake_build
	)

	with pytest.raises(RuntimeError, match="cannot supersede"):
		scripts.import_publication_bundle.import_publication_bundle(
			provisional, str(tmp_path), fake_build
		)


#============================================
def test_different_final_bundle_cannot_replace_final(tmp_path) -> None:
	"""A final publication remains stable across a later conflicting final bundle."""
	initialize_site(tmp_path)
	first = make_bundle(tmp_path, "run-first-final", quality="final")
	second = make_bundle(tmp_path, "run-second-final", quality="final")
	scripts.import_publication_bundle.import_publication_bundle(
		first, str(tmp_path), fake_build
	)

	with pytest.raises(RuntimeError, match="existing final"):
		scripts.import_publication_bundle.import_publication_bundle(
			second, str(tmp_path), fake_build
		)


#============================================
def test_incomplete_editorial_contract_is_rejected(tmp_path) -> None:
	"""The importer rejects a rehashed bundle with missing candidate summaries."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-invalid-contract")
	manifest_path = os.path.join(bundle_path, "bundle.json")
	with open(manifest_path, "r", encoding="utf-8") as handle:
		manifest = json.load(handle)
	manifest["candidates"] = []
	manifest["bundle_id"] = scripts.import_publication_bundle.bundle_identity(manifest)
	with open(manifest_path, "w", encoding="utf-8") as handle:
		json.dump(manifest, handle, indent=2, sort_keys=True)
		handle.write("\n")

	with pytest.raises(RuntimeError, match="exactly two"):
			scripts.import_publication_bundle.import_publication_bundle(
				bundle_path, str(tmp_path), fake_build
			)


#============================================
def test_install_failure_restores_source_record_release_and_pointer(tmp_path, monkeypatch) -> None:
	"""A failure after moving prior state rolls the complete publication transaction back."""
	initialize_site(tmp_path)
	first = make_bundle(tmp_path, "run-installed")
	second = make_bundle(tmp_path, "run-install-failure")
	scripts.import_publication_bundle.import_publication_bundle(
		first, str(tmp_path), fake_build
	)
	original = publication_snapshot(tmp_path)
	real_replace = scripts.import_publication_bundle.os.replace

	def fail_docs_install(source: str, destination: str) -> None:
		if os.path.basename(source) == "docs" and destination == str(tmp_path / "docs"):
			raise RuntimeError("synthetic source install failure")
		real_replace(source, destination)

	monkeypatch.setattr(scripts.import_publication_bundle.os, "replace", fail_docs_install)
	with pytest.raises(RuntimeError, match="synthetic source install failure"):
		scripts.import_publication_bundle.import_publication_bundle(
			second, str(tmp_path), fake_build
		)

	assert publication_snapshot(tmp_path) == original


#============================================
def test_final_post_must_match_referee_selected_valid_candidate(tmp_path) -> None:
	"""A rehashed manifest cannot redirect the referee label to another candidate."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-invalid-winner", quality="final")
	manifest_path = os.path.join(bundle_path, "bundle.json")
	with open(manifest_path, "r", encoding="utf-8") as handle:
		manifest = json.load(handle)
	manifest["referee"]["anonymous_mapping"] = {"A": "candidate_2"}
	manifest["bundle_id"] = scripts.import_publication_bundle.bundle_identity(manifest)
	with open(manifest_path, "w", encoding="utf-8") as handle:
		json.dump(manifest, handle, indent=2, sort_keys=True)
		handle.write("\n")

	with pytest.raises(RuntimeError, match="valid candidate"):
		scripts.import_publication_bundle.import_publication_bundle(
			bundle_path, str(tmp_path), fake_build
		)


#============================================
def test_post_hash_tampering_is_rejected_before_staging(tmp_path) -> None:
	"""Bundle content changes remain ineligible when the manifest hash is unchanged."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-tampered")
	with open(os.path.join(bundle_path, "post.md"), "a", encoding="utf-8") as handle:
		handle.write("tampered\n")

	with pytest.raises(RuntimeError, match="post hash"):
		scripts.import_publication_bundle.import_publication_bundle(
			bundle_path, str(tmp_path), fake_build
		)


#============================================
def test_unknown_bundle_schema_is_rejected(tmp_path) -> None:
	"""Schema dispatch rejects a rehashed manifest from an unsupported contract generation."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-unknown-schema")
	manifest_path = os.path.join(bundle_path, "bundle.json")
	with open(manifest_path, "r", encoding="utf-8") as handle:
		manifest = json.load(handle)
	manifest["schema_version"] = "vosslab.daily-blog.bundle.v2"
	manifest["bundle_id"] = scripts.import_publication_bundle.bundle_identity(manifest)
	with open(manifest_path, "w", encoding="utf-8") as handle:
		json.dump(manifest, handle, indent=2, sort_keys=True)

	with pytest.raises(RuntimeError, match="schema"):
		scripts.import_publication_bundle.import_publication_bundle(
			bundle_path, str(tmp_path), fake_build
		)


#============================================
def test_asset_path_must_remain_inside_bundle(tmp_path) -> None:
	"""A rehashed asset manifest cannot name a path outside the physical bundle."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-asset-path")
	manifest_path = os.path.join(bundle_path, "bundle.json")
	with open(manifest_path, "r", encoding="utf-8") as handle:
		manifest = json.load(handle)
	manifest["assets"] = [
		{
			"path": "../escape.png",
			"sha256": "a" * 64,
			"blob_hash": "b" * 40,
			"evidence_id": "ev-outside",
			"publish_path": "../../assets/publications/2026-08-23/escape.png",
		}
	]
	manifest["bundle_id"] = scripts.import_publication_bundle.bundle_identity(manifest)
	with open(manifest_path, "w", encoding="utf-8") as handle:
		json.dump(manifest, handle, indent=2, sort_keys=True)

	with pytest.raises(RuntimeError, match="asset path"):
		scripts.import_publication_bundle.import_publication_bundle(
			bundle_path, str(tmp_path), fake_build
		)

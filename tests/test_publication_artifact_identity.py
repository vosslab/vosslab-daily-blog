"""Selected-artifact bundle admission tests."""

# Standard Library
import json
import pathlib

# PIP3 modules
import pytest

# local repo modules
import scripts.import_publication_bundle
import scripts.publication_record
import scripts.publication_surface
import test_publication_bundle_import


#============================================
def test_bundle_rejects_noncanonical_best_artifact_identity(tmp_path: pathlib.Path) -> None:
	"""A self-consistent bundle still requires the canonical artifact identity format."""
	test_publication_bundle_import.initialize_site(tmp_path)
	bundle_path = test_publication_bundle_import.make_bundle(tmp_path, "run-artifact-format")
	bundle_file = pathlib.Path(bundle_path) / "bundle.json"
	bundle = json.loads(bundle_file.read_text(encoding="utf-8"))
	bundle["best_artifact_id"] = "artifact-not-hex-identity"
	bundle["post"]["artifact_id"] = bundle["best_artifact_id"]
	bundle["bundle_sha256"] = scripts.import_publication_bundle.bundle_sha256(bundle)
	test_publication_bundle_import.write_json(bundle_file, bundle)

	with pytest.raises(RuntimeError, match="best artifact identity"):
		scripts.import_publication_bundle.import_publication_bundle(
			bundle_path, str(tmp_path), test_publication_bundle_import.fake_build
		)


#============================================
def test_publication_v6_record_rejects_invalid_best_artifact_identity(
	tmp_path: pathlib.Path,
) -> None:
	"""The committed v6 receipt admits only a valid selected artifact identity."""
	test_publication_bundle_import.initialize_site(tmp_path)
	bundle_path = test_publication_bundle_import.make_bundle(tmp_path, "run-record-artifact")
	scripts.import_publication_bundle.import_publication_bundle(
		bundle_path, str(tmp_path), test_publication_bundle_import.fake_build
	)
	record_path = tmp_path / "data" / "publications" / f"{test_publication_bundle_import.REPORT_DATE}.json"
	record = json.loads(record_path.read_text(encoding="utf-8"))

	assert scripts.publication_record.validate_publication_record(record) == record
	record["best_artifact_id"] = "artifact-not-hex-identity"
	with pytest.raises(RuntimeError, match="best artifact"):
		scripts.publication_record.validate_publication_record(record)


#============================================
@pytest.mark.parametrize("asset_path", ("assets//proof.png", "assets\\proof.png", "assets/proof\x00.png"))
def test_bundle_rejects_noncanonical_direct_asset_path(
	tmp_path: pathlib.Path,
	asset_path: str,
) -> None:
	"""Manifest and survivor surface share one direct asset-path grammar."""
	test_publication_bundle_import.initialize_site(tmp_path)
	bundle_path = test_publication_bundle_import.make_bundle(tmp_path, "run-direct-asset-path")
	bundle_file = pathlib.Path(bundle_path) / "bundle.json"
	bundle = json.loads(bundle_file.read_text(encoding="utf-8"))
	bundle["assets"][0]["path"] = asset_path
	bundle["bundle_sha256"] = scripts.import_publication_bundle.bundle_sha256(bundle)
	test_publication_bundle_import.write_json(bundle_file, bundle)

	with pytest.raises(RuntimeError, match="Bundle asset path"):
		scripts.import_publication_bundle.import_publication_bundle(
			bundle_path, str(tmp_path), test_publication_bundle_import.fake_build
		)


#============================================
def test_stage_implementation_fault_remains_a_pipeline_fault(
	tmp_path: pathlib.Path,
) -> None:
	"""Only expected publication-domain failures receive import classifications."""
	test_publication_bundle_import.initialize_site(tmp_path)
	bundle_path = test_publication_bundle_import.make_bundle(tmp_path, "run-stage-implementation-fault")

	def broken_build(_stage_root: str, _site_dir: str, _root: str) -> None:
		raise AssertionError("implementation invariant failed")

	with pytest.raises(AssertionError, match="implementation invariant"):
		scripts.import_publication_bundle.import_publication_bundle(
			bundle_path, str(tmp_path), broken_build
		)

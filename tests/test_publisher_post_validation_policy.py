"""Publisher-local admission tests for versioned post-validation policies."""

# Standard Library
import pathlib

# PIP3 modules
import pytest

# local repo modules
import scripts.import_publication_bundle
import scripts.maker_activation
import scripts.publication_source_safety
import scripts.publication_transaction
import scripts.validate_daily_post


#============================================
def report_identity_bundle(policy: scripts.validate_daily_post.PostValidationPolicy) -> dict:
	"""Return the smallest bundle object that reaches importer contract admission."""
	receipt = scripts.maker_activation.load_maker_activation()
	return {
		"report_date": "2026-08-26",
		"timezone": "America/Chicago",
		"created_at": "2026-08-26T12:00:00Z",
		"generator": {
			"run_id": "policy-test",
			"revision": "a" * 64,
			"version": "daily-blog-generator-v2",
		},
		"contracts": {
			"evidence_schema": "vosslab.daily-blog.evidence.v4",
			"editorial_projection_schema": "vosslab.daily-blog.editorial-projection.v2",
			"prompt_version": policy.prompt_version,
			"rubric_version": policy.rubric_version,
			"candidate_validation": {
				"name": policy.name,
				"version": policy.version,
				"sha256": policy.digest,
			},
			"publication_source_safety": scripts.publication_source_safety.policy_identity(),
		},
		"maker_activation": {
			"activation_id": receipt["activation_id"],
			"editorial_prompt_contract_sha256": receipt["editorial_prompt_contract_sha256"],
		},
		"editorial_prompt_contract": receipt["editorial_prompt_contract"],
	}


#============================================
def test_import_admission_accepts_only_the_activated_v4_maker_policy() -> None:
	"""The importer admits the exact maker policy sealed by its receipt."""
	bundle = report_identity_bundle(scripts.validate_daily_post.V4_MAKER_POLICY)

	scripts.import_publication_bundle._validate_report_identity(bundle)


#============================================
def test_import_admission_requires_the_complete_maker_policy_tuple() -> None:
	"""A missing policy identity cannot be inferred from maker prompt labels."""
	bundle = report_identity_bundle(scripts.validate_daily_post.V4_MAKER_POLICY)
	del bundle["contracts"]["candidate_validation"]

	with pytest.raises(RuntimeError, match="missing required fields"):
		scripts.import_publication_bundle._validate_report_identity(bundle)


#============================================
def test_import_admission_rejects_v3_historical_policy() -> None:
	"""The historical policy cannot enter the activated maker boundary."""
	bundle = report_identity_bundle(scripts.validate_daily_post.V3_HISTORICAL_POLICY)

	with pytest.raises(RuntimeError, match="contract versions are unsupported"):
		scripts.import_publication_bundle._validate_report_identity(bundle)


#============================================
def test_import_admission_rejects_an_altered_activation_receipt_identity() -> None:
	"""A self-consistent policy cannot substitute a different activation receipt."""
	bundle = report_identity_bundle(scripts.validate_daily_post.V4_MAKER_POLICY)
	bundle["maker_activation"]["activation_id"] = "daily-blog-maker-activation-" + "0" * 64

	with pytest.raises(RuntimeError, match="maker activation"):
		scripts.import_publication_bundle._validate_report_identity(bundle)


#============================================
def test_maker_activation_loader_rejects_missing_or_altered_receipt(
	tmp_path: pathlib.Path,
) -> None:
	"""The publisher receipt is required and pinned to its exact accepted bytes."""
	with pytest.raises(RuntimeError, match="unavailable or malformed"):
		scripts.maker_activation.load_maker_activation(str(tmp_path))
	(tmp_path / scripts.maker_activation.ACTIVATION_FILENAME).write_text("{}\n", encoding="utf-8")
	with pytest.raises(RuntimeError, match="integrity"):
		scripts.maker_activation.load_maker_activation(str(tmp_path))


#============================================
def test_skipped_mirror_allows_only_the_explicit_no_refresh_timestamp() -> None:
	"""Fixture-owned read-only mirrors retain their distinct provenance state."""
	mirror = {
		"repository": "vosslab/alpha",
		"repository_url": "https://github.com/vosslab/alpha",
		"clone_url": "https://github.com/vosslab/alpha.git",
		"created_at": "2020-01-01T00:00:00Z",
		"is_fork": False,
		"roster_id": "a" * 64,
		"cache_path": "/cache/vosslab/alpha",
		"refresh_result": "skipped",
		"refresh_error": "",
		"default_revision": "b" * 40,
		"object_available": True,
		"ref_fingerprint": "c" * 64,
		"refreshed_at": "",
	}
	evidence = {"mirrors": [mirror], "activity": []}

	scripts.import_publication_bundle._validate_provenance_records(evidence)
	mirror["refresh_result"] = "refreshed"

	with pytest.raises(RuntimeError, match="refresh time"):
		scripts.import_publication_bundle._validate_provenance_records(evidence)


#============================================
def test_invalid_bundle_never_reaches_publisher_lock_or_reconciliation(
	tmp_path: pathlib.Path,
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""Admission failure leaves an otherwise empty publisher root untouched."""
	bundle_path = tmp_path / "bundle"
	publisher_root = tmp_path / "publisher"
	bundle_path.mkdir()

	def reject_bundle(_path: str) -> tuple[dict, dict, dict, str]:
		raise RuntimeError("invalid activation")

	def reject_reconciliation(_root: str) -> None:
		raise AssertionError("invalid bundle reached reconciliation")

	monkeypatch.setattr(scripts.import_publication_bundle, "validate_bundle", reject_bundle)
	monkeypatch.setattr(
		scripts.publication_transaction,
		"reconcile_interrupted_staging",
		reject_reconciliation,
	)
	with pytest.raises(RuntimeError, match="invalid activation"):
		scripts.import_publication_bundle.import_publication_bundle(
			str(bundle_path), str(publisher_root)
		)

	assert not publisher_root.exists()


#============================================
@pytest.mark.parametrize("version", ("v1", "v2"))
def test_import_admission_rejects_superseded_policy_versions(version: str) -> None:
	"""Old policy digests cannot enter through otherwise familiar v3 labels."""
	bundle = report_identity_bundle(scripts.validate_daily_post.V4_MAKER_POLICY)
	bundle["contracts"]["candidate_validation"]["version"] = version

	with pytest.raises(RuntimeError, match="contract versions are unsupported"):
		scripts.import_publication_bundle._validate_report_identity(bundle)

"""Publisher-local admission tests for versioned post-validation policies."""

# PIP3 modules
import pytest

# local repo modules
import scripts.import_publication_bundle
import scripts.validate_daily_post


#============================================
def report_identity_bundle(policy: scripts.validate_daily_post.PostValidationPolicy) -> dict:
	"""Return the smallest bundle object that reaches importer contract admission."""
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
			"evidence_schema": "vosslab.daily-blog.evidence.v3",
			"editorial_projection_schema": "vosslab.daily-blog.editorial-projection.v1",
			"prompt_version": policy.prompt_version,
			"rubric_version": policy.rubric_version,
			"candidate_validation": {
				"name": policy.name,
				"version": policy.version,
				"sha256": policy.digest,
			},
		},
	}


#============================================
def test_import_admission_rejects_registered_v4_before_activation() -> None:
	"""The importer remains v3-only while direct v4 validation is exercised."""
	bundle = report_identity_bundle(scripts.validate_daily_post.V4_MAKER_POLICY)

	with pytest.raises(RuntimeError, match="contract versions are unsupported"):
		scripts.import_publication_bundle._validate_report_identity(bundle)


#============================================
def test_import_admission_requires_the_complete_v3_policy_tuple() -> None:
	"""A missing policy identity cannot be inferred from v3 prompt and rubric labels."""
	bundle = report_identity_bundle(scripts.validate_daily_post.V3_HISTORICAL_POLICY)
	del bundle["contracts"]["candidate_validation"]

	with pytest.raises(RuntimeError, match="missing required fields"):
		scripts.import_publication_bundle._validate_report_identity(bundle)

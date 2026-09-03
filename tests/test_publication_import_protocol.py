"""Offline tests for the producer-facing importer protocol boundary."""

# Standard Library
import json
import pathlib

# Third-Party
import pytest

# local repo modules
import scripts.import_publication_bundle
import scripts.publication_import_protocol
import scripts.bundle_snapshot
import test_publication_bundle_import


def test_failure_envelope_is_text_free_bounded_and_allowlisted() -> None:
	"""Automated failure output never carries local diagnostics to the producer."""
	error = scripts.publication_import_protocol.ImportProtocolError(
		"publication_conflict", "preflight", "/private/path 2026-08-28 secret post",
	)
	contents = scripts.publication_import_protocol.failure_envelope(error)
	assert len(contents) <= scripts.publication_import_protocol.MAX_FAILURE_BYTES
	assert b"private" not in contents
	assert json.loads(contents) == {
		"category": "publication_conflict",
		"phase": "preflight",
		"schema_version": "vosslab.daily-blog.import-failure.v1",
	}
	assert json.loads(
		scripts.publication_import_protocol.failure_envelope(RuntimeError("internal"))
	)["category"] == "publisher_implementation_defect"


def test_failure_envelope_uses_the_canonical_success_json_bytes() -> None:
	"""Failure bytes use the exact strict formatter accepted by the producer."""
	error = scripts.publication_import_protocol.ImportProtocolError(
		"publication_conflict", "preflight", "local diagnostic",
	)
	contents = scripts.publication_import_protocol.failure_envelope(error)
	expected = (
		b"{\n"
		b'  "category": "publication_conflict",\n'
		b'  "phase": "preflight",\n'
		b'  "schema_version": "vosslab.daily-blog.import-failure.v1"\n'
		b"}\n"
	)
	assert contents == expected


@pytest.mark.parametrize(
	("current", "authorized", "expected_status", "raises"),
	(
		(None, False, "imported", False),
		(None, True, "imported", False),
		({"bundle_sha256": "other"}, False, None, True),
		({"bundle_sha256": "other"}, True, "replaced", False),
	),
)
def test_replacement_authorizes_only_occupied_date_transition(
	monkeypatch: pytest.MonkeyPatch,
	tmp_path: pathlib.Path,
	current: dict | None,
	authorized: bool,
	expected_status: str | None,
	raises: bool,
) -> None:
	"""The flag permits only a different existing publication to be replaced."""
	bundle = {"report_date": "2026-08-28", "bundle_sha256": "new"}
	sealed_contents = {}
	prepared = {"record": "new"}
	stage_root = tmp_path / "stage"
	stage_root.mkdir()

	class Lock:
		def __enter__(self) -> None:
			return None

		def __exit__(self, *_args: object) -> None:
			return None

	monkeypatch.setattr(
		scripts.import_publication_bundle.scripts.publication_transaction,
		"publisher_lock", lambda _root: Lock(),
	)
	monkeypatch.setattr(
		scripts.import_publication_bundle.scripts.publication_transaction,
		"reconcile_interrupted_staging", lambda _root: None,
	)
	monkeypatch.setattr(scripts.import_publication_bundle, "_is_idempotent", lambda *_args: False)
	monkeypatch.setattr(scripts.import_publication_bundle, "_load_current_record", lambda *_args: current)
	monkeypatch.setattr(
		scripts.import_publication_bundle.scripts.publication_record,
		"validate_existing_publication_record", lambda record: record,
	)
	monkeypatch.setattr(
		scripts.import_publication_bundle, "_new_stage_root", lambda *_args: str(stage_root),
	)
	monkeypatch.setattr(
		scripts.import_publication_bundle.scripts.publication_staging,
		"prepare_stage", lambda *_args: (str(stage_root), prepared),
	)
	monkeypatch.setattr(scripts.import_publication_bundle, "_commit_stage", lambda *_args: None)
	if raises:
		with pytest.raises(scripts.publication_import_protocol.ImportProtocolError):
			scripts.import_publication_bundle._import_validated_bundle(
				bundle, {}, {}, {}, "", sealed_contents, str(tmp_path), object(), authorized,
			)
	else:
		result = scripts.import_publication_bundle._import_validated_bundle(
			bundle, {}, {}, {}, "", sealed_contents, str(tmp_path), object(), authorized,
		)
		assert result["status"] == expected_status


def test_identical_authorized_reimport_is_idempotent(tmp_path: pathlib.Path) -> None:
	"""Replacement authorization leaves an exact installed bundle a no-op."""
	test_publication_bundle_import.initialize_site(tmp_path)
	bundle_path = test_publication_bundle_import.make_bundle(tmp_path, "run-idempotent")
	scripts.import_publication_bundle.import_publication_bundle(
		bundle_path, str(tmp_path), test_publication_bundle_import.fake_build
	)
	result = scripts.import_publication_bundle.import_publication_bundle(
		bundle_path,
		str(tmp_path),
		test_publication_bundle_import.fake_build,
		replace_existing=True,
	)
	assert result["status"] == "idempotent"

"""Publisher boundary tests for sealed authoritative repository rosters."""

# Standard Library
import json
import pathlib

# PIP3 modules
import pytest

# local repo modules
import scripts.import_publication_bundle
import scripts.bundle_snapshot
import scripts.publication_transaction
from test_publication_bundle_import import fake_build
from test_publication_bundle_import import initialize_site
from test_publication_bundle_import import make_bundle


#============================================
def test_sealed_roster_retains_an_eligible_quiet_repository(tmp_path: pathlib.Path) -> None:
	"""The publisher accepts a full roster even when projection has no quiet-repository card."""
	initialize_site(tmp_path)
	bundle_path = pathlib.Path(make_bundle(tmp_path, "roster-quiet"))
	roster = json.loads((bundle_path / "repository_roster.json").read_text(encoding="utf-8"))
	projection = json.loads((bundle_path / "editorial_projection.json").read_text(encoding="utf-8"))

	assert "vosslab/quiet-repository" in {
		record["repository"] for record in roster["repositories"]
	}
	assert "vosslab/quiet-repository" not in {
		card["repository"] for card in projection["repositories"]
	}
	result = scripts.import_publication_bundle.import_publication_bundle(
		str(bundle_path), str(tmp_path), fake_build
	)
	assert result["status"] == "imported"


#============================================
def test_sealed_roster_is_not_reopened_after_snapshot(
	tmp_path: pathlib.Path,
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""A roster replacement after capture cannot change validation or the archive."""
	initialize_site(tmp_path)
	bundle_path = pathlib.Path(make_bundle(tmp_path, "roster-snapshot"))
	roster_path = bundle_path / "repository_roster.json"
	original_roster = roster_path.read_bytes()
	def replace_roster_after_validation(_root: str) -> None:
		roster_path.write_text("{}\n", encoding="utf-8")

	monkeypatch.setattr(
		scripts.publication_transaction,
		"reconcile_interrupted_staging",
		replace_roster_after_validation,
	)
	result = scripts.import_publication_bundle.import_publication_bundle(
		str(bundle_path), str(tmp_path), fake_build
	)
	archive = tmp_path / "data" / "publication_bundles" / "2026-08-23"
	assert result["status"] == "imported"
	assert (archive / "repository_roster.json").read_bytes() == original_roster


#============================================
def test_held_bundle_descriptor_rejects_root_path_substitution(
	tmp_path: pathlib.Path,
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""A root rename and symlink cannot redirect a descriptor-held bundle snapshot."""
	initialize_site(tmp_path)
	bundle_path = pathlib.Path(make_bundle(tmp_path, "root-source"))
	other_bundle = pathlib.Path(make_bundle(tmp_path, "root-other"))
	moved_bundle = tmp_path / "moved-source"
	read = scripts.bundle_snapshot.BundleSnapshot.read

	def replace_root(snapshot: object, relative_path: str) -> bytes:
		contents = read(snapshot, relative_path)
		if relative_path == "bundle.json":
			bundle_path.rename(moved_bundle)
			bundle_path.symlink_to(other_bundle, target_is_directory=True)
		return contents

	monkeypatch.setattr(scripts.bundle_snapshot.BundleSnapshot, "read", replace_root)
	result = scripts.import_publication_bundle.import_publication_bundle(
		str(bundle_path), str(tmp_path), fake_build
	)
	assert result["status"] == "imported"
	assert result["bundle_sha256"] == json.loads(
		(moved_bundle / "bundle.json").read_text(encoding="utf-8")
	)["bundle_sha256"]

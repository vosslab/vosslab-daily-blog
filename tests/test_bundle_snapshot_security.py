"""Bounded, descriptor-held publication bundle snapshot tests."""

# Standard Library
import hashlib
import io
import json
import pathlib

# PIP3 modules
import pytest

# local repo modules
import scripts.bundle_snapshot
import scripts.canonical_json
import scripts.import_publication_bundle


ASSET_PATH = "assets/alpha.bin"


def write_bundle_manifest(root: pathlib.Path, assets: list[dict]) -> None:
	"""Write the minimal manifest needed to exercise snapshot admission."""
	(root / "bundle.json").write_bytes(
		scripts.canonical_json.stable_json_bytes({"assets": assets})
	)


def transfer_bytes(entries: list[tuple[str, bytes]]) -> bytes:
	"""Build one inline transport fixture with independently declared entry hashes."""
	header = {
		"schema_version": scripts.bundle_snapshot.TRANSFER_SCHEMA_VERSION,
		"report_date": "2026-08-23",
		"bundle_sha256": "a" * 64,
		"entries": [
			{
				"path": path,
				"size": len(contents),
				"sha256": hashlib.sha256(contents).hexdigest(),
			}
			for path, contents in entries
		],
	}
	header_bytes = json.dumps(
		header, ensure_ascii=True, separators=(",", ":"), sort_keys=True,
	).encode("utf-8")
	return (
		scripts.bundle_snapshot.TRANSFER_MAGIC
		+ len(header_bytes).to_bytes(8, "big")
		+ header_bytes
		+ b"".join(contents for _path, contents in entries)
	)


def transfer_entries() -> list[tuple[str, bytes]]:
	"""Return the smallest path-complete transport payload in sorted order."""
	return sorted([
		("bundle.json", b"{}"),
		("editorial_projection.json", b"{}"),
		("evidence.json", b"{}"),
		("publication_surface.json", b"{}"),
		("post.md", b"# Post\n"),
		("repository_roster.json", b"{}"),
	])


class FragmentedStream(io.BytesIO):
	"""Expose a complete binary stream through deliberately short reads."""

	def read(self, size: int = -1) -> bytes:
		return super().read(min(size, 3))


class HeaderOnlyStream(io.BytesIO):
	"""Fail if a rejected header causes any payload read."""

	def read(self, size: int = -1) -> bytes:
		contents = super().read(size)
		if not contents:
			raise AssertionError("aggregate rejection read payload bytes")
		return contents


#============================================
def test_artifact_json_requires_the_producer_stable_encoding() -> None:
	"""Core artifacts retain the producer's indented final-newline byte form."""
	value = {"alpha": "value", "nested": {"count": 2}}
	stable = scripts.canonical_json.stable_json_bytes(value)

	assert scripts.canonical_json.load_stable_json(stable, "artifact") == value
	with pytest.raises(RuntimeError, match="stable canonical JSON bytes"):
		scripts.canonical_json.load_stable_json(
			scripts.canonical_json.compact_json_bytes(value), "artifact",
		)


#============================================
@pytest.mark.parametrize("contents", (b"{\"value\":NaN}", b"{\"value\":Infinity}", b"\xff"))
def test_strict_json_loaders_reject_extensions_and_invalid_utf8(contents: bytes) -> None:
	"""Artifact and header parsers accept only portable UTF-8 JSON values."""
	with pytest.raises(RuntimeError, match="valid canonical JSON"):
		scripts.canonical_json.load_stable_json(contents, "artifact")
	with pytest.raises(RuntimeError, match="valid canonical JSON"):
		scripts.canonical_json.load_compact_json(contents, "header")


#============================================
def test_transfer_rejects_stable_artifact_encoding_for_header_before_payload() -> None:
	"""The stdin envelope reserves compact JSON only for its transport header."""
	entries = transfer_entries()
	header = {
		"schema_version": scripts.bundle_snapshot.TRANSFER_SCHEMA_VERSION,
		"report_date": "2026-08-23",
		"bundle_sha256": "a" * 64,
		"entries": [
			{"path": path, "size": len(contents),
			 "sha256": hashlib.sha256(contents).hexdigest()}
			for path, contents in entries
		],
	}
	header_bytes = scripts.canonical_json.stable_json_bytes(header)
	transfer = (
		scripts.bundle_snapshot.TRANSFER_MAGIC
		+ len(header_bytes).to_bytes(8, "big")
		+ header_bytes
	)

	with pytest.raises(RuntimeError, match="compact canonical JSON bytes"):
		scripts.bundle_snapshot.BundleSnapshot.from_stream(HeaderOnlyStream(transfer))


#============================================
def test_transfer_rejects_duplicate_header_member_before_payload() -> None:
	"""An ambiguous header member fails before any declared artifact is read."""
	entries = transfer_entries()
	header = {
		"schema_version": scripts.bundle_snapshot.TRANSFER_SCHEMA_VERSION,
		"report_date": "2026-08-23",
		"bundle_sha256": "a" * 64,
		"entries": [
			{"path": path, "size": len(contents),
			 "sha256": hashlib.sha256(contents).hexdigest()}
			for path, contents in entries
		],
	}
	header_text = scripts.canonical_json.compact_json_bytes(header).decode("ascii")
	duplicate_text = header_text.replace(
		'"report_date":"2026-08-23",',
		'"report_date":"2026-08-23","report_date":"2026-08-23",',
	)
	header_bytes = duplicate_text.encode("ascii")
	transfer = (
		scripts.bundle_snapshot.TRANSFER_MAGIC
		+ len(header_bytes).to_bytes(8, "big")
		+ header_bytes
	)

	with pytest.raises(RuntimeError, match="valid canonical JSON"):
		scripts.bundle_snapshot.BundleSnapshot.from_stream(HeaderOnlyStream(transfer))


def test_snapshot_asset_admission_rejects_missing_symlink_and_escape(
	tmp_path: pathlib.Path,
) -> None:
	"""Asset admission accepts only direct regular manifest children."""
	assets_dir = tmp_path / "assets"
	assets_dir.mkdir()
	write_bundle_manifest(tmp_path, [{"path": ASSET_PATH}])
	with pytest.raises(RuntimeError, match="regular"):
		scripts.import_publication_bundle.validate_bundle(str(tmp_path))

	outside_asset = tmp_path / "outside.bin"
	outside_asset.write_bytes(b"outside bundle")
	(assets_dir / "alpha.bin").symlink_to(outside_asset)
	with pytest.raises(RuntimeError, match="regular"):
		scripts.import_publication_bundle.validate_bundle(str(tmp_path))

	write_bundle_manifest(tmp_path, [{"path": "../escape.png"}])
	with pytest.raises(RuntimeError, match="asset path"):
		scripts.import_publication_bundle.validate_bundle(str(tmp_path))


def test_snapshot_rejects_oversized_generic_json_artifact(
	tmp_path: pathlib.Path,
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""Ordinary core JSON artifacts must fit their declared storage envelope."""
	monkeypatch.setattr(scripts.bundle_snapshot, "MAX_JSON_BYTES", 8)
	(tmp_path / "editorial_projection.json").write_bytes(b"oversized")

	with scripts.bundle_snapshot.BundleSnapshot(str(tmp_path)) as snapshot:
		with pytest.raises(RuntimeError, match="schema envelope: editorial_projection.json"):
			snapshot.read("editorial_projection.json")


def test_snapshot_gives_evidence_its_complete_packet_envelope(
	tmp_path: pathlib.Path,
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""Evidence may exceed ordinary JSON while other core JSON stays bounded."""
	monkeypatch.setattr(scripts.bundle_snapshot, "MAX_JSON_BYTES", 8)
	monkeypatch.setattr(scripts.bundle_snapshot, "MAX_EVIDENCE_BYTES", 16)
	(tmp_path / "evidence.json").write_bytes(b"evidence+")
	(tmp_path / "repository_roster.json").write_bytes(b"oversized")

	with scripts.bundle_snapshot.BundleSnapshot(str(tmp_path)) as snapshot:
		assert snapshot.read("evidence.json") == b"evidence+"
		with pytest.raises(RuntimeError, match="schema envelope: repository_roster.json"):
			snapshot.read("repository_roster.json")


def test_snapshot_rejects_oversized_declared_asset(
	tmp_path: pathlib.Path,
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""A declared asset must fit the shared publication storage envelope."""
	monkeypatch.setattr(scripts.bundle_snapshot, "MAX_ASSET_BYTES", 8)
	assets_dir = tmp_path / "assets"
	assets_dir.mkdir()
	(assets_dir / "alpha.bin").write_bytes(b"oversized")

	with scripts.bundle_snapshot.BundleSnapshot(str(tmp_path)) as snapshot:
		with pytest.raises(RuntimeError, match=f"schema envelope: {ASSET_PATH}"):
			snapshot.read_declared_assets({ASSET_PATH})


def test_snapshot_rejects_undeclared_asset_without_reading_its_bytes(
	tmp_path: pathlib.Path,
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""An unmanifested child is rejected during descriptor-held name inspection."""
	assets_dir = tmp_path / "assets"
	assets_dir.mkdir()
	(assets_dir / "alpha.bin").write_bytes(b"declared bytes")
	(assets_dir / "undeclared.bin").write_bytes(b"bytes that must remain unread")
	real_read_regular = scripts.bundle_snapshot.BundleSnapshot._read_regular

	def reject_undeclared_read(
		self: scripts.bundle_snapshot.BundleSnapshot,
		name: str,
		parent_fd: int,
		label: str,
		maximum_bytes: int,
	) -> bytes:
		if label == "assets/undeclared.bin":
			raise AssertionError("undeclared asset bytes were read")
		return real_read_regular(self, name, parent_fd, label, maximum_bytes)

	monkeypatch.setattr(
		scripts.bundle_snapshot.BundleSnapshot, "_read_regular", reject_undeclared_read,
	)
	with scripts.bundle_snapshot.BundleSnapshot(str(tmp_path)) as snapshot:
		with pytest.raises(RuntimeError, match="assets directory does not match"):
			snapshot.read_declared_assets({ASSET_PATH})


@pytest.mark.parametrize(
	("contents", "message"),
	[
		(b"vosslab.daily-blog.bundle-transfer.v1\n", "header is truncated"),
		(transfer_bytes(transfer_entries())[:-1], "entry is truncated"),
		(transfer_bytes(transfer_entries()) + b"unexpected", "trailing bytes"),
	],
)
def test_transfer_snapshot_rejects_incomplete_or_extra_bytes(
	contents: bytes,
	message: str,
) -> None:
	"""The stream envelope accepts one exact bounded sequence of declared bytes."""
	with pytest.raises(RuntimeError, match=message):
		scripts.bundle_snapshot.BundleSnapshot.from_transfer_bytes(contents)


def test_transfer_snapshot_rejects_duplicate_or_unsupported_entries() -> None:
	"""The transport contract has one sorted declaration for each permitted path."""
	duplicate_entries = transfer_entries() + [("repository_roster.json", b"again")]
	with pytest.raises(RuntimeError, match="unique and sorted"):
		scripts.bundle_snapshot.BundleSnapshot.from_transfer_bytes(
			transfer_bytes(duplicate_entries)
		)

	unsupported_entries = transfer_entries() + [("unexpected.bin", b"not a bundle artifact")]
	with pytest.raises(RuntimeError, match="entry path"):
		scripts.bundle_snapshot.BundleSnapshot.from_transfer_bytes(
			transfer_bytes(unsupported_entries)
		)


def test_transfer_snapshot_accepts_a_fragmented_complete_stream() -> None:
	"""Pipe read boundaries do not change an otherwise complete envelope."""
	snapshot = scripts.bundle_snapshot.BundleSnapshot.from_stream(
		FragmentedStream(transfer_bytes(transfer_entries()))
	)
	assert snapshot.read("post.md") == b"# Post\n"


def test_transfer_snapshot_rejects_oversized_total_before_payload_read(
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""Declared aggregate size is bounded before any declared entry is retained."""
	entries = transfer_entries() + [(ASSET_PATH, b"asset")]
	header = {
		"schema_version": scripts.bundle_snapshot.TRANSFER_SCHEMA_VERSION,
		"report_date": "2026-08-23",
		"bundle_sha256": "a" * 64,
		"entries": [
			{"path": path, "size": len(contents),
			 "sha256": hashlib.sha256(contents).hexdigest()}
			for path, contents in sorted(entries)
		],
	}
	header_bytes = json.dumps(
		header, ensure_ascii=True, separators=(",", ":"), sort_keys=True,
	).encode("utf-8")
	contents = (
		scripts.bundle_snapshot.TRANSFER_MAGIC
		+ len(header_bytes).to_bytes(8, "big")
		+ header_bytes
	)
	declared_payload_size = sum(len(payload) for _path, payload in entries)
	monkeypatch.setattr(
		scripts.bundle_snapshot,
		"MAX_TRANSFER_BYTES",
		len(contents) + declared_payload_size - 1,
	)
	with pytest.raises(RuntimeError, match="aggregate envelope"):
		scripts.bundle_snapshot.BundleSnapshot.from_stream(HeaderOnlyStream(contents))


def test_transfer_snapshot_counts_framing_bytes_in_aggregate_limit(
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""The producer and sibling cap the same complete encoded transport size."""
	contents = transfer_bytes(transfer_entries())
	monkeypatch.setattr(scripts.bundle_snapshot, "MAX_TRANSFER_BYTES", len(contents))
	snapshot = scripts.bundle_snapshot.BundleSnapshot.from_transfer_bytes(contents)
	assert snapshot.read("post.md") == b"# Post\n"
	monkeypatch.setattr(scripts.bundle_snapshot, "MAX_TRANSFER_BYTES", len(contents) - 1)
	with pytest.raises(RuntimeError, match="aggregate envelope"):
		scripts.bundle_snapshot.BundleSnapshot.from_transfer_bytes(contents)


def test_transfer_evidence_uses_its_packet_limit_but_still_hits_total_cap(
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""The evidence entry limit cannot bypass the enclosing transfer limit."""
	monkeypatch.setattr(scripts.bundle_snapshot, "MAX_JSON_BYTES", 1024)
	monkeypatch.setattr(scripts.bundle_snapshot, "MAX_EVIDENCE_BYTES", 2048)
	evidence = b"e" * 1025
	entries = [
		(path, evidence if path == "evidence.json" else contents)
		for path, contents in transfer_entries()
	]
	contents = transfer_bytes(entries)
	monkeypatch.setattr(scripts.bundle_snapshot, "MAX_TRANSFER_BYTES", len(contents) - 1)

	with pytest.raises(RuntimeError, match="aggregate envelope"):
		scripts.bundle_snapshot.BundleSnapshot.from_transfer_bytes(contents)

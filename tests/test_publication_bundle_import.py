"""Final-only bundle validation, idempotency, and transaction tests."""

# Standard Library
import os
import json
import pathlib
import threading

# PIP3 modules
import pytest

# local repo modules
import scripts.import_publication_bundle
import scripts.publication_transaction
import scripts.site_deployment


REPORT_DATE = "2026-08-23"


#============================================
def write_json(path: pathlib.Path, value: dict) -> None:
	"""Write one stable inline JSON test artifact."""
	path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


#============================================
def initialize_site(root: pathlib.Path) -> None:
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
def make_repository_evidence(repository: str, suffix: str) -> tuple[dict, dict, dict]:
	"""Return matching mirror, activity, and evidence-item records."""
	commit_id = suffix * 40
	parent_id = chr(ord(suffix) + 1) * 40
	content = f"{repository} moved publication ownership into one exact contract."
	mirror = {
		"repository": repository,
		"repository_url": f"https://github.com/{repository}",
		"cache_path": f"/cache/{repository.replace('/', '-')}",
		"refresh_result": "refreshed",
		"refresh_error": "",
		"default_revision": commit_id,
		"object_available": True,
		"ref_fingerprint": scripts.import_publication_bundle.sha256_bytes(
			repository.encode("utf-8")
		),
		"refreshed_at": "2026-08-24T08:00:00Z",
	}
	activity = {
		"repository": repository,
		"repository_url": mirror["repository_url"],
		"cache_path": mirror["cache_path"],
		"default_revision": commit_id,
		"commits": [
			{
				"sha": commit_id,
				"parents": [parent_id],
				"author_name": "Author",
				"author_email": "author@example.invalid",
				"author_timestamp": "2026-08-23T12:00:00-05:00",
				"committer_timestamp": "2026-08-23T12:00:00-05:00",
				"message": "Move publication ownership into an exact contract",
			}
		],
		"revision_ranges": [{"base_commit": parent_id, "final_commit": commit_id}],
		"snapshot_commits": [commit_id],
	}
	item = {
		"evidence_id": "",
		"kind": "changed_documentation",
		"authority_level": "strong_support",
		"authority_rank": 500,
		"repository": repository,
		"commit": commit_id,
		"path": "docs/CODE_ARCHITECTURE.md",
		"blob_hash": suffix * 40,
		"content": content,
		"content_hash": scripts.import_publication_bundle.sha256_bytes(content.encode("utf-8")),
		"acquisition_source": "git show",
		"truncated": False,
		"asset_path": "",
		"publish_path": "",
	}
	item["evidence_id"] = scripts.import_publication_bundle.evidence_item_identity(item)
	return mirror, activity, item


#============================================
def make_bundle(root: pathlib.Path, run_id: str) -> str:
	"""Write one complete inline final-only contract bundle without media assets."""
	bundle_dir = root / f"bundle-{run_id}"
	(bundle_dir / "assets").mkdir(parents=True)
	records = [
		make_repository_evidence("vosslab/alpha", "a"),
		make_repository_evidence("vosslab/beta", "c"),
	]
	mirrors = [record[0] for record in records]
	activity = [record[1] for record in records]
	items = [record[2] for record in records]
	evidence = {
		"schema_version": "vosslab.daily-blog.evidence.v3",
		"report_date": REPORT_DATE,
		"timezone": "America/Chicago",
		"complete": True,
		"collection_limits": {"item_chars": 12000},
		"mirrors": mirrors,
		"activity": activity,
		"items": items,
	}
	evidence["packet_id"] = scripts.import_publication_bundle.hash_value(evidence)
	repositories = [
		{
			"repository": record[1]["repository"],
			"repository_url": record[1]["repository_url"],
			"commit_count": len(record[1]["commits"]),
			"commit_shas": [record[1]["commits"][0]["sha"]],
			"commit_subjects": [record[1]["commits"][0]["message"]],
		}
		for record in records
	]
	excerpts = []
	for item in items:
		start = item["content"].index("moved")
		end = len(item["content"])
		content = item["content"][start:end]
		excerpt = {
			"excerpt_id": "",
			"evidence_id": item["evidence_id"],
			"repository": item["repository"],
			"kind": item["kind"],
			"authority_level": item["authority_level"],
			"authority_rank": item["authority_rank"],
			"commit": item["commit"],
			"path": item["path"],
			"start": start,
			"end": end,
			"source_content_hash": item["content_hash"],
			"content_hash": scripts.import_publication_bundle.sha256_bytes(
				content.encode("utf-8")
			),
			"content": content,
		}
		excerpt_identity = dict(excerpt)
		excerpt_identity.pop("excerpt_id")
		excerpt["excerpt_id"] = (
			"ex-" + scripts.import_publication_bundle.hash_value(excerpt_identity)[:16]
		)
		excerpts.append(excerpt)
	projection = {
		"schema_version": "vosslab.daily-blog.editorial-projection.v1",
		"projection_id": "",
		"packet_id": evidence["packet_id"],
		"report_date": REPORT_DATE,
		"timezone": "America/Chicago",
		"projection_limits": {
			"context_chars": 12000,
			"excerpt_chars": 1000,
			"commit_subject_chars": 160,
		},
		"repositories": repositories,
		"excerpts": excerpts,
	}
	projection_content = dict(projection)
	projection_content.pop("projection_id")
	projection["projection_id"] = scripts.import_publication_bundle.hash_value(projection_content)
	post = (
		"---\n"
		+ f"date: {REPORT_DATE}\n"
		+ "slug: exact-evidence\n"
		+ f"generator_run: {run_id}\n"
		+ "evidence_manifest: evidence.json\n"
		+ "editorial_projection: editorial_projection.json\n"
		+ "---\n\n"
		+ "# Exact evidence preserves the publication boundary\n\n"
		+ f"I kept the account tied to exact objects. <!-- evidence: {items[0]['evidence_id']} -->\n\n"
		+ "<!-- more -->\n\n"
		+ "## Publication state\n\n"
		+ f"I retained a bounded work log. <!-- evidence: {items[1]['evidence_id']} -->\n"
		+ "\n## Evidence trail\n\n"
		+ (
			"I kept the visible record tied to the same small, inspectable boundary. " * 35
		)
		+ f"<!-- evidence: {items[0]['evidence_id']} -->\n\n"
		+ "## Project coverage\n\n"
		+ (
			f"vosslab/alpha and vosslab/beta both remain in this bounded publication record. "
			f"<!-- evidence: {items[1]['evidence_id']} -->\n"
		)
	)
	post_hash = scripts.import_publication_bundle.sha256_bytes(post.encode("utf-8"))
	bundle = {
		"schema_version": "vosslab.daily-blog.bundle.v2",
		"bundle_id": "",
		"report_date": REPORT_DATE,
		"timezone": "America/Chicago",
		"created_at": "2026-08-24T08:00:00Z",
		"generator": {
			"run_id": run_id,
			"revision": "f" * 64,
			"version": "daily-blog-generator-v2",
		},
		"contracts": {
			"evidence_schema": "vosslab.daily-blog.evidence.v3",
			"editorial_projection_schema": "vosslab.daily-blog.editorial-projection.v1",
			"prompt_version": "daily-blog-prompts-v3",
			"rubric_version": "daily-blog-rubric-v3",
			"candidate_validation": {
				"name": scripts.validate_daily_post.V3_HISTORICAL_POLICY.name,
				"version": scripts.validate_daily_post.V3_HISTORICAL_POLICY.version,
				"sha256": scripts.validate_daily_post.V3_HISTORICAL_POLICY.digest,
			},
		},
		"evidence": {
			"path": "evidence.json",
			"packet_id": evidence["packet_id"],
			"sha256": scripts.import_publication_bundle.hash_value(evidence),
		},
		"editorial_projection": {
			"path": "editorial_projection.json",
			"projection_id": projection["projection_id"],
			"sha256": scripts.import_publication_bundle.hash_value(projection),
		},
		"post": {"path": "post.md", "sha256": post_hash},
		"assets": [],
		"candidates": [
			{
				"candidate_id": "candidate_1",
				"post_hash": post_hash,
				"projection_id": projection["projection_id"],
				"valid": True,
				"issues": [],
			},
			{
				"candidate_id": "candidate_2",
				"post_hash": scripts.import_publication_bundle.sha256_bytes(
					f"alternate {run_id}".encode("utf-8")
				),
				"projection_id": projection["projection_id"],
				"valid": True,
				"issues": [],
			},
		],
		"referee": {
			"projection_id": projection["projection_id"],
			"winner": "A",
			"reason": "Candidate A best reflects the exact evidence.",
			"evidence_quality": "high",
			"confidence": 0.9,
			"anonymous_mapping": {"A": "candidate_1", "B": "candidate_2"},
		},
	}
	bundle["bundle_id"] = scripts.import_publication_bundle.bundle_identity(bundle)
	write_json(bundle_dir / "evidence.json", evidence)
	write_json(bundle_dir / "editorial_projection.json", projection)
	(bundle_dir / "post.md").write_text(post, encoding="utf-8")
	write_json(bundle_dir / "bundle.json", bundle)
	return str(bundle_dir)


#============================================
def rehash_projection_bundle(bundle_path: str, projection: dict) -> None:
	"""Rehash an intentionally changed projection and its enclosing bundle."""
	bundle_dir = pathlib.Path(bundle_path)
	projection_content = dict(projection)
	projection_content.pop("projection_id", None)
	projection["projection_id"] = scripts.import_publication_bundle.hash_value(projection_content)
	write_json(bundle_dir / "editorial_projection.json", projection)
	bundle = json.loads((bundle_dir / "bundle.json").read_text(encoding="utf-8"))
	bundle["editorial_projection"]["projection_id"] = projection["projection_id"]
	bundle["editorial_projection"]["sha256"] = scripts.import_publication_bundle.hash_value(
		projection
	)
	for candidate in bundle["candidates"]:
		candidate["projection_id"] = projection["projection_id"]
	bundle["referee"]["projection_id"] = projection["projection_id"]
	bundle["bundle_id"] = scripts.import_publication_bundle.bundle_identity(bundle)
	write_json(bundle_dir / "bundle.json", bundle)


#============================================
def rehash_post_bundle(bundle_path: str, post: str) -> None:
	"""Rehash an intentionally changed selected post and enclosing bundle."""
	bundle_dir = pathlib.Path(bundle_path)
	post_hash = scripts.import_publication_bundle.sha256_bytes(post.encode("utf-8"))
	(bundle_dir / "post.md").write_text(post, encoding="utf-8")
	bundle = json.loads((bundle_dir / "bundle.json").read_text(encoding="utf-8"))
	bundle["post"]["sha256"] = post_hash
	bundle["candidates"][0]["post_hash"] = post_hash
	bundle["bundle_id"] = scripts.import_publication_bundle.bundle_identity(bundle)
	write_json(bundle_dir / "bundle.json", bundle)


#============================================
def fake_build(_stage_root: str, site_dir: str, _root: str) -> None:
	"""Create the minimal built release expected by the transaction."""
	os.makedirs(site_dir)
	with open(os.path.join(site_dir, "index.html"), "w", encoding="utf-8") as handle:
		handle.write("new release")


#============================================
def publication_snapshot(root: pathlib.Path) -> dict:
	"""Return the complete publisher transaction state."""
	post_path = root / "docs" / "blog" / "posts" / f"{REPORT_DATE}.md"
	record_path = root / "data" / "publications" / f"{REPORT_DATE}.json"
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
def test_import_archives_projection_and_writes_publication_v2(tmp_path: pathlib.Path) -> None:
	"""A valid final-only import retains the projection and records no quality state."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-one")

	result = scripts.import_publication_bundle.import_publication_bundle(
		bundle_path, str(tmp_path), fake_build
	)
	record = json.loads(
		(tmp_path / "data" / "publications" / f"{REPORT_DATE}.json").read_text(encoding="utf-8")
	)
	archive = tmp_path / "data" / "publication_bundles" / result["bundle_id"]

	assert record["schema_version"] == "vosslab.daily-blog.publication.v2"
	assert (archive / "editorial_projection.json").is_file()


#============================================
def test_import_v3_rejects_one_uncited_narrative_block(tmp_path: pathlib.Path) -> None:
	"""The active historical importer preserves paragraph-level provenance."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-uncited-narrative")
	post_path = pathlib.Path(bundle_path) / "post.md"
	post = post_path.read_text(encoding="utf-8")
	post = post.replace(
		"## Publication state\n\n",
		"## Publication state\n\n"
		"I enjoyed finding the smaller shape of this publication boundary.\n\n",
	)
	rehash_post_bundle(bundle_path, post)

	with pytest.raises(RuntimeError, match="every factual prose paragraph"):
		scripts.import_publication_bundle.import_publication_bundle(
			bundle_path, str(tmp_path), fake_build
		)


#============================================
def test_generator_source_fingerprint_accepts_64_hex_identity(
	tmp_path: pathlib.Path,
) -> None:
	"""Publisher records retain a producer source fingerprint longer than a Git SHA."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-source-fingerprint")
	bundle_file = pathlib.Path(bundle_path) / "bundle.json"
	bundle = json.loads(bundle_file.read_text(encoding="utf-8"))
	bundle["generator"]["revision"] = "0" * 64
	bundle["bundle_id"] = scripts.import_publication_bundle.bundle_identity(bundle)
	write_json(bundle_file, bundle)

	result = scripts.import_publication_bundle.import_publication_bundle(
		bundle_path, str(tmp_path), fake_build
	)
	record = json.loads(
		(tmp_path / "data" / "publications" / f"{REPORT_DATE}.json").read_text(encoding="utf-8")
	)

	assert result["status"] == "imported"
	assert record["generator_revision"] == "0" * 64


#============================================
def test_generator_revision_rejects_40_hex_legacy_identity(
	tmp_path: pathlib.Path,
) -> None:
	"""The v2 publisher does not retain the former Git-length generator revision contract."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-legacy-generator-revision")
	bundle_file = pathlib.Path(bundle_path) / "bundle.json"
	bundle = json.loads(bundle_file.read_text(encoding="utf-8"))
	bundle["generator"]["revision"] = "f" * 40
	bundle["bundle_id"] = scripts.import_publication_bundle.bundle_identity(bundle)
	write_json(bundle_file, bundle)

	with pytest.raises(RuntimeError, match="64-hex"):
		scripts.import_publication_bundle.import_publication_bundle(
			bundle_path, str(tmp_path), fake_build
		)


#============================================
def test_identical_reimport_is_idempotent(tmp_path: pathlib.Path) -> None:
	"""The exact installed bundle remains a successful no-op."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-idempotent")
	scripts.import_publication_bundle.import_publication_bundle(
		bundle_path, str(tmp_path), fake_build
	)

	result = scripts.import_publication_bundle.import_publication_bundle(
		bundle_path, str(tmp_path), fake_build
	)

	assert result["status"] == "idempotent"


#============================================
def test_idempotency_rejects_changed_archive_bytes(tmp_path: pathlib.Path) -> None:
	"""A bundle ID cannot hide byte drift in the publisher-owned immutable archive."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-archive-drift")
	result = scripts.import_publication_bundle.import_publication_bundle(
		bundle_path, str(tmp_path), fake_build
	)
	archived_evidence = (
		tmp_path
		/ "data"
		/ "publication_bundles"
		/ result["bundle_id"]
		/ "evidence.json"
	)
	archived_evidence.write_text("{}\n", encoding="utf-8")

	with pytest.raises(RuntimeError, match="archive has different content"):
		scripts.import_publication_bundle.import_publication_bundle(
			bundle_path, str(tmp_path), fake_build
		)


#============================================
def test_conflicting_bundle_for_published_date_is_rejected(tmp_path: pathlib.Path) -> None:
	"""A report date is immutable after any different final-only bundle is installed."""
	initialize_site(tmp_path)
	first = make_bundle(tmp_path, "run-first")
	second = make_bundle(tmp_path, "run-conflict")
	scripts.import_publication_bundle.import_publication_bundle(first, str(tmp_path), fake_build)
	original = publication_snapshot(tmp_path)

	with pytest.raises(RuntimeError, match="already-published report date"):
		scripts.import_publication_bundle.import_publication_bundle(
			second, str(tmp_path), fake_build
		)

	assert publication_snapshot(tmp_path) == original


#============================================
def test_projection_file_tampering_is_rejected_before_staging(tmp_path: pathlib.Path) -> None:
	"""Projection bytes cannot change behind their bundle manifest hash."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-projection-tamper")
	projection_path = pathlib.Path(bundle_path) / "editorial_projection.json"
	projection = json.loads(projection_path.read_text(encoding="utf-8"))
	projection["excerpts"][0]["content"] = "fabricated"
	write_json(projection_path, projection)

	with pytest.raises(RuntimeError, match="projection hash"):
		scripts.import_publication_bundle.import_publication_bundle(
			bundle_path, str(tmp_path), fake_build
		)


#============================================
def test_projection_packet_binding_cannot_be_rehashed_away(tmp_path: pathlib.Path) -> None:
	"""A self-consistent projection must still bind to the exact evidence packet."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-packet-binding")
	projection_path = pathlib.Path(bundle_path) / "editorial_projection.json"
	projection = json.loads(projection_path.read_text(encoding="utf-8"))
	projection["packet_id"] = "0" * 64
	rehash_projection_bundle(bundle_path, projection)

	with pytest.raises(RuntimeError, match="packet"):
		scripts.import_publication_bundle.import_publication_bundle(
			bundle_path, str(tmp_path), fake_build
		)


#============================================
def test_projection_cards_cover_every_active_repository(tmp_path: pathlib.Path) -> None:
	"""A rehashed projection cannot omit an active evidence repository."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-card-coverage")
	projection_path = pathlib.Path(bundle_path) / "editorial_projection.json"
	projection = json.loads(projection_path.read_text(encoding="utf-8"))
	projection["repositories"].pop()
	rehash_projection_bundle(bundle_path, projection)

	with pytest.raises(RuntimeError, match="active evidence repositories"):
		scripts.import_publication_bundle.import_publication_bundle(
			bundle_path, str(tmp_path), fake_build
		)


@pytest.mark.parametrize(
	("field", "value", "message"),
	(
		("evidence_id", "ev-unknown", "known evidence item"),
		("source_content_hash", "0" * 64, "source content hash"),
		("start", -1, "offsets"),
		("content", "fabricated", "exact source substring"),
	),
)
def test_projection_exact_excerpt_integrity(
	tmp_path: pathlib.Path,
	field: str,
	value: object,
	message: str,
) -> None:
	"""Every excerpt remains an exact, hash-bound slice of known packet evidence."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, f"run-excerpt-{field}")
	projection_path = pathlib.Path(bundle_path) / "editorial_projection.json"
	projection = json.loads(projection_path.read_text(encoding="utf-8"))
	projection["excerpts"][0][field] = value
	rehash_projection_bundle(bundle_path, projection)

	with pytest.raises(RuntimeError, match=message):
		scripts.import_publication_bundle.import_publication_bundle(
			bundle_path, str(tmp_path), fake_build
		)


#============================================
def test_two_author_validation_summaries_are_required(
	tmp_path: pathlib.Path,
) -> None:
	"""A bundle cannot exist before both author routes complete deterministic validation."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-invalid-author")
	bundle_file = pathlib.Path(bundle_path) / "bundle.json"
	bundle = json.loads(bundle_file.read_text(encoding="utf-8"))
	bundle["candidates"].pop()
	bundle["bundle_id"] = scripts.import_publication_bundle.bundle_identity(bundle)
	write_json(bundle_file, bundle)

	with pytest.raises(RuntimeError, match="exactly two"):
		scripts.import_publication_bundle.import_publication_bundle(
			bundle_path, str(tmp_path), fake_build
		)


#============================================
def test_referee_mapping_excludes_failed_candidate_validation(tmp_path: pathlib.Path) -> None:
	"""The referee cannot receive a candidate that failed deterministic validation."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-invalid-mapped-author")
	bundle_file = pathlib.Path(bundle_path) / "bundle.json"
	bundle = json.loads(bundle_file.read_text(encoding="utf-8"))
	bundle["candidates"][1]["valid"] = False
	bundle["candidates"][1]["issues"] = ["deterministic validation failed"]
	bundle["bundle_id"] = scripts.import_publication_bundle.bundle_identity(bundle)
	write_json(bundle_file, bundle)

	with pytest.raises(RuntimeError, match="only valid candidates"):
		scripts.import_publication_bundle.import_publication_bundle(
			bundle_path, str(tmp_path), fake_build
		)


#============================================
def test_referee_requires_an_ab_selection(tmp_path: pathlib.Path) -> None:
	"""Publication requires a selected winner in the anonymous candidate mapping."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-invalid-referee")
	bundle_file = pathlib.Path(bundle_path) / "bundle.json"
	bundle = json.loads(bundle_file.read_text(encoding="utf-8"))
	bundle["referee"]["anonymous_mapping"] = {}
	bundle["bundle_id"] = scripts.import_publication_bundle.bundle_identity(bundle)
	write_json(bundle_file, bundle)

	with pytest.raises(RuntimeError, match="anonymous A/B mapping"):
		scripts.import_publication_bundle.import_publication_bundle(
			bundle_path, str(tmp_path), fake_build
		)


#============================================
def test_referee_selection_binds_to_the_editorial_projection(tmp_path: pathlib.Path) -> None:
	"""A referee decision from another projection cannot select the published post."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-referee-projection")
	bundle_file = pathlib.Path(bundle_path) / "bundle.json"
	bundle = json.loads(bundle_file.read_text(encoding="utf-8"))
	bundle["referee"]["projection_id"] = "0" * 64
	bundle["bundle_id"] = scripts.import_publication_bundle.bundle_identity(bundle)
	write_json(bundle_file, bundle)

	with pytest.raises(RuntimeError, match="referee projection"):
		scripts.import_publication_bundle.import_publication_bundle(
			bundle_path, str(tmp_path), fake_build
		)


#============================================
def test_candidate_front_matter_rejects_unknown_contract_fields(
	tmp_path: pathlib.Path,
) -> None:
	"""The selected post front matter is a closed, versioned contract."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-old-front-matter")
	post_path = pathlib.Path(bundle_path) / "post.md"
	post = post_path.read_text(encoding="utf-8").replace(
		"slug: exact-evidence\n",
		"slug: exact-evidence\nobsolete_contract_field: removed\n",
	)
	rehash_post_bundle(bundle_path, post)

	with pytest.raises(RuntimeError, match="unsupported fields"):
		scripts.import_publication_bundle.import_publication_bundle(
			bundle_path, str(tmp_path), fake_build
		)


#============================================
def test_candidate_front_matter_requires_projection_manifest(tmp_path: pathlib.Path) -> None:
	"""Every selected post names the editorial projection used by both authors."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-missing-front-projection")
	post_path = pathlib.Path(bundle_path) / "post.md"
	post = post_path.read_text(encoding="utf-8").replace(
		"editorial_projection: editorial_projection.json\n",
		"",
	)
	rehash_post_bundle(bundle_path, post)

	with pytest.raises(RuntimeError, match="missing editorial_projection"):
		scripts.import_publication_bundle.import_publication_bundle(
			bundle_path, str(tmp_path), fake_build
		)


#============================================
def test_generic_date_derived_work_log_title_is_rejected(tmp_path: pathlib.Path) -> None:
	"""A date plus generic Work log wording is not a descriptive publication title."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-generic-title")
	post_path = pathlib.Path(bundle_path) / "post.md"
	post = post_path.read_text(encoding="utf-8").replace(
		"# Exact evidence preserves the publication boundary",
		"# Work log for August 23, 2026",
	)
	rehash_post_bundle(bundle_path, post)

	with pytest.raises(RuntimeError, match="descriptive H1"):
		scripts.import_publication_bundle.import_publication_bundle(
			bundle_path, str(tmp_path), fake_build
		)


#============================================
def test_unresolved_slug_placeholder_is_rejected(tmp_path: pathlib.Path) -> None:
	"""The publisher rejects an output-contract sentinel that escaped the producer adapter."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-placeholder-slug")
	post_path = pathlib.Path(bundle_path) / "post.md"
	post = post_path.read_text(encoding="utf-8").replace(
		"slug: exact-evidence",
		"slug: thematic-lowercase-slug",
	)
	rehash_post_bundle(bundle_path, post)

	with pytest.raises(RuntimeError, match="slug placeholder"):
		scripts.import_publication_bundle.import_publication_bundle(
			bundle_path, str(tmp_path), fake_build
		)


#============================================
def test_publisher_lock_lives_in_generated_runtime_state(tmp_path: pathlib.Path) -> None:
	"""Locking cannot dirty the repository root during normal publisher operation."""
	with scripts.publication_transaction.publisher_lock(str(tmp_path)):
		lock_path = tmp_path / "generated" / "publisher.lock"
		assert lock_path.is_file()

	assert not (tmp_path / ".publisher.lock").exists()


#============================================
def test_asset_path_must_remain_inside_bundle(tmp_path: pathlib.Path) -> None:
	"""A rehashed asset manifest cannot name a path outside the physical bundle."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-asset-path")
	bundle_file = pathlib.Path(bundle_path) / "bundle.json"
	bundle = json.loads(bundle_file.read_text(encoding="utf-8"))
	bundle["assets"] = [
		{
			"path": "../escape.png",
			"sha256": "a" * 64,
			"git_blob_hash": "b" * 40,
			"evidence_id": "ev-outside",
			"publish_path": f"../../assets/publications/{REPORT_DATE}/escape.png",
		}
	]
	bundle["bundle_id"] = scripts.import_publication_bundle.bundle_identity(bundle)
	write_json(bundle_file, bundle)

	with pytest.raises(RuntimeError, match="asset path"):
		scripts.import_publication_bundle.import_publication_bundle(
			bundle_path, str(tmp_path), fake_build
		)


#============================================
def test_failed_staged_build_preserves_complete_publication_state(
	tmp_path: pathlib.Path,
) -> None:
	"""A strict build failure leaves the complete last-good transaction unchanged."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-build-failure")
	original = publication_snapshot(tmp_path)

	def failed_build(_stage_root: str, _site_dir: str, _root: str) -> None:
		raise RuntimeError("synthetic strict build failure")

	with pytest.raises(RuntimeError, match="synthetic strict build failure"):
		scripts.import_publication_bundle.import_publication_bundle(
			bundle_path, str(tmp_path), failed_build
		)

	assert publication_snapshot(tmp_path) == original


#============================================
def test_install_failure_restores_complete_publication_state(
	tmp_path: pathlib.Path,
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""A failure after immutable moves restores every publisher-owned boundary."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-install-failure")
	original = publication_snapshot(tmp_path)
	real_replace = scripts.import_publication_bundle.os.replace

	def fail_docs_install(source: str, destination: str) -> None:
		if os.path.basename(source) == "docs" and destination == str(tmp_path / "docs"):
			raise RuntimeError("synthetic source install failure")
		real_replace(source, destination)

	monkeypatch.setattr(scripts.import_publication_bundle.os, "replace", fail_docs_install)
	with pytest.raises(RuntimeError, match="synthetic source install failure"):
		scripts.import_publication_bundle.import_publication_bundle(
			bundle_path, str(tmp_path), fake_build
		)

	assert publication_snapshot(tmp_path) == original


#============================================
def test_idempotency_requires_site_to_resolve_to_expected_release(
	tmp_path: pathlib.Path,
) -> None:
	"""An identical record is incomplete when the served pointer names another release."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-wrong-site")
	scripts.import_publication_bundle.import_publication_bundle(
		bundle_path, str(tmp_path), fake_build
	)
	site = tmp_path / "site"
	site.unlink()
	site.symlink_to("generated/releases/old")

	with pytest.raises(RuntimeError, match="publication record is incomplete"):
		scripts.import_publication_bundle.import_publication_bundle(
			bundle_path, str(tmp_path), fake_build
		)


#============================================
def test_idempotency_accepts_valid_derived_site_release(tmp_path: pathlib.Path) -> None:
	"""A presentation release retains the exact bundle identity beneath it."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-derived-site")
	first = scripts.import_publication_bundle.import_publication_bundle(
		bundle_path, str(tmp_path), fake_build
	)
	scripts.site_deployment.publish_site(str(tmp_path), fake_build)
	second = scripts.import_publication_bundle.import_publication_bundle(
		bundle_path, str(tmp_path), fake_build
	)

	assert first["bundle_id"] == second["bundle_id"]
	assert second["status"] == "idempotent"


#============================================
def test_temp_site_link_is_removed_when_pointer_switch_fails(
	tmp_path: pathlib.Path,
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""A fault at the final pointer replace leaves no temporary site link or partial state."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-temp-link-cleanup")
	original = publication_snapshot(tmp_path)
	real_replace = scripts.import_publication_bundle.os.replace

	def fail_site_switch(source: str, destination: str) -> None:
		if os.path.basename(source).startswith(".site-next-"):
			raise RuntimeError("synthetic site switch failure")
		real_replace(source, destination)

	monkeypatch.setattr(scripts.import_publication_bundle.os, "replace", fail_site_switch)
	with pytest.raises(RuntimeError, match="synthetic site switch failure"):
		scripts.import_publication_bundle.import_publication_bundle(
			bundle_path, str(tmp_path), fake_build
		)

	assert publication_snapshot(tmp_path) == original
	assert not tuple(tmp_path.glob(".site-next-*"))


#============================================
def test_concurrent_imports_serialize_before_idempotency_and_commit(
	tmp_path: pathlib.Path,
) -> None:
	"""A publisher-global lock admits one same-date bundle and rejects the other."""
	initialize_site(tmp_path)
	first = make_bundle(tmp_path, "run-concurrent-first")
	second = make_bundle(tmp_path, "run-concurrent-second")
	build_started = threading.Event()
	second_build_started = threading.Event()
	release_first = threading.Event()
	second_ready = threading.Event()
	results = {}
	errors = {}
	calls = []

	def controlled_build(stage_root: str, site_dir: str, root: str) -> None:
		calls.append(stage_root)
		if len(calls) == 1:
			build_started.set()
			release_first.wait(2)
		else:
			second_build_started.set()
		fake_build(stage_root, site_dir, root)

	def run_import(path: str, key: str, ready: threading.Event) -> None:
		ready.set()
		try:
			results[key] = scripts.import_publication_bundle.import_publication_bundle(
				path, str(tmp_path), controlled_build
			)
		except BaseException as error:
			errors[key] = error

	first_thread = threading.Thread(
		target=run_import, args=(first, "first", threading.Event())
	)
	first_thread.start()
	assert build_started.wait(2)
	second_thread = threading.Thread(
		target=run_import, args=(second, "second", second_ready)
	)
	second_thread.start()
	assert second_ready.wait(2)
	assert not second_build_started.is_set()
	release_first.set()
	first_thread.join(2)
	second_thread.join(2)

	assert results["first"]["status"] == "imported"
	assert isinstance(errors["second"], RuntimeError)
	assert len(calls) == 1


#============================================
def test_crashed_commit_is_reconciled_before_next_import(
	tmp_path: pathlib.Path,
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""A crash before record installation is rolled back before retry can succeed."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-crash-recovery")
	record_path = tmp_path / "data" / "publications" / f"{REPORT_DATE}.json"
	real_replace = scripts.import_publication_bundle.os.replace

	class SimulatedCrash(BaseException):
		"""Represent process loss at one atomic commit boundary."""

	def crash_before_record(source: str, destination: str) -> None:
		if os.path.basename(source) == "publication.json" and destination == str(record_path):
			raise SimulatedCrash()
		real_replace(source, destination)

	monkeypatch.setattr(scripts.import_publication_bundle.os, "replace", crash_before_record)
	with pytest.raises(SimulatedCrash):
		scripts.import_publication_bundle.import_publication_bundle(
			bundle_path, str(tmp_path), fake_build
		)
	monkeypatch.undo()

	assert not record_path.exists()
	assert tuple((tmp_path / "generated" / "staging").iterdir())
	result = scripts.import_publication_bundle.import_publication_bundle(
		bundle_path, str(tmp_path), fake_build
	)

	assert result["status"] == "imported"
	assert not tuple((tmp_path / "generated" / "staging").iterdir())


#============================================
@pytest.mark.parametrize(
	("field", "message"),
	(
		("context_chars", "context"),
		("excerpt_chars", "excerpt"),
		("commit_subject_chars", "subject"),
	),
)
def test_rehashed_projection_cannot_exceed_declared_limits(
	tmp_path: pathlib.Path,
	field: str,
	message: str,
) -> None:
	"""Projection limits bind independently even after a producer-style rehash."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, f"run-limit-{field}")
	projection_path = pathlib.Path(bundle_path) / "editorial_projection.json"
	projection = json.loads(projection_path.read_text(encoding="utf-8"))
	projection["projection_limits"][field] = 1
	rehash_projection_bundle(bundle_path, projection)

	with pytest.raises(RuntimeError, match=message):
		scripts.import_publication_bundle.import_publication_bundle(
			bundle_path, str(tmp_path), fake_build
		)


#============================================
def test_candidate_projection_identity_is_bound_to_bundle(
	tmp_path: pathlib.Path,
) -> None:
	"""Each candidate summary must describe the exact projection it was judged against."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-candidate-projection")
	bundle_file = pathlib.Path(bundle_path) / "bundle.json"
	bundle = json.loads(bundle_file.read_text(encoding="utf-8"))
	bundle["candidates"][0]["projection_id"] = "0" * 64
	bundle["bundle_id"] = scripts.import_publication_bundle.bundle_identity(bundle)
	write_json(bundle_file, bundle)

	with pytest.raises(RuntimeError, match="candidate projection"):
		scripts.import_publication_bundle.import_publication_bundle(
			bundle_path, str(tmp_path), fake_build
		)


#============================================
def test_bundle_object_contract_rejects_unknown_fields(
	tmp_path: pathlib.Path,
) -> None:
	"""The v2 bundle contract rejects fields from an unrecognized producer revision."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-exact-fields")
	bundle_file = pathlib.Path(bundle_path) / "bundle.json"
	bundle = json.loads(bundle_file.read_text(encoding="utf-8"))
	bundle["candidates"][0]["unexpected"] = True
	bundle["bundle_id"] = scripts.import_publication_bundle.bundle_identity(bundle)
	write_json(bundle_file, bundle)

	with pytest.raises(RuntimeError, match="unsupported fields"):
		scripts.import_publication_bundle.import_publication_bundle(
			bundle_path, str(tmp_path), fake_build
		)

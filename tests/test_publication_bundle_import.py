"""Final-only bundle validation, idempotency, and transaction tests."""
# Standard Library
import hashlib
import os
import json
import pathlib
import threading

# PIP3 modules
import pytest

# local repo modules
import scripts.import_publication_bundle
import scripts.bundle_snapshot
import scripts.maker_activation
import scripts.publication_record
import scripts.publication_transaction
import scripts.site_deployment
import scripts.publication_article_projection
import scripts.publication_surface
REPORT_DATE = "2026-08-23"
ASSET_NAME = "alpha.bin"
ASSET_BYTES = b"offline screenshot bytes"
def write_json(path: pathlib.Path, value: dict) -> None:
	"""Write one stable inline JSON test artifact."""
	path.write_bytes(scripts.canonical_json.stable_json_bytes(value))
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
def make_repository_evidence(repository: str, suffix: str) -> tuple[dict, dict, dict]:
	"""Return matching mirror, activity, and evidence-item records."""
	owner, name = repository.split("/", 1)
	commit_id = suffix * 40
	parent_id = chr(ord(suffix) + 1) * 40
	content = f"{repository} moved publication ownership into one exact contract."
	mirror = {
		"repository": repository,
		"repository_url": f"https://github.com/{repository}",
		"clone_url": f"https://github.com/{repository}.git",
		"created_at": "2020-01-01T00:00:00Z",
		"is_fork": False,
		"roster_id": "e" * 64,
		"cache_path": f"/cache/{owner}/{name}",
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
		"is_fork": False,
		"lifecycle_events": [
			{
				"event_type": "repository_created",
				"source": "github_owner_roster",
				"occurred_at": "2020-01-01T00:00:00Z",
				"occurred_in_report_window": False,
			}
		],
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

def make_bundle(root: pathlib.Path, run_id: str) -> str:
	"""Write one complete inline final-only contract bundle with one declared asset."""
	activation = scripts.maker_activation.load_maker_activation()
	bundle_dir = root / f"bundle-{run_id}"
	(bundle_dir / "assets").mkdir(parents=True)
	repository_roster = {
		"schema_version": "vosslab.daily-blog.repository-roster.v1",
		"owner": "vosslab",
		"repositories": [
			{
				"repository": repository,
				"repository_url": f"https://github.com/{repository}",
				"clone_url": f"https://github.com/{repository}.git",
				"created_at": "2020-01-01T00:00:00Z",
				"is_fork": False,
			}
			for repository in ("vosslab/alpha", "vosslab/beta", "vosslab/quiet-repository")
		],
	}
	roster_content = dict(repository_roster)
	repository_roster["roster_id"] = scripts.import_publication_bundle.hash_value(roster_content)
	records = [
		make_repository_evidence("vosslab/alpha", "a"),
		make_repository_evidence("vosslab/beta", "c"),
	]
	daily_active_roster = {
		"owner": "vosslab",
		"report_date": REPORT_DATE,
		"repository_roster_id": repository_roster["roster_id"],
		"repositories": [
			{
				"repository": repository,
				"commits": [{
					"sha": suffix * 40,
					"author_timestamp": "2026-08-23T12:00:00Z",
					"author_name": "Voss Lab",
					"message": "Daily work",
					"url": f"https://github.com/{repository}/commit/{suffix * 40}",
				}],
			}
			for repository, suffix in (("vosslab/alpha", "a"), ("vosslab/beta", "c"))
		],
	}
	daily_active_roster["active_roster_id"] = scripts.import_publication_bundle.hash_value(
		daily_active_roster
	)
	mirrors = [record[0] for record in records]
	for mirror in mirrors:
		mirror["roster_id"] = repository_roster["roster_id"]
	activity = [record[1] for record in records]
	items = [record[2] for record in records]
	asset_item = dict(records[0][2])
	asset_item.update(
		{
			"kind": "screenshot",
			"authority_level": "visual_support",
			"authority_rank": 200,
			"asset_path": f"assets/{ASSET_NAME}",
			"publish_path": f"../../assets/publications/{REPORT_DATE}/{ASSET_NAME}",
		}
	)
	asset_item["evidence_id"] = scripts.import_publication_bundle.evidence_item_identity(asset_item)
	items.append(asset_item)
	unselected_asset_item = dict(asset_item)
	unselected_asset_item.update({
		"asset_path": "assets/unselected.bin",
		"publish_path": f"../../assets/publications/{REPORT_DATE}/unselected.bin",
	})
	unselected_asset_item["content"] += " This screenshot remains outside the survivor surface."
	unselected_asset_item["content_hash"] = scripts.import_publication_bundle.sha256_bytes(
		unselected_asset_item["content"].encode("utf-8")
	)
	unselected_asset_item["evidence_id"] = scripts.import_publication_bundle.evidence_item_identity(
		unselected_asset_item
	)
	items.append(unselected_asset_item)
	(bundle_dir / "assets" / ASSET_NAME).write_bytes(ASSET_BYTES)
	evidence = {
		"schema_version": "vosslab.daily-blog.evidence.v4",
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
			"created_at": record[1]["lifecycle_events"][0]["occurred_at"],
			"created_in_report_window": False,
			"is_fork": False,
			"story_signals": [],
		}
		for record in records
	]
	excerpts = []
	for item in items:
		if item["asset_path"] == "assets/unselected.bin":
			continue
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
		"schema_version": "vosslab.daily-blog.editorial-projection.v2",
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
		+ f"I kept the account tied to [vosslab/alpha](https://github.com/vosslab/alpha) exact objects. <!-- evidence: {items[0]['evidence_id']} -->\n\n"
		+ "<!-- more -->\n\n"
		+ "## Publication state\n\n"
		+ f"I retained a bounded work log. <!-- evidence: {items[1]['evidence_id']} -->\n"
		+ "\n## Evidence trail\n\n"
		+ (
			"I kept the visible record tied to the same small, inspectable boundary. " * 35
		)
		+ f"<!-- evidence: {items[0]['evidence_id']} -->\n\n"
		+ f"![Selected proof]({asset_item['publish_path']})\n\n"
		+ "## Project coverage\n\n"
		+ (
			f"vosslab/alpha and vosslab/beta both remain in this bounded publication record. "
			f"<!-- evidence: {items[1]['evidence_id']} -->\n"
		)
	)
	post_hash = scripts.import_publication_bundle.sha256_bytes(post.encode("utf-8"))
	surface = {
		"schema_version": "vosslab.daily-blog.publication-surface.v1",
		"surface_id": "",
		"report_date": REPORT_DATE,
		"timezone": "America/Chicago",
		"aggregate_packet_id": evidence["packet_id"],
		"source_packet_ids": scripts.publication_surface.reconstruct_source_packet_ids(evidence),
		"repositories": sorted(record["repository"] for record in repositories),
		"source_artifacts": [
			{"kind": "DailyOutline", "artifact_id": "artifact-" + "b" * 24, "content_hash": "b" * 64},
			{"kind": "RepoStory", "artifact_id": "artifact-" + "c" * 24, "content_hash": "c" * 64},
		],
		"editorial_projection_id": projection["projection_id"],
		"allowed_evidence_ids": sorted({excerpt["evidence_id"] for excerpt in excerpts}),
		"allowed_images": [{
			"evidence_id": asset_item["evidence_id"],
			"asset_path": asset_item["asset_path"],
			"publish_path": asset_item["publish_path"],
		}],
	}
	surface["surface_id"] = scripts.publication_surface.surface_id(surface)
	bundle = {
		"schema_version": scripts.import_publication_bundle.BUNDLE_SCHEMA_VERSION,
		"bundle_sha256": "",
		"best_artifact_id": "artifact-" + "a" * 24,
		"report_date": REPORT_DATE,
		"timezone": "America/Chicago",
		"created_at": "2026-08-24T08:00:00Z",
		"generator": {
			"run_id": run_id,
			"revision": "f" * 64,
			"version": "daily-blog-generator-v2",
		},
		"contracts": {
			"evidence_schema": "vosslab.daily-blog.evidence.v4",
			"editorial_projection_schema": "vosslab.daily-blog.editorial-projection.v2",
			"prompt_version": "daily-blog-prompts-v4",
			"rubric_version": "daily-blog-rubric-v4",
		"candidate_validation": {
				"name": scripts.validate_daily_post.V4_MAKER_POLICY.name,
				"version": scripts.validate_daily_post.V4_MAKER_POLICY.version,
			"sha256": scripts.validate_daily_post.V4_MAKER_POLICY.digest,
		},
		"publication_source_safety": scripts.publication_source_safety.policy_identity(),
	},
		"evidence": {
			"path": "evidence.json",
			"packet_id": evidence["packet_id"],
			"sha256": scripts.import_publication_bundle.hash_value(evidence),
		},
		"repository_roster": {
			"path": "repository_roster.json",
			"roster_id": repository_roster["roster_id"],
			"sha256": scripts.import_publication_bundle.hash_value(repository_roster),
		},
		"daily_active_roster": {
			"path": "daily_active_roster.json",
			"active_roster_id": daily_active_roster["active_roster_id"],
			"sha256": scripts.import_publication_bundle.hash_value(daily_active_roster),
		},
		"editorial_projection": {
			"path": "editorial_projection.json",
			"projection_id": projection["projection_id"],
			"sha256": scripts.import_publication_bundle.hash_value(projection),
		},
		"publication_surface": {
			"path": "publication_surface.json",
			"surface_id": surface["surface_id"],
			"sha256": scripts.import_publication_bundle.hash_value(surface),
		},
		"post": {
			"path": "post.md",
			"sha256": post_hash,
			"artifact_id": "artifact-" + "a" * 24,
		},
		"assets": [
			{
				"path": asset_item["asset_path"],
				"sha256": scripts.import_publication_bundle.sha256_bytes(ASSET_BYTES),
				"git_blob_hash": asset_item["blob_hash"],
				"evidence_id": asset_item["evidence_id"],
				"publish_path": asset_item["publish_path"],
			}
		],
		"maker_activation": {
			"activation_id": activation["activation_id"],
			"editorial_prompt_contract_sha256": activation["editorial_prompt_contract_sha256"],
		},
		"editorial_prompt_contract": activation["editorial_prompt_contract"],
	}
	bundle["bundle_sha256"] = scripts.import_publication_bundle.bundle_sha256(bundle)
	write_json(bundle_dir / "evidence.json", evidence)
	write_json(bundle_dir / "repository_roster.json", repository_roster)
	write_json(bundle_dir / "daily_active_roster.json", daily_active_roster)
	write_json(bundle_dir / "editorial_projection.json", projection)
	write_json(bundle_dir / "publication_surface.json", surface)
	(bundle_dir / "post.md").write_text(post, encoding="utf-8")
	write_json(bundle_dir / "bundle.json", bundle)
	return str(bundle_dir)
def bundle_transfer(bundle_path: str) -> bytes:
	"""Encode one existing offline bundle as the producer stdin transport."""
	bundle_root = pathlib.Path(bundle_path)
	bundle = json.loads((bundle_root / "bundle.json").read_text(encoding="utf-8"))
	paths = (
		"bundle.json",
		"daily_active_roster.json",
		"editorial_projection.json",
		"evidence.json",
		"publication_surface.json",
		"post.md",
		"repository_roster.json",
		*(asset["path"] for asset in bundle["assets"]),
	)
	contents_by_path = {path: (bundle_root / path).read_bytes() for path in paths}
	entries = [
		{"path": path, "size": len(contents_by_path[path]),
			"sha256": hashlib.sha256(contents_by_path[path]).hexdigest()}
		for path in sorted(paths)
	]
	header = {
		"schema_version": scripts.bundle_snapshot.TRANSFER_SCHEMA_VERSION,
		"report_date": bundle["report_date"],
		"bundle_sha256": bundle["bundle_sha256"],
		"entries": entries,
	}
	header_bytes = json.dumps(header, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")
	return (
		scripts.bundle_snapshot.TRANSFER_MAGIC
		+ len(header_bytes).to_bytes(8, "big")
		+ header_bytes
		+ b"".join(contents_by_path[path] for path in sorted(paths))
	)
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
	bundle["bundle_sha256"] = scripts.import_publication_bundle.bundle_sha256(bundle)
	write_json(bundle_dir / "bundle.json", bundle)
def rehash_post_bundle(bundle_path: str, post: str) -> None:
	"""Rehash an intentionally changed selected post and enclosing bundle."""
	bundle_dir = pathlib.Path(bundle_path)
	post_hash = scripts.import_publication_bundle.sha256_bytes(post.encode("utf-8"))
	(bundle_dir / "post.md").write_text(post, encoding="utf-8")
	bundle = json.loads((bundle_dir / "bundle.json").read_text(encoding="utf-8"))
	bundle["post"]["sha256"] = post_hash
	bundle["bundle_sha256"] = scripts.import_publication_bundle.bundle_sha256(bundle)
	write_json(bundle_dir / "bundle.json", bundle)
def fake_build(stage_root: str, site_dir: str, _root: str) -> None:
	"""Create one dated reader article with the staged Markdown body."""
	os.makedirs(site_dir)
	post_path = os.path.join(stage_root, "docs", "blog", "posts", f"{REPORT_DATE}.md")
	with open(post_path, encoding="utf-8") as handle:
		post = handle.read()
	rendered = scripts.publication_article_projection.render_staged_post_body(
		post,
		os.path.join(stage_root, "mkdocs.yml"),
	)
	with open(os.path.join(site_dir, "index.html"), "w", encoding="utf-8") as handle:
		handle.write(
			f'<time datetime="{REPORT_DATE} 00:00:00+00:00"></time>'
			f'<article class="md-content__inner md-typeset">{rendered}</article>'
		)

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

def test_import_archives_only_bytes_accepted_during_validation(
	tmp_path: pathlib.Path,
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""A source swap after validation cannot alter the archive or published asset."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-one")
	source_asset = pathlib.Path(bundle_path) / "assets" / ASSET_NAME

	def swap_source_after_validation(_root: str) -> None:
		source_asset.write_bytes(b"swapped after validation")

	monkeypatch.setattr(
		scripts.publication_transaction,
		"reconcile_interrupted_staging",
		swap_source_after_validation,
	)
	scripts.import_publication_bundle.import_publication_bundle(
		bundle_path,
		str(tmp_path),
		fake_build,
	)
	archive = tmp_path / "data" / "publication_bundles" / REPORT_DATE
	published_asset = tmp_path / "docs" / "assets" / "publications" / REPORT_DATE / ASSET_NAME
	assert (
		(archive / "assets" / ASSET_NAME).read_bytes()
		== published_asset.read_bytes()
		== ASSET_BYTES
	)

def test_import_v4_accepts_one_uncited_maker_reflection(tmp_path: pathlib.Path) -> None:
	"""The maker policy permits one reflective paragraph without a citation."""
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
	result = scripts.import_publication_bundle.import_publication_bundle(
		bundle_path, str(tmp_path), fake_build
	)
	assert result["status"] == "imported"


#============================================
def test_renderer_publishes_producer_supplied_nonsense_when_mkdocs_accepts_it(
	tmp_path: pathlib.Path,
) -> None:
	"""The display repository has no editorial or Markdown-readability gate."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-renderable-nonsense")
	nonsense = "this is producer-approved nonsense ::: ]]]\n"
	rehash_post_bundle(bundle_path, nonsense)
	def accepting_mkdocs(_stage_root: str, site_dir: str, _root: str) -> None:
		"""Model MkDocs accepting arbitrary producer Markdown."""
		os.makedirs(site_dir)
		pathlib.Path(site_dir, "index.html").write_text("rendered", encoding="utf-8")

	result = scripts.import_publication_bundle.import_publication_bundle(
		bundle_path, str(tmp_path), accepting_mkdocs,
	)

	assert result["status"] == "imported"
	assert (tmp_path / "docs" / "blog" / "posts" / f"{REPORT_DATE}.md").read_text() == nonsense

def test_generator_source_fingerprint_accepts_64_hex_identity(
	tmp_path: pathlib.Path,
) -> None:
	"""Publisher records retain a producer source fingerprint longer than a Git SHA."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-source-fingerprint")
	bundle_file = pathlib.Path(bundle_path) / "bundle.json"
	bundle = json.loads(bundle_file.read_text(encoding="utf-8"))
	bundle["generator"]["revision"] = "0" * 64
	bundle["bundle_sha256"] = scripts.import_publication_bundle.bundle_sha256(bundle)
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
def test_bundle_rejects_rechecksummed_noncanonical_json_before_staging(
	tmp_path: pathlib.Path,
) -> None:
	"""An equivalent manifest still needs its one canonical archival byte form."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-noncanonical-json")
	bundle_file = pathlib.Path(bundle_path) / "bundle.json"
	bundle = json.loads(bundle_file.read_text(encoding="utf-8"))
	bundle["bundle_sha256"] = scripts.import_publication_bundle.bundle_sha256(bundle)
	bundle_file.write_text(json.dumps(bundle, indent=2, sort_keys=True), encoding="utf-8")
	with pytest.raises(RuntimeError, match="canonical JSON bytes"):
		scripts.import_publication_bundle.import_publication_bundle(
			bundle_path, str(tmp_path), fake_build
		)
def test_transfer_snapshot_imports_the_same_sealed_bundle(tmp_path: pathlib.Path) -> None:
	"""The stdin transport reaches the ordinary validation and publication boundary."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-stdin-transfer")
	snapshot = scripts.bundle_snapshot.BundleSnapshot.from_transfer_bytes(bundle_transfer(bundle_path))
	result = scripts.import_publication_bundle.import_publication_snapshot(snapshot, str(tmp_path), fake_build)
	assert result["status"] == "imported"
	assert (tmp_path / "data" / "publication_bundles" / REPORT_DATE / "post.md").is_file()


#============================================
def test_surface_stages_only_selected_aggregate_screenshot(tmp_path: pathlib.Path) -> None:
	"""One selected screenshot imports although aggregate evidence has another one."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-selected-surface-image")
	scripts.import_publication_bundle.import_publication_bundle(
		bundle_path, str(tmp_path), fake_build
	)
	archive = tmp_path / "data" / "publication_bundles" / REPORT_DATE / "assets"
	installed = tmp_path / "docs" / "assets" / "publications" / REPORT_DATE
	assert (archive / ASSET_NAME).is_file()
	assert (installed / ASSET_NAME).is_file()
	assert not (archive / "unselected.bin").exists()
	assert not (installed / "unselected.bin").exists()


#============================================
def test_idempotency_rejects_tampered_archived_asset(tmp_path: pathlib.Path) -> None:
	"""A bundle checksum cannot hide asset-byte drift in the date-owned archive."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-archive-drift")
	scripts.import_publication_bundle.import_publication_bundle(
		bundle_path, str(tmp_path), fake_build
	)
	archived_asset = (
		tmp_path
		/ "data"
		/ "publication_bundles"
		/ REPORT_DATE
		/ "assets"
		/ ASSET_NAME
	)
	archived_asset.write_bytes(b"tampered archive asset")

	with pytest.raises(RuntimeError, match="archive has different content"):
		scripts.import_publication_bundle.import_publication_bundle(
			bundle_path, str(tmp_path), fake_build
		)


#============================================
def test_idempotency_rejects_tampered_archived_publication_surface(tmp_path: pathlib.Path) -> None:
	"""The survivor authority is an exact archived idempotency input."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-archive-surface-drift")
	scripts.import_publication_bundle.import_publication_bundle(
		bundle_path, str(tmp_path), fake_build
	)
	archived_surface = (
		tmp_path / "data" / "publication_bundles" / REPORT_DATE / "publication_surface.json"
	)
	archived_surface.write_bytes(b"{}\n")

	with pytest.raises(RuntimeError, match="archive has different content"):
		scripts.import_publication_bundle.import_publication_bundle(
			bundle_path, str(tmp_path), fake_build
		)

def test_conflicting_bundle_for_published_date_is_rejected(tmp_path: pathlib.Path) -> None:
	"""A report date changes only through the explicit replacement path."""
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

def test_confirmed_replacement_installs_one_new_date_owned_publication(
	tmp_path: pathlib.Path,
) -> None:
	"""Explicit replacement leaves only the new date-owned publication active."""
	initialize_site(tmp_path)
	first = make_bundle(tmp_path, "run-first")
	second = make_bundle(tmp_path, "run-replacement")
	scripts.import_publication_bundle.import_publication_bundle(first, str(tmp_path), fake_build)
	record_path = tmp_path / "data" / "publications" / f"{REPORT_DATE}.json"
	current = json.loads(record_path.read_text(encoding="utf-8"))
	legacy = {key: current[key] for key in scripts.publication_record.HISTORICAL_PUBLICATION_RECORD_FIELDS}
	legacy["schema_version"] = scripts.publication_record.HISTORICAL_PUBLICATION_SCHEMA_VERSION
	write_json(record_path, legacy)
	scripts.import_publication_bundle.import_publication_bundle(
		second, str(tmp_path), fake_build, replace_existing=True
	)
	record = json.loads(record_path.read_text(encoding="utf-8"))
	archive = tmp_path / "data" / "publication_bundles" / REPORT_DATE
	post_path = tmp_path / "docs" / "blog" / "posts" / f"{REPORT_DATE}.md"

	assert scripts.publication_record.validate_publication_record(record) == record
	assert (archive / "post.md").read_bytes() == post_path.read_bytes() == (
		pathlib.Path(second) / "post.md"
	).read_bytes()

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
	"""A failed date-owned exchange restores every publisher-owned boundary."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-install-failure")
	original = publication_snapshot(tmp_path)
	real_exchange = scripts.atomic_paths.exchange_directories
	def fail_docs_exchange(first: str, second: str) -> None:
		if str(tmp_path / "docs") in (first, second):
			raise RuntimeError("synthetic source install failure")
		real_exchange(first, second)
	monkeypatch.setattr(scripts.atomic_paths, "exchange_directories", fail_docs_exchange)
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
	"""A presentation release retains the exact publication date beneath it."""
	initialize_site(tmp_path)
	bundle_path = make_bundle(tmp_path, "run-derived-site")
	first = scripts.import_publication_bundle.import_publication_bundle(
		bundle_path, str(tmp_path), fake_build
	)
	scripts.site_deployment.publish_site(str(tmp_path), fake_build)
	second = scripts.import_publication_bundle.import_publication_bundle(
		bundle_path, str(tmp_path), fake_build
	)
	assert first["bundle_sha256"] == second["bundle_sha256"]
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

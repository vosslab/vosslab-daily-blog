#!/usr/bin/env python3
"""Place producer-owned publication bytes, render them with MkDocs, and deploy."""

import datetime
import os
import pathlib
import shutil
import subprocess
import sys
import uuid

import scripts.bundle_snapshot
import scripts.canonical_json
import scripts.publication_import_cli
import scripts.publication_import_protocol
import scripts.publication_staging
import scripts.publication_transaction
import scripts.repository_paths
import scripts.site_deployment


REPO_ROOT = scripts.repository_paths.repository_root(__file__)


def utc_now() -> str:
	"""Return a stable UTC timestamp without microseconds."""
	return datetime.datetime.now(datetime.UTC).replace(microsecond=0).isoformat().replace(
		"+00:00", "Z"
	)


def _asset_paths(bundle: dict) -> set[str]:
	"""Return confined direct asset routes without interpreting their meaning."""
	assets = bundle.get("assets")
	if not isinstance(assets, list):
		raise RuntimeError("Publication transfer asset routing is invalid.")
	paths = set()
	for asset in assets:
		if not isinstance(asset, dict) or not isinstance(asset.get("path"), str):
			raise RuntimeError("Publication transfer asset routing is invalid.")
		path = asset["path"]
		pure = pathlib.PurePosixPath(path)
		if (
			pure.is_absolute() or len(pure.parts) != 2 or pure.parts[0] != "assets"
			or pure.name in {"", ".", ".."}
		):
			raise RuntimeError("Publication asset path is not confined.")
		paths.add(path)
	if len(paths) != len(assets):
		raise RuntimeError("Publication transfer contains duplicate asset routes.")
	return paths


def _receive_snapshot(
	snapshot: scripts.bundle_snapshot.BundleSnapshot,
) -> tuple[dict, bytes, dict[str, bytes]]:
	"""Receive authoritative producer bytes and validate only placement mechanics."""
	sealed = {"bundle.json": snapshot.read("bundle.json")}
	bundle = scripts.canonical_json.load_stable_json(
		sealed["bundle.json"], "Publication bundle routing manifest",
	)
	if not isinstance(bundle, dict):
		raise RuntimeError("Publication bundle routing manifest must be an object.")
	report_date = bundle.get("report_date")
	try:
		if (
			not isinstance(report_date, str)
			or datetime.date.fromisoformat(report_date).isoformat() != report_date
		):
			raise ValueError
	except ValueError as error:
		raise RuntimeError("Publication transfer report date is invalid.") from error
	post_manifest = bundle.get("post")
	if not isinstance(post_manifest, dict) or post_manifest.get("path") != "post.md":
		raise RuntimeError("Publication transfer has no fixed post destination.")
	asset_paths = _asset_paths(bundle)
	sealed.update(snapshot.read_declared_assets(asset_paths))
	sealed["post.md"] = snapshot.read("post.md")
	if snapshot.transfer_header is not None and (
		snapshot.transfer_header["report_date"] != report_date
		or snapshot.transfer_header["bundle_sha256"] != bundle.get("bundle_sha256")
	):
		raise RuntimeError("Publication transfer routing identity is inconsistent.")
	return bundle, sealed["post.md"], sealed


def validate_snapshot(
	snapshot: scripts.bundle_snapshot.BundleSnapshot,
) -> tuple[dict, dict, dict, dict, bytes, dict[str, bytes]]:
	"""Receive one held snapshot using the historical internal tuple shape."""
	try:
		bundle, post, sealed = _receive_snapshot(snapshot)
		return bundle, {}, {}, {}, post, sealed
	except scripts.publication_import_protocol.ImportProtocolError:
		raise
	except (RuntimeError, UnicodeDecodeError) as error:
		raise scripts.publication_import_protocol.ImportProtocolError(
			"snapshot_rejected", "receive", str(error),
		) from error


def validate_bundle(bundle_path: str) -> tuple[dict, dict, dict, dict, bytes, dict[str, bytes]]:
	"""Hold a physical producer directory while receiving its routed bytes."""
	with scripts.bundle_snapshot.BundleSnapshot(bundle_path) as snapshot:
		return validate_snapshot(snapshot)


def strict_mkdocs_build(stage_root: str, site_dir: str, root: str) -> None:
	"""Ask MkDocs to decide whether the staged source can be rendered."""
	venv_mkdocs = os.path.join(root, ".venv", "bin", "mkdocs")
	mkdocs = venv_mkdocs if os.path.isfile(venv_mkdocs) else shutil.which("mkdocs")
	if not mkdocs:
		raise RuntimeError("MkDocs executable is unavailable.")
	result = subprocess.run(
		[
			mkdocs, "build", "--strict", "--config-file",
			os.path.join(stage_root, "mkdocs.yml"), "--site-dir", site_dir,
		],
		cwd=stage_root,
		check=False,
		text=True,
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE,
		timeout=600,
	)
	if result.returncode:
		raise RuntimeError(
			f"Strict staged MkDocs build failed: {result.stderr.strip() or result.stdout.strip()}"
		)


def _installed_bytes_match(
	root: str, bundle: dict, post: bytes, sealed: dict[str, bytes],
) -> bool:
	"""Return whether the final Markdown/assets are already rendered for this date."""
	report_date = bundle["report_date"]
	post_path = os.path.join(root, "docs", "blog", "posts", f"{report_date}.md")
	if not os.path.isfile(post_path):
		return False
	with open(post_path, "rb") as handle:
		if handle.read() != post:
			return False
	asset_directory = os.path.join(root, "docs", "blog", "posts", report_date)
	expected = {
		pathlib.PurePosixPath(asset["path"]).name: sealed[asset["path"]]
		for asset in bundle["assets"]
	}
	actual = set(os.listdir(asset_directory)) if os.path.isdir(asset_directory) else set()
	if actual != set(expected):
		return False
	for name, contents in expected.items():
		path = os.path.join(asset_directory, name)
		if os.path.islink(path) or not os.path.isfile(path):
			return False
		with open(path, "rb") as handle:
			if handle.read() != contents:
				return False
	return scripts.site_deployment.site_serves_publication(root, report_date)


def _new_stage_root(root: str, report_date: str) -> str:
	"""Create one disposable renderer stage."""
	parent = os.path.join(root, "generated", "staging")
	os.makedirs(parent, exist_ok=True)
	path = os.path.join(parent, f"import-{report_date}-{uuid.uuid4().hex}")
	os.makedirs(path)
	return path


def import_publication_snapshot(
	snapshot: scripts.bundle_snapshot.BundleSnapshot,
	root: str = REPO_ROOT,
	build_function: object = strict_mkdocs_build,
	replace_existing: bool = False,
) -> dict:
	"""Receive, place, render, deploy, and report one producer snapshot."""
	bundle, _evidence, _projection, _surface, post, sealed = validate_snapshot(snapshot)
	return _import_received(bundle, post, sealed, root, build_function)


def import_publication_bundle(
	bundle_path: str,
	root: str = REPO_ROOT,
	build_function: object = strict_mkdocs_build,
	replace_existing: bool = False,
) -> dict:
	"""Receive and render a physical producer handoff directory."""
	with scripts.bundle_snapshot.BundleSnapshot(bundle_path) as snapshot:
		return import_publication_snapshot(snapshot, root, build_function, replace_existing)


def _import_received(
	bundle: dict, post: bytes, sealed: dict[str, bytes], root: str, build_function: object,
) -> dict:
	"""Install already-received bytes without persisting transfer JSON."""
	with scripts.publication_transaction.publisher_lock(root):
		scripts.publication_transaction.reconcile_interrupted_staging(root)
		if _installed_bytes_match(root, bundle, post, sealed):
			status = "idempotent"
		else:
			current = os.path.isfile(os.path.join(
				root, "docs", "blog", "posts", f"{bundle['report_date']}.md",
			))
			stage_root = _new_stage_root(root, bundle["report_date"])
			try:
				try:
					_stage, receipt = scripts.publication_staging.prepare_stage(
						root, stage_root, bundle, {}, {}, {}, post, sealed,
						build_function, utc_now(),
					)
				except RuntimeError as error:
					raise scripts.publication_import_protocol.ImportProtocolError(
						"staged_build_failed", "stage", str(error),
					) from error
				try:
					scripts.publication_transaction.commit_stage(root, stage_root, receipt)
				except RuntimeError as error:
					raise scripts.publication_import_protocol.ImportProtocolError(
						"commit_failed", "commit", str(error),
					) from error
			finally:
				if os.path.isdir(stage_root):
					shutil.rmtree(stage_root)
			status = "replaced" if current else "imported"
	return {
		"status": status,
		"bundle_sha256": bundle["bundle_sha256"],
		"report_date": bundle["report_date"],
	}


def main() -> None:
	"""Run the renderer's sole producer-facing import command."""
	args = scripts.publication_import_cli.parse_args()
	try:
		if args.bundle_stdin:
			snapshot = scripts.bundle_snapshot.BundleSnapshot.from_stream(sys.stdin.buffer)
			result = import_publication_snapshot(snapshot, replace_existing=args.replace_existing)
		else:
			result = import_publication_bundle(
				args.bundle_path, replace_existing=args.replace_existing,
			)
	except (RuntimeError, UnicodeDecodeError) as error:
		sys.stderr.buffer.write(scripts.publication_import_protocol.failure_envelope(error))
		raise SystemExit(1) from error
	print(scripts.publication_import_protocol.stable_success_text(result), end="")


if __name__ == "__main__":
	main()

"""Validate the survivor-scoped authority sealed into bundle v9."""

# Standard Library
import re
import pathlib

# local repo modules
import scripts.canonical_json


SURFACE_SCHEMA_VERSION = "vosslab.daily-blog.publication-surface.v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ARTIFACT_ID_RE = re.compile(r"^artifact-[0-9a-f]{24}$")
_CONTROL_CHARACTER_RE = re.compile(r"[\x00-\x1f\x7f]")


#============================================
def validate_direct_asset_path(value: object) -> str:
	"""Return one canonical direct bundle asset path.

	ASVS 5.3.2: producer-controlled asset paths still cross a repository
	boundary, so every consumer admits the same narrow spelling.
	"""
	if not isinstance(value, str) or _CONTROL_CHARACTER_RE.search(value):
		raise RuntimeError("Bundle asset path must be one canonical assets/<name> path.")
	if "\\" in value:
		raise RuntimeError("Bundle asset path must use canonical POSIX separators.")
	pure = pathlib.PurePosixPath(value)
	if (
		value != str(pure)
		or len(pure.parts) != 2
		or pure.parts[0] != "assets"
		or pure.name in {"", ".", ".."}
	):
		raise RuntimeError("Bundle asset path must be one canonical assets/<name> path.")
	return value


#============================================
def reconstruct_source_packet_ids(evidence: dict) -> list[str]:
	"""Return canonical IDs of the per-repository packets that formed evidence.

	The aggregate packet contains every member needed to deterministically rebuild
	each survivor packet.  This closes the otherwise unverifiable source-packet
	claim at the producer/publisher boundary.
	"""
	if not isinstance(evidence, dict):
		raise RuntimeError("Publication evidence must be one object.")
	repositories = sorted({
		item.get("repository") for item in evidence.get("activity", [])
		if isinstance(item, dict) and isinstance(item.get("repository"), str) and item["repository"]
	} or {
		item.get("repository") for item in evidence.get("items", [])
		if isinstance(item, dict) and isinstance(item.get("repository"), str) and item["repository"]
	})
	if not repositories:
		raise RuntimeError("Publication evidence has no reconstructable repositories.")
	common = {
		"schema_version": evidence.get("schema_version"),
		"report_date": evidence.get("report_date"),
		"timezone": evidence.get("timezone"),
		"complete": evidence.get("complete"),
		"collection_limits": evidence.get("collection_limits"),
	}
	identities = []
	for repository in repositories:
		packet = dict(common)
		packet["mirrors"] = [
			item for item in evidence.get("mirrors", [])
			if isinstance(item, dict) and item.get("repository") == repository
		]
		packet["activity"] = [
			item for item in evidence.get("activity", [])
			if isinstance(item, dict) and item.get("repository") == repository
		]
		packet["items"] = [
			item for item in evidence.get("items", [])
			if isinstance(item, dict) and item.get("repository") == repository
		]
		if not packet["items"]:
			raise RuntimeError("Publication evidence cannot reconstruct each survivor packet.")
		identities.append(scripts.canonical_json.hash_value(packet))
	return sorted(identities)


#============================================
def surface_id(value: dict) -> str:
	"""Return the canonical identity of a surface without its declared ID."""
	content = dict(value)
	content.pop("surface_id", None)
	return scripts.canonical_json.hash_value(content)


#============================================
def validate_surface(surface: object, evidence: dict, projection: dict, bundle: dict) -> dict:
	"""Return one exact surface whose authority matches sealed evidence and projection."""
	# ASVS 1.5.2 and 2.2.1: parse the producer authority with an exact schema.
	if not isinstance(surface, dict):
		raise RuntimeError("Publication surface must be one JSON object.")
	required = {
		"schema_version", "surface_id", "report_date", "timezone", "aggregate_packet_id",
		"source_packet_ids", "repositories", "source_artifacts", "editorial_projection_id",
		"allowed_evidence_ids", "allowed_images",
	}
	if set(surface) != required:
		raise RuntimeError("Publication surface fields are unsupported.")
	if surface["schema_version"] != SURFACE_SCHEMA_VERSION:
		raise RuntimeError("Publication surface schema is unsupported.")
	if surface["surface_id"] != surface_id(surface):
		raise RuntimeError("Publication surface identity does not match its contents.")
	if not isinstance(surface["surface_id"], str) or _SHA256_RE.fullmatch(surface["surface_id"]) is None:
		raise RuntimeError("Publication surface identity is invalid.")
	if surface["report_date"] != bundle["report_date"] or surface["timezone"] != bundle["timezone"]:
		raise RuntimeError("Publication surface report identity does not match the bundle.")
	if surface["aggregate_packet_id"] != evidence.get("packet_id"):
		raise RuntimeError("Publication surface packet identity does not match evidence.")
	if surface["editorial_projection_id"] != projection.get("projection_id"):
		raise RuntimeError("Publication surface projection identity does not match projection.")
	if projection.get("packet_id") != evidence.get("packet_id"):
		raise RuntimeError("Publication projection packet identity does not match evidence.")
	if (
		not isinstance(surface["source_packet_ids"], list)
		or not surface["source_packet_ids"]
		or not all(isinstance(value, str) and _SHA256_RE.fullmatch(value) for value in surface["source_packet_ids"])
		or surface["source_packet_ids"] != sorted(set(surface["source_packet_ids"]))
		or surface["source_packet_ids"] != reconstruct_source_packet_ids(evidence)
	):
		raise RuntimeError("Publication surface source packet identities are not reconstructable.")
	packet_repositories = {item.get("repository") for item in evidence.get("activity", []) if isinstance(item, dict)} or {
		item.get("repository") for item in evidence.get("items", []) if isinstance(item, dict)
	}
	if (
		not isinstance(surface["repositories"], list)
		or not all(isinstance(value, str) and value for value in surface["repositories"])
		or surface["repositories"] != sorted(packet_repositories)
	):
		raise RuntimeError("Publication surface repositories do not match projection coverage.")
	if not isinstance(surface["source_artifacts"], list) or not surface["source_artifacts"]:
		raise RuntimeError("Publication surface source artifacts are invalid.")
	artifact_ids = []
	artifact_kinds = []
	for artifact in surface["source_artifacts"]:
		if not isinstance(artifact, dict) or set(artifact) != {"kind", "artifact_id", "content_hash"}:
			raise RuntimeError("Publication surface source artifact fields are invalid.")
		if (
			artifact["kind"] not in {"DailyOutline", "RepoStory"}
			or not isinstance(artifact["artifact_id"], str)
			or _ARTIFACT_ID_RE.fullmatch(artifact["artifact_id"]) is None
			or not isinstance(artifact["content_hash"], str)
			or _SHA256_RE.fullmatch(artifact["content_hash"]) is None
		):
			raise RuntimeError("Publication surface source artifact values are invalid.")
		artifact_ids.append(artifact["artifact_id"])
		artifact_kinds.append(artifact["kind"])
	if artifact_ids != sorted(set(artifact_ids)) or artifact_kinds.count("DailyOutline") != 1 or "RepoStory" not in artifact_kinds:
		raise RuntimeError("Publication surface source artifacts are not one editorial survivor set.")
	allowed_ids = surface["allowed_evidence_ids"]
	if (
		not isinstance(allowed_ids, list) or not allowed_ids
		or not all(isinstance(value, str) and value for value in allowed_ids)
		or allowed_ids != sorted(set(allowed_ids))
	):
		raise RuntimeError("Publication surface evidence IDs are invalid.")
	projection_ids = sorted({excerpt.get("evidence_id") for excerpt in projection.get("excerpts", [])})
	if allowed_ids != projection_ids:
		raise RuntimeError("Publication surface evidence IDs do not exactly match projection excerpts.")
	items_by_id = {item.get("evidence_id"): item for item in evidence.get("items", []) if isinstance(item, dict)}
	if any(identifier not in items_by_id for identifier in allowed_ids):
		raise RuntimeError("Publication surface permits evidence absent from its packet.")
	images = surface["allowed_images"]
	if not isinstance(images, list):
		raise RuntimeError("Publication surface images are invalid.")
	asset_paths = set()
	publish_paths = set()
	image_keys = []
	for image in images:
		if not isinstance(image, dict) or set(image) != {"evidence_id", "asset_path", "publish_path"}:
			raise RuntimeError("Publication surface image fields are invalid.")
		if not all(isinstance(image[key], str) and image[key] for key in image):
			raise RuntimeError("Publication surface image values are invalid.")
		validate_direct_asset_path(image["asset_path"])
		item = items_by_id.get(image["evidence_id"])
		# ASVS 2.2.3/5.3.2: bind every accepted image to its exact sealed screenshot path.
		if (
			image["evidence_id"] not in allowed_ids or item is None or item.get("kind") != "screenshot"
			or item.get("asset_path") != image["asset_path"]
			or item.get("publish_path") != image["publish_path"]
		):
			raise RuntimeError("Publication surface image does not match allowed screenshot evidence.")
		if image["asset_path"] in asset_paths or image["publish_path"] in publish_paths:
			raise RuntimeError("Publication surface image paths are duplicated.")
		asset_paths.add(image["asset_path"])
		publish_paths.add(image["publish_path"])
		image_keys.append((image["evidence_id"], image["asset_path"], image["publish_path"]))
	if image_keys != sorted(image_keys):
		raise RuntimeError("Publication surface images are not canonical.")
	return surface


#============================================
def allowed_asset_paths(surface: dict) -> set[str]:
	"""Return the exact survivor-scoped bundle asset paths."""
	return {image["asset_path"] for image in surface["allowed_images"]}


#============================================
def allowed_publish_paths(surface: dict) -> set[str]:
	"""Return the exact survivor-scoped post image destinations."""
	return {image["publish_path"] for image in surface["allowed_images"]}

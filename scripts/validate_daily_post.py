#!/usr/bin/env python3
"""Validate one bundle-backed MkDocs daily work-log post."""

# Standard Library
import re
import json
import argparse

# PIP3 modules
import yaml


FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
EVIDENCE_COMMENT_RE = re.compile(r"<!--\s*evidence:\s*([^>]+?)\s*-->")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FENCE_RE = re.compile(r"(^|\n)\s*(?:`{3,}|~{3,})")


#============================================
def parse_args() -> argparse.Namespace:
	"""Parse post, evidence, and bundle paths."""
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("-c", "--candidate", dest="candidate_path", required=True)
	parser.add_argument("-e", "--evidence", dest="evidence_path", required=True)
	parser.add_argument("-b", "--bundle", dest="bundle_path", required=True)
	args = parser.parse_args()
	return args


#============================================
def parse_front_matter(post: str) -> tuple[dict, str]:
	"""Parse opening YAML front matter and return the Markdown body."""
	match = FRONT_MATTER_RE.search(post)
	if not match:
		raise RuntimeError("post must begin with YAML front matter")
	value = yaml.safe_load(match.group(1))
	if not isinstance(value, dict):
		raise RuntimeError("post front matter must be a mapping")
	body = post[match.end():]
	return value, body


#============================================
def evidence_ids_in_post(post: str) -> set[str]:
	"""Return all packet evidence IDs named in provenance comments."""
	identifiers = set()
	for match in EVIDENCE_COMMENT_RE.finditer(post):
		for value in match.group(1).split(","):
			identifier = value.strip()
			if identifier:
				identifiers.add(identifier)
	return identifiers


#============================================
def prose_blocks(body: str) -> list[str]:
	"""Return factual prose blocks that require provenance comments."""
	blocks = []
	for block in re.split(r"\n\s*\n", body.strip()):
		text = block.strip()
		if not text or text == "<!-- more -->":
			continue
		if text.startswith("#") or text.startswith("!["):
			continue
		if text.startswith("<!--") and text.endswith("-->"):
			continue
		blocks.append(text)
	return blocks


#============================================
def validate_post(post: str, evidence: dict, bundle: dict) -> list[str]:
	"""Return every deterministic post, front-matter, and provenance issue."""
	issues = []
	try:
		front_matter, body = parse_front_matter(post)
	except RuntimeError as error:
		return [str(error)]
	required = ("date", "slug", "publication_quality", "generator_run", "evidence_manifest")
	for key in required:
		if key not in front_matter:
			issues.append(f"front matter is missing {key}")
	report_date = str(bundle["report_date"])
	if str(front_matter.get("date") or "") != report_date:
		issues.append("front matter date does not match the bundle")
	if evidence.get("report_date") != report_date:
		issues.append("evidence date does not match the bundle")
	slug = str(front_matter.get("slug") or "")
	if not SLUG_RE.fullmatch(slug):
		issues.append("front matter slug must use lowercase ASCII words and hyphens")
	if front_matter.get("publication_quality") != bundle["publication_quality"]:
		issues.append("front matter publication_quality does not match the bundle")
	if front_matter.get("generator_run") != bundle["generator"]["run_id"]:
		issues.append("front matter generator_run does not match the bundle")
	if front_matter.get("evidence_manifest") != "evidence.json":
		issues.append("front matter evidence_manifest must name evidence.json")
	if len(re.findall(r"^#\s+\S", body, flags=re.MULTILINE)) != 1:
		issues.append("post body must contain exactly one H1")
	if not re.search(r"^##\s+\S", body, flags=re.MULTILINE):
		issues.append("post body must contain at least one H2")
	if body.count("<!-- more -->") != 1:
		issues.append("post body must contain exactly one excerpt marker")
	if FENCE_RE.search(body):
		issues.append("post body contains a fenced payload")
	if not re.search(r"\b(?:I|my)\b", body, flags=re.IGNORECASE):
		issues.append("post body must use first-person work-log voice")
	items = evidence.get("items")
	if not isinstance(items, list):
		return issues + ["evidence packet must contain an items list"]
	known_ids = {
		str(item.get("evidence_id") or "")
		for item in items
		if isinstance(item, dict)
	}
	used_ids = evidence_ids_in_post(body)
	unknown = sorted(used_ids - known_ids)
	if unknown:
		issues.append("post cites unknown evidence IDs: " + ", ".join(unknown))
	for block in prose_blocks(body):
		if not EVIDENCE_COMMENT_RE.search(block):
			issues.append("every factual prose paragraph must cite packet evidence")
			break
	primary_ids = {
		item["evidence_id"]
		for item in items
		if isinstance(item, dict) and item.get("kind") == "dated_changelog"
	}
	if primary_ids and not used_ids.intersection(primary_ids):
		issues.append("post must cite dated changelog evidence when available")
	if not primary_ids and not used_ids:
		issues.append("post must cite at least one evidence item")
	image_items = {
		str(item.get("publish_path") or ""): str(item.get("evidence_id") or "")
		for item in items
		if isinstance(item, dict) and item.get("kind") == "screenshot"
	}
	for path in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", body):
		if path not in image_items:
			issues.append(f"post embeds an image outside bundle evidence: {path}")
		elif image_items[path] not in used_ids:
			issues.append(f"post image lacks its evidence citation: {path}")
	return issues


#============================================
def read_json_object(path: str) -> dict:
	"""Read one required JSON object."""
	with open(path, "r", encoding="utf-8") as handle:
		value = json.load(handle)
	if not isinstance(value, dict):
		raise RuntimeError(f"Expected one JSON object: {path}")
	return value


#============================================
def main() -> None:
	"""Validate one candidate and print a promotion-friendly result."""
	args = parse_args()
	with open(args.candidate_path, "r", encoding="utf-8") as handle:
		post = handle.read()
	evidence = read_json_object(args.evidence_path)
	bundle = read_json_object(args.bundle_path)
	issues = validate_post(post, evidence, bundle)
	if issues:
		raise RuntimeError("Daily post validation failed: " + "; ".join(issues))
	print("Daily post validation passed.")


if __name__ == "__main__":
	main()

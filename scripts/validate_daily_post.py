#!/usr/bin/env python3
"""Validate one bundle-backed MkDocs daily work-log post."""

# Standard Library
import re
import json
import argparse
import datetime
import hashlib
import dataclasses

# PIP3 modules
import yaml


FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
EVIDENCE_COMMENT_RE = re.compile(r"<!--\s*evidence:\s*([^>]+?)\s*-->")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SLUG_PLACEHOLDER = "thematic-lowercase-slug"
FENCE_RE = re.compile(r"(^|\n)\s*(?:`{3,}|~{3,})")
PROJECT_COVERAGE_RE = re.compile(
	r"^##\s+Project coverage\s*$", re.MULTILINE | re.IGNORECASE
)
NARRATIVE_H2_RE = re.compile(r"^##\s+\S.*$", re.MULTILINE)
MAX_UNCITED_NARRATIVE_BLOCKS = 3
FENCED_CODE_BLOCK_RE = re.compile(r"(?ms)^[ \t]*(`{3,}|~{3,})[^\n]*\n.*?^[ \t]*\1[ \t]*$")
INLINE_CODE_RE = re.compile(r"(?<!`)`+[^`\n]*`+")
REFERENCE_DEFINITION_RE = re.compile(r"(?m)^\s*\[[^\]\n]+\]:[^\n]*$")
INLINE_LINK_RE = re.compile(
	r"(?P<image>!)?\[(?P<label>[^\]\n]*)\]\(\s*"
	r"(?P<target><[^>\n]+>|[^()\s]+)(?:\s+(?:\"[^\"\n]*\"|'[^'\n]*'|\([^\)\n]*\)))?\s*\)"
)
V3_PROMPT_VERSION = "daily-blog-prompts-v3"
V3_RUBRIC_VERSION = "daily-blog-rubric-v3"
V4_PROMPT_VERSION = "daily-blog-prompts-v4"
V4_RUBRIC_VERSION = "daily-blog-rubric-v4"


#============================================
@dataclasses.dataclass(frozen=True)
class PostValidationPolicy:
	"""One publisher-owned immutable daily-post validation policy."""

	name: str
	version: str
	prompt_version: str
	rubric_version: str
	rules: tuple[tuple[str, bool | int], ...]
	digest: str

	#============================================
	def rule(self, name: str) -> bool | int:
		"""Return one policy rule from immutable, complete declared storage."""
		return dict(self.rules)[name]


#============================================
def _policy_digest(
	name: str,
	version: str,
	rules: tuple[tuple[str, bool | int], ...],
) -> str:
	"""Return the independently computed identity for one named policy."""
	value = {
		"name": name,
		"rules": dict(rules),
		"version": version,
	}
	text = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
	return hashlib.sha256(text.encode("utf-8")).hexdigest()


POLICY_BOOLEAN_RULES = frozenset({
	"coverage_reject_afterword",
	"require_final_project_coverage",
	"require_first_narrative_repository_link",
	"require_paragraph_evidence",
	"require_section_evidence",
})
POLICY_LIMIT_RULES = frozenset({
	"coverage_max_blocks",
	"coverage_max_words",
	"max_narrative_h2",
	"max_narrative_words",
	"max_uncited_narrative_blocks",
	"min_narrative_h2",
	"min_narrative_words",
})


def _registered_policy(
	name: str,
	version: str,
	prompt_version: str,
	rubric_version: str,
	rules: dict[str, bool | int],
) -> PostValidationPolicy:
	"""Build one import-time policy whose digest has no producer dependency."""
	if set(rules) != POLICY_BOOLEAN_RULES | POLICY_LIMIT_RULES:
		raise RuntimeError("Post validation policy rules are incomplete.")
	for rule_name in POLICY_BOOLEAN_RULES:
		if type(rules[rule_name]) is not bool:
			raise RuntimeError("Post validation policy Boolean rules must be Boolean.")
	for rule_name in POLICY_LIMIT_RULES:
		if type(rules[rule_name]) is not int or rules[rule_name] < 0:
			raise RuntimeError("Post validation policy limits must be nonnegative integers.")
	frozen_rules = tuple(sorted(rules.items()))
	return PostValidationPolicy(
		name=name,
		version=version,
		prompt_version=prompt_version,
		rubric_version=rubric_version,
		rules=frozen_rules,
		digest=_policy_digest(name, version, frozen_rules),
	)


V3_HISTORICAL_POLICY = _registered_policy(
	"v3-historical",
	"v1",
	V3_PROMPT_VERSION,
	V3_RUBRIC_VERSION,
	{
		"coverage_max_blocks": 0,
		"coverage_max_words": 0,
		"coverage_reject_afterword": False,
		"max_narrative_h2": 4,
		"max_narrative_words": 650,
		"max_uncited_narrative_blocks": 0,
		"min_narrative_h2": 2,
		"min_narrative_words": 350,
		"require_final_project_coverage": True,
		"require_first_narrative_repository_link": False,
		"require_paragraph_evidence": True,
		"require_section_evidence": False,
	},
)
V4_MAKER_POLICY = _registered_policy(
	"v4-maker",
	"v1",
	V4_PROMPT_VERSION,
	V4_RUBRIC_VERSION,
	{
		"coverage_max_blocks": 1,
		"coverage_max_words": 200,
		"coverage_reject_afterword": True,
		"max_narrative_h2": 12,
		"max_narrative_words": 2500,
		"max_uncited_narrative_blocks": 3,
		"min_narrative_h2": 0,
		"min_narrative_words": 300,
		"require_final_project_coverage": True,
		"require_first_narrative_repository_link": True,
		"require_paragraph_evidence": False,
		"require_section_evidence": True,
	},
)
POST_VALIDATION_POLICIES = {
	V3_HISTORICAL_POLICY.name: V3_HISTORICAL_POLICY,
	V4_MAKER_POLICY.name: V4_MAKER_POLICY,
}


#============================================
def parse_args() -> argparse.Namespace:
	"""Parse post, evidence, projection, and bundle paths."""
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("-c", "--candidate", dest="candidate_path", required=True)
	parser.add_argument("-e", "--evidence", dest="evidence_path", required=True)
	parser.add_argument("-p", "--projection", dest="projection_path", required=True)
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
		# A heading may share its block with prose when Markdown omits a blank line.
		text = re.sub(r"\A#{1,6}\s+[^\n]*(?:\n|\Z)", "", text).strip()
		if not text or text == "<!-- more -->":
			continue
		if text.startswith("!["):
			continue
		if text.startswith("<!--") and text.endswith("-->"):
			continue
		blocks.append(text)
	return blocks


#============================================
def narrative_sections(body: str) -> list[str]:
	"""Return opening and H2 prose sections before final Project coverage."""
	heading_matches = list(NARRATIVE_H2_RE.finditer(body))
	narrative = body
	if heading_matches and PROJECT_COVERAGE_RE.fullmatch(heading_matches[-1].group()):
		narrative = body[:heading_matches[-1].start()]
	sections = [
		section
		for section in re.split(r"(?=^##\s+)", narrative, flags=re.MULTILINE)
		if prose_blocks(section)
	]
	return sections


#============================================
def _masked_text(text: str) -> str:
	"""Return whitespace with the same length as one nonvisible source span."""
	return " " * len(text)


#============================================
def _mask_image_markdown(text: str) -> str:
	"""Mask complete images while respecting quoted and nested destinations."""
	parts = []
	index = 0
	while index < len(text):
		start = text.find("![", index)
		if start < 0:
			parts.append(text[index:])
			break
		parts.append(text[index:start])
		alt_end = text.find("]", start + 2)
		if alt_end < 0:
			parts.append(text[start:])
			break
		end = alt_end + 1
		if end < len(text) and text[end] == "(":
			depth = 0
			quote = ""
			cursor = end
			while cursor < len(text):
				character = text[cursor]
				if quote:
					if character == quote and (cursor == 0 or text[cursor - 1] != "\\"):
						quote = ""
				elif character in {"\"", "'"}:
					quote = character
				elif character == "(":
					depth += 1
				elif character == ")":
					depth -= 1
					if depth == 0:
						end = cursor + 1
						break
				cursor += 1
			if depth != 0 or quote:
				parts.append(text[start:])
				break
		elif end < len(text) and text[end] == "[":
			reference_end = text.find("]", end + 1)
			if reference_end < 0:
				parts.append(text[start:])
				break
			end = reference_end + 1
		parts.append(_masked_text(text[start:end]))
		index = end
	return "".join(parts)


#============================================
def _mask_html_tags(text: str) -> str:
	"""Mask well-formed raw HTML tags and attributes from visible-text decisions."""
	parts = []
	index = 0
	while index < len(text):
		start = text.find("<", index)
		if start < 0:
			parts.append(text[index:])
			break
		parts.append(text[index:start])
		if start + 1 >= len(text) or text[start + 1] not in "/!" and not text[start + 1].isalpha():
			parts.append("<")
			index = start + 1
			continue
		quote = ""
		cursor = start + 1
		while cursor < len(text):
			character = text[cursor]
			if quote:
				if character == quote and text[cursor - 1] != "\\":
					quote = ""
			elif character in {"\"", "'"}:
				quote = character
			elif character == ">":
				break
			cursor += 1
		if cursor >= len(text) or quote:
			parts.append(text[start:])
			break
		parts.append(_masked_text(text[start:cursor + 1]))
		index = cursor + 1
	return "".join(parts)


#============================================
def _reader_visible_markdown(text: str) -> str:
	"""Keep reader-visible labels while excluding Markdown metadata and hidden spans."""
	visible = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
	visible = FENCED_CODE_BLOCK_RE.sub(" ", visible)
	visible = INLINE_CODE_RE.sub(" ", visible)
	visible = _mask_image_markdown(visible)
	visible = _mask_html_tags(visible)
	visible = REFERENCE_DEFINITION_RE.sub(" ", visible)
	visible = INLINE_LINK_RE.sub(
		lambda match: match.group("label") if not match.group("image") else " ", visible
	)
	return visible


#============================================
def visible_word_count(text: str) -> int:
	"""Count reader-visible words rather than Markdown source syntax."""
	visible = _reader_visible_markdown(text)
	return len(re.findall(r"[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)*", visible))


#============================================
def _policy_from_bundle(bundle: dict, requested: PostValidationPolicy | None) -> PostValidationPolicy:
	"""Resolve only an exact publisher-registered policy and manifest identity."""
	policy = V3_HISTORICAL_POLICY if requested is None else requested
	registered = POST_VALIDATION_POLICIES.get(policy.name)
	if registered is not policy:
		raise RuntimeError("Post validation policy must be one publisher-registered object.")
	contracts = bundle.get("contracts")
	if not isinstance(contracts, dict):
		raise RuntimeError("Bundle contracts metadata must be an object.")
	candidate_validation = contracts.get("candidate_validation")
	if not isinstance(candidate_validation, dict):
		raise RuntimeError("Bundle contracts metadata is missing candidate_validation.")
	expected = {
		"name": policy.name,
		"version": policy.version,
		"sha256": policy.digest,
	}
	if candidate_validation != expected:
		raise RuntimeError("Bundle candidate validation policy is unsupported.")
	if (
		contracts.get("prompt_version") != policy.prompt_version
		or contracts.get("rubric_version") != policy.rubric_version
	):
		raise RuntimeError("Bundle prompt and rubric versions do not match its validation policy.")
	return policy


#============================================
def _project_coverage(body: str, reject_afterword: bool) -> tuple[str, str]:
	"""Return narrative and final Project coverage text, if exactly final."""
	matches = list(PROJECT_COVERAGE_RE.finditer(body))
	if len(matches) != 1:
		return body, ""
	match = matches[0]
	coverage = body[match.end():]
	if reject_afterword and re.search(r"^##\s+\S", coverage, flags=re.MULTILINE):
		return body, ""
	return body[:match.start()], coverage


#============================================
def _v3_shape_issues(
	body: str,
	projection: dict,
	known_ids: set[str],
	policy: PostValidationPolicy,
) -> list[str]:
	"""Apply the historical full-coverage and paragraph-evidence policy."""
	issues = []
	narrative, coverage = _project_coverage(
		body, bool(policy.rule("coverage_reject_afterword"))
	)
	headings = re.findall(r"^##\s+(.+?)\s*$", narrative, flags=re.MULTILINE)
	if policy.rule("require_final_project_coverage") and not coverage:
		issues.append("post must finish with one Project coverage H2 section")
	if not policy.rule("min_narrative_h2") <= len(headings) <= policy.rule("max_narrative_h2"):
		issues.append("post must contain two through four narrative H2 sections")
	word_count = sum(visible_word_count(block) for block in prose_blocks(narrative))
	if not policy.rule("min_narrative_words") <= word_count <= policy.rule("max_narrative_words"):
		issues.append("post narrative must contain 350 through 650 visible words")
	if policy.rule("require_paragraph_evidence"):
		for block in prose_blocks(body):
			block_ids = evidence_ids_in_post(block)
			if not block_ids.intersection(known_ids):
				issues.append("every factual prose paragraph must cite packet evidence")
				break
	if policy.rule("require_final_project_coverage"):
		for repository in projection.get("repositories", []):
			name = repository.get("repository") if isinstance(repository, dict) else ""
			if name and name not in coverage:
				issues.append("Project coverage is missing active repositories: " + name)
	return issues


#============================================
def _first_narrative_repository_link(
	narrative: str,
	repository: str,
	repository_url: str,
) -> bool | None:
	"""Return whether the first visible repository use is its exact inline link."""
	masked = re.sub(r"<!--.*?-->", " ", narrative, flags=re.DOTALL)
	masked = FENCED_CODE_BLOCK_RE.sub(" ", masked)
	masked = INLINE_CODE_RE.sub(" ", masked)
	masked = _mask_image_markdown(masked)
	masked = _mask_html_tags(masked)
	masked = REFERENCE_DEFINITION_RE.sub(" ", masked)
	position = 0
	for match in INLINE_LINK_RE.finditer(masked):
		if re.search(re.escape(repository), masked[position:match.start()]):
			return False
		position = match.end()
		if not match.group("image") and repository in match.group("label"):
			target = match.group("target").removeprefix("<").removesuffix(">")
			return match.group("label") == repository and target == repository_url
	return False if re.search(re.escape(repository), masked[position:]) else None


#============================================
def _v4_shape_issues(
	body: str,
	projection: dict,
	known_ids: set[str],
	policy: PostValidationPolicy,
) -> list[str]:
	"""Apply the maker policy used by explicit pre-activation validation tests."""
	issues = []
	narrative, coverage = _project_coverage(
		body, bool(policy.rule("coverage_reject_afterword"))
	)
	headings = re.findall(r"^##\s+(.+?)\s*$", narrative, flags=re.MULTILINE)
	if policy.rule("require_final_project_coverage") and not coverage:
		issues.append("post must finish with one Project coverage H2 section")
	if not policy.rule("min_narrative_h2") <= len(headings) <= policy.rule("max_narrative_h2"):
		issues.append("post may contain at most twelve narrative H2 sections")
	word_count = sum(visible_word_count(block) for block in prose_blocks(narrative))
	if not policy.rule("min_narrative_words") <= word_count <= policy.rule("max_narrative_words"):
		issues.append("post narrative must contain 300 through 2500 visible words")
	sections = narrative_sections(body)
	if policy.rule("require_section_evidence") and any(
		not evidence_ids_in_post(section).intersection(known_ids) for section in sections
	):
		issues.append("every narrative prose section must cite packet evidence")
	maximum_uncited = policy.rule("max_uncited_narrative_blocks")
	coverage_max_blocks = policy.rule("coverage_max_blocks")
	coverage_max_words = policy.rule("coverage_max_words")
	if not all(type(value) is int for value in (
		maximum_uncited, coverage_max_blocks, coverage_max_words,
	)):
		raise RuntimeError("Maker validation policy requires concrete compactness limits.")
	uncited = sum(
		1 for section in sections for block in prose_blocks(section)
		if not evidence_ids_in_post(block).intersection(known_ids)
	)
	if uncited > maximum_uncited:
		issues.append("post contains too many uncited narrative prose blocks")
	if policy.rule("require_final_project_coverage"):
		if policy.rule("coverage_reject_afterword") and re.search(
			r"^#{1,6}\s+\S|^<h[1-6][\s>]", coverage,
			flags=re.MULTILINE | re.IGNORECASE,
		):
			issues.append("Project coverage must not contain a later heading or afterword")
		coverage_blocks = prose_blocks(coverage)
		if (
			len(coverage_blocks) != coverage_max_blocks
			or visible_word_count(coverage_blocks[0]) > coverage_max_words
		):
			issues.append("Project coverage must use one compact paragraph or list")
		for repository in projection.get("repositories", []):
			if not isinstance(repository, dict):
				continue
			name = repository.get("repository", "")
			if name and name not in coverage:
				issues.append("Project coverage is missing active repositories: " + name)
	else:
		coverage_blocks = []
	for repository in projection.get("repositories", []):
		if not isinstance(repository, dict):
			continue
		name = repository.get("repository", "")
		linked = _first_narrative_repository_link(narrative, name, repository.get("repository_url", ""))
		if policy.rule("require_first_narrative_repository_link") and linked is False:
			issues.append("first narrative repository mention must be an exact inline link: " + name)
	return issues


#============================================
def generic_work_log_title(body: str, report_date: str) -> bool:
	"""Return whether the H1 contains only generic Work log and date wording."""
	match = re.search(r"^#\s+(.+?)\s*$", body, flags=re.MULTILINE)
	if not match:
		return False
	title = match.group(1).lower()
	if "work log" not in title:
		return False
	date_value = datetime.date.fromisoformat(report_date)
	day = str(date_value.day)
	allowed = {
		"work", "log", "daily", "for", "on",
		str(date_value.year), str(date_value.month), f"{date_value.month:02d}", day,
		date_value.strftime("%B").lower(), date_value.strftime("%b").lower(),
		f"{day}st", f"{day}nd", f"{day}rd", f"{day}th",
	}
	tokens = re.findall(r"[a-z]+|\d+(?:st|nd|rd|th)?", title)
	return bool(tokens) and set(tokens) <= allowed


#============================================
def validate_post(
	post: str,
	evidence: dict,
	projection: dict,
	bundle: dict,
	*,
	policy: PostValidationPolicy | None = None,
) -> list[str]:
	"""Return every deterministic post, front-matter, and provenance issue."""
	resolved_policy = _policy_from_bundle(bundle, policy)
	issues = []
	try:
		front_matter, body = parse_front_matter(post)
	except RuntimeError as error:
		return [str(error)]
	required = (
		"date", "slug", "generator_run", "evidence_manifest", "editorial_projection",
	)
	for key in required:
		if key not in front_matter:
			issues.append(f"front matter is missing {key}")
	unsupported = sorted(set(front_matter) - set(required))
	if unsupported:
		issues.append("front matter contains unsupported fields: " + ", ".join(unsupported))
	report_date = str(bundle["report_date"])
	if str(front_matter.get("date") or "") != report_date:
		issues.append("front matter date does not match the bundle")
	if evidence.get("report_date") != report_date:
		issues.append("evidence date does not match the bundle")
	slug = str(front_matter.get("slug") or "")
	if slug == SLUG_PLACEHOLDER:
		issues.append("front matter contains an unresolved slug placeholder")
	elif not SLUG_RE.fullmatch(slug):
		issues.append("front matter slug must use lowercase ASCII words and hyphens")
	if front_matter.get("generator_run") != bundle["generator"]["run_id"]:
		issues.append("front matter generator_run does not match the bundle")
	if front_matter.get("evidence_manifest") != "evidence.json":
		issues.append("front matter evidence_manifest must name evidence.json")
	if front_matter.get("editorial_projection") != "editorial_projection.json":
		issues.append("front matter editorial_projection must name editorial_projection.json")
	if len(re.findall(r"^#\s+\S", body, flags=re.MULTILINE)) != 1:
		issues.append("post body must contain exactly one H1")
	elif generic_work_log_title(body, report_date):
		issues.append("post body must use a descriptive H1 rather than a date-derived Work log title")
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
		str(excerpt.get("evidence_id") or "")
		for excerpt in projection["excerpts"]
		if isinstance(excerpt, dict)
	}
	used_ids = evidence_ids_in_post(body)
	unknown = sorted(used_ids - known_ids)
	if unknown:
		issues.append("post cites unknown evidence IDs: " + ", ".join(unknown))
	# ASVS 2.2.1: enforce the allowlisted contract at the model-output boundary.
	if resolved_policy is V3_HISTORICAL_POLICY:
		issues.extend(_v3_shape_issues(body, projection, known_ids, resolved_policy))
	else:
		issues.extend(_v4_shape_issues(body, projection, known_ids, resolved_policy))
	primary_ids = {
		excerpt["evidence_id"]
		for excerpt in projection["excerpts"]
		if isinstance(excerpt, dict) and excerpt.get("kind") == "dated_changelog"
	}
	if primary_ids and not used_ids.intersection(primary_ids):
		issues.append("post must cite dated changelog evidence when available")
	if not primary_ids and not used_ids:
		issues.append("post must cite at least one evidence item")
	image_paths = {
		str(item.get("publish_path") or "")
		for item in items
		if (
			isinstance(item, dict)
			and item.get("kind") == "screenshot"
			and item.get("evidence_id") in known_ids
		)
	}
	for path in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", body):
		if path not in image_paths:
			issues.append(f"post embeds an image outside bundle evidence: {path}")
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
	projection = read_json_object(args.projection_path)
	bundle = read_json_object(args.bundle_path)
	issues = validate_post(post, evidence, projection, bundle)
	if issues:
		raise RuntimeError("Daily post validation failed: " + "; ".join(issues))
	print("Daily post validation passed.")


if __name__ == "__main__":
	main()

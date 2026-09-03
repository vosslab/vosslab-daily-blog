#!/usr/bin/env python3
"""Validate one bundle-backed MkDocs daily work-log post."""

# Standard Library
import re
import json
import argparse
import hashlib
import dataclasses

# PIP3 modules
import yaml

# local repo modules
import scripts.publication_source_safety


FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
EVIDENCE_COMMENT_RE = re.compile(r"<!--\s*evidence:\s*([^>]+?)\s*-->")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SLUG_PLACEHOLDER = "thematic-lowercase-slug"
FENCE_RE = re.compile(r"(^|\n)\s*(?:`{3,}|~{3,})")
PROJECT_COVERAGE_RE = re.compile(
	r"^##\s+Project coverage\s*$", re.MULTILINE | re.IGNORECASE
)
NARRATIVE_H2_RE = re.compile(r"^##\s+\S.*$", re.MULTILINE)
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
	rules: tuple[tuple[str, bool | int | str], ...]
	digest: str

	#============================================
	def rule(self, name: str) -> bool | int | str:
		"""Return one policy rule from immutable, complete declared storage."""
		return dict(self.rules)[name]


#============================================
def _policy_digest(
	name: str,
	version: str,
	rules: tuple[tuple[str, bool | int | str], ...],
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
	"max_candidate_chars",
	"max_narrative_h2",
	"max_narrative_words",
	"max_uncited_narrative_blocks",
	"max_opening_h2",
	"max_opening_words",
	"min_narrative_h2",
	"min_narrative_words",
	"required_excerpt_marker_count",
	"required_opening_prose_blocks",
})
POLICY_ENUM_RULES = {
	"coverage_repository_scope": frozenset({
		"all_packet_activity", "projected_repositories",
	}),
	"word_count_mode": frozenset({"legacy_source", "reader_visible_markdown"}),
}


#============================================
def _registered_policy(
	name: str,
	version: str,
	prompt_version: str,
	rubric_version: str,
	rules: dict[str, bool | int | str],
) -> PostValidationPolicy:
	"""Build one import-time policy whose digest has no producer dependency."""
	if set(rules) != POLICY_BOOLEAN_RULES | POLICY_LIMIT_RULES | set(POLICY_ENUM_RULES):
		raise RuntimeError("Post validation policy rules are incomplete.")
	for rule_name in POLICY_BOOLEAN_RULES:
		if type(rules[rule_name]) is not bool:
			raise RuntimeError("Post validation policy Boolean rules must be Boolean.")
	for rule_name in POLICY_LIMIT_RULES:
		if type(rules[rule_name]) is not int or rules[rule_name] < 0:
			raise RuntimeError("Post validation policy limits must be nonnegative integers.")
	if rules["max_candidate_chars"] <= 0:
		raise RuntimeError("Post validation policy candidate character limit must be positive.")
	if rules["required_excerpt_marker_count"] != 1 and any(
		rules[name] != 0
		for name in (
			"required_opening_prose_blocks",
			"max_opening_h2",
			"max_opening_words",
		)
	):
		raise RuntimeError("Post validation policy opening rules require one excerpt marker.")
	for rule_name, values in POLICY_ENUM_RULES.items():
		if type(rules[rule_name]) is not str or rules[rule_name] not in values:
			raise RuntimeError("Post validation policy enum rules must use registered values.")
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
	"v3",
	V3_PROMPT_VERSION,
	V3_RUBRIC_VERSION,
	{
		"coverage_max_blocks": 0,
		"coverage_max_words": 0,
		"coverage_repository_scope": "all_packet_activity",
		"coverage_reject_afterword": False,
		"max_candidate_chars": 24000,
		"max_narrative_h2": 4,
		"max_narrative_words": 650,
		"max_uncited_narrative_blocks": 0,
		"max_opening_h2": 0,
		"max_opening_words": 100,
		"min_narrative_h2": 2,
		"min_narrative_words": 350,
		"required_excerpt_marker_count": 1,
		"required_opening_prose_blocks": 1,
		"require_final_project_coverage": True,
		"require_first_narrative_repository_link": False,
		"require_paragraph_evidence": True,
		"require_section_evidence": False,
		"word_count_mode": "legacy_source",
	},
)
V4_MAKER_POLICY = _registered_policy(
	"v4-maker",
	"v3",
	V4_PROMPT_VERSION,
	V4_RUBRIC_VERSION,
	{
		"coverage_max_blocks": 1,
		"coverage_max_words": 200,
		"coverage_repository_scope": "projected_repositories",
		"coverage_reject_afterword": True,
		"max_candidate_chars": 24000,
		"max_narrative_h2": 12,
		"max_narrative_words": 2500,
		"max_uncited_narrative_blocks": 3,
		"max_opening_h2": 0,
		"max_opening_words": 100,
		"min_narrative_h2": 0,
		"min_narrative_words": 300,
		"required_excerpt_marker_count": 1,
		"required_opening_prose_blocks": 1,
		"require_final_project_coverage": True,
		"require_first_narrative_repository_link": True,
		"require_paragraph_evidence": False,
		"require_section_evidence": True,
		"word_count_mode": "reader_visible_markdown",
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
def legacy_source_word_count(text: str) -> int:
	"""Count historical Markdown source after removing only HTML comments."""
	source = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
	return len(re.findall(r"[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)*", source))


#============================================
def policy_word_count(text: str, policy: PostValidationPolicy) -> int:
	"""Count Markdown using the immutable policy's declared reader model."""
	mode = policy.rule("word_count_mode")
	if mode == "legacy_source":
		return legacy_source_word_count(text)
	if mode == "reader_visible_markdown":
		return visible_word_count(text)
	raise RuntimeError("Post validation policy has an unsupported word-count mode.")


#============================================
def _policy_from_bundle(
	bundle: dict,
	requested: PostValidationPolicy | None,
) -> PostValidationPolicy:
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
def _project_coverage(body: str) -> tuple[str, str]:
	"""Return narrative and Project coverage text when the post has one coverage H2."""
	matches = list(PROJECT_COVERAGE_RE.finditer(body))
	if len(matches) != 1:
		return body, ""
	match = matches[0]
	coverage = body[match.end():]
	return body[:match.start()], coverage


#============================================
def _coverage_repository_names(
	evidence: dict,
	projection: dict,
	policy: PostValidationPolicy,
) -> list[str] | None:
	"""Return the policy-selected coverage names or None for malformed inputs."""
	scope = policy.rule("coverage_repository_scope")
	if scope == "all_packet_activity":
		records = evidence.get("activity")
	elif scope == "projected_repositories":
		records = projection.get("repositories")
	else:
		raise RuntimeError("Post validation policy has an unsupported coverage scope.")
	if not isinstance(records, list):
		return None
	names = []
	for record in records:
		if not isinstance(record, dict):
			return None
		name = record.get("repository")
		if not isinstance(name, str) or not name:
			return None
		names.append(name)
	return names


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
def _heading_count_issue(
	minimum: int,
	maximum: int,
) -> str:
	"""Describe one declared narrative-H2 boundary without a policy-family branch."""
	if minimum == 0:
		return f"post may contain at most {maximum} narrative H2 sections"
	if minimum == maximum:
		return f"post must contain exactly {minimum} narrative H2 sections"
	if minimum == 2 and maximum == 4:
		return "post must contain two through four narrative H2 sections"
	return f"post must contain {minimum} through {maximum} narrative H2 sections"


#============================================
def _opening_issues(post: str, body: str, policy: PostValidationPolicy) -> list[str]:
	"""Apply the registered post-size and pre-excerpt opening constraints."""
	issues = []
	if len(post) > policy.rule("max_candidate_chars"):
		issues.append("post exceeds the candidate character budget")
	marker = "<!-- more -->"
	marker_count = body.count(marker)
	expected_marker_count = policy.rule("required_excerpt_marker_count")
	if marker_count != expected_marker_count:
		issues.append(f"post body must contain exactly {expected_marker_count} excerpt marker(s)")
		return issues
	if expected_marker_count != 1:
		return issues
	marker_index = body.index(marker)
	opening = body[:marker_index]
	opening_blocks = prose_blocks(opening)
	expected_opening_blocks = policy.rule("required_opening_prose_blocks")
	if len(opening_blocks) != expected_opening_blocks:
		issues.append("post opening must contain exactly one prose block before the excerpt marker")
	opening_h2 = len(re.findall(r"^##\s+\S.*$", opening, flags=re.MULTILINE))
	if opening_h2 > policy.rule("max_opening_h2"):
		issues.append("post opening must not contain an H2 before the excerpt marker")
	opening_words = sum(policy_word_count(block, policy) for block in opening_blocks)
	if opening_words > policy.rule("max_opening_words"):
		issues.append("post opening exceeds the policy word budget before the excerpt marker")
	return issues


def _shape_issues(
	body: str,
	evidence: dict,
	projection: dict,
	known_ids: set[str],
	policy: PostValidationPolicy,
) -> list[str]:
	"""Apply every registered shape rule without selecting a policy family."""
	issues = []
	narrative, coverage = _project_coverage(body)
	headings = re.findall(r"^##\s+(.+?)\s*$", narrative, flags=re.MULTILINE)
	coverage_required = policy.rule("require_final_project_coverage")
	coverage_matches = list(PROJECT_COVERAGE_RE.finditer(body))
	all_h2 = list(NARRATIVE_H2_RE.finditer(body))
	coverage_is_final_h2 = (
		len(coverage_matches) == 1
		and bool(all_h2)
		and coverage_matches[0].start() == all_h2[-1].start()
	)
	if coverage_required and not coverage_is_final_h2:
		issues.append("post must finish with one Project coverage H2 section")
	minimum_h2 = policy.rule("min_narrative_h2")
	maximum_h2 = policy.rule("max_narrative_h2")
	if not minimum_h2 <= len(headings) <= maximum_h2:
		issues.append(_heading_count_issue(minimum_h2, maximum_h2))
	word_count = sum(policy_word_count(block, policy) for block in prose_blocks(narrative))
	minimum_words = policy.rule("min_narrative_words")
	maximum_words = policy.rule("max_narrative_words")
	if not minimum_words <= word_count <= maximum_words:
		issues.append(
			f"post narrative must contain {minimum_words} through {maximum_words} visible words"
		)
	sections = narrative_sections(body)
	if policy.rule("require_section_evidence") and any(
		not evidence_ids_in_post(section).intersection(known_ids) for section in sections
	):
		issues.append("every narrative prose section must cite packet evidence")
	if policy.rule("require_paragraph_evidence"):
		for block in prose_blocks(body):
			if not evidence_ids_in_post(block).intersection(known_ids):
				issues.append("every factual prose paragraph must cite packet evidence")
				break
	maximum_uncited = policy.rule("max_uncited_narrative_blocks")
	coverage_max_blocks = policy.rule("coverage_max_blocks")
	coverage_max_words = policy.rule("coverage_max_words")
	uncited = sum(
		1 for section in sections for block in prose_blocks(section)
		if not evidence_ids_in_post(block).intersection(known_ids)
	)
	if not policy.rule("require_paragraph_evidence") and uncited > maximum_uncited:
		issues.append("post contains too many uncited narrative prose blocks")
	if coverage_required:
		if policy.rule("coverage_reject_afterword") and re.search(
			r"^#{1,6}\s+\S|^<h[1-6][\s>]", coverage,
			flags=re.MULTILINE | re.IGNORECASE,
		):
			issues.append("Project coverage must not contain a later heading or afterword")
		coverage_blocks = prose_blocks(coverage)
		if coverage_max_blocks and (
			len(coverage_blocks) != coverage_max_blocks
			or not coverage_blocks
			or policy_word_count(coverage_blocks[0], policy) > coverage_max_words
		):
			issues.append("Project coverage must use one compact paragraph or list")
		repositories = _coverage_repository_names(evidence, projection, policy)
		if repositories is None:
			issues.append("Project coverage repository scope is malformed")
		else:
			for name in repositories:
				if name not in coverage:
					issues.append("Project coverage is missing active repositories: " + name)
	if policy.rule("require_first_narrative_repository_link"):
		repositories = projection.get("repositories")
		if not isinstance(repositories, list):
			issues.append("Project coverage repository scope is malformed")
		else:
			for repository in repositories:
				if not isinstance(repository, dict):
					issues.append("Project coverage repository scope is malformed")
					break
				name = repository.get("repository")
				url = repository.get("repository_url")
				if not isinstance(name, str) or not name or not isinstance(url, str):
					issues.append("Project coverage repository scope is malformed")
					break
				linked = _first_narrative_repository_link(narrative, name, url)
				if linked is False:
					issues.append("first narrative repository mention must be an exact inline link: " + name)
	return issues


#============================================
def generic_work_log_title(body: str, report_date: str) -> bool:
	"""Return whether the H1 contains only generic Work log and date wording."""
	match = re.search(r"^#\s+(.+?)\s*$", body, flags=re.MULTILINE)
	if not match:
		return False
	normalized = re.sub(r"[^a-z0-9]+", " ", match.group(1).casefold()).strip()
	date_words = report_date.replace("-", " ")
	generic = {
		"work log",
		"daily work log",
		f"work log {date_words}",
		f"work log for {date_words}",
		f"daily work log {date_words}",
		f"daily work log for {date_words}",
		f"{date_words} work log",
		f"{date_words} daily work log",
	}
	return normalized in generic


#============================================
def validate_post(
	post: str,
	evidence: dict,
	projection: dict,
	bundle: dict,
	*,
	policy: PostValidationPolicy | None = None,
	surface: dict | None = None,
) -> list[str]:
	"""Return every deterministic post, front-matter, and provenance issue."""
	resolved_policy = _policy_from_bundle(bundle, policy)
	issues = []
	try:
		front_matter, body = parse_front_matter(post)
	except RuntimeError as error:
		return [str(error)]
	issues.extend(_opening_issues(post, body, resolved_policy))
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
	issues.extend(_shape_issues(body, evidence, projection, known_ids, resolved_policy))
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
		)
	}
	if surface is not None:
		# ASVS 2.2.1/2.2.3: use the same survivor authority as the bundle importer.
		image_paths = {image["publish_path"] for image in surface["allowed_images"]}
	if bundle.get("contracts", {}).get("publication_source_safety") == scripts.publication_source_safety.policy_identity():
		for reason in scripts.publication_source_safety.validate_post_source(post, image_paths):
			issues.append("post source safety rejected: " + reason)
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

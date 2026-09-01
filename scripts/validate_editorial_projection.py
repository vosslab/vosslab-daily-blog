"""Validate one exact, evidence-bound editorial projection."""

# Standard Library
import hashlib

# local repo modules
import scripts.canonical_json


EDITORIAL_PROJECTION_SCHEMA_VERSION = "vosslab.daily-blog.editorial-projection.v2"
AUTHORITY_ORDER = [
	"dated_changelog",
	"changed_documentation",
	"diff",
	"readme_context",
	"screenshot",
	"commit_metadata",
]


#============================================
def canonical_json_bytes(value: object) -> bytes:
	"""Return deterministic UTF-8 JSON bytes for hashing."""
	return scripts.canonical_json.compact_json_bytes(value)


#============================================
def hash_value(value: object) -> str:
	"""Hash one JSON-compatible value canonically."""
	return scripts.canonical_json.hash_value(value)


#============================================
def projection_identity(projection: dict) -> str:
	"""Recompute the projection identity without trusting producer code."""
	content = dict(projection)
	content.pop("projection_id", None)
	return hash_value(content)


#============================================
def _require_keys(value: dict, required: set[str], label: str) -> None:
	"""Require the exact named projection contract fields."""
	missing = sorted(required - set(value))
	if missing:
		raise RuntimeError(f"{label} is missing required fields: {', '.join(missing)}")
	extra = sorted(set(value) - required)
	if extra:
		raise RuntimeError(f"{label} has unsupported fields: {', '.join(extra)}")


#============================================
def _validate_repository_cards(projection: dict, evidence: dict) -> None:
	"""Require one unique card for every active evidence repository."""
	cards = projection["repositories"]
	if not isinstance(cards, list):
		raise RuntimeError("Projection repository cards must be a list.")
	activity_by_repository = {
		activity["repository"]: activity
		for activity in evidence["activity"]
		if isinstance(activity, dict)
	}
	card_repositories = []
	card_order = []
	for card in cards:
		if not isinstance(card, dict):
			raise RuntimeError("Projection repository cards must be objects.")
		_require_keys(
			card,
			{
				"repository", "repository_url", "commit_count",
				"commit_shas", "commit_subjects", "created_at",
				"created_in_report_window", "is_fork", "story_signals",
			},
			"Projection repository card",
		)
		repository = card["repository"]
		if not isinstance(repository, str) or not repository:
			raise RuntimeError("Projection repository card identity must be non-empty text.")
		activity = activity_by_repository.get(repository)
		if activity is None:
			raise RuntimeError("Projection repository card has no active evidence repository.")
		if card["repository_url"] != activity["repository_url"]:
			raise RuntimeError("Projection repository card URL does not match evidence activity.")
		lifecycle = activity["lifecycle_events"][0]
		if (
			card["created_at"] != lifecycle["occurred_at"]
			or card["created_in_report_window"] is not lifecycle["occurred_in_report_window"]
			or card["is_fork"] is not activity["is_fork"]
		):
			raise RuntimeError("Projection repository card lifecycle does not match evidence activity.")
		expected_signals = (
			["new_source_repository"]
			if card["created_in_report_window"] and not card["is_fork"]
			else []
		)
		if card["story_signals"] != expected_signals:
			raise RuntimeError("Projection repository card story signals are inconsistent.")
		commits = activity["commits"]
		if type(card["commit_count"]) is not int or card["commit_count"] != len(commits):
			raise RuntimeError("Projection repository card commit count does not match activity.")
		commit_shas = card["commit_shas"]
		commit_subjects = card["commit_subjects"]
		if not isinstance(commit_shas, list) or not isinstance(commit_subjects, list):
			raise RuntimeError("Projection repository card commits must be lists.")
		known_commits = {commit["sha"] for commit in commits}
		if (
			len(commit_shas) != len(commit_subjects)
			or len(set(commit_shas)) != len(commit_shas)
			or any(commit not in known_commits for commit in commit_shas)
			or any(not isinstance(subject, str) or not subject for subject in commit_subjects)
		):
			raise RuntimeError("Projection repository card commits do not match evidence activity.")
		if any(
			len(subject) > projection["projection_limits"]["commit_subject_chars"]
			for subject in commit_subjects
		):
			raise RuntimeError("Projection commit subject exceeds its declared limit.")
		card_repositories.append(repository)
		card_order.append((0 if expected_signals else 1, repository.casefold()))
	if len(set(card_repositories)) != len(card_repositories):
		raise RuntimeError("Projection repository cards contain duplicate repositories.")
	if set(card_repositories) != set(activity_by_repository):
		raise RuntimeError("Projection cards must cover all active evidence repositories.")
	if card_order != sorted(card_order):
		raise RuntimeError("Projection repository cards do not follow story-first order.")


#============================================
def _validate_exact_excerpts(projection: dict, evidence: dict) -> None:
	"""Require every excerpt to equal one hash-bound evidence substring."""
	excerpts = projection["excerpts"]
	if not isinstance(excerpts, list) or not excerpts:
		raise RuntimeError("Editorial projection requires exact excerpts.")
	items_by_id = {
		item["evidence_id"]: item
		for item in evidence["items"]
		if isinstance(item, dict)
	}
	for excerpt in excerpts:
		if not isinstance(excerpt, dict):
			raise RuntimeError("Projection exact excerpts must be objects.")
		_require_keys(
			excerpt,
			{
				"excerpt_id", "evidence_id", "repository", "kind", "authority_level",
				"authority_rank", "commit", "path", "start", "end",
				"source_content_hash", "content_hash", "content",
			},
			"Projection exact excerpt",
		)
		item = items_by_id.get(excerpt["evidence_id"])
		if item is None:
			raise RuntimeError("Projection excerpt must reference a known evidence item.")
		if excerpt["source_content_hash"] != item["content_hash"]:
			raise RuntimeError("Projection excerpt source content hash does not match evidence.")
		start = excerpt["start"]
		end = excerpt["end"]
		content = item["content"]
		if (
			type(start) is not int
			or type(end) is not int
			or start < 0
			or end <= start
			or end > len(content)
		):
			raise RuntimeError("Projection excerpt offsets are outside the source content.")
		if excerpt["content"] != content[start:end]:
			raise RuntimeError("Projection excerpt does not equal the exact source substring.")
		if len(excerpt["content"]) > projection["projection_limits"]["excerpt_chars"]:
			raise RuntimeError("Projection excerpt exceeds its declared limit.")
		for key in (
			"repository", "kind", "authority_level", "authority_rank", "commit", "path",
		):
			if excerpt[key] != item[key]:
				raise RuntimeError("Projection excerpt provenance does not match its evidence item.")
		excerpt_hash = hashlib.sha256(excerpt["content"].encode("utf-8")).hexdigest()
		if excerpt["content_hash"] != excerpt_hash:
			raise RuntimeError("Projection excerpt content hash does not match its content.")
		identity = dict(excerpt)
		identity.pop("excerpt_id")
		expected_id = "ex-" + hash_value(identity)[:16]
		if excerpt["excerpt_id"] != expected_id:
			raise RuntimeError("Projection excerpt identity does not match its exact slice.")


#============================================
def _validate_context_bound(projection: dict, limit: int) -> None:
	"""Enforce the same canonical rendered context bound used by the producer."""
	context = {
		"schema_version": projection["schema_version"],
		"projection_id": projection["projection_id"],
		"packet_id": projection["packet_id"],
		"report_date": projection["report_date"],
		"timezone": projection["timezone"],
		"authority_order": AUTHORITY_ORDER,
		"repositories": projection["repositories"],
		"excerpts": projection["excerpts"],
	}
	context_size = len(canonical_json_bytes(context).decode("utf-8"))
	if context_size > limit:
		raise RuntimeError("Editorial projection context exceeds its declared limit.")


#============================================
def validate_projection(projection: dict, evidence: dict, bundle: dict) -> None:
	"""Validate projection identity, packet binding, coverage, and exact excerpts."""
	_require_keys(
		projection,
		{
			"schema_version", "projection_id", "packet_id", "report_date", "timezone",
			"projection_limits", "repositories", "excerpts",
		},
		"Editorial projection",
	)
	if projection["schema_version"] != EDITORIAL_PROJECTION_SCHEMA_VERSION:
		raise RuntimeError("Unsupported editorial projection schema.")
	if projection_identity(projection) != projection["projection_id"]:
		raise RuntimeError("Editorial projection identity does not match its content.")
	if projection["projection_id"] != bundle["editorial_projection"]["projection_id"]:
		raise RuntimeError("Bundle projection identity does not match editorial_projection.json.")
	if projection["packet_id"] != evidence["packet_id"]:
		raise RuntimeError("Editorial projection packet binding does not match evidence.json.")
	if projection["report_date"] != bundle["report_date"]:
		raise RuntimeError("Editorial projection report date does not match the bundle.")
	if projection["timezone"] != bundle["timezone"]:
		raise RuntimeError("Editorial projection timezone does not match the bundle.")
	limits = projection["projection_limits"]
	if not isinstance(limits, dict) or set(limits) != {
		"context_chars", "excerpt_chars", "commit_subject_chars",
	}:
		raise RuntimeError("Editorial projection limits use unsupported fields.")
	if any(type(value) is not int or value <= 0 for value in limits.values()):
		raise RuntimeError("Editorial projection limits must be positive integers.")
	_validate_context_bound(projection, limits["context_chars"])
	_validate_repository_cards(projection, evidence)
	_validate_exact_excerpts(projection, evidence)

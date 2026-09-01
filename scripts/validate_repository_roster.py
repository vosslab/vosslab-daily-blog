"""Validate the sealed authoritative repository roster in one publication bundle."""

# Standard Library
import datetime
import re

# local repo modules
import scripts.canonical_json


REPOSITORY_ROSTER_SCHEMA_VERSION = "vosslab.daily-blog.repository-roster.v1"
HEX_DIGITS = frozenset("0123456789abcdef")
REPOSITORY_RE = re.compile(r"^(?P<owner>[A-Za-z0-9-]+)/(?P<name>[A-Za-z0-9._-]+)$")


#============================================
def _require_keys(value: object, required: set[str], label: str) -> dict:
	"""Return one object with exactly the fields its contract permits."""
	if not isinstance(value, dict):
		raise RuntimeError(f"{label} must be an object.")
	if set(value) != required:
		raise RuntimeError(f"{label} fields are unsupported.")
	return value


#============================================
def _hash_value(value: object) -> str:
	"""Return a canonical SHA-256 content identity."""
	return scripts.canonical_json.hash_value(value)


#============================================
def _canonical_utc_timestamp(value: object) -> bool:
	"""Return whether a timestamp has canonical whole-second UTC form."""
	if not isinstance(value, str):
		return False
	try:
		moment = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
	except ValueError:
		return False
	if moment.tzinfo is None:
		return False
	canonical = moment.astimezone(datetime.timezone.utc).replace(microsecond=0)
	return value == canonical.isoformat().replace("+00:00", "Z")


#============================================
def _validate_roster_manifest(manifest: dict, roster: object) -> dict:
	"""Accept only the sealed roster object captured with its bundle snapshot."""
	if manifest["path"] != "repository_roster.json":
		raise RuntimeError("Bundle repository roster path is invalid.")
	roster = _require_keys(
		roster,
		{"schema_version", "owner", "repositories", "roster_id"},
		"Repository roster",
	)
	return roster


#============================================
def validate_repository_roster(bundle: dict, evidence: dict, roster: object) -> None:
	"""Require every evidence mirror to match the complete sealed owner roster."""
	manifest = _require_keys(
		bundle["repository_roster"],
		{"path", "roster_id", "sha256"},
		"Bundle repository roster manifest",
	)
	roster = _validate_roster_manifest(manifest, roster)
	if roster["schema_version"] != REPOSITORY_ROSTER_SCHEMA_VERSION:
		raise RuntimeError("Unsupported repository roster schema.")
	owner = roster["owner"]
	if not isinstance(owner, str) or not re.fullmatch(r"[A-Za-z0-9-]+", owner):
		raise RuntimeError("Repository roster owner is invalid.")
	records = roster["repositories"]
	if not isinstance(records, list) or not records:
		raise RuntimeError("Repository roster must contain eligible repositories.")
	records_by_repository = {}
	for value in records:
		record = _require_keys(
			value,
			{"repository", "repository_url", "clone_url", "created_at", "is_fork"},
			"Repository roster record",
		)
		repository = record["repository"]
		match = REPOSITORY_RE.fullmatch(repository) if isinstance(repository, str) else None
		expected_page = f"https://github.com/{repository}"
		if (
			match is None
			or ".." in match.group("name")
			or match.group("owner").casefold() != owner.casefold()
			or record["repository_url"] != expected_page
			or record["clone_url"] != expected_page + ".git"
			or not _canonical_utc_timestamp(record["created_at"])
			or type(record["is_fork"]) is not bool
			or repository in records_by_repository
		):
			raise RuntimeError("Repository roster record is invalid.")
		records_by_repository[repository] = record
	content = {key: roster[key] for key in ("schema_version", "owner", "repositories")}
	if (
		not isinstance(manifest["roster_id"], str)
		or len(manifest["roster_id"]) != 64
		or set(manifest["roster_id"]) - HEX_DIGITS
		or roster["roster_id"] != manifest["roster_id"]
		or _hash_value(content) != roster["roster_id"]
		or _hash_value(roster) != manifest["sha256"]
	):
		raise RuntimeError("Repository roster identity does not match its content.")
	# ASVS 1.5.2, 2.2.1, and 2.3.1: only sealed roster records authorize mirrors.
	for mirror in evidence["mirrors"]:
		record = records_by_repository.get(mirror["repository"])
		if record is None or mirror["roster_id"] != roster["roster_id"]:
			raise RuntimeError("Evidence mirror is outside the sealed repository roster.")
		for key in ("repository_url", "clone_url", "created_at", "is_fork"):
			if mirror[key] != record[key]:
				raise RuntimeError("Evidence mirror does not match its sealed roster record.")

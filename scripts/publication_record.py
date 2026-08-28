"""Exact schema and value validation for publisher-owned publication receipts."""

# Standard Library
import datetime
import re
import zoneinfo


PUBLICATION_SCHEMA_VERSION = "vosslab.daily-blog.publication.v2"
PUBLICATION_RECORD_FIELDS = frozenset(
	{
		"bundle_id",
		"editorial_projection_manifest",
		"evidence_manifest",
		"generator_revision",
		"generator_run",
		"imported_at",
		"post_path",
		"release_id",
		"report_date",
		"schema_version",
		"timezone",
	}
)
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
LOWER_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


#============================================
def _validate_date(value: object) -> str:
	"""Return one canonical ISO report date."""
	if not isinstance(value, str):
		raise RuntimeError("Publication record report date is invalid.")
	try:
		parsed = datetime.date.fromisoformat(value)
	except ValueError as error:
		raise RuntimeError("Publication record report date is invalid.") from error
	if parsed.isoformat() != value:
		raise RuntimeError("Publication record report date is invalid.")
	return value


#============================================
def _validate_imported_at(value: object) -> None:
	"""Require the canonical whole-second UTC import timestamp."""
	if not isinstance(value, str) or not value.endswith("Z"):
		raise RuntimeError("Publication record imported_at is invalid.")
	try:
		moment = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
	except ValueError as error:
		raise RuntimeError("Publication record imported_at is invalid.") from error
	canonical = moment.astimezone(datetime.UTC).replace(microsecond=0)
	if moment.microsecond or canonical.isoformat().replace("+00:00", "Z") != value:
		raise RuntimeError("Publication record imported_at is invalid.")


#============================================
def validate_publication_record(record: object) -> dict:
	"""Validate and return one exact clean-cutover publication v2 receipt."""
	if not isinstance(record, dict):
		raise RuntimeError("Publication record must be one JSON object.")
	if record.get("schema_version") != PUBLICATION_SCHEMA_VERSION:
		raise RuntimeError("Unsupported publication record schema.")
	if set(record) != PUBLICATION_RECORD_FIELDS:
		raise RuntimeError("Publication record fields are unsupported.")
	report_date = _validate_date(record["report_date"])
	bundle_id = record["bundle_id"]
	if not isinstance(bundle_id, str) or LOWER_SHA256_RE.fullmatch(bundle_id) is None:
		raise RuntimeError("Publication record bundle identity is invalid.")
	if record["release_id"] != bundle_id:
		raise RuntimeError("Publication record release identity is inconsistent.")
	generator_revision = record["generator_revision"]
	if (
		not isinstance(generator_revision, str)
		or LOWER_SHA256_RE.fullmatch(generator_revision) is None
	):
		raise RuntimeError("Publication record generator revision is invalid.")
	generator_run = record["generator_run"]
	if not isinstance(generator_run, str) or RUN_ID_RE.fullmatch(generator_run) is None:
		raise RuntimeError("Publication record generator run is invalid.")
	timezone = record["timezone"]
	if not isinstance(timezone, str) or not timezone:
		raise RuntimeError("Publication record timezone is invalid.")
	try:
		zoneinfo.ZoneInfo(timezone)
	except zoneinfo.ZoneInfoNotFoundError as error:
		raise RuntimeError("Publication record timezone is invalid.") from error
	expected_paths = {
		"editorial_projection_manifest": (
			f"data/publication_bundles/{bundle_id}/editorial_projection.json"
		),
		"evidence_manifest": f"data/publication_bundles/{bundle_id}/evidence.json",
		"post_path": f"docs/blog/posts/{report_date}.md",
	}
	for field, expected in expected_paths.items():
		if record[field] != expected:
			raise RuntimeError(f"Publication record {field} is inconsistent.")
	_validate_imported_at(record["imported_at"])
	return record

"""Render authoritative final-only publication records for the local status page."""

# Standard Library
import os
import json

# local repo modules
import scripts.publication_record


PUBLICATION_SCHEMA_VERSION = scripts.publication_record.PUBLICATION_SCHEMA_VERSION


#============================================
def read_json_object(path: str) -> dict:
	"""Read one required publication-record object."""
	with open(path, "r", encoding="utf-8") as handle:
		value = json.load(handle)
	if not isinstance(value, dict):
		raise RuntimeError(f"Expected one JSON object: {path}")
	return value


#============================================
def validate_publication_record(record: dict) -> dict:
	"""Validate one clean-cutover final-only publication record."""
	return scripts.publication_record.validate_publication_record(record)


#============================================
def read_publication_records(root: str, proposed: dict) -> list[dict]:
	"""Read current publication records and replace the proposed date in memory."""
	directory = os.path.join(root, "data", "publications")
	records_by_date = {}
	if os.path.isdir(directory):
		for name in os.listdir(directory):
			if not name.endswith(".json"):
				continue
			path = os.path.join(directory, name)
			if os.path.islink(path) or not os.path.isfile(path):
				continue
			record = validate_publication_record(read_json_object(path))
			expected_date = os.path.splitext(name)[0]
			if record["report_date"] != expected_date:
				raise RuntimeError("Publication record date does not match its path.")
			records_by_date[record["report_date"]] = record
	proposed = validate_publication_record(proposed)
	records_by_date[proposed["report_date"]] = proposed
	records = [records_by_date[key] for key in sorted(records_by_date, reverse=True)]
	return records


#============================================
def render_status(records: list[dict]) -> str:
	"""Render the local status page from validated current records."""
	lines = [
		"# Publication status",
		"",
		"| Report date | Generator run | Bundle |",
		"| --- | --- | --- |",
	]
	for value in records[:30]:
		record = validate_publication_record(value)
		date_text = record["report_date"]
		run_id = record["generator_run"]
		bundle_id = record["bundle_id"][:12]
		lines.append(f"| {date_text} | {run_id} | {bundle_id} |")
	lines.extend(
		[
			"",
			"An identical bundle is idempotent. Any different bundle for an already-published "
			+ "report date is rejected before staging.",
			"",
		]
	)
	return "\n".join(lines)

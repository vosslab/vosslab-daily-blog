"""Bounded machine protocol for producer-facing publication import commands."""

# Standard Library
import json


FAILURE_SCHEMA_VERSION = "vosslab.daily-blog.import-failure.v1"
VALIDATION_SCHEMA_VERSION = "vosslab.daily-blog.import-validation.v1"
MAX_FAILURE_BYTES = 1024
FAILURE_CATEGORIES = frozenset({
	"snapshot_rejected",
	"publication_conflict",
	"staged_build_failed",
	"commit_failed",
	"publisher_implementation_defect",
})
FAILURE_PHASES = frozenset({"receive", "validate", "preflight", "stage", "commit"})


#============================================
class ImportProtocolError(RuntimeError):
	"""Carry a safe failure category and phase while retaining local diagnostics."""

	#============================================
	def __init__(self, category: str, phase: str, message: str) -> None:
		"""Create one allowlisted protocol failure."""
		if category not in FAILURE_CATEGORIES or phase not in FAILURE_PHASES:
			raise RuntimeError("Publication import failure classification is invalid.")
		super().__init__(message)
		self.category = category
		self.phase = phase


#============================================
def failure_envelope(error: BaseException, phase: str = "preflight") -> bytes:
	"""Return one bounded, text-free error envelope for an automated caller."""
	if isinstance(error, ImportProtocolError):
		category = error.category
		resolved_phase = error.phase
	else:
		category = "publisher_implementation_defect"
		resolved_phase = phase
	if resolved_phase not in FAILURE_PHASES:
		resolved_phase = "preflight"
	payload = {
		"category": category,
		"phase": resolved_phase,
		"schema_version": FAILURE_SCHEMA_VERSION,
	}
	# Keep failure bytes identical to the success JSON contract so the producer
	# can enforce one canonical parser for both protocol directions.
	contents = stable_success_text(payload).encode("ascii")
	if len(contents) > MAX_FAILURE_BYTES:
		raise RuntimeError("Publication import failure envelope exceeds its envelope.")
	return contents


#============================================
def validation_receipt(bundle: dict) -> dict:
	"""Build the exact identity-bound success receipt for stdin validation."""
	return {
		"best_artifact_id": bundle["best_artifact_id"],
		"bundle_sha256": bundle["bundle_sha256"],
		"report_date": bundle["report_date"],
		"schema_version": VALIDATION_SCHEMA_VERSION,
		"status": "valid",
	}


#============================================
def stable_success_text(value: dict) -> str:
	"""Render one sole stdout JSON result with a terminal newline."""
	return json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"

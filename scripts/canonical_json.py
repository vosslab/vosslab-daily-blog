"""Strict JSON encodings for publication artifacts and transfer headers."""

# Standard Library
import hashlib
import json


#============================================
def compact_json_bytes(value: object) -> bytes:
	"""Render one transfer header with its compact canonical wire encoding."""
	text = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
	contents = text.encode("utf-8")
	return contents


#============================================
def hash_value(value: object) -> str:
	"""Return the SHA-256 identity of one compact canonical JSON value."""
	contents = compact_json_bytes(value)
	digest = hashlib.sha256(contents).hexdigest()
	return digest


#============================================
def stable_json_bytes(value: object) -> bytes:
	"""Render one producer artifact using stable_json_text's inspectable encoding."""
	text = json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
	contents = text.encode("utf-8")
	return contents


#============================================
def _reject_duplicate_members(pairs: list[tuple[str, object]]) -> dict:
	"""Build one object while rejecting ambiguous repeated JSON member names."""
	value = {}
	for key, member in pairs:
		if key in value:
			raise ValueError("duplicate member")
		value[key] = member
	return value


#============================================
def _reject_nonstandard_constant(_value: str) -> object:
	"""Reject JSON extensions that cannot form a portable canonical artifact."""
	raise ValueError("nonstandard numeric constant")


#============================================
def _load_json_value(contents: bytes, label: str) -> object:
	"""Parse one JSON byte string while rejecting ambiguous extensions."""
	try:
		text = contents.decode("utf-8")
		value = json.loads(
			text,
			object_pairs_hook=_reject_duplicate_members,
			parse_constant=_reject_nonstandard_constant,
		)
	except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
		raise RuntimeError(f"{label} must be valid canonical JSON.") from error
	return value


#============================================
def load_compact_json(contents: bytes, label: str) -> object:
	"""Parse one exact compact transport-header JSON byte string."""
	value = _load_json_value(contents, label)
	if compact_json_bytes(value) != contents:
		raise RuntimeError(f"{label} must use compact canonical JSON bytes.")
	return value


#============================================
def load_stable_json(contents: bytes, label: str) -> object:
	"""Parse one exact producer stable_json_text artifact byte string."""
	value = _load_json_value(contents, label)
	if stable_json_bytes(value) != contents:
		raise RuntimeError(f"{label} must use stable canonical JSON bytes.")
	return value

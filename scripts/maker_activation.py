"""Independently validate the sealed producer maker-activation receipt."""

# Standard Library
import hashlib
import json
import os

# local repo modules
import scripts.repository_paths


ACTIVATION_FILENAME = "daily_blog_maker_activation.json"
ACTIVATION_SCHEMA_VERSION = "vosslab.daily-blog.maker-activation.v1"
ACTIVATION_FILE_SHA256 = "2180e6ca447efa43e11039397403ca167e11ef4aec41a0499f919341a8cd8db4"
ACTIVATION_ID = "daily-blog-maker-activation-6b104be9c6907eeeffcf330f6b10173857b39c6b05baa46d4cf009a67daa7547"
PROMPT_IDENTITY_SHA256 = "2fdae757fad5392adc1dd50cbadf13ff535871485220f1b0b52a19ff5d98cf47"


#============================================
def _unique_object(pairs: list[tuple[str, object]]) -> dict:
	"""Return one JSON object while rejecting duplicate keys."""
	value = {}
	for key, item in pairs:
		if key in value:
			raise ValueError("duplicate key")
		value[key] = item
	return value


#============================================
def _reject_constant(value: str) -> None:
	"""Reject non-standard JSON constants in the sealed receipt."""
	raise ValueError(f"unsupported JSON constant: {value}")


#============================================
def canonical_json_sha256(value: object) -> str:
	"""Return the canonical identity digest for one JSON-compatible value."""
	text = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
	return hashlib.sha256(text.encode("utf-8")).hexdigest()


#============================================
def load_maker_activation(repository_root: str | None = None) -> dict:
	"""Load only the tracked, content-addressed production activation receipt."""
	root = repository_root or scripts.repository_paths.repository_root(__file__)
	path = os.path.join(root, ACTIVATION_FILENAME)
	try:
		if not os.path.isfile(path) or os.path.islink(path):
			raise RuntimeError("Publisher maker activation receipt is unavailable or malformed.")
		with open(path, "rb") as handle:
			contents = handle.read()
		if hashlib.sha256(contents).hexdigest() != ACTIVATION_FILE_SHA256:
			raise RuntimeError("Publisher maker activation receipt integrity is invalid.")
		value = json.loads(
			contents.decode("utf-8"),
			object_pairs_hook=_unique_object,
			parse_constant=_reject_constant,
		)
	except (OSError, UnicodeDecodeError, ValueError) as error:
		raise RuntimeError("Publisher maker activation receipt is unavailable or malformed.") from error
	if not isinstance(value, dict):
		raise RuntimeError("Publisher maker activation receipt is unavailable or malformed.")
	if set(value) != {
		"activation_id", "candidate_validation", "editorial_prompt_contract",
		"editorial_prompt_contract_sha256", "f4_evidence", "schema_version", "selected_contract",
	}:
		raise RuntimeError("Publisher maker activation receipt is invalid.")
	if (
		value["schema_version"] != ACTIVATION_SCHEMA_VERSION
		or value["activation_id"] != ACTIVATION_ID
		or value["activation_id"] != "daily-blog-maker-activation-" + canonical_json_sha256(
			{key: item for key, item in value.items() if key != "activation_id"}
		)
		or value["selected_contract"] != "v4-three-examples-corpus-v2"
		or value["editorial_prompt_contract_sha256"] != PROMPT_IDENTITY_SHA256
		or canonical_json_sha256(value["editorial_prompt_contract"]) != PROMPT_IDENTITY_SHA256
	):
		raise RuntimeError("Publisher maker activation receipt is invalid.")
	policy = value["candidate_validation"]
	if policy != {
		"name": "v4-maker",
		"version": "v3",
		"sha256": "3a4b7148579e509b6c32fa19b31d107dc4278eb5f721b2a01353a1a9a51264ee",
	}:
		raise RuntimeError("Publisher maker activation receipt is invalid.")
	if not isinstance(value["f4_evidence"], dict) or value["f4_evidence"].get("f4_accepted") is not True:
		raise RuntimeError("Publisher maker activation receipt is invalid.")
	return value


#============================================
def validate_bundle_activation(bundle: dict) -> dict:
	"""Bind an incoming v5 bundle to this exact sealed activation identity."""
	receipt = load_maker_activation()
	expected = {
		"activation_id": receipt["activation_id"],
		"editorial_prompt_contract_sha256": receipt["editorial_prompt_contract_sha256"],
	}
	if bundle.get("maker_activation") != expected:
		raise RuntimeError("Bundle maker activation does not match the accepted receipt.")
	if bundle.get("editorial_prompt_contract") != receipt["editorial_prompt_contract"]:
		raise RuntimeError("Bundle editorial prompt contract does not match the accepted receipt.")
	return receipt

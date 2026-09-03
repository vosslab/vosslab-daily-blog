"""Descriptor-pinned capture of a physical publication bundle."""

# Standard Library
import hashlib
import io
import os
import pathlib
import stat

# local repo modules
import scripts.canonical_json


# Match the producer's descriptor-owned publication storage envelopes. The
# independent importer applies them before retaining untrusted bundle bytes.
MAX_JSON_BYTES = 128 * 1024
MAX_POST_BYTES = 2 * 1024 * 1024
MAX_ASSET_BYTES = 8 * 1024 * 1024
# The complete transfer is the final limit on bytes retained from standard
# input, including its framing and every declared artifact.
MAX_TRANSFER_BYTES = 128 * 1024 * 1024
# Evidence is the one complete, producer-owned packet. It can legitimately be
# larger than an individual JSON artifact; the complete transport remains the
# final, stricter bound.
MAX_EVIDENCE_BYTES = MAX_TRANSFER_BYTES
TRANSFER_SCHEMA_VERSION = "vosslab.daily-blog.bundle-transfer.v1"
TRANSFER_MAGIC = (TRANSFER_SCHEMA_VERSION + "\n").encode("ascii")
CORE_PATHS = frozenset({
	"bundle.json",
	"daily_active_roster.json",
	"evidence.json",
	"repository_roster.json",
	"editorial_projection.json",
	"publication_surface.json",
	"post.md",
})
HEX_DIGITS = frozenset("0123456789abcdef")


#============================================
class BundleSnapshot:
	"""Hold one physical bundle root while collecting validated source bytes."""

	#============================================
	def __init__(self, bundle_path: str) -> None:
		self.bundle_path = os.path.abspath(bundle_path)
		self.root_fd: int | None = None
		self._sealed_contents: dict[str, bytes] | None = None
		self.transfer_header: dict | None = None

	#============================================
	@classmethod
	def from_transfer_bytes(cls, contents: bytes) -> "BundleSnapshot":
		"""Parse one complete producer transfer envelope held entirely in memory."""
		return cls.from_stream(io.BytesIO(contents))

	#============================================
	@classmethod
	def from_stream(cls, stream: object) -> "BundleSnapshot":
		"""Read one exact stdin transfer envelope before importer validation."""
		magic = _read_exact(
			stream, len(TRANSFER_MAGIC), "Publication bundle transfer magic is truncated.",
		)
		if magic != TRANSFER_MAGIC:
			raise RuntimeError("Publication bundle transfer magic is invalid.")
		header_length_bytes = _read_exact(
			stream, 8, "Publication bundle transfer header is truncated.",
		)
		header_length = int.from_bytes(header_length_bytes, "big")
		if header_length < 1 or header_length > MAX_JSON_BYTES:
			raise RuntimeError("Publication bundle transfer header exceeds its envelope.")
		header_bytes = _read_exact(
			stream, header_length, "Publication bundle transfer header is truncated.",
		)
		header = scripts.canonical_json.load_compact_json(
			header_bytes, "Publication bundle transfer header",
		)
		if not isinstance(header, dict):
			raise RuntimeError("Publication bundle transfer header must be an object.")
		_validate_transfer_header(header, header_length)
		sealed_contents = {}
		for entry in header["entries"]:
			path = entry["path"]
			contents = _read_exact(
				stream,
				entry["size"],
				f"Publication bundle transfer entry is truncated: {path}",
			)
			if hashlib.sha256(contents).hexdigest() != entry["sha256"]:
				raise RuntimeError(f"Publication bundle transfer entry checksum is invalid: {path}")
			sealed_contents[path] = contents
		if stream.read(1) != b"":
			raise RuntimeError("Publication bundle transfer has trailing bytes.")
		snapshot = cls.__new__(cls)
		snapshot.bundle_path = "<stdin-transfer>"
		snapshot.root_fd = None
		snapshot._sealed_contents = sealed_contents
		snapshot.transfer_header = header
		return snapshot

	#============================================
	def __enter__(self) -> "BundleSnapshot":
		flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
		# ASVS 2.2.1 and 2.3.1: pin one physical root before accepting bundle input.
		try:
			self.root_fd = os.open(self.bundle_path, flags)
		except OSError as error:
			raise RuntimeError("Publication bundle directory must be physical.") from error
		return self

	#============================================
	def __exit__(self, _type: object, _value: object, _traceback: object) -> None:
		if self.root_fd is not None:
			os.close(self.root_fd)
			self.root_fd = None

	#============================================
	def _root_descriptor(self) -> int:
		"""Return the active root descriptor instead of reopening its pathname."""
		if self.root_fd is None:
			raise RuntimeError("Publication bundle snapshot is closed.")
		return self.root_fd

	#============================================
	def read(self, relative_path: str) -> bytes:
		"""Read one flat core or asset file without following path substitutions."""
		if self._sealed_contents is not None:
			if relative_path not in self._sealed_contents:
				raise RuntimeError(f"Bundle artifact is absent from transfer: {relative_path}")
			return self._sealed_contents[relative_path]
		pure = pathlib.PurePosixPath(relative_path)
		if len(pure.parts) not in {1, 2} or pure.is_absolute() or ".." in pure.parts:
			raise RuntimeError(f"Bundle path is not confined: {relative_path}")
		root_fd = self._root_descriptor()
		parent_fd = root_fd
		if len(pure.parts) == 2:
			parent_fd = self._open_directory(pure.parts[0], root_fd)
		try:
			maximum_bytes = _maximum_bytes(relative_path)
			contents = self._read_regular(
				pure.name, parent_fd, relative_path, maximum_bytes,
			)
		finally:
			if parent_fd != root_fd:
				os.close(parent_fd)
		return contents

	#============================================
	def read_declared_assets(self, paths: set[str]) -> dict[str, bytes]:
		"""Seal declared direct assets without reading unmanifested bytes."""
		if self._sealed_contents is not None:
			contents_by_path = {
				path: contents
				for path, contents in self._sealed_contents.items()
				if path.startswith("assets/")
			}
			if set(contents_by_path) != paths:
				raise RuntimeError("Bundle assets directory does not match its manifest.")
			return contents_by_path
		root_fd = self._root_descriptor()
		assets_fd = self._open_directory("assets", root_fd)
		try:
			contents_by_path = {}
			with os.scandir(assets_fd) as entries:
				for entry in entries:
					path = f"assets/{entry.name}"
					if path not in paths:
						raise RuntimeError("Bundle assets directory does not match its manifest.")
					metadata = entry.stat(follow_symlinks=False)
					if not stat.S_ISREG(metadata.st_mode):
						raise RuntimeError(f"Bundle artifact must be regular: {path}")
			for path in paths:
				contents_by_path[path] = self._read_regular(
					path.removeprefix("assets/"), assets_fd, path, MAX_ASSET_BYTES,
				)
		finally:
			os.close(assets_fd)
		return contents_by_path

	#============================================
	def _open_directory(self, name: str, parent_fd: int) -> int:
		"""Open one direct physical child directory without following links."""
		flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
		try:
			return os.open(name, flags, dir_fd=parent_fd)
		except OSError as error:
			raise RuntimeError("Bundle assets must use one physical assets directory.") from error

	#============================================
	def _read_regular(
		self, name: str, parent_fd: int, label: str, maximum_bytes: int,
	) -> bytes:
		"""Read one regular direct child through a held parent descriptor."""
		try:
			file_fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd)
		except OSError as error:
			raise RuntimeError(f"Bundle artifact must be regular: {label}") from error
		try:
			metadata = os.fstat(file_fd)
			if not stat.S_ISREG(metadata.st_mode):
				raise RuntimeError(f"Bundle artifact must be regular: {label}")
			if metadata.st_size > maximum_bytes:
				raise RuntimeError(f"Bundle artifact exceeds its schema envelope: {label}")
			with os.fdopen(file_fd, "rb", closefd=False) as handle:
				contents = handle.read(maximum_bytes + 1)
			if len(contents) > maximum_bytes or len(contents) != metadata.st_size:
				raise RuntimeError(f"Bundle artifact changed while it was read: {label}")
			return contents
		finally:
			os.close(file_fd)


#============================================
def _canonical_json_bytes(value: object) -> bytes:
	"""Render the transport header in its required canonical JSON form."""
	contents = scripts.canonical_json.compact_json_bytes(value)
	return contents


#============================================
def _read_exact(stream: object, size: int, truncated_message: str) -> bytes:
	"""Read exactly one bounded binary field from a fragmented pipe stream."""
	chunks = []
	remaining = size
	while remaining:
		chunk = stream.read(remaining)
		if not chunk:
			raise RuntimeError(truncated_message)
		if not isinstance(chunk, bytes):
			raise RuntimeError("Publication bundle transfer stream must provide bytes.")
		chunks.append(chunk)
		remaining -= len(chunk)
	return b"".join(chunks)


#============================================
def _validate_transfer_header(header: dict, header_length: int) -> None:
	"""Reject envelopes that cannot describe one bounded publication bundle."""
	required = {"schema_version", "report_date", "bundle_sha256", "entries"}
	if set(header) != required:
		raise RuntimeError("Publication bundle transfer header fields are invalid.")
	if header["schema_version"] != TRANSFER_SCHEMA_VERSION:
		raise RuntimeError("Publication bundle transfer schema is unsupported.")
	if not isinstance(header["report_date"], str) or not header["report_date"]:
		raise RuntimeError("Publication bundle transfer report date is invalid.")
	if not _is_sha256(header["bundle_sha256"]):
		raise RuntimeError("Publication bundle transfer checksum is invalid.")
	entries = header["entries"]
	if not isinstance(entries, list) or not entries:
		raise RuntimeError("Publication bundle transfer entries are invalid.")
	paths = []
	total_size = 0
	for entry in entries:
		if not isinstance(entry, dict) or set(entry) != {"path", "size", "sha256"}:
			raise RuntimeError("Publication bundle transfer entry fields are invalid.")
		path = entry["path"]
		if not _is_transfer_path(path):
			raise RuntimeError("Publication bundle transfer entry path is invalid.")
		maximum_bytes = _maximum_bytes(path)
		if type(entry["size"]) is not int or entry["size"] < 0 or entry["size"] > maximum_bytes:
			raise RuntimeError("Publication bundle transfer entry exceeds its envelope.")
		if not _is_sha256(entry["sha256"]):
			raise RuntimeError("Publication bundle transfer entry checksum is invalid.")
		paths.append(path)
		total_size += entry["size"]
	if paths != sorted(paths) or len(paths) != len(set(paths)):
		raise RuntimeError("Publication bundle transfer entries must be unique and sorted.")
	if not CORE_PATHS.issubset(paths):
		raise RuntimeError("Publication bundle transfer core artifacts are incomplete.")
	encoded_size = len(TRANSFER_MAGIC) + 8 + header_length + total_size
	if encoded_size > MAX_TRANSFER_BYTES:
		raise RuntimeError("Publication bundle transfer exceeds its aggregate envelope.")


#============================================
def _is_transfer_path(path: object) -> bool:
	"""Return whether one transport path is a supported bundle artifact."""
	if not isinstance(path, str):
		return False
	if path in CORE_PATHS:
		return True
	pure = pathlib.PurePosixPath(path)
	return (
		str(pure) == path
		and
		len(pure.parts) == 2
		and pure.parts[0] == "assets"
		and pure.name == pure.parts[1]
		and not pure.is_absolute()
		and ".." not in pure.parts
	)


#============================================
def _maximum_bytes(path: str) -> int:
	"""Return the existing storage envelope for one supported transport path."""
	if path == "post.md":
		return MAX_POST_BYTES
	if path == "evidence.json":
		return MAX_EVIDENCE_BYTES
	if path.startswith("assets/"):
		return MAX_ASSET_BYTES
	return MAX_JSON_BYTES


#============================================
def _is_sha256(value: object) -> bool:
	"""Return whether one value is a lowercase SHA-256 identity."""
	return isinstance(value, str) and len(value) == 64 and set(value) <= HEX_DIGITS

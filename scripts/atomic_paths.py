"""Platform-owned atomic replacement operations for publisher directories."""

# Standard Library
import ctypes
import errno
import os
import platform


_LINUX_RENAME_EXCHANGE = 0x2
_DARWIN_RENAME_SWAP = 0x00000002
_DIRECTORY_OPEN_FLAGS = (
	os.O_RDONLY
	| getattr(os, "O_DIRECTORY", 0)
	| getattr(os, "O_NOFOLLOW", 0)
	| getattr(os, "O_CLOEXEC", 0)
)


#============================================
def _require_exchange_directories(first: str, second: str) -> tuple[str, str, str]:
	"""Return one held-parent operation shape for two physical directories."""
	first_path = os.path.abspath(first)
	second_path = os.path.abspath(second)
	parent = os.path.commonpath((first_path, second_path))
	if parent in (os.path.sep, first_path, second_path):
		raise RuntimeError("Atomic directory replacement requires a controlled common parent.")
	if (
		not os.path.isdir(first_path)
		or os.path.islink(first_path)
		or not os.path.isdir(second_path)
		or os.path.islink(second_path)
	):
		raise RuntimeError("Atomic directory replacement requires two physical directories.")
	first_relative = os.path.relpath(first_path, parent)
	second_relative = os.path.relpath(second_path, parent)
	return parent, first_relative, second_relative


#============================================
def _raise_swap_error(error_number: int) -> None:
	"""Raise one stable failure when the operating system rejects an exchange."""
	if error_number == errno.EXDEV:
		raise RuntimeError("Atomic directory replacement requires one filesystem.")
	raise RuntimeError("Atomic directory replacement was rejected by the operating system.")


#============================================
def _linux_exchange(parent_fd: int, first: bytes, second: bytes) -> None:
	"""Exchange two names through Linux renameat2 RENAME_EXCHANGE."""
	try:
		function = ctypes.CDLL(None, use_errno=True).renameat2
	except AttributeError as error:
		raise RuntimeError("Atomic directory replacement requires Linux renameat2.") from error
	function.argtypes = [
		ctypes.c_int,
		ctypes.c_char_p,
		ctypes.c_int,
		ctypes.c_char_p,
		ctypes.c_uint,
	]
	function.restype = ctypes.c_int
	if function(parent_fd, first, parent_fd, second, _LINUX_RENAME_EXCHANGE) == 0:
		return
	_raise_swap_error(ctypes.get_errno())


#============================================
def _darwin_exchange(parent_fd: int, first: bytes, second: bytes) -> None:
	"""Exchange two names through Darwin renameatx_np RENAME_SWAP."""
	try:
		function = ctypes.CDLL(None, use_errno=True).renameatx_np
	except AttributeError as error:
		raise RuntimeError("Atomic directory replacement requires Darwin renameatx_np.") from error
	function.argtypes = [
		ctypes.c_int,
		ctypes.c_char_p,
		ctypes.c_int,
		ctypes.c_char_p,
		ctypes.c_uint,
	]
	function.restype = ctypes.c_int
	if function(parent_fd, first, parent_fd, second, _DARWIN_RENAME_SWAP) == 0:
		return
	_raise_swap_error(ctypes.get_errno())


#============================================
def exchange_directories(first: str, second: str) -> None:
	"""Atomically exchange two existing physical directories on one filesystem.

	The call either leaves both directory names unchanged or swaps both names in one
	filesystem operation.  It intentionally fails closed on platforms without the
	required kernel primitive, because a remove-then-install sequence would make a
	stable publication path disappear.  The paths may be in different child
	directories beneath one controlled common parent, but must remain on the same
	filesystem for the kernel operation to succeed.
	"""
	parent, first_name, second_name = _require_exchange_directories(first, second)
	parent_fd = os.open(parent, _DIRECTORY_OPEN_FLAGS)
	try:
		system = platform.system()
		first_bytes = os.fsencode(first_name)
		second_bytes = os.fsencode(second_name)
		if system == "Linux":
			_linux_exchange(parent_fd, first_bytes, second_bytes)
			return
		if system == "Darwin":
			_darwin_exchange(parent_fd, first_bytes, second_bytes)
			return
		raise RuntimeError(
			"Atomic directory replacement requires Linux or macOS kernel support."
		)
	finally:
		os.close(parent_fd)

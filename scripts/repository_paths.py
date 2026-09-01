"""Shared physical Git repository path discovery."""

# Standard Library
import os
import subprocess


#============================================
def repository_root(start_path: str) -> str:
	"""Resolve one physical repository root through Git."""
	start = os.path.dirname(os.path.abspath(start_path))
	result = subprocess.run(
		["git", "-C", start, "rev-parse", "--show-toplevel"],
		check=False,
		text=True,
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE,
		timeout=60,
	)
	if result.returncode:
		message = result.stderr.strip() or result.stdout.strip()
		raise RuntimeError(f"Publisher repository root is unavailable: {message}")
	root = result.stdout.strip()
	if not os.path.isabs(root):
		raise RuntimeError("Publisher repository root must be absolute.")
	return root

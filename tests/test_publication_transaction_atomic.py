"""Atomic replacement tests for publisher-owned stable publication paths."""

# Standard Library
import pathlib
import platform

# PIP3 modules
import pytest

# local repo modules
import scripts.atomic_paths
import scripts.publication_transaction


#============================================
def _write_directory(path: pathlib.Path, text: str) -> None:
	"""Create one physical directory with identifiable replacement content."""
	path.mkdir()
	(path / "value.txt").write_text(text, encoding="utf-8")


#============================================
def test_exchange_keeps_the_stable_directory_name_available(tmp_path: pathlib.Path) -> None:
	"""One exchange replaces content without a remove-then-install path gap."""
	stable = tmp_path / "generated" / "releases" / "2026-08-23"
	staged = tmp_path / "generated" / "staging" / "import" / "site"
	stable.parent.mkdir(parents=True)
	staged.parent.mkdir(parents=True)
	_write_directory(stable, "old")
	_write_directory(staged, "new")

	scripts.atomic_paths.exchange_directories(str(stable), str(staged))

	assert stable.is_dir() and (stable / "value.txt").read_text(encoding="utf-8") == "new"
	assert staged.is_dir() and (staged / "value.txt").read_text(encoding="utf-8") == "old"


#============================================
def test_kernel_failure_leaves_both_directory_names_intact(
	tmp_path: pathlib.Path,
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""An injected OS failure preserves the old live path and staged candidate."""
	stable = tmp_path / "publication"
	staged = tmp_path / "stage"
	_write_directory(stable, "old")
	_write_directory(staged, "new")

	def fail_exchange(parent_fd: int, first: bytes, second: bytes) -> None:
		"""Represent a kernel rejection before either directory entry changes."""
		raise RuntimeError("synthetic atomic exchange failure")

	if platform.system() == "Linux":
		monkeypatch.setattr(scripts.atomic_paths, "_linux_exchange", fail_exchange)
	elif platform.system() == "Darwin":
		monkeypatch.setattr(scripts.atomic_paths, "_darwin_exchange", fail_exchange)
	else:
		pytest.skip("The publisher supports atomic exchange only on Linux and macOS.")
	with pytest.raises(RuntimeError, match="synthetic atomic exchange failure"):
		scripts.atomic_paths.exchange_directories(str(stable), str(staged))

	assert stable.is_dir() and (stable / "value.txt").read_text(encoding="utf-8") == "old"
	assert staged.is_dir() and (staged / "value.txt").read_text(encoding="utf-8") == "new"


#============================================
def test_cleanup_backups_removes_the_recovery_site_target(tmp_path: pathlib.Path) -> None:
	"""Successful commit cleanup discards the temporary prior served-link target."""
	(tmp_path / "previous_site_target").write_text("generated/releases/old", encoding="utf-8")

	scripts.publication_transaction._cleanup_backups(str(tmp_path))

	assert not tuple(tmp_path.iterdir())


#============================================
def test_publisher_lock_lives_in_generated_runtime_state(tmp_path: pathlib.Path) -> None:
	"""Locking records coordination below generated runtime state."""
	with scripts.publication_transaction.publisher_lock(str(tmp_path)):
		assert (tmp_path / "generated" / "publisher.lock").is_file()

	assert not (tmp_path / ".publisher.lock").exists()

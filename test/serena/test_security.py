"""
Regression tests for this fork's security patches, ported from the
pre-sync fork onto upstream v1.5.3 (see CHANGELOG.md):

- S-1: shell metacharacter guard in ``serena.util.shell.execute_shell_command``
- S-2: memory path-traversal guard in ``MemoryManager.get_memory_file_path``.
  As of the 2026-07-11 incremental sync, this fork adopted upstream's own
  ``_resolve_memory_path`` containment check (deliberately lexical, no
  symlink resolution — upstream now supports symlinked memory directories
  for monorepo sharing, see commit 310a01c1). The dotdot-segment check below
  still applies; symlink-escape is no longer rejected by design.
"""

import os
from pathlib import Path

import pytest

from serena.memories.memory_manager import MemoryManager
from serena.util.shell import execute_shell_command


class TestShellMetacharacterGuard:
    @pytest.mark.parametrize(
        "payload",
        [
            "ls; rm -rf /tmp/x",
            "ls && rm -rf /tmp/x",
            "ls | tee /tmp/x",
            "ls `whoami`",
            "ls $(whoami)",
        ],
    )
    def test_rejects_shell_metacharacters(self, payload: str) -> None:
        with pytest.raises(ValueError, match="shell metacharacter"):
            execute_shell_command(payload)

    def test_allows_plain_command(self) -> None:
        result = execute_shell_command("echo hello")
        assert result.return_code == 0
        assert "hello" in result.stdout


class TestMemoryPathTraversalGuard:
    def _manager(self, tmp_path: Path) -> MemoryManager:
        return MemoryManager(serena_data_folder=str(tmp_path))

    def test_rejects_dotdot_segments(self, tmp_path: Path) -> None:
        mm = self._manager(tmp_path)
        with pytest.raises(ValueError, match="cannot contain '..' segments"):
            mm.get_memory_file_path("../../etc/passwd")

    def test_symlinked_memory_dir_resolves_to_its_target(self, tmp_path: Path) -> None:
        """Upstream's own design decision (commit 310a01c1): a directory
        symlink inside the memories folder is a supported way to share
        memories across projects (e.g. a monorepo symlinking each
        submodule's memory dir) and must keep resolving to its target,
        even when that target is outside the nominal memory root.
        """
        mm = self._manager(tmp_path)
        memories_dir = tmp_path / "memories"
        memories_dir.mkdir(parents=True, exist_ok=True)
        outside = tmp_path.parent / f"shared_{os.getpid()}"
        outside.mkdir(exist_ok=True)
        try:
            (memories_dir / "shared_link").symlink_to(outside)
            path = mm.get_memory_file_path("shared_link/note")
            assert path.name == "note.md"
        finally:
            (memories_dir / "shared_link").unlink(missing_ok=True)
            os.rmdir(outside)

    def test_rejects_dotdot_via_lexical_normpath(self, tmp_path: Path) -> None:
        """The '..' segment check runs before ``_resolve_memory_path``, but
        even a name that slipped past it would still be caught by the
        lexical normpath containment check as a backstop.
        """
        mm = self._manager(tmp_path)
        with pytest.raises(ValueError, match="cannot contain '..' segments"):
            mm.get_memory_file_path("topic/../../escape")

    def test_allows_normal_memory_name(self, tmp_path: Path) -> None:
        mm = self._manager(tmp_path)
        path = mm.get_memory_file_path("normal_memory")
        assert path.name == "normal_memory.md"

    def test_allows_nested_memory_name(self, tmp_path: Path) -> None:
        mm = self._manager(tmp_path)
        path = mm.get_memory_file_path("topic/subtopic/note")
        assert path.name == "note.md"
        assert path.parent.name == "subtopic"

    def test_allows_global_memory_name(self, tmp_path: Path) -> None:
        mm = self._manager(tmp_path)
        path = mm.get_memory_file_path(f"{MemoryManager.GLOBAL_TOPIC}/shared_note")
        assert path.name == "shared_note.md"

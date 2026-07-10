"""
Regression tests for this fork's security patches, ported from the
pre-sync fork onto upstream v1.5.3 (see CHANGELOG.md):

- S-1: shell metacharacter guard in ``serena.util.shell.execute_shell_command``
- S-2: memory path-traversal guard in ``MemoryManager.get_memory_file_path``,
  added as defense-in-depth alongside upstream's own lexical ``".." in parts``
  check (which does not catch a symlink pointing outside the memory root).
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

    def test_rejects_symlink_escape(self, tmp_path: Path) -> None:
        """The lexical '..' check alone does not catch this: 'evil_link' has
        no '..' in its name, but resolves outside the memory root.
        """
        mm = self._manager(tmp_path)
        memories_dir = tmp_path / "memories"
        memories_dir.mkdir(parents=True, exist_ok=True)
        outside = tmp_path.parent / f"outside_{os.getpid()}"
        outside.mkdir(exist_ok=True)
        try:
            (memories_dir / "evil_link").symlink_to(outside)
            with pytest.raises(ValueError, match="escapes allowed root"):
                mm.get_memory_file_path("evil_link/pwned")
        finally:
            (memories_dir / "evil_link").unlink(missing_ok=True)
            os.rmdir(outside)

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

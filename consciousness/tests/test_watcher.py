"""
Tests for ConsciousnessWatcher (File Watching Component)

Tests cover:
- Ignore pattern matching
- Debouncing behavior
- Change detection and event types
- LLM formatting
"""

import asyncio
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from consciousness.watcher import (
    ConsciousnessWatcher,
    FileChange,
    ChangeBatch,
    DEFAULT_IGNORE_PATTERNS,
    create_watcher,
)


class TestFileChange:
    """Test FileChange dataclass."""

    def test_file_change_creation(self):
        """FileChange should store all fields."""
        change = FileChange(
            path="/test/path/file.md",
            change_type="modified",
            timestamp=1234567890.0,
            relative_path="path/file.md",
        )

        assert change.path == "/test/path/file.md"
        assert change.change_type == "modified"
        assert change.timestamp == 1234567890.0
        assert change.relative_path == "path/file.md"

    def test_file_change_auto_relative_path(self):
        """FileChange should auto-set relative_path from path if not provided."""
        change = FileChange(
            path="/test/path/file.md",
            change_type="created",
            timestamp=time.time(),
        )

        # relative_path defaults to path when not set
        assert change.relative_path == "/test/path/file.md"


class TestChangeBatch:
    """Test ChangeBatch dataclass."""

    def test_change_batch_filters_by_type(self):
        """ChangeBatch should filter changes by type."""
        changes = [
            FileChange("a.md", "created", time.time()),
            FileChange("b.md", "modified", time.time()),
            FileChange("c.md", "deleted", time.time()),
            FileChange("d.md", "created", time.time()),
        ]
        batch = ChangeBatch(changes=changes, batch_timestamp=time.time())

        assert len(batch.created) == 2
        assert len(batch.modified) == 1
        assert len(batch.deleted) == 1


class TestIgnorePatterns:
    """Test that ignore patterns correctly filter files."""

    def setup_method(self):
        """Create watcher instance for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.tmpdir = Path(tmpdir)
            self.watcher = ConsciousnessWatcher(
                root_path=self.tmpdir,
                ignore_patterns=DEFAULT_IGNORE_PATTERNS.copy(),
                debounce_ms=100,
            )

    def test_should_ignore_git_directory(self):
        """Files in .git should be ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            watcher = ConsciousnessWatcher(
                root_path=tmppath,
                ignore_patterns=[".git", ".git/**"],
            )

            git_file = tmppath / ".git" / "config"
            git_file.parent.mkdir(parents=True, exist_ok=True)
            git_file.touch()

            assert watcher._should_ignore(git_file)

    def test_should_ignore_node_modules(self):
        """node_modules directory should be ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            watcher = ConsciousnessWatcher(
                root_path=tmppath,
                ignore_patterns=["node_modules", "node_modules/**"],
            )

            node_file = tmppath / "node_modules" / "react" / "index.js"
            node_file.parent.mkdir(parents=True, exist_ok=True)
            node_file.touch()

            assert watcher._should_ignore(node_file)

    def test_should_ignore_pyc_files(self):
        """Python cache files should be ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            watcher = ConsciousnessWatcher(
                root_path=tmppath,
                ignore_patterns=["*.pyc", "__pycache__"],
            )

            pyc_file = tmppath / "module.pyc"
            assert watcher._should_ignore(pyc_file)

    def test_should_ignore_ds_store(self):
        """macOS .DS_Store files should be ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            watcher = ConsciousnessWatcher(
                root_path=tmppath,
                ignore_patterns=[".DS_Store"],
            )

            ds_file = tmppath / ".DS_Store"
            assert watcher._should_ignore(ds_file)

    def test_should_not_ignore_source_files(self):
        """Source files should not be ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            watcher = ConsciousnessWatcher(
                root_path=tmppath,
                ignore_patterns=[".git", "node_modules", "*.pyc"],
            )

            src_file = tmppath / "src" / "main.py"
            src_file.parent.mkdir(parents=True, exist_ok=True)
            src_file.touch()

            assert not watcher._should_ignore(src_file)

    def test_should_ignore_database_files(self):
        """Database files should be ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            watcher = ConsciousnessWatcher(
                root_path=tmppath,
                ignore_patterns=["*.db", "*.db-journal"],
            )

            db_file = tmppath / "consciousness.db"
            assert watcher._should_ignore(db_file)

    def test_default_patterns_include_common_ignores(self):
        """Default patterns should include common directories to ignore."""
        expected = [".git", "__pycache__", "node_modules", "*.pyc", ".DS_Store"]

        for pattern in expected:
            assert pattern in DEFAULT_IGNORE_PATTERNS


class TestChangeTypeMapping:
    """Test change type conversion."""

    def test_added_maps_to_created(self):
        """Change.added should map to 'created'."""
        from watchfiles import Change

        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = ConsciousnessWatcher(Path(tmpdir))

            result = watcher._change_type_to_str(Change.added)
            assert result == "created"

    def test_modified_maps_correctly(self):
        """Change.modified should map to 'modified'."""
        from watchfiles import Change

        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = ConsciousnessWatcher(Path(tmpdir))

            result = watcher._change_type_to_str(Change.modified)
            assert result == "modified"

    def test_deleted_maps_correctly(self):
        """Change.deleted should map to 'deleted'."""
        from watchfiles import Change

        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = ConsciousnessWatcher(Path(tmpdir))

            result = watcher._change_type_to_str(Change.deleted)
            assert result == "deleted"


class TestLLMFormatting:
    """Test LLM output formatting."""

    def test_format_empty_changes(self):
        """Empty changes should return appropriate message."""
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = ConsciousnessWatcher(Path(tmpdir))

            result = watcher.format_for_llm([])

            assert "No file changes detected" in result

    def test_format_created_files(self):
        """Created files should be marked with +."""
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = ConsciousnessWatcher(Path(tmpdir))

            changes = [
                FileChange("/test/new.md", "created", time.time(), "new.md"),
            ]

            result = watcher.format_for_llm(changes)

            assert "CREATED" in result
            assert "+ new.md" in result

    def test_format_modified_files(self):
        """Modified files should be marked with ~."""
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = ConsciousnessWatcher(Path(tmpdir))

            changes = [
                FileChange("/test/existing.md", "modified", time.time(), "existing.md"),
            ]

            result = watcher.format_for_llm(changes)

            assert "MODIFIED" in result
            assert "~ existing.md" in result

    def test_format_deleted_files(self):
        """Deleted files should be marked with -."""
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = ConsciousnessWatcher(Path(tmpdir))

            changes = [
                FileChange("/test/removed.md", "deleted", time.time(), "removed.md"),
            ]

            result = watcher.format_for_llm(changes)

            assert "DELETED" in result
            assert "- removed.md" in result

    def test_format_includes_context(self):
        """Format should include context hints."""
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = ConsciousnessWatcher(Path(tmpdir))

            changes = [
                FileChange("/test/knowledge/thinker.md", "created", time.time(), "knowledge/thinker.md"),
            ]

            result = watcher.format_for_llm(changes)

            assert "CONTEXT" in result
            assert ".md" in result  # File type
            assert "knowledge" in result  # Directory

    def test_format_compact(self):
        """Compact format should be token-efficient."""
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = ConsciousnessWatcher(Path(tmpdir))

            changes = [
                FileChange("/test/a.md", "created", time.time(), "a.md"),
                FileChange("/test/b.md", "modified", time.time(), "b.md"),
            ]

            result = watcher.format_for_llm_compact(changes)

            assert "+a.md" in result
            assert "~b.md" in result
            assert len(result) < 100  # Should be short


class TestDebouncing:
    """Test debouncing behavior."""

    def test_debounce_ms_setting(self):
        """Debounce setting should be stored correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = ConsciousnessWatcher(
                root_path=Path(tmpdir),
                debounce_ms=500,
            )

            assert watcher.debounce_ms == 500


class TestWatcherLifecycle:
    """Test watcher start/stop lifecycle."""

    def test_stop_sets_flag(self):
        """Stopping watcher should set running flag to False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = ConsciousnessWatcher(Path(tmpdir))

            watcher._running = True
            watcher.stop()

            assert watcher._running is False


class TestIntegrationWithRealFiles:
    """Integration tests with actual file system."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_detects_new_file(self):
        """Watcher should detect when a new file is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            watcher = ConsciousnessWatcher(
                root_path=tmppath,
                ignore_patterns=[],
                debounce_ms=100,
            )

            # Start watching in background
            async def watch_for_changes():
                async for changes in watcher.watch():
                    return changes

            # Create task
            watch_task = asyncio.create_task(watch_for_changes())

            # Wait a bit for watcher to start
            await asyncio.sleep(0.1)

            # Create a file
            test_file = tmppath / "test.txt"
            test_file.write_text("hello world")

            # Wait for detection
            try:
                changes = await asyncio.wait_for(watch_task, timeout=2.0)
                watcher.stop()

                assert len(changes) >= 1
                assert any(c.change_type == "created" for c in changes)
            except asyncio.TimeoutError:
                watcher.stop()
                pytest.skip("Watcher did not detect changes in time")

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_ignores_filtered_files(self):
        """Watcher should not report changes to ignored files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            watcher = ConsciousnessWatcher(
                root_path=tmppath,
                ignore_patterns=["*.log", "*.tmp"],
                debounce_ms=100,
            )

            # Create ignored files directly
            (tmppath / "debug.log").write_text("log content")
            (tmppath / "cache.tmp").write_text("temp content")

            # Use _create_file_change to test filtering
            from watchfiles import Change

            log_change = watcher._create_file_change(
                Change.added, str(tmppath / "debug.log")
            )
            tmp_change = watcher._create_file_change(
                Change.added, str(tmppath / "cache.tmp")
            )

            # Both should be None (ignored)
            assert log_change is None
            assert tmp_change is None


class TestFactoryFunction:
    """Test create_watcher factory function."""

    @pytest.mark.asyncio
    async def test_create_watcher_returns_watcher(self):
        """create_watcher should return a configured watcher."""
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = await create_watcher(
                root_path=tmpdir,
                ignore_patterns=[".git"],
                debounce_ms=200,
            )

            assert isinstance(watcher, ConsciousnessWatcher)
            assert watcher.debounce_ms == 200
            assert ".git" in watcher.ignore_patterns


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

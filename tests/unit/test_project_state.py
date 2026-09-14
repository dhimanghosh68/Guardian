from pathlib import Path

import pytest

from guardian.project import ProjectState, ProjectStateCapture


def test_project_state_capture_records_project_root(tmp_path):
    root = tmp_path / "project"
    root.mkdir()

    state = ProjectStateCapture().capture(root)

    assert state.root == root
    assert state.normalized_root() == root
    assert state.filesystem.root == root


def test_project_state_capture_records_filesystem_state(tmp_path):
    root = tmp_path / "project"
    root.mkdir()

    file = root / "README.md"
    file.write_text("guardian", encoding="utf-8")

    state = ProjectStateCapture().capture(root)

    observation = state.filesystem.by_path()[file]

    assert observation.exists
    assert observation.size == len("guardian")


def test_project_state_is_immutable(tmp_path):
    root = tmp_path / "project"
    root.mkdir()

    state = ProjectStateCapture().capture(root)

    with pytest.raises(AttributeError):
        state.root = Path("/tmp")


def test_project_state_capture_does_not_modify_project(tmp_path):
    root = tmp_path / "project"
    root.mkdir()

    file = root / "file.txt"
    file.write_text("original", encoding="utf-8")
    before = file.stat()

    ProjectStateCapture().capture(root)

    after = file.stat()

    assert file.read_text(encoding="utf-8") == "original"
    assert after.st_mtime_ns == before.st_mtime_ns
    assert after.st_size == before.st_size


def test_project_state_capture_uses_normalized_root(tmp_path):
    root = tmp_path / "project"
    root.mkdir()

    state = ProjectStateCapture().capture(root / ".")

    assert state.root == root
    assert state.filesystem.root == root

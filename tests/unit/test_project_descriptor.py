from pathlib import Path

import pytest

from guardian.project import (
    ProjectDescriptor,
    ProjectDescriptorDetector,
    ProjectKind,
)


def test_detector_reports_python_project(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "pyproject.toml").write_text("", encoding="utf-8")

    descriptor = ProjectDescriptorDetector().detect(root)

    assert descriptor.root == root
    assert descriptor.markers == ("pyproject.toml",)
    assert descriptor.kinds == (ProjectKind.PYTHON,)
    assert descriptor.has_marker("pyproject.toml")
    assert descriptor.has_kind(ProjectKind.PYTHON)


def test_detector_reports_multiple_independent_markers(tmp_path):
    root = tmp_path / "project"
    root.mkdir()

    for marker in ("pyproject.toml", "Dockerfile", "Makefile"):
        (root / marker).write_text("", encoding="utf-8")

    descriptor = ProjectDescriptorDetector().detect(root)

    assert descriptor.markers == (
        "pyproject.toml",
        "Makefile",
        "Dockerfile",
    )
    assert descriptor.kinds == (
        ProjectKind.PYTHON,
        ProjectKind.MAKE,
        ProjectKind.DOCKER,
    )


def test_detector_reports_gradle_kotlin_marker(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "build.gradle.kts").write_text("", encoding="utf-8")

    descriptor = ProjectDescriptorDetector().detect(root)

    assert descriptor.markers == ("build.gradle.kts",)
    assert descriptor.kinds == (ProjectKind.GRADLE,)


def test_detector_reports_git_marker(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / ".git").mkdir()

    descriptor = ProjectDescriptorDetector().detect(root)

    assert descriptor.markers == (".git",)
    assert descriptor.kinds == (ProjectKind.GIT,)


def test_detector_reports_no_markers(tmp_path):
    root = tmp_path / "project"
    root.mkdir()

    descriptor = ProjectDescriptorDetector().detect(root)

    assert descriptor == ProjectDescriptor(
        root=root,
        markers=(),
        kinds=(),
    )


def test_descriptor_is_immutable(tmp_path):
    root = tmp_path / "project"
    root.mkdir()

    descriptor = ProjectDescriptorDetector().detect(root)

    with pytest.raises(AttributeError):
        descriptor.root = Path("/tmp")


def test_detector_does_not_execute_or_modify_project(tmp_path):
    root = tmp_path / "project"
    root.mkdir()

    marker = root / "pyproject.toml"
    marker.write_text("[project]\nname='test'\n", encoding="utf-8")
    before = marker.stat()

    ProjectDescriptorDetector().detect(root)

    after = marker.stat()

    assert marker.read_text(encoding="utf-8") == "[project]\nname='test'\n"
    assert after.st_mtime_ns == before.st_mtime_ns
    assert after.st_size == before.st_size

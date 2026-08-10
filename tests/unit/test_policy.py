from pathlib import Path

from guardian.policy import SafetyBoundary


def test_system_paths_are_protected() -> None:
    boundary = SafetyBoundary()

    assert boundary.protects(Path("/etc"))
    assert boundary.protects(Path("/usr/bin/example"))
    assert boundary.protects(Path("/boot/example"))


def test_guardian_lab_is_not_protected_by_host_policy() -> None:
    boundary = SafetyBoundary()

    lab = Path.home() / "Development" / "guardian-lab"

    assert not boundary.protects(lab)


def test_protected_project_is_protected() -> None:
    boundary = SafetyBoundary()

    project = Path.home() / "Development" / "react"

    assert boundary.protects(project)
    assert boundary.protects(project / "src")

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


def test_unrelated_path_with_similar_name_is_not_protected() -> None:
    boundary = SafetyBoundary()

    assert not boundary.protects(Path("/etc-backup"))
    assert not boundary.protects(Path("/usr-local"))


def test_nested_protected_path_is_protected() -> None:
    boundary = SafetyBoundary()

    assert boundary.protects(Path("/var/lib/guardian"))
    assert boundary.protects(Path("/usr/local/bin/tool"))


def test_protected_project_sibling_is_not_protected() -> None:
    boundary = SafetyBoundary()

    project = Path.home() / "Development" / "react"

    assert not boundary.protects(
        Path(str(project) + "-backup")
    )


def test_operation_policy_allows_non_destructive_operations() -> None:
    from guardian.core.operation import GuardianOperation
    from guardian.policy import OperationPolicy

    policy = OperationPolicy()

    assert policy.allows(GuardianOperation.INSPECT)
    assert policy.allows(GuardianOperation.MODIFY)
    assert policy.allows(GuardianOperation.WRITE)
    assert policy.allows(GuardianOperation.RESTORE)


def test_operation_policy_blocks_delete() -> None:
    from guardian.core.operation import GuardianOperation
    from guardian.policy import OperationPolicy

    policy = OperationPolicy()

    assert not policy.allows(GuardianOperation.DELETE)

from pathlib import Path
from guardian.sandbox import SandboxWorkspace
from guardian.core import (
    Guardian,
    GuardianRequest,
    GuardianStatus,
)


def test_guardian_allows_unprotected_target() -> None:
    guardian = Guardian()

    request = GuardianRequest(
        target=Path("/tmp/example"),
        operation="inspect",
    )

    result = guardian.evaluate(request)

    assert result.status is GuardianStatus.ALLOWED
    assert result.allowed
    assert result.target == Path("/tmp/example").resolve()


def test_guardian_blocks_system_target() -> None:
    guardian = Guardian()

    request = GuardianRequest(
        target=Path("/etc"),
        operation="delete",
    )

    result = guardian.evaluate(request)

    assert result.status is GuardianStatus.BLOCKED
    assert not result.allowed
    assert result.target == Path("/etc").resolve()


def test_guardian_blocks_protected_project() -> None:
    guardian = Guardian()

    project = Path.home() / "Development" / "react"

    request = GuardianRequest(
        target=project / "src",
        operation="modify",
    )

    result = guardian.evaluate(request)

    assert result.status is GuardianStatus.BLOCKED
    assert not result.allowed


def test_guardian_rejects_invalid_request() -> None:
    import pytest

    request = GuardianRequest(
        target=Path("/tmp/example"),
        operation="   ",
    )

    with pytest.raises(ValueError, match="operation"):
        Guardian().evaluate(request)

def test_guardian_allows_target_inside_workspace() -> None:
    workspace = SandboxWorkspace(Path("/tmp/guardian-workspace"))
    guardian = Guardian(workspace=workspace)

    request = GuardianRequest(
        target=Path("/tmp/guardian-workspace/project"),
        operation="inspect",
    )

    result = guardian.evaluate(request)

    assert result.allowed
    assert result.message == "operation permitted"


def test_guardian_blocks_target_outside_workspace() -> None:
    workspace = SandboxWorkspace(Path("/tmp/guardian-workspace"))
    guardian = Guardian(workspace=workspace)

    request = GuardianRequest(
        target=Path("/tmp/outside"),
        operation="inspect",
    )

    result = guardian.evaluate(request)

    assert not result.allowed
    assert result.status is GuardianStatus.BLOCKED
    assert result.message == "target is outside the Guardian workspace"


def test_guardian_host_policy_overrides_workspace() -> None:
    workspace = SandboxWorkspace(Path("/"))
    guardian = Guardian(workspace=workspace)

    request = GuardianRequest(
        target=Path("/etc"),
        operation="inspect",
    )

    result = guardian.evaluate(request)

    assert not result.allowed
    assert result.status is GuardianStatus.BLOCKED
    assert result.message == "target is protected by host policy"


def test_guardian_blocks_delete_by_operation_policy() -> None:
    guardian = Guardian()

    request = GuardianRequest(
        target=Path("/tmp/example"),
        operation="delete",
    )

    result = guardian.evaluate(request)

    assert result.status is GuardianStatus.BLOCKED
    assert not result.allowed
    assert result.message == "operation is blocked by Guardian policy"


def test_guardian_operation_policy_runs_before_host_policy() -> None:
    guardian = Guardian()

    request = GuardianRequest(
        target=Path("/etc"),
        operation="delete",
    )

    result = guardian.evaluate(request)

    assert result.status is GuardianStatus.BLOCKED
    assert result.message == "operation is blocked by Guardian policy"

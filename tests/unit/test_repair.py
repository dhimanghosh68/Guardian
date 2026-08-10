import pytest
from pathlib import Path

from guardian.core import GuardianRequest
from guardian.repair import RepairAction, RepairPlanner
from guardian.sandbox import SandboxWorkspace


def test_repair_normalizes_target() -> None:
    action = RepairAction(
        operation="restore",
        target=Path("~/Development/guardian-lab"),
    )

    assert action.normalized_target() == (
        Path.home() / "Development" / "guardian-lab"
    ).resolve()


def test_repair_is_immutable() -> None:
    action = RepairAction(
        operation="restore",
        target=Path("/tmp/example"),
    )

    try:
        action.operation = "delete"
    except AttributeError:
        pass
    else:
        raise AssertionError("RepairAction must be immutable")


def test_repair_planner_creates_proposal() -> None:
    request = GuardianRequest(
        target=Path("/tmp/example"),
        operation="restore",
    )

    action = RepairPlanner().plan(request)

    assert action.operation == "restore"
    assert action.normalized_target() == Path("/tmp/example").resolve()


def test_repair_planner_rejects_protected_target() -> None:
    request = GuardianRequest(
        target=Path("/etc"),
        operation="restore",
    )

    try:
        RepairPlanner().plan(request)
    except PermissionError as exc:
        assert "host policy" in str(exc)
    else:
        raise AssertionError("protected repair target must be rejected")


def test_repair_planner_rejects_target_outside_workspace() -> None:
    planner = RepairPlanner(
        workspace=SandboxWorkspace(Path("/tmp/guardian-workspace")),
    )

    request = GuardianRequest(
        target=Path("/tmp/outside"),
        operation="restore",
    )

    try:
        planner.plan(request)
    except PermissionError as exc:
        assert "workspace" in str(exc)
    else:
        raise AssertionError("outside repair target must be rejected")

def test_repair_planner_rejects_invalid_request() -> None:
    planner = RepairPlanner()

    request = GuardianRequest(
        target=Path("/tmp/example"),
        operation="   ",
    )

    with pytest.raises(ValueError, match="operation"):
        planner.plan(request)

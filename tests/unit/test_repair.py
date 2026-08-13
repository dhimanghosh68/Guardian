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


def test_repair_executor_writes_file(tmp_path) -> None:
    from guardian.repair import RepairAction, RepairExecutor, RepairStatus

    workspace = SandboxWorkspace(tmp_path / "workspace")
    workspace.root.mkdir()

    target = workspace.root / "project" / "file.txt"

    action = RepairAction(
        operation="write",
        target=target,
        content="repaired\n",
    )

    result = RepairExecutor(workspace=workspace).execute(action)

    assert result.status is RepairStatus.APPLIED
    assert result.applied
    assert target.read_text(encoding="utf-8") == "repaired\n"


def test_repair_executor_replaces_existing_file(tmp_path) -> None:
    from guardian.repair import RepairAction, RepairExecutor, RepairStatus

    workspace = SandboxWorkspace(tmp_path / "workspace")
    workspace.root.mkdir()

    target = workspace.root / "file.txt"
    target.write_text("old\n", encoding="utf-8")

    action = RepairAction(
        operation="modify",
        target=target,
        content="new\n",
    )

    result = RepairExecutor(workspace=workspace).execute(action)

    assert result.status is RepairStatus.APPLIED
    assert target.read_text(encoding="utf-8") == "new\n"


def test_repair_executor_rejects_missing_content(tmp_path) -> None:
    from guardian.repair import RepairAction, RepairExecutor, RepairStatus

    workspace = SandboxWorkspace(tmp_path / "workspace")
    workspace.root.mkdir()

    result = RepairExecutor(workspace=workspace).execute(
        RepairAction(
            operation="write",
            target=workspace.root / "file.txt",
        )
    )

    assert result.status is RepairStatus.REJECTED
    assert "content" in result.message


def test_repair_executor_rejects_directory_target(tmp_path) -> None:
    from guardian.repair import RepairAction, RepairExecutor, RepairStatus

    workspace = SandboxWorkspace(tmp_path / "workspace")
    workspace.root.mkdir()

    target = workspace.root / "directory"
    target.mkdir()

    result = RepairExecutor(workspace=workspace).execute(
        RepairAction(
            operation="write",
            target=target,
            content="data",
        )
    )

    assert result.status is RepairStatus.REJECTED
    assert "regular file" in result.message


def test_repair_executor_rejects_delete_by_policy(tmp_path) -> None:
    from guardian.repair import RepairAction, RepairExecutor, RepairStatus

    workspace = SandboxWorkspace(tmp_path / "workspace")
    workspace.root.mkdir()

    target = workspace.root / "file.txt"
    target.write_text("keep", encoding="utf-8")

    result = RepairExecutor(workspace=workspace).execute(
        RepairAction(
            operation="delete",
            target=target,
        )
    )

    assert result.status is RepairStatus.REJECTED
    assert "blocked" in result.message
    assert target.read_text(encoding="utf-8") == "keep"


def test_repair_executor_rejects_outside_workspace(tmp_path) -> None:
    from guardian.repair import RepairAction, RepairExecutor, RepairStatus

    workspace = SandboxWorkspace(tmp_path / "workspace")
    workspace.root.mkdir()

    target = tmp_path / "outside.txt"

    result = RepairExecutor(workspace=workspace).execute(
        RepairAction(
            operation="write",
            target=target,
            content="must not write",
        )
    )

    assert result.status is RepairStatus.REJECTED
    assert "workspace" in result.message
    assert not target.exists()


def test_repair_action_content_is_immutable() -> None:
    from guardian.repair import RepairAction

    action = RepairAction(
        operation="write",
        target=Path("/tmp/example"),
        content="data",
    )

    try:
        action.content = "changed"
    except AttributeError:
        pass
    else:
        raise AssertionError("RepairAction must be immutable")


def test_repair_executor_preserves_existing_file_mode(tmp_path) -> None:
    import os
    import stat

    from guardian.repair import RepairAction, RepairExecutor, RepairStatus

    workspace = SandboxWorkspace(tmp_path / "workspace")
    workspace.root.mkdir()

    target = workspace.root / "file.txt"
    target.write_text("old\n", encoding="utf-8")
    os.chmod(target, 0o640)

    action = RepairAction(
        operation="modify",
        target=target,
        content="new\n",
    )

    result = RepairExecutor(workspace=workspace).execute(action)

    assert result.status is RepairStatus.APPLIED
    assert stat.S_IMODE(target.stat().st_mode) == 0o640


def test_repair_executor_rejects_symlink_target_outside_workspace(
    tmp_path,
) -> None:
    from guardian.repair import RepairAction, RepairExecutor, RepairStatus

    workspace = SandboxWorkspace(tmp_path / "workspace")
    workspace.root.mkdir()

    outside = tmp_path / "outside.txt"
    outside.write_text("must remain unchanged", encoding="utf-8")

    target = workspace.root / "file.txt"
    target.symlink_to(outside)

    result = RepairExecutor(workspace=workspace).execute(
        RepairAction(
            operation="modify",
            target=target,
            content="must not write",
        )
    )

    assert result.status is RepairStatus.REJECTED
    assert "workspace" in result.message
    assert outside.read_text(encoding="utf-8") == "must remain unchanged"


def test_repair_executor_replaces_internal_symlink_destination(
    tmp_path,
) -> None:
    from guardian.repair import RepairAction, RepairExecutor, RepairStatus

    workspace = SandboxWorkspace(tmp_path / "workspace")
    workspace.root.mkdir()

    source = workspace.root / "source.txt"
    source.write_text("old", encoding="utf-8")

    target = workspace.root / "target.txt"
    target.symlink_to(source)

    result = RepairExecutor(workspace=workspace).execute(
        RepairAction(
            operation="modify",
            target=target,
            content="new",
        )
    )

    assert result.status is RepairStatus.APPLIED
    assert source.read_text(encoding="utf-8") == "new"
    assert target.is_symlink()
    assert target.resolve() == source.resolve()

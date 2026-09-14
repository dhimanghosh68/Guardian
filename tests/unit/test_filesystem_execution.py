import os
import stat
from pathlib import Path

import pytest

from guardian.adapters import FilesystemExecutionAdapter
from guardian.core import Guardian, GuardianOperation, GuardianRequest
from guardian.execution import (
    AuthorizedExecution,
    ExecutionAdapterRegistry,
    ExecutionCoordinator,
    ExecutionStatus,
)
from guardian.policy import SafetyBoundary
from guardian.sandbox import SandboxWorkspace


def make_guardian(tmp_path: Path) -> Guardian:
    return Guardian(
        boundary=SafetyBoundary(
            protected_paths=(),
            protected_projects=(),
        ),
        workspace=SandboxWorkspace(tmp_path),
    )


def test_filesystem_adapter_reports_capabilities():
    adapter = FilesystemExecutionAdapter()

    assert adapter.capabilities == frozenset(
        {
            "filesystem.write",
            "filesystem.modify",
        }
    )


def test_filesystem_adapter_supports_write(tmp_path):
    adapter = FilesystemExecutionAdapter()

    request = GuardianRequest(
        target=tmp_path / "file.txt",
        operation="write",
        content="hello\n",
    )

    assert adapter.can_execute(request)


def test_filesystem_adapter_supports_modify(tmp_path):
    adapter = FilesystemExecutionAdapter()

    request = GuardianRequest(
        target=tmp_path / "file.txt",
        operation="modify",
        content="changed\n",
    )

    assert adapter.can_execute(request)


@pytest.mark.parametrize("operation", ["inspect", "restore", "delete"])
def test_filesystem_adapter_rejects_unsupported_operations(
    tmp_path,
    operation,
):
    adapter = FilesystemExecutionAdapter()

    request = GuardianRequest(
        target=tmp_path / "file.txt",
        operation=operation,
    )

    assert not adapter.can_execute(request)


def test_filesystem_adapter_writes_authorized_content(tmp_path):
    adapter = FilesystemExecutionAdapter()
    target = tmp_path / "file.txt"

    adapter.execute(
        AuthorizedExecution(
            operation=GuardianOperation.WRITE,
            target=target,
            content="hello\n",
        )
    )

    assert target.read_text(encoding="utf-8") == "hello\n"


def test_filesystem_adapter_modifies_existing_file(tmp_path):
    adapter = FilesystemExecutionAdapter()
    target = tmp_path / "file.txt"

    target.write_text("old\n", encoding="utf-8")

    adapter.execute(
        AuthorizedExecution(
            operation=GuardianOperation.MODIFY,
            target=target,
            content="new\n",
        )
    )

    assert target.read_text(encoding="utf-8") == "new\n"


def test_filesystem_adapter_preserves_existing_mode(tmp_path):
    adapter = FilesystemExecutionAdapter()
    target = tmp_path / "file.txt"

    target.write_text("old\n", encoding="utf-8")
    os.chmod(target, 0o640)

    adapter.execute(
        AuthorizedExecution(
            operation=GuardianOperation.MODIFY,
            target=target,
            content="new\n",
        )
    )

    assert stat.S_IMODE(target.stat().st_mode) == 0o640


def test_filesystem_adapter_requires_content(tmp_path):
    adapter = FilesystemExecutionAdapter()

    with pytest.raises(ValueError, match="content"):
        adapter.execute(
            AuthorizedExecution(
                operation=GuardianOperation.WRITE,
                target=tmp_path / "file.txt",
            )
        )


def test_filesystem_adapter_rejects_directory(tmp_path):
    adapter = FilesystemExecutionAdapter()
    target = tmp_path / "directory"
    target.mkdir()

    with pytest.raises(ValueError, match="regular file"):
        adapter.execute(
            AuthorizedExecution(
                operation=GuardianOperation.WRITE,
                target=target,
                content="data",
            )
        )


def test_coordinator_executes_filesystem_write(tmp_path):
    guardian = make_guardian(tmp_path)
    adapter = FilesystemExecutionAdapter()

    request = GuardianRequest(
        target=tmp_path / "project" / "file.txt",
        operation="write",
        content="created\n",
    )

    result = ExecutionCoordinator(
        guardian=guardian,
        adapter=adapter,
    ).execute(request)

    assert result.status is ExecutionStatus.EXECUTED
    assert (
        tmp_path / "project" / "file.txt"
    ).read_text(encoding="utf-8") == "created\n"


def test_coordinator_passes_authorized_content_only_after_authorization(
    tmp_path,
):
    guardian = make_guardian(tmp_path)
    adapter = FilesystemExecutionAdapter()

    request = GuardianRequest(
        target=tmp_path / "file.txt",
        operation="write",
        content="authorized\n",
    )

    result = ExecutionCoordinator(
        guardian=guardian,
        adapter=adapter,
    ).execute(request)

    assert result.status is ExecutionStatus.EXECUTED
    assert (tmp_path / "file.txt").read_text(
        encoding="utf-8"
    ) == "authorized\n"


def test_coordinator_blocks_protected_target(tmp_path):
    protected = tmp_path / "protected"
    protected.mkdir()

    guardian = Guardian(
        boundary=SafetyBoundary(
            protected_paths=(protected,),
            protected_projects=(),
        ),
        workspace=SandboxWorkspace(tmp_path),
    )

    adapter = FilesystemExecutionAdapter()

    request = GuardianRequest(
        target=protected / "file.txt",
        operation="write",
        content="must not exist",
    )

    result = ExecutionCoordinator(
        guardian=guardian,
        adapter=adapter,
    ).execute(request)

    assert result.status is ExecutionStatus.REJECTED
    assert not (protected / "file.txt").exists()


def test_coordinator_blocks_target_outside_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    outside = tmp_path / "outside.txt"

    guardian = Guardian(
        boundary=SafetyBoundary(
            protected_paths=(),
            protected_projects=(),
        ),
        workspace=SandboxWorkspace(workspace),
    )

    adapter = FilesystemExecutionAdapter()

    request = GuardianRequest(
        target=outside,
        operation="write",
        content="must not exist",
    )

    result = ExecutionCoordinator(
        guardian=guardian,
        adapter=adapter,
    ).execute(request)

    assert result.status is ExecutionStatus.REJECTED
    assert not outside.exists()


def test_coordinator_registry_selects_filesystem_adapter(tmp_path):
    guardian = make_guardian(tmp_path)
    adapter = FilesystemExecutionAdapter()

    registry = ExecutionAdapterRegistry()
    registry.register(adapter)

    request = GuardianRequest(
        target=tmp_path / "file.txt",
        operation="write",
        content="registry\n",
    )

    result = ExecutionCoordinator(
        guardian=guardian,
        registry=registry,
    ).execute(request)

    assert result.status is ExecutionStatus.EXECUTED
    assert (tmp_path / "file.txt").read_text(
        encoding="utf-8"
    ) == "registry\n"



def test_coordinator_rejects_symlink_resolving_outside_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    outside = tmp_path / "outside"
    outside.mkdir()

    link = workspace / "linked"
    link.symlink_to(outside, target_is_directory=True)

    guardian = Guardian(
        boundary=SafetyBoundary(
            protected_paths=(),
            protected_projects=(),
        ),
        workspace=SandboxWorkspace(workspace),
    )

    result = ExecutionCoordinator(
        guardian=guardian,
        adapter=FilesystemExecutionAdapter(),
    ).execute(
        GuardianRequest(
            target=link / "file.txt",
            operation="write",
            content="must not escape workspace",
        )
    )

    assert result.status is ExecutionStatus.REJECTED
    assert not (outside / "file.txt").exists()


def test_coordinator_rejects_symlink_file_resolving_outside_workspace(
    tmp_path,
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    outside = tmp_path / "outside"
    outside.mkdir()

    outside_target = outside / "target.txt"
    link = workspace / "linked.txt"
    link.symlink_to(outside_target)

    guardian = Guardian(
        boundary=SafetyBoundary(
            protected_paths=(),
            protected_projects=(),
        ),
        workspace=SandboxWorkspace(workspace),
    )

    result = ExecutionCoordinator(
        guardian=guardian,
        adapter=FilesystemExecutionAdapter(),
    ).execute(
        GuardianRequest(
            target=link,
            operation="write",
            content="must not escape workspace",
        )
    )

    assert result.status is ExecutionStatus.REJECTED
    assert not outside_target.exists()

def test_authorized_execution_remains_immutable(tmp_path):
    authorization = AuthorizedExecution(
        operation=GuardianOperation.WRITE,
        target=tmp_path / "file.txt",
        content="immutable",
    )

    with pytest.raises(AttributeError):
        authorization.content = "changed"


def test_request_content_remains_immutable(tmp_path):
    request = GuardianRequest(
        target=tmp_path / "file.txt",
        operation="write",
        content="immutable",
    )

    with pytest.raises(AttributeError):
        request.content = "changed"


def test_filesystem_adapter_rejects_delete_even_if_directly_authorized(
    tmp_path,
):
    adapter = FilesystemExecutionAdapter()

    with pytest.raises(ValueError, match="does not support"):
        adapter.execute(
            AuthorizedExecution(
                operation=GuardianOperation.DELETE,
                target=tmp_path / "file.txt",
                content=None,
            )
        )

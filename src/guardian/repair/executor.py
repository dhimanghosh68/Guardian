import os
import stat
import tempfile
from pathlib import Path

from guardian.core.operation import GuardianOperation
from guardian.policy import OperationPolicy, SafetyBoundary
from guardian.repair.action import RepairAction
from guardian.repair.result import RepairResult, RepairStatus
from guardian.sandbox import SandboxWorkspace


class RepairExecutor:
    """Execute explicitly planned repairs within Guardian safety boundaries."""

    def __init__(
        self,
        boundary: SafetyBoundary | None = None,
        workspace: SandboxWorkspace | None = None,
        operation_policy: OperationPolicy | None = None,
    ) -> None:
        self._boundary = boundary or SafetyBoundary()
        self._workspace = workspace
        self._operation_policy = operation_policy or OperationPolicy()

    def execute(self, action: RepairAction) -> RepairResult:
        """Execute a repair action after re-validating its safety boundary."""

        target = action.normalized_target()

        try:
            operation = GuardianOperation.parse(action.operation)
        except ValueError as exc:
            return RepairResult(
                status=RepairStatus.REJECTED,
                operation=action.operation,
                target=target,
                message=str(exc),
            )

        if not self._operation_policy.allows(operation):
            return RepairResult(
                status=RepairStatus.REJECTED,
                operation=action.operation,
                target=target,
                message="operation is blocked by Guardian policy",
            )

        if self._boundary.protects(target):
            return RepairResult(
                status=RepairStatus.REJECTED,
                operation=action.operation,
                target=target,
                message="target is protected by host policy",
            )

        if self._workspace is not None and not self._workspace.contains(target):
            return RepairResult(
                status=RepairStatus.REJECTED,
                operation=action.operation,
                target=target,
                message="target is outside the Guardian workspace",
            )

        if operation not in {
            GuardianOperation.WRITE,
            GuardianOperation.MODIFY,
        }:
            return RepairResult(
                status=RepairStatus.REJECTED,
                operation=action.operation,
                target=target,
                message=f"repair execution does not support {operation.value}",
            )

        if action.content is None:
            return RepairResult(
                status=RepairStatus.REJECTED,
                operation=action.operation,
                target=target,
                message="repair content is required for file mutation",
            )

        if target.exists() and not target.is_file():
            return RepairResult(
                status=RepairStatus.REJECTED,
                operation=action.operation,
                target=target,
                message="repair target is not a regular file",
            )

        try:
            self._atomic_write(target, action.content)
        except OSError as exc:
            return RepairResult(
                status=RepairStatus.FAILED,
                operation=action.operation,
                target=target,
                message=f"repair failed: {exc}",
            )

        return RepairResult(
            status=RepairStatus.APPLIED,
            operation=action.operation,
            target=target,
            message="repair applied successfully",
        )

    @staticmethod
    def _atomic_write(target: Path, content: str) -> None:
        """Atomically replace a file while preserving its existing mode."""

        parent = target.parent
        parent.mkdir(parents=True, exist_ok=True)

        existing_mode: int | None = None
        if target.exists():
            existing_mode = stat.S_IMODE(target.stat().st_mode)

        fd, temporary = tempfile.mkstemp(
            prefix=f".{target.name}.",
            dir=parent,
            text=True,
        )

        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)

                if existing_mode is not None:
                    os.fchmod(handle.fileno(), existing_mode)

                handle.flush()
                os.fsync(handle.fileno())

            os.replace(temporary, target)
        except BaseException:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            raise

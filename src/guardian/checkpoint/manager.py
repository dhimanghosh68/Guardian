from pathlib import Path

from guardian.checkpoint.state import CheckpointState
from guardian.checkpoint.store import CheckpointStore
from guardian.core.request import GuardianRequest
from guardian.restore import (
    RestoreBackend,
    RestorePlan,
    RestoreResult,
    RestoreStatus,
)
from guardian.sandbox import SandboxWorkspace


class CheckpointManager:
    """Creates, validates, persists, and loads Guardian checkpoints."""

    def __init__(
        self,
        workspace: SandboxWorkspace | None = None,
        store: CheckpointStore | None = None,
        restore_backend: RestoreBackend | None = None,
    ) -> None:
        self._workspace = workspace
        self._store = store
        self._restore_backend = restore_backend

    def prepare(self, request: GuardianRequest) -> CheckpointState:
        """Prepare and optionally persist a checkpoint for a request."""

        if self._workspace is None:
            raise ValueError("workspace is required for prepare()")

        target = request.normalized_target()

        if not self._workspace.contains(target):
            raise PermissionError(
                "checkpoint target is outside the Guardian workspace"
            )

        checkpoint = CheckpointState.create(
            workspace=self._workspace.normalized_root(),
            operation=request.operation.strip(),
            target=target,
        )

        self._persist(checkpoint)
        return checkpoint

    def create(
        self,
        workspace: Path,
        operation: str,
        target: Path,
    ) -> CheckpointState:
        """Create a standalone checkpoint state."""

        normalized_workspace = workspace.expanduser().resolve(strict=False)
        normalized_target = target.expanduser().resolve(strict=False)

        try:
            normalized_target.relative_to(normalized_workspace)
        except ValueError as exc:
            raise PermissionError(
                "checkpoint target is outside the Guardian workspace"
            ) from exc

        checkpoint = CheckpointState.create(
            workspace=normalized_workspace,
            operation=operation.strip(),
            target=normalized_target,
        )

        self._persist(checkpoint)
        return checkpoint

    def save(self, checkpoint: CheckpointState) -> None:
        """Persist an existing checkpoint."""

        if self._store is None:
            raise ValueError("store is required for save()")

        self._store.save(checkpoint)

    def load(self, checkpoint_id):
        """Load a persisted checkpoint."""

        if self._store is None:
            raise ValueError("store is required for load()")

        return self._store.load(checkpoint_id)

    def restore(self, checkpoint: CheckpointState) -> RestoreResult:
        """Validate and execute restoration through a capability backend."""

        target = checkpoint.normalized_target()

        try:
            plan = RestorePlan.from_checkpoint(checkpoint)
        except (PermissionError, ValueError) as exc:
            return RestoreResult(
                status=RestoreStatus.REJECTED,
                checkpoint_id=checkpoint.checkpoint_id,
                target=target,
                message=str(exc),
            )

        if self._restore_backend is None:
            return RestoreResult(
                status=RestoreStatus.REJECTED,
                checkpoint_id=plan.checkpoint_id,
                target=plan.target,
                message="no restoration backend is available",
            )

        try:
            plan.validate_against(checkpoint)
        except (PermissionError, ValueError) as exc:
            return RestoreResult(
                status=RestoreStatus.REJECTED,
                checkpoint_id=plan.checkpoint_id,
                target=plan.target,
                message=str(exc),
            )

        if not self._restore_backend.can_restore(checkpoint):
            return RestoreResult(
                status=RestoreStatus.REJECTED,
                checkpoint_id=plan.checkpoint_id,
                target=plan.target,
                message="restoration backend does not support this checkpoint",
            )

        try:
            self._restore_backend.restore(checkpoint)
        except Exception as exc:
            return RestoreResult(
                status=RestoreStatus.FAILED,
                checkpoint_id=plan.checkpoint_id,
                target=plan.target,
                message=f"restoration failed: {exc}",
            )

        return RestoreResult(
            status=RestoreStatus.RESTORED,
            checkpoint_id=plan.checkpoint_id,
            target=plan.target,
            message="checkpoint restored successfully",
        )

    def _persist(self, checkpoint: CheckpointState) -> None:
        if self._store is not None:
            self._store.save(checkpoint)

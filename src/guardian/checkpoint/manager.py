from pathlib import Path

from guardian.checkpoint.state import CheckpointState
from guardian.core.request import GuardianRequest
from guardian.sandbox import SandboxWorkspace


class CheckpointManager:
    """Creates and validates checkpoint state for Guardian operations."""

    def __init__(
        self,
        workspace: SandboxWorkspace | None = None,
    ) -> None:
        self._workspace = workspace

    def prepare(self, request: GuardianRequest) -> CheckpointState:
        """Prepare a checkpoint for a validated Guardian request."""

        if self._workspace is None:
            raise ValueError("workspace is required for prepare()")

        target = request.normalized_target()

        if not self._workspace.contains(target):
            raise PermissionError(
                "checkpoint target is outside the Guardian workspace"
            )

        return CheckpointState.create(
            workspace=self._workspace.normalized_root(),
            operation=request.operation.strip(),
            target=target,
        )

    def create(
        self,
        workspace: Path,
        operation: str,
        target: Path,
    ) -> CheckpointState:
        """Create standalone checkpoint state."""

        normalized_workspace = workspace.expanduser().resolve(strict=False)
        normalized_target = target.expanduser().resolve(strict=False)

        try:
            normalized_target.relative_to(normalized_workspace)
        except ValueError as exc:
            raise PermissionError(
                "checkpoint target is outside the Guardian workspace"
            ) from exc

        return CheckpointState.create(
            workspace=normalized_workspace,
            operation=operation.strip(),
            target=normalized_target,
        )

    def restore(self, checkpoint: CheckpointState) -> None:
        """Restore a checkpoint.

        The persistence/restoration backend is intentionally deferred until
        the checkpoint storage contract is defined.
        """

        raise NotImplementedError(
            "checkpoint restoration backend is not implemented"
        )

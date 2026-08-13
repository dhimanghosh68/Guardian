from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from guardian.checkpoint.state import CheckpointState
from guardian.restore.request import RestoreRequest


@dataclass(frozen=True)
class RestorePlan:
    """Validated, immutable plan for restoring one checkpoint."""

    checkpoint_id: UUID
    workspace: Path
    target: Path

    @classmethod
    def from_checkpoint(
        cls,
        checkpoint: CheckpointState,
    ) -> "RestorePlan":
        request = RestoreRequest(
            checkpoint_id=checkpoint.checkpoint_id,
            workspace=checkpoint.workspace,
            target=checkpoint.target,
        )
        request.validate_boundary()

        return cls(
            checkpoint_id=checkpoint.checkpoint_id,
            workspace=request.normalized_workspace(),
            target=request.normalized_target(),
        )

    def validate_against(
        self,
        checkpoint: CheckpointState,
    ) -> None:
        """Verify that the plan still represents its original checkpoint."""

        if self.checkpoint_id != checkpoint.checkpoint_id:
            raise ValueError("restore plan checkpoint identifier mismatch")

        if self.workspace != checkpoint.normalized_workspace():
            raise ValueError("restore plan workspace mismatch")

        if self.target != checkpoint.normalized_target():
            raise ValueError("restore plan target mismatch")

        try:
            self.target.relative_to(self.workspace)
        except ValueError as exc:
            raise PermissionError(
                "restore target is outside the authorized workspace"
            ) from exc

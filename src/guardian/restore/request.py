from dataclasses import dataclass
from pathlib import Path
from uuid import UUID


@dataclass(frozen=True)
class RestoreRequest:
    """Immutable authorization context for a checkpoint restoration."""

    checkpoint_id: UUID
    workspace: Path
    target: Path

    def normalized_workspace(self) -> Path:
        return self.workspace.expanduser().resolve(strict=False)

    def normalized_target(self) -> Path:
        return self.target.expanduser().resolve(strict=False)

    def validate_boundary(self) -> None:
        """Reject targets that escape the authorized workspace."""

        workspace = self.normalized_workspace()
        target = self.normalized_target()

        try:
            target.relative_to(workspace)
        except ValueError as exc:
            raise PermissionError(
                "restore target is outside the authorized workspace"
            ) from exc

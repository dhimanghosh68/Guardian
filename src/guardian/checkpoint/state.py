from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID, uuid4


@dataclass(frozen=True)
class CheckpointState:
    """Immutable description of a Guardian checkpoint."""

    workspace: Path
    operation: str
    target: Path
    checkpoint_id: UUID = field(default_factory=uuid4)

    @classmethod
    def create(
        cls,
        workspace: Path,
        operation: str,
        target: Path,
    ) -> "CheckpointState":
        return cls(
            workspace=workspace,
            operation=operation,
            target=target,
        )

    def normalized_workspace(self) -> Path:
        return self.workspace.expanduser().resolve(strict=False)

    def normalized_target(self) -> Path:
        return self.target.expanduser().resolve(strict=False)

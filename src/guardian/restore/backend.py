from pathlib import Path
from typing import Protocol

from guardian.checkpoint.state import CheckpointState


class RestoreBackend(Protocol):
    """Capability contract for restoring Guardian checkpoints."""

    def can_restore(self, checkpoint: CheckpointState) -> bool:
        """Return whether this backend can restore the checkpoint."""
        ...

    def restore(self, checkpoint: CheckpointState) -> None:
        """Restore the checkpoint."""
        ...


class RestorePlan(Protocol):
    """Contract for describing a planned restoration."""

    @property
    def target(self) -> Path:
        """Return the restoration target."""
        ...

    @property
    def checkpoint_id(self) -> str:
        """Return the checkpoint identifier."""
        ...

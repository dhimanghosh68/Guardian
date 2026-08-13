from typing import Protocol

from guardian.checkpoint.state import CheckpointState
from guardian.restore.plan import RestorePlan


class RestoreBackend(Protocol):
    """Capability contract for restoring Guardian checkpoints."""

    @property
    def capabilities(self) -> frozenset[str]:
        """Return capabilities provided by this backend."""
        ...

    def can_restore(self, checkpoint: CheckpointState) -> bool:
        """Return whether this backend can restore the checkpoint."""
        ...

    def restore(self, plan: RestorePlan) -> None:
        """Execute a validated restoration plan."""
        ...

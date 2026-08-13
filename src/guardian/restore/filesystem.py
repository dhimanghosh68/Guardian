from guardian.checkpoint.state import CheckpointState
from guardian.restore.plan import RestorePlan
from guardian.restore.snapshot import FilesystemSnapshotStore


class FilesystemRestoreBackend:
    """Restore backend for checkpoints containing filesystem snapshots."""

    CAPABILITY = "checkpoint.restore"

    def __init__(self, snapshots: FilesystemSnapshotStore) -> None:
        self._snapshots = snapshots

    @property
    def capabilities(self) -> frozenset[str]:
        return frozenset({self.CAPABILITY})

    def can_restore(self, checkpoint: CheckpointState) -> bool:
        return (
            self.CAPABILITY in self.capabilities
            and self._snapshots.exists(checkpoint.checkpoint_id)
        )

    def restore(self, plan: RestorePlan) -> None:
        self._snapshots.restore(
            CheckpointState(
                workspace=plan.workspace,
                operation="restore",
                target=plan.target,
                checkpoint_id=plan.checkpoint_id,
            )
        )

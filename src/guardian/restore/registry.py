from guardian.checkpoint.state import CheckpointState
from guardian.restore.backend import RestoreBackend


class RestoreBackendRegistry:
    """Deterministic registry for capability-driven restore backends."""

    def __init__(self) -> None:
        self._backends: list[RestoreBackend] = []

    def register(self, backend: RestoreBackend) -> None:
        """Register a backend once, preserving registration order."""

        if backend not in self._backends:
            self._backends.append(backend)

    def discover(
        self,
        checkpoint: CheckpointState | None = None,
    ) -> tuple[RestoreBackend, ...]:
        """Discover registered backends, optionally filtered by capability."""

        if checkpoint is None:
            return tuple(self._backends)

        return tuple(
            backend
            for backend in self._backends
            if backend.can_restore(checkpoint)
        )

    def select(self, checkpoint: CheckpointState) -> RestoreBackend | None:
        """Select the first registered backend capable of restoration."""

        for backend in self._backends:
            if backend.can_restore(checkpoint):
                return backend

        return None

    def resolve(self, checkpoint: CheckpointState) -> RestoreBackend | None:
        """Compatibility alias for select()."""

        return self.select(checkpoint)

    def __len__(self) -> int:
        return len(self._backends)

from guardian.core.request import GuardianRequest
from guardian.execution.adapter import ExecutionAdapter


class ExecutionAdapterRegistry:
    """Deterministic registry for capability-driven execution adapters."""

    def __init__(self) -> None:
        self._adapters: list[ExecutionAdapter] = []

    def register(self, adapter: ExecutionAdapter) -> None:
        """Register an adapter once, preserving registration order."""
        if adapter not in self._adapters:
            self._adapters.append(adapter)

    def discover(
        self,
        request: GuardianRequest | None = None,
    ) -> tuple[ExecutionAdapter, ...]:
        """Discover adapters, optionally filtered by execution capability."""
        if request is None:
            return tuple(self._adapters)

        return tuple(
            adapter
            for adapter in self._adapters
            if adapter.can_execute(request)
        )

    def select(
        self,
        request: GuardianRequest,
    ) -> ExecutionAdapter | None:
        """Select the first registered adapter capable of execution."""
        for adapter in self._adapters:
            if adapter.can_execute(request):
                return adapter

        return None

    def resolve(
        self,
        request: GuardianRequest,
    ) -> ExecutionAdapter | None:
        """Compatibility alias for select()."""
        return self.select(request)

    def __len__(self) -> int:
        return len(self._adapters)

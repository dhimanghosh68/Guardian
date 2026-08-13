from typing import Protocol

from guardian.core.request import GuardianRequest
from guardian.execution.authorized import AuthorizedExecution


class ExecutionAdapter(Protocol):
    """Capability contract for executing an authorized operation."""

    @property
    def capabilities(self) -> frozenset[str]:
        """Return capabilities provided by this adapter."""
        ...

    def can_execute(self, request: GuardianRequest) -> bool:
        """Return whether this adapter can execute the request."""
        ...

    def execute(self, authorization: AuthorizedExecution) -> None:
        """Execute an operation using explicit Guardian authorization."""
        ...

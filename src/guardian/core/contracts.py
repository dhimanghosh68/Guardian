from typing import Protocol

from guardian.core.request import GuardianRequest
from guardian.core.result import GuardianResult


class GuardianEvaluator(Protocol):
    """Contract implemented by components that evaluate Guardian requests."""

    def evaluate(self, request: GuardianRequest) -> GuardianResult:
        """Evaluate a request and return an immutable decision."""
        ...

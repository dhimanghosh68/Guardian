from dataclasses import dataclass
from pathlib import Path

from guardian.core.status import GuardianStatus


@dataclass(frozen=True)
class GuardianResult:
    """Immutable result of evaluating a Guardian request."""

    status: GuardianStatus
    operation: str
    target: Path
    message: str

    @property
    def allowed(self) -> bool:
        """Return whether the requested operation is allowed."""
        return self.status is GuardianStatus.ALLOWED

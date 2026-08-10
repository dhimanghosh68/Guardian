from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class GuardianStatus(str, Enum):
    """Terminal state of a Guardian operation."""

    ALLOWED = "allowed"
    BLOCKED = "blocked"
    FAILED = "failed"


@dataclass(frozen=True)
class GuardianRequest:
    """Immutable description of an operation requested from Guardian."""

    target: Path
    operation: str

    def normalized_target(self) -> Path:
        """Return the normalized target without requiring it to exist."""
        return self.target.expanduser().resolve(strict=False)


@dataclass(frozen=True)
class GuardianResult:
    """Immutable result produced by a Guardian operation."""

    status: GuardianStatus
    operation: str
    target: Path
    message: str

    @property
    def allowed(self) -> bool:
        """Return whether Guardian allowed the operation."""
        return self.status is GuardianStatus.ALLOWED

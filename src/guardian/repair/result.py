from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class RepairStatus(str, Enum):
    """Terminal state of a repair execution."""

    APPLIED = "applied"
    REJECTED = "rejected"
    FAILED = "failed"


@dataclass(frozen=True)
class RepairResult:
    """Immutable result of a repair execution."""

    status: RepairStatus
    operation: str
    target: Path
    message: str

    @property
    def applied(self) -> bool:
        """Return whether the repair completed successfully."""

        return self.status is RepairStatus.APPLIED

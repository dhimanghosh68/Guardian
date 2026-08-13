from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from uuid import UUID


class RestoreStatus(str, Enum):
    """Terminal state of a restoration operation."""

    RESTORED = "restored"
    REJECTED = "rejected"
    FAILED = "failed"


@dataclass(frozen=True)
class RestoreResult:
    """Immutable result of a restoration attempt."""

    status: RestoreStatus
    checkpoint_id: UUID
    target: Path
    message: str

    @property
    def restored(self) -> bool:
        """Return whether restoration completed successfully."""
        return self.status is RestoreStatus.RESTORED

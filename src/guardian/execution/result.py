from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class ExecutionStatus(str, Enum):
    """Terminal state of an execution attempt."""

    EXECUTED = "executed"
    REJECTED = "rejected"
    FAILED = "failed"


@dataclass(frozen=True)
class ExecutionResult:
    """Immutable result of an execution attempt."""

    status: ExecutionStatus
    operation: str
    target: Path
    message: str

    @property
    def executed(self) -> bool:
        """Return whether execution completed successfully."""
        return self.status is ExecutionStatus.EXECUTED

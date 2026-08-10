from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RepairAction:
    """Immutable description of a proposed repair."""

    operation: str
    target: Path

    def normalized_target(self) -> Path:
        return self.target.expanduser().resolve(strict=False)

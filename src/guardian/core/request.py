from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GuardianRequest:
    """Immutable description of a requested Guardian operation."""

    target: Path
    operation: str

    def normalized_target(self) -> Path:
        """Return the canonical target path."""
        return self.target.expanduser().resolve(strict=False)

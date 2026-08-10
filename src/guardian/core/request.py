from dataclasses import dataclass
from pathlib import Path

from guardian.core.operation import GuardianOperation


@dataclass(frozen=True)
class GuardianRequest:
    """Immutable description of a requested Guardian operation."""

    target: Path
    operation: str

    def normalized_target(self) -> Path:
        """Return the canonical target path."""

        return self.target.expanduser().resolve(strict=False)

    def parsed_operation(self) -> GuardianOperation:
        """Return the canonical operation classification."""

        return GuardianOperation.parse(self.operation)

from dataclasses import dataclass
from pathlib import Path

from guardian.core.operation import GuardianOperation


@dataclass(frozen=True)
class AuthorizedExecution:
    """Immutable execution authority issued after Guardian authorization."""

    operation: GuardianOperation
    target: Path

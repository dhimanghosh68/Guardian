from enum import Enum


class GuardianStatus(str, Enum):
    """Terminal state of a Guardian operation."""

    ALLOWED = "allowed"
    BLOCKED = "blocked"
    FAILED = "failed"

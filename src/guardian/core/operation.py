from enum import Enum


class GuardianOperation(str, Enum):
    """Supported operations that Guardian can evaluate."""

    INSPECT = "inspect"
    MODIFY = "modify"
    WRITE = "write"
    RESTORE = "restore"
    DELETE = "delete"

    @classmethod
    def parse(cls, value: str) -> "GuardianOperation":
        """Parse a user-supplied operation into a supported operation."""
        normalized = value.strip().lower()

        try:
            return cls(normalized)
        except ValueError as exc:
            raise ValueError(
                f"unsupported Guardian operation: {value!r}"
            ) from exc

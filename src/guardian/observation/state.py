from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class FilesystemObjectType(str, Enum):
    """Observed filesystem object classification."""

    MISSING = "missing"
    FILE = "file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"
    OTHER = "other"


@dataclass(frozen=True)
class FilesystemObservation:
    """Immutable observation of one filesystem path."""

    path: Path
    object_type: FilesystemObjectType
    exists: bool
    mode: int | None = None
    size: int | None = None
    sha256: str | None = None
    symlink_target: str | None = None
    error: str | None = None

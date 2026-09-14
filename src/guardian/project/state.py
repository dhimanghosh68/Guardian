from dataclasses import dataclass
from pathlib import Path

from guardian.observation.snapshot import FilesystemTreeSnapshot


@dataclass(frozen=True)
class ProjectState:
    """Immutable observable state of one project."""

    root: Path
    filesystem: FilesystemTreeSnapshot

    def normalized_root(self) -> Path:
        return self.root.expanduser().absolute()

from pathlib import Path

from guardian.observation.snapshot import FilesystemTreeObserver
from guardian.project.state import ProjectState


class ProjectStateCapture:
    """Capture observable state for one project."""

    def __init__(
        self,
        observer: FilesystemTreeObserver | None = None,
    ) -> None:
        self._observer = observer or FilesystemTreeObserver()

    def capture(self, root: Path) -> ProjectState:
        normalized_root = root.expanduser().absolute()
        filesystem = self._observer.observe(normalized_root)

        return ProjectState(
            root=normalized_root,
            filesystem=filesystem,
        )

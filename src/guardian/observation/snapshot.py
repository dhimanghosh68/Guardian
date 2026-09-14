import os
from dataclasses import dataclass
from pathlib import Path

from guardian.observation.filesystem import FilesystemObserver
from guardian.observation.state import (
    FilesystemObservation,
    FilesystemObjectType,
)


@dataclass(frozen=True)
class FilesystemTreeSnapshot:
    """Immutable observation snapshot of a filesystem tree."""

    root: Path
    observations: tuple[FilesystemObservation, ...]

    def by_path(self) -> dict[Path, FilesystemObservation]:
        return {
            observation.path: observation
            for observation in self.observations
        }


class FilesystemTreeObserver:
    """Read-only observer for a filesystem tree."""

    def __init__(self, observer: FilesystemObserver | None = None) -> None:
        self._observer = observer or FilesystemObserver()

    def observe(self, root: Path) -> FilesystemTreeSnapshot:
        normalized_root = root.expanduser().absolute()
        observations: list[FilesystemObservation] = []

        self._walk(normalized_root, observations)

        observations.sort(key=lambda observation: str(observation.path))

        return FilesystemTreeSnapshot(
            root=normalized_root,
            observations=tuple(observations),
        )

    def _walk(
        self,
        path: Path,
        observations: list[FilesystemObservation],
    ) -> None:
        observation = self._observer.observe(path)
        observations.append(observation)

        if observation.object_type is not FilesystemObjectType.DIRECTORY:
            return

        try:
            entries = sorted(
                os.scandir(path),
                key=lambda entry: entry.name,
            )
        except OSError:
            return

        for entry in entries:
            child = Path(entry.path)

            child_observation = self._observer.observe(child)
            observations.append(child_observation)

            if (
                child_observation.object_type
                is FilesystemObjectType.DIRECTORY
            ):
                self._walk_directory(child, observations)

    def _walk_directory(
        self,
        directory: Path,
        observations: list[FilesystemObservation],
    ) -> None:
        try:
            entries = sorted(
                os.scandir(directory),
                key=lambda entry: entry.name,
            )
        except OSError:
            return

        for entry in entries:
            child = Path(entry.path)
            observation = self._observer.observe(child)
            observations.append(observation)

            if observation.object_type is FilesystemObjectType.DIRECTORY:
                self._walk_directory(child, observations)

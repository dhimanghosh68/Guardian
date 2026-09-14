import hashlib
import os
import stat
from pathlib import Path

from guardian.observation.state import (
    FilesystemObservation,
    FilesystemObjectType,
)


class FilesystemObserver:
    """Read-only observer for one filesystem path."""

    def observe(self, path: Path) -> FilesystemObservation:
        target = path.expanduser().absolute()

        try:
            metadata = os.lstat(target)
        except FileNotFoundError:
            return FilesystemObservation(
                path=target,
                object_type=FilesystemObjectType.MISSING,
                exists=False,
            )
        except OSError as exc:
            return FilesystemObservation(
                path=target,
                object_type=FilesystemObjectType.OTHER,
                exists=False,
                error=f"{type(exc).__name__}: {exc}",
            )

        mode = stat.S_IMODE(metadata.st_mode)

        if os.path.islink(target):
            try:
                link_target = os.readlink(target)
            except OSError as exc:
                return FilesystemObservation(
                    path=target,
                    object_type=FilesystemObjectType.SYMLINK,
                    exists=True,
                    mode=mode,
                    error=f"{type(exc).__name__}: {exc}",
                )

            return FilesystemObservation(
                path=target,
                object_type=FilesystemObjectType.SYMLINK,
                exists=True,
                mode=mode,
                symlink_target=link_target,
            )

        if os.path.isfile(target):
            try:
                digest = self._sha256(target)
            except OSError as exc:
                return FilesystemObservation(
                    path=target,
                    object_type=FilesystemObjectType.FILE,
                    exists=True,
                    mode=mode,
                    size=metadata.st_size,
                    error=f"{type(exc).__name__}: {exc}",
                )

            return FilesystemObservation(
                path=target,
                object_type=FilesystemObjectType.FILE,
                exists=True,
                mode=mode,
                size=metadata.st_size,
                sha256=digest,
            )

        if os.path.isdir(target):
            return FilesystemObservation(
                path=target,
                object_type=FilesystemObjectType.DIRECTORY,
                exists=True,
                mode=mode,
            )

        return FilesystemObservation(
            path=target,
            object_type=FilesystemObjectType.OTHER,
            exists=True,
            mode=mode,
            size=metadata.st_size,
        )

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()

        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)

        return digest.hexdigest()

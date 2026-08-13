from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from uuid import UUID

from guardian.checkpoint.state import CheckpointState


class FilesystemSnapshotStore:
    """Persistent filesystem snapshots keyed by Guardian checkpoint ID."""

    def __init__(self, root: Path) -> None:
        self.root = root.expanduser().resolve(strict=False)

    def capture(self, checkpoint: CheckpointState) -> None:
        """Capture filesystem state after validating its authorization boundary."""

        self._validate_target(checkpoint)

        target = checkpoint.normalized_target()

        if not target.exists() and not target.is_symlink():
            raise FileNotFoundError(
                f"checkpoint target does not exist: {target}"
            )

        self.root.mkdir(parents=True, exist_ok=True)

        destination = self._path_for(checkpoint.checkpoint_id)
        temporary = Path(
            tempfile.mkdtemp(
                prefix=f".{checkpoint.checkpoint_id}.",
                dir=self.root,
            )
        )

        try:
            snapshot = temporary / "snapshot"
            metadata = temporary / "metadata"

            self._copy_entry(
                source=target,
                destination=snapshot,
                workspace=checkpoint.normalized_workspace(),
            )

            metadata.write_text(
                "symlink\n"
                if target.is_symlink()
                else "directory\n"
                if target.is_dir()
                else "file\n",
                encoding="utf-8",
            )

            if destination.exists():
                shutil.rmtree(destination)

            temporary.replace(destination)
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            raise

    def exists(self, checkpoint_id: UUID) -> bool:
        return self._path_for(checkpoint_id).is_dir()

    def remove(self, checkpoint_id: UUID) -> None:
        shutil.rmtree(
            self._path_for(checkpoint_id),
            ignore_errors=True,
        )

    def restore(self, checkpoint: CheckpointState) -> None:
        """Restore a snapshot without destroying the target on copy failure."""

        self._validate_target(checkpoint)

        target = checkpoint.normalized_target()
        source = self._path_for(checkpoint.checkpoint_id) / "snapshot"

        if not source.exists() and not source.is_symlink():
            raise FileNotFoundError(
                f"filesystem snapshot not found: {checkpoint.checkpoint_id}"
            )

        target.parent.mkdir(parents=True, exist_ok=True)

        temporary = Path(
            tempfile.mkdtemp(
                prefix=f".guardian-restore-{checkpoint.checkpoint_id}.",
                dir=target.parent,
            )
        )

        staged = temporary / "target"

        try:
            self._copy_entry(
                source=source,
                destination=staged,
                workspace=checkpoint.normalized_workspace(),
            )

            self._replace_target(target, staged)
        finally:
            shutil.rmtree(temporary, ignore_errors=True)

    def _copy_entry(
        self,
        source: Path,
        destination: Path,
        workspace: Path,
    ) -> None:
        """Copy one filesystem entry while enforcing symlink boundaries."""

        if source.is_symlink():
            resolved = source.resolve(strict=False)

            try:
                resolved.relative_to(workspace)
            except ValueError as exc:
                raise PermissionError(
                    "snapshot contains a symlink outside the authorized workspace"
                ) from exc

            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.symlink_to(os.readlink(source))
            return

        if source.is_dir():
            destination.mkdir(parents=True, exist_ok=False)

            for child in source.iterdir():
                self._copy_entry(
                    source=child,
                    destination=destination / child.name,
                    workspace=workspace,
                )

            shutil.copystat(
                source,
                destination,
                follow_symlinks=False,
            )
            return

        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(
            source,
            destination,
            follow_symlinks=False,
        )

    @staticmethod
    def _replace_target(
        target: Path,
        staged: Path,
    ) -> None:
        """Replace an existing target only after staging succeeds."""

        backup = target.parent / (
            f".guardian-backup-{target.name}-"
            f"{next(tempfile._get_candidate_names())}"
        )

        moved_target = False

        try:
            if target.exists() or target.is_symlink():
                target.replace(backup)
                moved_target = True

            staged.replace(target)

            if moved_target:
                FilesystemSnapshotStore._remove_entry(backup)
        except Exception:
            if target.exists() or target.is_symlink():
                FilesystemSnapshotStore._remove_entry(target)

            if moved_target and (
                backup.exists() or backup.is_symlink()
            ):
                backup.replace(target)

            raise

    @staticmethod
    def _remove_entry(path: Path) -> None:
        if path.is_symlink() or path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)

    @staticmethod
    def _validate_target(checkpoint: CheckpointState) -> None:
        workspace = checkpoint.normalized_workspace()
        target = checkpoint.normalized_target()

        try:
            target.relative_to(workspace)
        except ValueError as exc:
            raise PermissionError(
                "restore target is outside the authorized workspace"
            ) from exc

    def _path_for(self, checkpoint_id: UUID) -> Path:
        return self.root / str(checkpoint_id)

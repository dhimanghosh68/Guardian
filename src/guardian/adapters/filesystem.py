import os
import stat
import tempfile
from pathlib import Path

from guardian.core.operation import GuardianOperation
from guardian.core.request import GuardianRequest
from guardian.execution.authorized import AuthorizedExecution


class FilesystemExecutionAdapter:
    """Execute explicitly authorized filesystem file mutations."""

    WRITE_CAPABILITY = "filesystem.write"
    MODIFY_CAPABILITY = "filesystem.modify"

    @property
    def capabilities(self) -> frozenset[str]:
        return frozenset(
            {
                self.WRITE_CAPABILITY,
                self.MODIFY_CAPABILITY,
            }
        )

    def can_execute(self, request: GuardianRequest) -> bool:
        """Return whether this adapter implements the requested operation."""

        try:
            operation = request.parsed_operation()
        except ValueError:
            return False

        return operation in {
            GuardianOperation.WRITE,
            GuardianOperation.MODIFY,
        }

    def execute(self, authorization: AuthorizedExecution) -> None:
        """Execute only the operation and target explicitly authorized."""

        if authorization.operation not in {
            GuardianOperation.WRITE,
            GuardianOperation.MODIFY,
        }:
            raise ValueError(
                f"filesystem adapter does not support "
                f"{authorization.operation.value}"
            )

        if authorization.content is None:
            raise ValueError("filesystem mutation requires content")

        target = authorization.target.expanduser().resolve(strict=False)

        if target.exists() and not target.is_file():
            raise ValueError("filesystem execution target is not a regular file")

        self._atomic_write(target, authorization.content)

    @staticmethod
    def _atomic_write(target: Path, content: str) -> None:
        """Atomically replace a file while preserving its existing mode."""

        parent = target.parent
        parent.mkdir(parents=True, exist_ok=True)

        existing_mode: int | None = None

        if target.exists():
            existing_mode = stat.S_IMODE(target.stat().st_mode)

        fd, temporary = tempfile.mkstemp(
            prefix=f".{target.name}.",
            dir=parent,
            text=True,
        )

        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)

                if existing_mode is not None:
                    os.fchmod(handle.fileno(), existing_mode)

                handle.flush()
                os.fsync(handle.fileno())

            os.replace(temporary, target)

        except BaseException:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            raise

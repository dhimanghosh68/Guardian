from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from guardian.observation.state import FilesystemObservation


class FilesystemChangeType(str, Enum):
    """Classification of a change between two filesystem snapshots."""

    CREATED = "created"
    DELETED = "deleted"
    MODIFIED = "modified"
    TYPE_CHANGED = "type_changed"
    UNCHANGED = "unchanged"


@dataclass(frozen=True)
class FilesystemChange:
    """Immutable description of one filesystem state change."""

    path: Path
    change_type: FilesystemChangeType
    before: FilesystemObservation | None
    after: FilesystemObservation | None


def diff_snapshots(
    before: tuple[FilesystemObservation, ...],
    after: tuple[FilesystemObservation, ...],
) -> tuple[FilesystemChange, ...]:
    """Compare two deterministic filesystem observation sets."""

    before_map = {observation.path: observation for observation in before}
    after_map = {observation.path: observation for observation in after}

    changes: list[FilesystemChange] = []

    for path in sorted(before_map.keys() | after_map.keys()):
        old = before_map.get(path)
        new = after_map.get(path)

        if old is None:
            change_type = FilesystemChangeType.CREATED
        elif new is None:
            change_type = FilesystemChangeType.DELETED
        elif old.object_type is not new.object_type:
            change_type = FilesystemChangeType.TYPE_CHANGED
        elif old != new:
            change_type = FilesystemChangeType.MODIFIED
        else:
            change_type = FilesystemChangeType.UNCHANGED

        changes.append(
            FilesystemChange(
                path=path,
                change_type=change_type,
                before=old,
                after=new,
            )
        )

    return tuple(changes)

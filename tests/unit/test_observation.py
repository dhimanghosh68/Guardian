import hashlib
import os
import stat
from pathlib import Path

import pytest

from guardian.observation import (
    FilesystemObservation,
    FilesystemObjectType,
    FilesystemObserver,
)


def test_observer_reports_missing_path(tmp_path):
    target = tmp_path / "missing.txt"

    observation = FilesystemObserver().observe(target)

    assert observation == FilesystemObservation(
        path=target.resolve(),
        object_type=FilesystemObjectType.MISSING,
        exists=False,
    )


def test_observer_reports_regular_file_and_hash(tmp_path):
    target = tmp_path / "file.txt"
    content = b"hello guardian\n"
    target.write_bytes(content)

    observation = FilesystemObserver().observe(target)

    assert observation.object_type is FilesystemObjectType.FILE
    assert observation.exists
    assert observation.size == len(content)
    assert observation.mode == stat.S_IMODE(target.stat().st_mode)
    assert observation.sha256 == hashlib.sha256(content).hexdigest()
    assert observation.symlink_target is None
    assert observation.error is None


def test_observer_reports_directory(tmp_path):
    target = tmp_path / "directory"
    target.mkdir()

    observation = FilesystemObserver().observe(target)

    assert observation.object_type is FilesystemObjectType.DIRECTORY
    assert observation.exists
    assert observation.mode == stat.S_IMODE(target.stat().st_mode)
    assert observation.size is None
    assert observation.sha256 is None


def test_observer_reports_symlink_without_following_it(tmp_path):
    target = tmp_path / "target.txt"
    target.write_text("target", encoding="utf-8")

    link = tmp_path / "link.txt"
    link.symlink_to(target)

    observation = FilesystemObserver().observe(link)

    assert observation.object_type is FilesystemObjectType.SYMLINK
    assert observation.exists
    assert observation.symlink_target == str(target)
    assert observation.sha256 is None


def test_observer_reports_broken_symlink_as_symlink(tmp_path):
    link = tmp_path / "broken"
    link.symlink_to(tmp_path / "does-not-exist")

    observation = FilesystemObserver().observe(link)

    assert observation.object_type is FilesystemObjectType.SYMLINK
    assert observation.exists
    assert observation.symlink_target == str(tmp_path / "does-not-exist")
    assert observation.error is None


def test_observer_normalizes_path(tmp_path):
    target = tmp_path / "file.txt"
    target.write_text("data", encoding="utf-8")

    observation = FilesystemObserver().observe(
        target.parent / "." / target.name
    )

    assert observation.path == target.resolve()


def test_observation_is_immutable(tmp_path):
    target = tmp_path / "file.txt"
    target.write_text("data", encoding="utf-8")

    observation = FilesystemObserver().observe(target)

    with pytest.raises(AttributeError):
        observation.exists = False


def test_observation_does_not_modify_file(tmp_path):
    target = tmp_path / "file.txt"
    target.write_text("original", encoding="utf-8")
    before = target.stat()

    FilesystemObserver().observe(target)

    after = target.stat()

    assert target.read_text(encoding="utf-8") == "original"
    assert after.st_mtime_ns == before.st_mtime_ns
    assert after.st_size == before.st_size


def test_observer_reports_other_filesystem_object(tmp_path):
    target = tmp_path / "fifo"
    import os

    os.mkfifo(target)

    observation = FilesystemObserver().observe(target)

    assert observation.object_type is FilesystemObjectType.OTHER
    assert observation.exists
    assert observation.mode is not None
    assert observation.size is not None
    assert observation.sha256 is None
    assert observation.symlink_target is None
    assert observation.error is None

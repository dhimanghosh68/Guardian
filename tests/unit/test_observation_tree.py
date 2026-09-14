from pathlib import Path

from guardian.observation import (
    FilesystemChangeType,
    FilesystemObjectType,
    FilesystemTreeObserver,
    diff_snapshots,
)


def test_tree_observer_captures_nested_tree(tmp_path):
    root = tmp_path / "root"
    root.mkdir()

    nested = root / "nested"
    nested.mkdir()

    file = nested / "file.txt"
    file.write_text("hello", encoding="utf-8")

    snapshot = FilesystemTreeObserver().observe(root)

    paths = [observation.path for observation in snapshot.observations]

    assert paths == sorted(paths)
    assert root in paths
    assert nested in paths
    assert file in paths


def test_tree_observer_does_not_follow_symlinks(tmp_path):
    root = tmp_path / "root"
    root.mkdir()

    outside = tmp_path / "outside"
    outside.mkdir()
    outside_file = outside / "secret.txt"
    outside_file.write_text("secret", encoding="utf-8")

    link = root / "link"
    link.symlink_to(outside, target_is_directory=True)

    snapshot = FilesystemTreeObserver().observe(root)

    paths = {observation.path for observation in snapshot.observations}

    assert link in paths
    assert outside_file not in paths

    link_observation = next(
        observation
        for observation in snapshot.observations
        if observation.path == link
    )
    assert link_observation.object_type is FilesystemObjectType.SYMLINK


def test_tree_observer_reports_missing_root(tmp_path):
    root = tmp_path / "missing"

    snapshot = FilesystemTreeObserver().observe(root)

    assert len(snapshot.observations) == 1
    assert snapshot.observations[0].object_type is FilesystemObjectType.MISSING


def test_diff_detects_created_deleted_and_modified(tmp_path):
    root = tmp_path / "root"
    root.mkdir()

    existing = root / "existing.txt"
    existing.write_text("before", encoding="utf-8")

    deleted = root / "deleted.txt"
    deleted.write_text("deleted", encoding="utf-8")

    observer = FilesystemTreeObserver()
    before = observer.observe(root)

    deleted.unlink()
    existing.write_text("after", encoding="utf-8")
    created = root / "created.txt"
    created.write_text("created", encoding="utf-8")

    after = observer.observe(root)

    changes = diff_snapshots(before.observations, after.observations)
    by_name = {change.path.name: change.change_type for change in changes}

    assert by_name["existing.txt"] is FilesystemChangeType.MODIFIED
    assert by_name["deleted.txt"] is FilesystemChangeType.DELETED
    assert by_name["created.txt"] is FilesystemChangeType.CREATED


def test_diff_detects_type_change(tmp_path):
    root = tmp_path / "root"
    root.mkdir()

    target = root / "target"
    target.write_text("file", encoding="utf-8")

    observer = FilesystemTreeObserver()
    before = observer.observe(root)

    target.unlink()
    target.mkdir()

    after = observer.observe(root)

    changes = diff_snapshots(before.observations, after.observations)

    target_change = next(
        change for change in changes if change.path == target
    )

    assert target_change.change_type is FilesystemChangeType.TYPE_CHANGED


def test_diff_detects_symlink_target_change(tmp_path):
    root = tmp_path / "root"
    root.mkdir()

    first = root / "first.txt"
    second = root / "second.txt"
    first.write_text("first", encoding="utf-8")
    second.write_text("second", encoding="utf-8")

    link = root / "link"
    link.symlink_to(first)

    observer = FilesystemTreeObserver()
    before = observer.observe(root)

    link.unlink()
    link.symlink_to(second)

    after = observer.observe(root)

    changes = diff_snapshots(before.observations, after.observations)

    link_change = next(change for change in changes if change.path == link)

    assert link_change.change_type is FilesystemChangeType.MODIFIED


def test_diff_reports_unchanged_observations(tmp_path):
    root = tmp_path / "root"
    root.mkdir()

    file = root / "file.txt"
    file.write_text("same", encoding="utf-8")

    observer = FilesystemTreeObserver()
    before = observer.observe(root)
    after = observer.observe(root)

    changes = diff_snapshots(before.observations, after.observations)

    assert all(
        change.change_type is FilesystemChangeType.UNCHANGED
        for change in changes
    )


def test_diff_order_is_deterministic(tmp_path):
    root = tmp_path / "root"
    root.mkdir()

    for name in ("z.txt", "a.txt", "m.txt"):
        (root / name).write_text(name, encoding="utf-8")

    observer = FilesystemTreeObserver()
    snapshot = observer.observe(root)

    changes = diff_snapshots(snapshot.observations, snapshot.observations)

    paths = [change.path for change in changes]

    assert paths == sorted(paths)


def test_snapshot_is_immutable(tmp_path):
    root = tmp_path / "root"
    root.mkdir()

    snapshot = FilesystemTreeObserver().observe(root)

    try:
        snapshot.root = Path("/tmp")
        raise AssertionError("snapshot must be immutable")
    except AttributeError:
        pass

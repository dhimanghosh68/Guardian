from pathlib import Path

import pytest

from guardian.checkpoint import CheckpointManager, CheckpointState
from guardian.core import GuardianRequest
from guardian.sandbox import SandboxWorkspace


def test_checkpoint_normalizes_workspace() -> None:
    state = CheckpointState(
        workspace=Path("~/guardian-workspace"),
        operation="modify",
        target=Path("~/guardian-workspace/project"),
    )

    assert state.normalized_workspace() == (
        Path.home() / "guardian-workspace"
    ).resolve()


def test_checkpoint_normalizes_target() -> None:
    state = CheckpointState(
        workspace=Path("/tmp/guardian-workspace"),
        operation="modify",
        target=Path("/tmp/guardian-workspace/project"),
    )

    assert state.normalized_target() == Path(
        "/tmp/guardian-workspace/project"
    ).resolve()


def test_checkpoint_is_immutable() -> None:
    state = CheckpointState(
        workspace=Path("/tmp/guardian-workspace"),
        operation="modify",
        target=Path("/tmp/guardian-workspace/project"),
    )

    with pytest.raises(Exception):
        state.target = Path("/tmp/other")


def test_checkpoint_manager_creates_state() -> None:
    workspace = SandboxWorkspace(Path("/tmp/guardian-workspace"))
    manager = CheckpointManager(workspace)

    request = GuardianRequest(
        target=Path("/tmp/guardian-workspace/project"),
        operation="modify",
    )

    state = manager.prepare(request)

    assert state.workspace == Path("/tmp/guardian-workspace").resolve()
    assert state.target == Path("/tmp/guardian-workspace/project").resolve()
    assert state.operation == "modify"


def test_checkpoint_manager_rejects_outside_target() -> None:
    workspace = SandboxWorkspace(Path("/tmp/guardian-workspace"))
    manager = CheckpointManager(workspace)

    request = GuardianRequest(
        target=Path("/tmp/outside"),
        operation="modify",
    )

    with pytest.raises(PermissionError, match="outside"):
        manager.prepare(request)

from guardian.checkpoint import CheckpointManager


def test_checkpoint_manager_creates_checkpoint() -> None:
    manager = CheckpointManager()

    checkpoint = manager.create(
        workspace=Path("/tmp/guardian-workspace"),
        operation="modify",
        target=Path("/tmp/guardian-workspace/project"),
    )

    assert checkpoint.normalized_workspace() == Path(
        "/tmp/guardian-workspace"
    ).resolve()

    assert checkpoint.normalized_target() == Path(
        "/tmp/guardian-workspace/project"
    ).resolve()


def test_checkpoint_has_unique_id() -> None:
    first = CheckpointState(
        workspace=Path("/tmp/guardian-workspace"),
        operation="modify",
        target=Path("/tmp/guardian-workspace/project"),
    )

    second = CheckpointState(
        workspace=Path("/tmp/guardian-workspace"),
        operation="modify",
        target=Path("/tmp/guardian-workspace/project"),
    )

    assert first.checkpoint_id != second.checkpoint_id


def test_checkpoint_id_is_uuid() -> None:
    state = CheckpointState(
        workspace=Path("/tmp/guardian-workspace"),
        operation="modify",
        target=Path("/tmp/guardian-workspace/project"),
    )

    assert state.checkpoint_id.version == 4

from guardian.checkpoint import CheckpointCodec


def test_checkpoint_codec_round_trips_state() -> None:
    state = CheckpointState.create(
        workspace=Path("/tmp/guardian-workspace"),
        operation="modify",
        target=Path("/tmp/guardian-workspace/project"),
    )

    encoded = CheckpointCodec.encode(state)
    decoded = CheckpointCodec.decode(encoded)

    assert decoded == state


def test_checkpoint_codec_is_deterministic() -> None:
    state = CheckpointState.create(
        workspace=Path("/tmp/guardian-workspace"),
        operation="modify",
        target=Path("/tmp/guardian-workspace/project"),
    )

    assert CheckpointCodec.encode(state) == CheckpointCodec.encode(state)


def test_checkpoint_codec_rejects_unknown_fields() -> None:
    state = CheckpointState.create(
        workspace=Path("/tmp/guardian-workspace"),
        operation="modify",
        target=Path("/tmp/guardian-workspace/project"),
    )

    encoded = CheckpointCodec.encode(state)
    payload = __import__("json").loads(encoded)
    payload["unexpected"] = "value"

    with pytest.raises(ValueError, match="invalid fields"):
        CheckpointCodec.decode(__import__("json").dumps(payload))


def test_checkpoint_codec_rejects_non_object_payload() -> None:
    with pytest.raises(ValueError, match="must be an object"):
        CheckpointCodec.decode("[]")


def test_checkpoint_store_contract_is_runtime_usable() -> None:
    from guardian.checkpoint import CheckpointStore

    assert CheckpointStore is not None

def test_file_checkpoint_store_round_trips_checkpoint(tmp_path) -> None:
    from guardian.checkpoint import FileCheckpointStore

    store = FileCheckpointStore(tmp_path / "checkpoints")
    checkpoint = CheckpointState.create(
        workspace=tmp_path / "workspace",
        operation="modify",
        target=tmp_path / "workspace" / "project",
    )

    store.save(checkpoint)

    assert store.exists(checkpoint.checkpoint_id)
    assert store.load(checkpoint.checkpoint_id) == checkpoint


def test_file_checkpoint_store_uses_checkpoint_id_filename(tmp_path) -> None:
    from guardian.checkpoint import FileCheckpointStore

    store = FileCheckpointStore(tmp_path / "checkpoints")
    checkpoint = CheckpointState.create(
        workspace=tmp_path / "workspace",
        operation="modify",
        target=tmp_path / "workspace" / "project",
    )

    store.save(checkpoint)

    assert (
        store.root / f"{checkpoint.checkpoint_id}.json"
    ).is_file()


def test_file_checkpoint_store_rejects_corruption(tmp_path) -> None:
    from guardian.checkpoint import FileCheckpointStore

    store = FileCheckpointStore(tmp_path / "checkpoints")
    checkpoint = CheckpointState.create(
        workspace=tmp_path / "workspace",
        operation="modify",
        target=tmp_path / "workspace" / "project",
    )

    store.save(checkpoint)

    path = store.root / f"{checkpoint.checkpoint_id}.json"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            '"modify"',
            '"delete"',
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="integrity"):
        store.load(checkpoint.checkpoint_id)


def test_file_checkpoint_store_rejects_identifier_mismatch(tmp_path) -> None:
    from guardian.checkpoint import FileCheckpointStore

    store = FileCheckpointStore(tmp_path / "checkpoints")

    first = CheckpointState.create(
        workspace=tmp_path / "workspace",
        operation="modify",
        target=tmp_path / "workspace" / "project",
    )
    second = CheckpointState.create(
        workspace=tmp_path / "workspace",
        operation="modify",
        target=tmp_path / "workspace" / "other",
    )

    store.save(first)

    path = store.root / f"{first.checkpoint_id}.json"
    path.write_text(
        store._encode(second),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="identifier"):
        store.load(first.checkpoint_id)


def test_file_checkpoint_store_missing_checkpoint_is_explicit(tmp_path) -> None:
    from uuid import uuid4

    from guardian.checkpoint import FileCheckpointStore

    store = FileCheckpointStore(tmp_path / "checkpoints")

    with pytest.raises(FileNotFoundError, match="checkpoint not found"):
        store.load(uuid4())


def test_file_checkpoint_store_delete_is_idempotent(tmp_path) -> None:
    from guardian.checkpoint import FileCheckpointStore

    store = FileCheckpointStore(tmp_path / "checkpoints")
    checkpoint = CheckpointState.create(
        workspace=tmp_path / "workspace",
        operation="modify",
        target=tmp_path / "workspace" / "project",
    )

    store.save(checkpoint)
    assert store.exists(checkpoint.checkpoint_id)

    store.delete(checkpoint.checkpoint_id)
    assert not store.exists(checkpoint.checkpoint_id)

    store.delete(checkpoint.checkpoint_id)


def test_checkpoint_manager_persists_checkpoint(tmp_path) -> None:
    from guardian.checkpoint import (
        CheckpointManager,
        FileCheckpointStore,
    )

    store = FileCheckpointStore(tmp_path / "checkpoints")
    manager = CheckpointManager(store=store)

    checkpoint = manager.create(
        workspace=tmp_path / "workspace",
        operation="modify",
        target=tmp_path / "workspace" / "project",
    )

    manager.save(checkpoint)

    assert manager.load(checkpoint.checkpoint_id) == checkpoint


def test_file_checkpoint_store_persists_checkpoint(tmp_path) -> None:
    from guardian.checkpoint import FileCheckpointStore

    store = FileCheckpointStore(tmp_path / "checkpoints")

    checkpoint = CheckpointState.create(
        workspace=tmp_path / "workspace",
        operation="modify",
        target=tmp_path / "workspace" / "project",
    )

    store.save(checkpoint)

    assert store.exists(checkpoint.checkpoint_id)
    assert store.load(checkpoint.checkpoint_id) == checkpoint


def test_file_checkpoint_store_uses_checkpoint_id_filename(tmp_path) -> None:
    from guardian.checkpoint import FileCheckpointStore

    root = tmp_path / "checkpoints"
    store = FileCheckpointStore(root)

    checkpoint = CheckpointState.create(
        workspace=tmp_path / "workspace",
        operation="modify",
        target=tmp_path / "workspace" / "project",
    )

    store.save(checkpoint)

    assert (
        root / f"{checkpoint.checkpoint_id}.json"
    ).is_file()


def test_file_checkpoint_store_rejects_missing_checkpoint(tmp_path) -> None:
    from uuid import uuid4

    from guardian.checkpoint import FileCheckpointStore

    store = FileCheckpointStore(tmp_path / "checkpoints")

    with pytest.raises(FileNotFoundError, match="checkpoint not found"):
        store.load(uuid4())


def test_checkpoint_manager_persists_checkpoint(tmp_path) -> None:
    from guardian.checkpoint import (
        CheckpointManager,
        FileCheckpointStore,
    )

    store = FileCheckpointStore(tmp_path / "checkpoints")
    manager = CheckpointManager(store=store)

    checkpoint = manager.create(
        workspace=tmp_path / "workspace",
        operation="modify",
        target=tmp_path / "workspace" / "project",
    )

    assert store.exists(checkpoint.checkpoint_id)
    assert manager.load(checkpoint.checkpoint_id) == checkpoint


def test_checkpoint_manager_prepare_persists_checkpoint(tmp_path) -> None:
    from guardian.checkpoint import (
        CheckpointManager,
        FileCheckpointStore,
    )

    workspace = SandboxWorkspace(tmp_path / "workspace")
    store = FileCheckpointStore(tmp_path / "checkpoints")
    manager = CheckpointManager(workspace=workspace, store=store)

    request = GuardianRequest(
        target=tmp_path / "workspace" / "project",
        operation="modify",
    )

    checkpoint = manager.prepare(request)

    assert manager.load(checkpoint.checkpoint_id) == checkpoint

def test_checkpoint_restore_without_backend_is_explicit(tmp_path) -> None:
    from guardian.checkpoint import CheckpointManager
    from guardian.restore import RestoreStatus

    manager = CheckpointManager()

    checkpoint = manager.create(
        workspace=tmp_path / "workspace",
        operation="modify",
        target=tmp_path / "workspace" / "project",
    )

    result = manager.restore(checkpoint)

    assert result.status is RestoreStatus.REJECTED
    assert not result.restored
    assert "no restoration backend" in result.message


def test_checkpoint_restore_uses_capability_backend(tmp_path) -> None:
    from guardian.checkpoint import CheckpointManager
    from guardian.restore import RestoreStatus

    class Backend:
        def can_restore(self, checkpoint) -> bool:
            return True

        def restore(self, checkpoint) -> None:
            self.restored = checkpoint

    backend = Backend()
    manager = CheckpointManager(restore_backend=backend)

    checkpoint = manager.create(
        workspace=tmp_path / "workspace",
        operation="modify",
        target=tmp_path / "workspace" / "project",
    )

    result = manager.restore(checkpoint)

    assert result.status is RestoreStatus.RESTORED
    assert result.restored
    assert backend.restored == checkpoint


def test_checkpoint_restore_rejects_unsupported_capability(tmp_path) -> None:
    from guardian.checkpoint import CheckpointManager
    from guardian.restore import RestoreStatus

    class Backend:
        def can_restore(self, checkpoint) -> bool:
            return False

        def restore(self, checkpoint) -> None:
            raise AssertionError("unsupported backend must not be invoked")

    manager = CheckpointManager(restore_backend=Backend())

    checkpoint = manager.create(
        workspace=tmp_path / "workspace",
        operation="modify",
        target=tmp_path / "workspace" / "project",
    )

    result = manager.restore(checkpoint)

    assert result.status is RestoreStatus.REJECTED
    assert "does not support" in result.message


def test_checkpoint_restore_reports_backend_failure(tmp_path) -> None:
    from guardian.checkpoint import CheckpointManager
    from guardian.restore import RestoreStatus

    class Backend:
        def can_restore(self, checkpoint) -> bool:
            return True

        def restore(self, checkpoint) -> None:
            raise RuntimeError("backend failure")

    manager = CheckpointManager(restore_backend=Backend())

    checkpoint = manager.create(
        workspace=tmp_path / "workspace",
        operation="modify",
        target=tmp_path / "workspace" / "project",
    )

    result = manager.restore(checkpoint)

    assert result.status is RestoreStatus.FAILED
    assert "backend failure" in result.message

def test_restore_plan_preserves_checkpoint_identity(tmp_path) -> None:
    from guardian.restore import RestorePlan

    checkpoint = CheckpointState.create(
        workspace=tmp_path / "workspace",
        operation="modify",
        target=tmp_path / "workspace" / "project",
    )

    plan = RestorePlan.from_checkpoint(checkpoint)

    assert plan.checkpoint_id == checkpoint.checkpoint_id
    assert plan.workspace == checkpoint.normalized_workspace()
    assert plan.target == checkpoint.normalized_target()


def test_restore_plan_rejects_identifier_substitution(tmp_path) -> None:
    from guardian.restore import RestorePlan

    first = CheckpointState.create(
        workspace=tmp_path / "workspace",
        operation="modify",
        target=tmp_path / "workspace" / "project",
    )
    second = CheckpointState.create(
        workspace=tmp_path / "workspace",
        operation="modify",
        target=tmp_path / "workspace" / "other",
    )

    plan = RestorePlan.from_checkpoint(first)

    with pytest.raises(ValueError, match="identifier mismatch"):
        plan.validate_against(second)


def test_restore_plan_rejects_workspace_substitution(tmp_path) -> None:
    from guardian.restore import RestorePlan

    checkpoint = CheckpointState.create(
        workspace=tmp_path / "workspace",
        operation="modify",
        target=tmp_path / "workspace" / "project",
    )
    substituted = CheckpointState(
        workspace=tmp_path / "other-workspace",
        operation=checkpoint.operation,
        target=tmp_path / "other-workspace" / "project",
        checkpoint_id=checkpoint.checkpoint_id,
    )

    plan = RestorePlan.from_checkpoint(checkpoint)

    with pytest.raises(ValueError, match="workspace mismatch"):
        plan.validate_against(substituted)


def test_restore_plan_rejects_target_escape(tmp_path) -> None:
    from guardian.restore import RestoreRequest

    checkpoint = CheckpointState.create(
        workspace=tmp_path / "workspace",
        operation="modify",
        target=tmp_path / "workspace" / "project",
    )

    request = RestoreRequest(
        checkpoint_id=checkpoint.checkpoint_id,
        workspace=tmp_path / "workspace",
        target=tmp_path / "outside",
    )

    with pytest.raises(PermissionError, match="outside"):
        request.validate_boundary()


def test_restore_backend_is_not_called_for_invalid_plan(tmp_path) -> None:
    from guardian.checkpoint import CheckpointManager
    from guardian.restore import RestoreStatus

    class Backend:
        def can_restore(self, checkpoint) -> bool:
            raise AssertionError("backend must not be queried")

        def restore(self, checkpoint) -> None:
            raise AssertionError("backend must not be invoked")

    manager = CheckpointManager(restore_backend=Backend())

    checkpoint = CheckpointState(
        workspace=tmp_path / "workspace",
        operation="modify",
        target=tmp_path / "outside",
    )

    result = manager.restore(checkpoint)

    assert result.status is RestoreStatus.REJECTED
    assert "outside" in result.message

def test_restore_backend_registry_selects_first_capable_backend() -> None:
    from guardian.restore import RestoreBackendRegistry

    class Backend:
        def __init__(self, capable: bool) -> None:
            self.capable = capable

        @property
        def capabilities(self) -> frozenset[str]:
            return frozenset({"checkpoint.restore"}) if self.capable else frozenset()

        def can_restore(self, checkpoint) -> bool:
            return self.capable

        def restore(self, plan) -> None:
            pass

    registry = RestoreBackendRegistry()
    unsupported = Backend(False)
    supported = Backend(True)

    registry.register(unsupported)
    registry.register(supported)

    checkpoint = CheckpointState.create(
        workspace=__import__("pathlib").Path("/tmp/workspace"),
        operation="modify",
        target=__import__("pathlib").Path("/tmp/workspace/project"),
    )

    assert registry.select(checkpoint) is supported


def test_restore_backend_registry_preserves_registration_order() -> None:
    from guardian.restore import RestoreBackendRegistry

    class Backend:
        def __init__(self, name: str) -> None:
            self.name = name

        @property
        def capabilities(self) -> frozenset[str]:
            return frozenset({"checkpoint.restore"})

        def can_restore(self, checkpoint) -> bool:
            return True

        def restore(self, plan) -> None:
            pass

    first = Backend("first")
    second = Backend("second")

    registry = RestoreBackendRegistry()
    registry.register(first)
    registry.register(second)

    checkpoint = CheckpointState.create(
        workspace=Path("/tmp/workspace"),
        operation="modify",
        target=Path("/tmp/workspace/project"),
    )

    assert registry.select(checkpoint) is first
    assert registry.discover(checkpoint) == (first, second)


def test_restore_backend_registry_deduplicates_backend() -> None:
    from guardian.restore import RestoreBackendRegistry

    class Backend:
        @property
        def capabilities(self) -> frozenset[str]:
            return frozenset({"checkpoint.restore"})

        def can_restore(self, checkpoint) -> bool:
            return True

        def restore(self, plan) -> None:
            pass

    backend = Backend()
    registry = RestoreBackendRegistry()

    registry.register(backend)
    registry.register(backend)

    checkpoint = CheckpointState.create(
        workspace=Path("/tmp/workspace"),
        operation="modify",
        target=Path("/tmp/workspace/project"),
    )

    assert registry.discover(checkpoint) == (backend,)


def test_restore_backend_registry_returns_none_without_capable_backend() -> None:
    from guardian.restore import RestoreBackendRegistry

    class Backend:
        @property
        def capabilities(self) -> frozenset[str]:
            return frozenset()

        def can_restore(self, checkpoint) -> bool:
            return False

        def restore(self, plan) -> None:
            raise AssertionError("must not execute")

    registry = RestoreBackendRegistry()
    registry.register(Backend())

    checkpoint = CheckpointState.create(
        workspace=Path("/tmp/workspace"),
        operation="modify",
        target=Path("/tmp/workspace/project"),
    )

    assert registry.select(checkpoint) is None


def test_restore_manager_rejects_without_capable_backend() -> None:
    from guardian.checkpoint import CheckpointManager
    from guardian.restore import RestoreBackendRegistry, RestoreStatus

    class Backend:
        @property
        def capabilities(self) -> frozenset[str]:
            return frozenset()

        def can_restore(self, checkpoint) -> bool:
            return False

        def restore(self, plan) -> None:
            raise AssertionError("must not execute")

    registry = RestoreBackendRegistry()
    registry.register(Backend())

    manager = CheckpointManager(restore_registry=registry)

    checkpoint = CheckpointState.create(
        workspace=Path("/tmp/workspace"),
        operation="modify",
        target=Path("/tmp/workspace/project"),
    )

    result = manager.restore(checkpoint)

    assert result.status is RestoreStatus.REJECTED
    assert "no capable" in result.message


def test_filesystem_snapshot_store_captures_and_restores_file(tmp_path) -> None:
    from guardian.restore import FilesystemSnapshotStore

    workspace = tmp_path / "workspace"
    target = workspace / "project.txt"
    target.parent.mkdir(parents=True)
    target.write_text("original", encoding="utf-8")

    checkpoint = CheckpointState.create(
        workspace=workspace,
        operation="modify",
        target=target,
    )

    snapshots = FilesystemSnapshotStore(tmp_path / "snapshots")
    snapshots.capture(checkpoint)

    target.write_text("modified", encoding="utf-8")
    snapshots.restore(checkpoint)

    assert target.read_text(encoding="utf-8") == "original"


def test_filesystem_snapshot_store_captures_and_restores_directory(
    tmp_path,
) -> None:
    from guardian.restore import FilesystemSnapshotStore

    workspace = tmp_path / "workspace"
    target = workspace / "project"
    target.mkdir(parents=True)
    (target / "one.txt").write_text("one", encoding="utf-8")
    (target / "two.txt").write_text("two", encoding="utf-8")

    checkpoint = CheckpointState.create(
        workspace=workspace,
        operation="modify",
        target=target,
    )

    snapshots = FilesystemSnapshotStore(tmp_path / "snapshots")
    snapshots.capture(checkpoint)

    (target / "one.txt").write_text("changed", encoding="utf-8")
    (target / "three.txt").write_text("three", encoding="utf-8")

    snapshots.restore(checkpoint)

    assert (target / "one.txt").read_text(encoding="utf-8") == "one"
    assert (target / "two.txt").read_text(encoding="utf-8") == "two"
    assert not (target / "three.txt").exists()


def test_filesystem_snapshot_store_rejects_target_escape(tmp_path) -> None:
    from guardian.restore import FilesystemSnapshotStore

    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    outside.mkdir()

    checkpoint = CheckpointState.create(
        workspace=workspace,
        operation="modify",
        target=outside,
    )

    snapshots = FilesystemSnapshotStore(tmp_path / "snapshots")

    with pytest.raises(PermissionError, match="outside"):
        snapshots.capture(checkpoint)


def test_filesystem_restore_backend_requires_snapshot(tmp_path) -> None:
    from guardian.restore import (
        FilesystemRestoreBackend,
        FilesystemSnapshotStore,
    )

    checkpoint = CheckpointState.create(
        workspace=tmp_path / "workspace",
        operation="modify",
        target=tmp_path / "workspace" / "project",
    )

    snapshots = FilesystemSnapshotStore(tmp_path / "snapshots")
    backend = FilesystemRestoreBackend(snapshots)

    assert backend.capabilities == frozenset({"checkpoint.restore"})
    assert not backend.can_restore(checkpoint)


def test_filesystem_restore_backend_restores_snapshot(tmp_path) -> None:
    from guardian.restore import (
        FilesystemRestoreBackend,
        FilesystemSnapshotStore,
        RestorePlan,
    )

    workspace = tmp_path / "workspace"
    target = workspace / "project.txt"
    workspace.mkdir()
    target.write_text("original", encoding="utf-8")

    checkpoint = CheckpointState.create(
        workspace=workspace,
        operation="modify",
        target=target,
    )

    snapshots = FilesystemSnapshotStore(tmp_path / "snapshots")
    snapshots.capture(checkpoint)

    target.write_text("changed", encoding="utf-8")

    backend = FilesystemRestoreBackend(snapshots)
    plan = RestorePlan.from_checkpoint(checkpoint)

    assert backend.can_restore(checkpoint)

    backend.restore(plan)

    assert target.read_text(encoding="utf-8") == "original"


def test_checkpoint_manager_can_capture_and_restore_filesystem(
    tmp_path,
) -> None:
    from guardian.checkpoint import CheckpointManager
    from guardian.restore import (
        FilesystemRestoreBackend,
        FilesystemSnapshotStore,
        RestoreBackendRegistry,
        RestoreStatus,
    )

    workspace = tmp_path / "workspace"
    target = workspace / "project.txt"
    workspace.mkdir()
    target.write_text("original", encoding="utf-8")

    snapshots = FilesystemSnapshotStore(tmp_path / "snapshots")
    backend = FilesystemRestoreBackend(snapshots)

    registry = RestoreBackendRegistry()
    registry.register(backend)

    manager = CheckpointManager(
        restore_registry=registry,
        snapshot_store=snapshots,
    )

    checkpoint = manager.create(
        workspace=workspace,
        operation="modify",
        target=target,
    )

    manager.capture(checkpoint)

    target.write_text("changed", encoding="utf-8")

    result = manager.restore(checkpoint)

    assert result.status is RestoreStatus.RESTORED
    assert target.read_text(encoding="utf-8") == "original"


def test_filesystem_snapshot_rejects_external_symlink(tmp_path) -> None:
    from guardian.restore import FilesystemSnapshotStore

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")

    target = workspace / "project"
    target.mkdir()
    (target / "escape").symlink_to(outside)

    checkpoint = CheckpointState.create(
        workspace=workspace,
        operation="modify",
        target=target,
    )

    snapshots = FilesystemSnapshotStore(tmp_path / "snapshots")

    with pytest.raises(PermissionError, match="outside"):
        snapshots.capture(checkpoint)


def test_filesystem_snapshot_allows_internal_symlink(tmp_path) -> None:
    from guardian.restore import FilesystemSnapshotStore

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    source = workspace / "source.txt"
    source.write_text("safe", encoding="utf-8")

    target = workspace / "project"
    target.mkdir()
    link = target / "link"
    link.symlink_to(source)

    checkpoint = CheckpointState.create(
        workspace=workspace,
        operation="modify",
        target=target,
    )

    snapshots = FilesystemSnapshotStore(tmp_path / "snapshots")
    snapshots.capture(checkpoint)

    source.write_text("changed", encoding="utf-8")
    snapshots.restore(checkpoint)

    assert link.is_symlink()
    assert link.resolve() == source.resolve()


def test_filesystem_restore_preserves_target_when_staging_fails(
    tmp_path,
    monkeypatch,
) -> None:
    from guardian.restore import FilesystemSnapshotStore

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    target = workspace / "project.txt"
    target.write_text("original", encoding="utf-8")

    checkpoint = CheckpointState.create(
        workspace=workspace,
        operation="modify",
        target=target,
    )

    snapshots = FilesystemSnapshotStore(tmp_path / "snapshots")
    snapshots.capture(checkpoint)

    target.write_text("current", encoding="utf-8")

    original_copy_entry = snapshots._copy_entry

    def failing_copy_entry(*args, **kwargs):
        raise RuntimeError("staging failure")

    monkeypatch.setattr(snapshots, "_copy_entry", failing_copy_entry)

    with pytest.raises(RuntimeError, match="staging failure"):
        snapshots.restore(checkpoint)

    assert target.read_text(encoding="utf-8") == "current"

    monkeypatch.setattr(
        snapshots,
        "_copy_entry",
        original_copy_entry,
    )

def test_checkpoint_manager_restores_from_snapshot_store(tmp_path) -> None:
    from guardian.checkpoint import CheckpointManager
    from guardian.restore import FilesystemSnapshotStore, RestoreStatus

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    target = workspace / "project"
    target.mkdir()
    (target / "file.txt").write_text("original", encoding="utf-8")

    snapshots = FilesystemSnapshotStore(tmp_path / "snapshots")
    manager = CheckpointManager(snapshot_store=snapshots)

    checkpoint = manager.create(
        workspace=workspace,
        operation="modify",
        target=target,
    )

    manager.capture(checkpoint)
    (target / "file.txt").write_text("changed", encoding="utf-8")

    result = manager.restore(checkpoint)

    assert result.status is RestoreStatus.RESTORED
    assert (target / "file.txt").read_text(encoding="utf-8") == "original"


def test_checkpoint_manager_snapshot_backend_rejects_missing_snapshot(
    tmp_path,
) -> None:
    from guardian.checkpoint import CheckpointManager
    from guardian.restore import FilesystemSnapshotStore, RestoreStatus

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    target = workspace / "project"
    target.mkdir()

    snapshots = FilesystemSnapshotStore(tmp_path / "snapshots")
    manager = CheckpointManager(snapshot_store=snapshots)

    checkpoint = manager.create(
        workspace=workspace,
        operation="modify",
        target=target,
    )

    result = manager.restore(checkpoint)

    assert result.status is RestoreStatus.REJECTED
    assert "no capable" in result.message


def test_filesystem_snapshot_preserves_relative_internal_symlink(
    tmp_path,
) -> None:
    from guardian.restore import FilesystemSnapshotStore

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    target = workspace / "project"
    target.mkdir()

    source = target / "source.txt"
    source.write_text("original", encoding="utf-8")

    link = target / "link.txt"
    link.symlink_to("source.txt")

    checkpoint = CheckpointState.create(
        workspace=workspace,
        operation="modify",
        target=target,
    )

    snapshots = FilesystemSnapshotStore(tmp_path / "snapshots")
    snapshots.capture(checkpoint)

    source.write_text("changed", encoding="utf-8")
    link.unlink()

    snapshots.restore(checkpoint)

    assert link.is_symlink()
    assert link.read_text(encoding="utf-8") == "changed"
    assert link.readlink() == Path("source.txt")


def test_filesystem_snapshot_preserves_broken_internal_symlink(
    tmp_path,
) -> None:
    from guardian.restore import FilesystemSnapshotStore

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    target = workspace / "project"
    target.mkdir()

    link = target / "missing.txt"
    link.symlink_to("missing.txt")

    checkpoint = CheckpointState.create(
        workspace=workspace,
        operation="modify",
        target=target,
    )

    snapshots = FilesystemSnapshotStore(tmp_path / "snapshots")
    snapshots.capture(checkpoint)

    link.unlink()
    snapshots.restore(checkpoint)

    assert link.is_symlink()
    assert link.readlink() == Path("missing.txt")
    assert not link.exists()


def test_filesystem_snapshot_rejects_symlink_outside_workspace_after_resolution(
    tmp_path,
) -> None:
    from guardian.restore import FilesystemSnapshotStore

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    outside = tmp_path / "outside"
    outside.mkdir()

    target = workspace / "project"
    target.mkdir()

    link = target / "escape"
    link.symlink_to(outside)

    checkpoint = CheckpointState.create(
        workspace=workspace,
        operation="modify",
        target=target,
    )

    snapshots = FilesystemSnapshotStore(tmp_path / "snapshots")

    with pytest.raises(PermissionError, match="outside"):
        snapshots.capture(checkpoint)


def test_filesystem_snapshot_rejects_symlinked_target_outside_workspace(
    tmp_path,
) -> None:
    from guardian.restore import FilesystemSnapshotStore

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")

    target = workspace / "project.txt"
    target.symlink_to(outside)

    checkpoint = CheckpointState.create(
        workspace=workspace,
        operation="modify",
        target=target,
    )

    snapshots = FilesystemSnapshotStore(tmp_path / "snapshots")

    with pytest.raises(PermissionError, match="outside"):
        snapshots.capture(checkpoint)


def test_filesystem_snapshot_rejects_restore_target_outside_workspace(
    tmp_path,
) -> None:
    from guardian.restore import FilesystemSnapshotStore

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    outside = tmp_path / "outside"
    outside.mkdir()

    target = workspace / "project"
    target.mkdir()

    checkpoint = CheckpointState.create(
        workspace=workspace,
        operation="modify",
        target=target,
    )

    snapshots = FilesystemSnapshotStore(tmp_path / "snapshots")
    snapshots.capture(checkpoint)

    substituted = CheckpointState(
        workspace=workspace,
        operation="restore",
        target=outside,
        checkpoint_id=checkpoint.checkpoint_id,
    )

    with pytest.raises(PermissionError, match="outside"):
        snapshots.restore(substituted)

def test_checkpoint_codec_rejects_non_string_checkpoint_id() -> None:
    from guardian.checkpoint import CheckpointCodec

    payload = (
        '{"checkpoint_id":123,'
        '"workspace":"/tmp/workspace",'
        '"operation":"modify",'
        '"target":"/tmp/workspace/project"}'
    )

    with pytest.raises((ValueError, TypeError), match="checkpoint"):
        CheckpointCodec.decode(payload)


def test_checkpoint_codec_rejects_non_string_workspace() -> None:
    from guardian.checkpoint import CheckpointCodec

    payload = (
        '{"checkpoint_id":"00000000-0000-0000-0000-000000000001",'
        '"workspace":123,'
        '"operation":"modify",'
        '"target":"/tmp/workspace/project"}'
    )

    with pytest.raises(ValueError, match="workspace"):
        CheckpointCodec.decode(payload)


def test_checkpoint_codec_rejects_non_string_operation() -> None:
    from guardian.checkpoint import CheckpointCodec

    payload = (
        '{"checkpoint_id":"00000000-0000-0000-0000-000000000001",'
        '"workspace":"/tmp/workspace",'
        '"operation":123,'
        '"target":"/tmp/workspace/project"}'
    )

    with pytest.raises(ValueError, match="operation"):
        CheckpointCodec.decode(payload)


def test_checkpoint_codec_rejects_non_string_target() -> None:
    from guardian.checkpoint import CheckpointCodec

    payload = (
        '{"checkpoint_id":"00000000-0000-0000-0000-000000000001",'
        '"workspace":"/tmp/workspace",'
        '"operation":"modify",'
        '"target":123}'
    )

    with pytest.raises(ValueError, match="target"):
        CheckpointCodec.decode(payload)


def test_checkpoint_codec_rejects_invalid_checkpoint_id() -> None:
    from guardian.checkpoint import CheckpointCodec

    payload = (
        '{"checkpoint_id":"not-a-uuid",'
        '"workspace":"/tmp/workspace",'
        '"operation":"modify",'
        '"target":"/tmp/workspace/project"}'
    )

    with pytest.raises(ValueError, match="checkpoint"):
        CheckpointCodec.decode(payload)


def test_checkpoint_codec_rejects_empty_operation() -> None:
    from guardian.checkpoint import CheckpointCodec

    payload = (
        '{"checkpoint_id":"00000000-0000-0000-0000-000000000001",'
        '"workspace":"/tmp/workspace",'
        '"operation":"   ",'
        '"target":"/tmp/workspace/project"}'
    )

    with pytest.raises(ValueError, match="operation"):
        CheckpointCodec.decode(payload)


def test_checkpoint_codec_rejects_empty_workspace() -> None:
    from guardian.checkpoint import CheckpointCodec

    payload = (
        '{"checkpoint_id":"00000000-0000-0000-0000-000000000001",'
        '"workspace":"",'
        '"operation":"modify",'
        '"target":"/tmp/workspace/project"}'
    )

    with pytest.raises(ValueError, match="workspace"):
        CheckpointCodec.decode(payload)


def test_checkpoint_codec_rejects_empty_target() -> None:
    from guardian.checkpoint import CheckpointCodec

    payload = (
        '{"checkpoint_id":"00000000-0000-0000-0000-000000000001",'
        '"workspace":"/tmp/workspace",'
        '"operation":"modify",'
        '"target":""}'
    )

    with pytest.raises(ValueError, match="target"):
        CheckpointCodec.decode(payload)


def test_checkpoint_store_does_not_leave_temporary_file(tmp_path) -> None:
    from guardian.checkpoint import FileCheckpointStore

    store = FileCheckpointStore(tmp_path / "checkpoints")
    checkpoint = CheckpointState.create(
        workspace=tmp_path / "workspace",
        operation="modify",
        target=tmp_path / "workspace" / "project",
    )

    store.save(checkpoint)

    assert not list(store.root.glob("*.tmp"))

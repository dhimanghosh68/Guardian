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

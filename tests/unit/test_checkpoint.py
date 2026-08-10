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


def test_checkpoint_manager_restore_is_not_implemented() -> None:
    manager = CheckpointManager()

    checkpoint = manager.create(
        workspace=Path("/tmp/guardian-workspace"),
        operation="modify",
        target=Path("/tmp/guardian-workspace/project"),
    )

    with pytest.raises(NotImplementedError):
        manager.restore(checkpoint)


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

import json
from pathlib import Path
from uuid import UUID

from guardian.checkpoint.state import CheckpointState


class CheckpointCodec:
    """Encodes and decodes Guardian checkpoint state deterministically."""

    @staticmethod
    def encode(state: CheckpointState) -> str:
        payload = {
            "checkpoint_id": str(state.checkpoint_id),
            "workspace": str(state.normalized_workspace()),
            "operation": state.operation.strip(),
            "target": str(state.normalized_target()),
        }

        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def decode(data: str) -> CheckpointState:
        payload = json.loads(data)

        if not isinstance(payload, dict):
            raise ValueError("checkpoint payload must be an object")

        required = {
            "checkpoint_id",
            "workspace",
            "operation",
            "target",
        }

        if set(payload) != required:
            raise ValueError("checkpoint payload has invalid fields")

        checkpoint_id = UUID(payload["checkpoint_id"])

        return CheckpointState(
            workspace=Path(payload["workspace"]),
            operation=payload["operation"],
            target=Path(payload["target"]),
            checkpoint_id=checkpoint_id,
        )

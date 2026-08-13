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

        checkpoint_id_value = payload["checkpoint_id"]
        workspace_value = payload["workspace"]
        operation_value = payload["operation"]
        target_value = payload["target"]

        if not isinstance(checkpoint_id_value, str):
            raise ValueError("checkpoint_id must be a string")

        if not isinstance(workspace_value, str):
            raise ValueError("workspace must be a string")

        if not isinstance(operation_value, str):
            raise ValueError("operation must be a string")

        if not isinstance(target_value, str):
            raise ValueError("target must be a string")

        if not workspace_value.strip():
            raise ValueError("workspace must not be empty")

        if not operation_value.strip():
            raise ValueError("operation must not be empty")

        if not target_value.strip():
            raise ValueError("target must not be empty")

        try:
            checkpoint_id = UUID(checkpoint_id_value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise ValueError(
                "checkpoint_id must be a valid UUID"
            ) from exc

        return CheckpointState(
            workspace=Path(workspace_value),
            operation=operation_value.strip(),
            target=Path(target_value),
            checkpoint_id=checkpoint_id,
        )
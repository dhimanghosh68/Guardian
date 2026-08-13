import hashlib
import json
from pathlib import Path
from typing import Protocol
from uuid import UUID

from guardian.checkpoint.codec import CheckpointCodec
from guardian.checkpoint.state import CheckpointState


class CheckpointStore(Protocol):
    """Contract for persistent Guardian checkpoint storage."""

    def save(self, checkpoint: CheckpointState) -> None:
        """Persist a checkpoint."""
        ...

    def load(self, checkpoint_id: UUID) -> CheckpointState:
        """Load a checkpoint by identifier."""
        ...

    def exists(self, checkpoint_id: UUID) -> bool:
        """Return whether a checkpoint exists."""
        ...

    def delete(self, checkpoint_id: UUID) -> None:
        """Delete a checkpoint if it exists."""
        ...


class FileCheckpointStore:
    """Filesystem-backed persistent checkpoint store."""

    def __init__(self, root: Path) -> None:
        self.root = root.expanduser().resolve(strict=False)

    def save(self, checkpoint: CheckpointState) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

        destination = self._path_for(checkpoint.checkpoint_id)
        temporary = destination.with_suffix(".tmp")

        temporary.write_text(
            self._encode(checkpoint),
            encoding="utf-8",
        )
        temporary.replace(destination)

    def load(self, checkpoint_id: UUID) -> CheckpointState:
        path = self._path_for(checkpoint_id)

        if not path.is_file():
            raise FileNotFoundError(
                f"checkpoint not found: {checkpoint_id}"
            )

        try:
            checkpoint = self._decode(
                path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError, TypeError, KeyError) as exc:
            raise ValueError(
                f"checkpoint {checkpoint_id} has invalid integrity"
            ) from exc

        if checkpoint.checkpoint_id != checkpoint_id:
            raise ValueError(
                f"checkpoint {checkpoint_id} has mismatched identifier"
            )

        return checkpoint

    def exists(self, checkpoint_id: UUID) -> bool:
        return self._path_for(checkpoint_id).is_file()

    def delete(self, checkpoint_id: UUID) -> None:
        self._path_for(checkpoint_id).unlink(missing_ok=True)

    def _path_for(self, checkpoint_id: UUID) -> Path:
        return self.root / f"{checkpoint_id}.json"

    def _encode(self, checkpoint: CheckpointState) -> str:
        payload = CheckpointCodec.encode(checkpoint)
        integrity = hashlib.sha256(
            payload.encode("utf-8")
        ).hexdigest()

        envelope = {
            "checkpoint": json.loads(payload),
            "integrity": integrity,
        }

        return json.dumps(
            envelope,
            sort_keys=True,
            separators=(",", ":"),
        )

    def _decode(self, data: str) -> CheckpointState:
        envelope = json.loads(data)

        if not isinstance(envelope, dict):
            raise ValueError("checkpoint envelope must be an object")

        if set(envelope) != {"checkpoint", "integrity"}:
            raise ValueError("checkpoint envelope has invalid fields")

        payload = envelope["checkpoint"]
        expected = envelope["integrity"]

        if not isinstance(payload, dict) or not isinstance(expected, str):
            raise ValueError("checkpoint integrity metadata is invalid")

        canonical_payload = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        )

        actual = hashlib.sha256(
            canonical_payload.encode("utf-8")
        ).hexdigest()

        if actual != expected:
            raise ValueError("checkpoint integrity verification failed")

        return CheckpointCodec.decode(canonical_payload)

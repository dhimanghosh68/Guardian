from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SandboxWorkspace:
    """Immutable description of an isolated Guardian workspace."""

    root: Path

    def normalized_root(self) -> Path:
        return self.root.expanduser().resolve(strict=False)

    def contains(self, path: Path) -> bool:
        candidate = path.expanduser().resolve(strict=False)
        root = self.normalized_root()

        if candidate == root:
            return True

        try:
            candidate.relative_to(root)
        except ValueError:
            return False
        else:
            return True

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SafetyBoundary:
    """Immutable description of Guardian's protected host boundary."""

    protected_paths: tuple[Path, ...] = (
        Path("/etc"),
        Path("/usr"),
        Path("/bin"),
        Path("/sbin"),
        Path("/boot"),
        Path("/var"),
    )

    protected_projects: tuple[Path, ...] = (
        Path.home() / "Development" / "react",
    )

    def protects(self, path: Path) -> bool:
        """Return True when path is inside a protected location."""
        candidate = path.expanduser().resolve(strict=False)

        return any(
            self._contains(protected, candidate)
            for protected in self.protected_paths + self.protected_projects
        )

    @staticmethod
    def _contains(parent: Path, candidate: Path) -> bool:
        """Return True when candidate is parent or below parent."""
        protected = parent.expanduser().resolve(strict=False)

        if candidate == protected:
            return True

        try:
            candidate.relative_to(protected)
        except ValueError:
            return False

        return True

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

        for protected in self.protected_paths + self.protected_projects:
            protected_path = protected.expanduser().resolve(strict=False)

            if candidate == protected_path:
                return True

            try:
                candidate.relative_to(protected_path)
            except ValueError:
                continue
            else:
                return True

        return False

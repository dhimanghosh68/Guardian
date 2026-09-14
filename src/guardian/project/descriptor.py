from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class ProjectKind(str, Enum):
    PYTHON = "python"
    NODE = "node"
    RUST = "rust"
    GO = "go"
    JAVA = "java"
    GRADLE = "gradle"
    MAKE = "make"
    CMAKE = "cmake"
    DOCKER = "docker"
    GIT = "git"


@dataclass(frozen=True)
class ProjectDescriptor:
    """Immutable description of observable project markers."""

    root: Path
    markers: tuple[str, ...]
    kinds: tuple[ProjectKind, ...]

    def has_marker(self, marker: str) -> bool:
        return marker in self.markers

    def has_kind(self, kind: ProjectKind) -> bool:
        return kind in self.kinds


class ProjectDescriptorDetector:
    """Detect project characteristics from filesystem evidence only."""

    _MARKERS: tuple[tuple[str, ProjectKind], ...] = (
        ("pyproject.toml", ProjectKind.PYTHON),
        ("package.json", ProjectKind.NODE),
        ("Cargo.toml", ProjectKind.RUST),
        ("go.mod", ProjectKind.GO),
        ("pom.xml", ProjectKind.JAVA),
        ("build.gradle", ProjectKind.GRADLE),
        ("build.gradle.kts", ProjectKind.GRADLE),
        ("Makefile", ProjectKind.MAKE),
        ("CMakeLists.txt", ProjectKind.CMAKE),
        ("Dockerfile", ProjectKind.DOCKER),
        ("docker-compose.yml", ProjectKind.DOCKER),
        ("docker-compose.yaml", ProjectKind.DOCKER),
        (".git", ProjectKind.GIT),
    )

    def detect(self, root: Path) -> ProjectDescriptor:
        normalized_root = root.expanduser().absolute()

        markers: list[str] = []
        kinds: set[ProjectKind] = set()

        for marker, kind in self._MARKERS:
            if (normalized_root / marker).exists():
                markers.append(marker)
                kinds.add(kind)

        ordered_kinds = tuple(
            kind
            for kind in ProjectKind
            if kind in kinds
        )

        return ProjectDescriptor(
            root=normalized_root,
            markers=tuple(markers),
            kinds=ordered_kinds,
        )

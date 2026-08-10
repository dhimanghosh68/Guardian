from pathlib import Path

from guardian.sandbox import SandboxWorkspace


def test_workspace_normalizes_root() -> None:
    workspace = SandboxWorkspace(
        Path("~/Development/guardian-lab/workspace")
    )

    assert workspace.normalized_root() == (
        Path.home() / "Development" / "guardian-lab" / "workspace"
    ).resolve()


def test_workspace_contains_root() -> None:
    workspace = SandboxWorkspace(Path("/tmp/guardian-workspace"))

    assert workspace.contains(Path("/tmp/guardian-workspace"))


def test_workspace_contains_descendant() -> None:
    workspace = SandboxWorkspace(Path("/tmp/guardian-workspace"))

    assert workspace.contains(
        Path("/tmp/guardian-workspace/project/file.txt")
    )


def test_workspace_rejects_outside_path() -> None:
    workspace = SandboxWorkspace(Path("/tmp/guardian-workspace"))

    assert not workspace.contains(Path("/tmp/other/file.txt"))


def test_workspace_is_immutable() -> None:
    workspace = SandboxWorkspace(Path("/tmp/guardian-workspace"))

    try:
        workspace.root = Path("/tmp/other")
    except AttributeError:
        pass
    else:
        raise AssertionError("SandboxWorkspace must be immutable")

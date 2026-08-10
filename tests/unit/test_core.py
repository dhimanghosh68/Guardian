from pathlib import Path

from guardian.core import GuardianRequest, GuardianResult, GuardianStatus


def test_request_normalizes_target() -> None:
    request = GuardianRequest(
        target=Path("~/Development/guardian-lab"),
        operation="inspect",
    )

    assert request.normalized_target() == (
        Path.home() / "Development" / "guardian-lab"
    ).resolve()


def test_request_is_immutable() -> None:
    request = GuardianRequest(
        target=Path("/tmp/example"),
        operation="inspect",
    )

    try:
        request.operation = "delete"
    except AttributeError:
        pass
    else:
        raise AssertionError("GuardianRequest must be immutable")


def test_result_reports_allowed_status() -> None:
    result = GuardianResult(
        status=GuardianStatus.ALLOWED,
        operation="inspect",
        target=Path("/tmp/example"),
        message="operation permitted",
    )

    assert result.allowed


def test_blocked_result_is_not_allowed() -> None:
    result = GuardianResult(
        status=GuardianStatus.BLOCKED,
        operation="delete",
        target=Path("/etc"),
        message="protected path",
    )

    assert not result.allowed

from pathlib import Path

import pytest

from guardian.core import GuardianRequest
from guardian.validation import RequestValidationError, RequestValidator


def test_validator_accepts_valid_request() -> None:
    request = GuardianRequest(
        target=Path("/tmp/example"),
        operation="inspect",
    )

    RequestValidator().validate(request)


def test_validator_rejects_empty_operation() -> None:
    request = GuardianRequest(
        target=Path("/tmp/example"),
        operation="   ",
    )

    with pytest.raises(RequestValidationError, match="operation"):
        RequestValidator().validate(request)

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from guardian.core.request import GuardianRequest


class RequestValidationError(ValueError):
    """Raised when a Guardian request is structurally invalid."""


class RequestValidator:
    """Validate Guardian requests before safety evaluation."""

    def validate(self, request: "GuardianRequest") -> None:
        if not request.operation.strip():
            raise RequestValidationError("operation must not be empty")

        if not request.target:
            raise RequestValidationError("target must not be empty")

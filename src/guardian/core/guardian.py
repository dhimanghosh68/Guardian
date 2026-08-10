from guardian.core.request import GuardianRequest
from guardian.core.result import GuardianResult
from guardian.core.status import GuardianStatus
from guardian.policy import SafetyBoundary
from guardian.sandbox import SandboxWorkspace
from guardian.validation import RequestValidator


class Guardian:
    """Coordinates request validation, host policy, and sandbox policy."""

    def __init__(
        self,
        boundary: SafetyBoundary | None = None,
        workspace: SandboxWorkspace | None = None,
    ) -> None:
        self._boundary = boundary or SafetyBoundary()
        self._workspace = workspace
        self._validator = RequestValidator()

    def evaluate(self, request: GuardianRequest) -> GuardianResult:
        self._validator.validate(request)

        target = request.normalized_target()

        if self._boundary.protects(target):
            return GuardianResult(
                status=GuardianStatus.BLOCKED,
                operation=request.operation,
                target=target,
                message="target is protected by host policy",
            )

        if self._workspace is not None and not self._workspace.contains(target):
            return GuardianResult(
                status=GuardianStatus.BLOCKED,
                operation=request.operation,
                target=target,
                message="target is outside the Guardian workspace",
            )

        return GuardianResult(
            status=GuardianStatus.ALLOWED,
            operation=request.operation,
            target=target,
            message="operation permitted",
        )

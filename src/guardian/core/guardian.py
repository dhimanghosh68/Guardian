from guardian.core.request import GuardianRequest
from guardian.core.result import GuardianResult
from guardian.core.status import GuardianStatus
from guardian.policy import OperationPolicy, SafetyBoundary
from guardian.sandbox import SandboxWorkspace
from guardian.validation import RequestValidator


class Guardian:
    """Coordinates validation, operation policy, host policy, and workspace policy."""

    def __init__(
        self,
        boundary: SafetyBoundary | None = None,
        workspace: SandboxWorkspace | None = None,
        operation_policy: OperationPolicy | None = None,
    ) -> None:
        self._boundary = boundary or SafetyBoundary()
        self._workspace = workspace
        self._operation_policy = operation_policy or OperationPolicy()
        self._validator = RequestValidator()

    def evaluate(self, request: GuardianRequest) -> GuardianResult:
        self._validator.validate(request)

        target = request.normalized_target()
        operation = request.parsed_operation()

        if not self._operation_policy.allows(operation):
            return GuardianResult(
                status=GuardianStatus.BLOCKED,
                operation=request.operation,
                target=target,
                message="operation is blocked by Guardian policy",
            )

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

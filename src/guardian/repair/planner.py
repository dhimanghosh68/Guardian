from guardian.core.request import GuardianRequest
from guardian.policy import SafetyBoundary
from guardian.repair.action import RepairAction
from guardian.sandbox import SandboxWorkspace
from guardian.validation import RequestValidator


class RepairPlanner:
    """Creates repair proposals only for validated, safe targets."""

    def __init__(
        self,
        boundary: SafetyBoundary | None = None,
        workspace: SandboxWorkspace | None = None,
    ) -> None:
        self._boundary = boundary or SafetyBoundary()
        self._workspace = workspace
        self._validator = RequestValidator()

    def plan(self, request: GuardianRequest) -> RepairAction:
        self._validator.validate(request)

        target = request.normalized_target()

        if self._boundary.protects(target):
            raise PermissionError(
                "repair target is protected by host policy"
            )

        if self._workspace is not None and not self._workspace.contains(target):
            raise PermissionError(
                "repair target is outside the Guardian workspace"
            )

        return RepairAction(
            operation=request.operation,
            target=target,
        )

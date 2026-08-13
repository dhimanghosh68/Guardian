from guardian.core.guardian import Guardian
from guardian.core.request import GuardianRequest
from guardian.core.status import GuardianStatus
from guardian.execution.adapter import ExecutionAdapter
from guardian.execution.authorized import AuthorizedExecution
from guardian.execution.registry import ExecutionAdapterRegistry
from guardian.execution.result import ExecutionResult, ExecutionStatus


class ExecutionCoordinator:
    """Authorize requests and execute them through capable adapters."""

    def __init__(
        self,
        guardian: Guardian,
        registry: ExecutionAdapterRegistry | None = None,
        adapter: ExecutionAdapter | None = None,
    ) -> None:
        if registry is not None and adapter is not None:
            raise ValueError(
                "execution coordinator cannot use both registry and adapter"
            )

        self._guardian = guardian
        self._registry = registry
        self._adapter = adapter

    def execute(self, request: GuardianRequest) -> ExecutionResult:
        """Authorize and execute one request."""
        decision = self._guardian.evaluate(request)

        if decision.status is not GuardianStatus.ALLOWED:
            return self._rejected(request, decision.message)

        adapter = self._select_adapter(request)

        if adapter is None:
            return self._rejected(
                request,
                "no capable execution adapter is available",
            )

        # Authorization is deliberately performed again immediately before
        # creating execution authority. Adapter selection therefore cannot
        # turn an earlier authorization decision into execution authority.
        decision = self._guardian.evaluate(request)

        if decision.status is not GuardianStatus.ALLOWED:
            return self._rejected(request, decision.message)

        authorization = AuthorizedExecution(
            operation=request.parsed_operation(),
            target=decision.target,
        )

        try:
            adapter.execute(authorization)
        except Exception as exc:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                operation=request.operation,
                target=authorization.target,
                message=f"execution failed: {exc}",
            )

        return ExecutionResult(
            status=ExecutionStatus.EXECUTED,
            operation=request.operation,
            target=authorization.target,
            message="operation executed successfully",
        )

    def _select_adapter(
        self,
        request: GuardianRequest,
    ) -> ExecutionAdapter | None:
        if self._registry is not None:
            return self._registry.select(request)

        return self._adapter

    @staticmethod
    def _rejected(
        request: GuardianRequest,
        message: str,
    ) -> ExecutionResult:
        return ExecutionResult(
            status=ExecutionStatus.REJECTED,
            operation=request.operation,
            target=request.normalized_target(),
            message=message,
        )

from pathlib import Path

from guardian.core import Guardian, GuardianRequest, GuardianStatus
from guardian.execution import (
    AuthorizedExecution,
    ExecutionAdapterRegistry,
    ExecutionCoordinator,
    ExecutionStatus,
)
from guardian.policy import SafetyBoundary
from guardian.sandbox import SandboxWorkspace


class FakeAdapter:
    CAPABILITY = "execution.fake"

    def __init__(
        self,
        *,
        capable: bool = True,
        failure: Exception | None = None,
    ) -> None:
        self._capable = capable
        self._failure = failure
        self.calls: list[AuthorizedExecution] = []

    @property
    def capabilities(self) -> frozenset[str]:
        return frozenset({self.CAPABILITY})

    def can_execute(self, request: GuardianRequest) -> bool:
        return self._capable

    def execute(self, authorization: AuthorizedExecution) -> None:
        self.calls.append(authorization)

        if self._failure is not None:
            raise self._failure


def make_guardian(tmp_path: Path) -> Guardian:
    return Guardian(
        boundary=SafetyBoundary(
            protected_paths=(),
            protected_projects=(),
        ),
        workspace=SandboxWorkspace(tmp_path),
    )


def test_execution_registry_selects_first_capable_adapter(tmp_path):
    request = GuardianRequest(
        target=tmp_path / "file.txt",
        operation="write",
    )

    first = FakeAdapter(capable=True)
    second = FakeAdapter(capable=True)

    registry = ExecutionAdapterRegistry()
    registry.register(first)
    registry.register(second)

    assert registry.select(request) is first


def test_execution_registry_preserves_registration_order(tmp_path):
    request = GuardianRequest(
        target=tmp_path / "file.txt",
        operation="write",
    )

    first = FakeAdapter(capable=False)
    second = FakeAdapter(capable=True)

    registry = ExecutionAdapterRegistry()
    registry.register(first)
    registry.register(second)

    assert registry.discover(request) == (second,)


def test_execution_registry_deduplicates_adapter(tmp_path):
    adapter = FakeAdapter()
    registry = ExecutionAdapterRegistry()

    registry.register(adapter)
    registry.register(adapter)

    assert len(registry) == 1


def test_execution_coordinator_executes_authorized_request(tmp_path):
    guardian = make_guardian(tmp_path)
    adapter = FakeAdapter()

    registry = ExecutionAdapterRegistry()
    registry.register(adapter)

    request = GuardianRequest(
        target=tmp_path / "file.txt",
        operation="write",
    )

    result = ExecutionCoordinator(
        guardian=guardian,
        registry=registry,
    ).execute(request)

    assert result.status is ExecutionStatus.EXECUTED
    assert result.executed
    assert len(adapter.calls) == 1
    assert adapter.calls[0].operation.value == "write"
    assert adapter.calls[0].target == request.normalized_target()


def test_execution_coordinator_rejects_blocked_request(tmp_path):
    guardian = Guardian(
        boundary=SafetyBoundary(
            protected_paths=(tmp_path,),
            protected_projects=(),
        ),
        workspace=SandboxWorkspace(tmp_path),
    )

    adapter = FakeAdapter()
    registry = ExecutionAdapterRegistry()
    registry.register(adapter)

    request = GuardianRequest(
        target=tmp_path / "file.txt",
        operation="write",
    )

    result = ExecutionCoordinator(
        guardian=guardian,
        registry=registry,
    ).execute(request)

    assert result.status is ExecutionStatus.REJECTED
    assert not result.executed
    assert adapter.calls == []


def test_execution_coordinator_rejects_without_capable_adapter(tmp_path):
    guardian = make_guardian(tmp_path)

    registry = ExecutionAdapterRegistry()
    registry.register(FakeAdapter(capable=False))

    request = GuardianRequest(
        target=tmp_path / "file.txt",
        operation="write",
    )

    result = ExecutionCoordinator(
        guardian=guardian,
        registry=registry,
    ).execute(request)

    assert result.status is ExecutionStatus.REJECTED
    assert "no capable execution adapter" in result.message


def test_execution_coordinator_reports_adapter_failure(tmp_path):
    guardian = make_guardian(tmp_path)
    adapter = FakeAdapter(failure=RuntimeError("adapter exploded"))

    registry = ExecutionAdapterRegistry()
    registry.register(adapter)

    request = GuardianRequest(
        target=tmp_path / "file.txt",
        operation="write",
    )

    result = ExecutionCoordinator(
        guardian=guardian,
        registry=registry,
    ).execute(request)

    assert result.status is ExecutionStatus.FAILED
    assert "adapter exploded" in result.message
    assert len(adapter.calls) == 1
    assert adapter.calls[0].operation.value == "write"
    assert adapter.calls[0].target == request.normalized_target()


def test_execution_coordinator_supports_direct_adapter(tmp_path):
    guardian = make_guardian(tmp_path)
    adapter = FakeAdapter()

    request = GuardianRequest(
        target=tmp_path / "file.txt",
        operation="write",
    )

    result = ExecutionCoordinator(
        guardian=guardian,
        adapter=adapter,
    ).execute(request)

    assert result.status is ExecutionStatus.EXECUTED
    assert len(adapter.calls) == 1
    assert adapter.calls[0].operation.value == "write"
    assert adapter.calls[0].target == request.normalized_target()


def test_execution_result_is_immutable(tmp_path):
    guardian = make_guardian(tmp_path)
    adapter = FakeAdapter()

    request = GuardianRequest(
        target=tmp_path / "file.txt",
        operation="write",
    )

    result = ExecutionCoordinator(
        guardian=guardian,
        adapter=adapter,
    ).execute(request)

    try:
        result.message = "changed"
    except AttributeError:
        pass
    else:
        raise AssertionError("execution result must be immutable")


def test_execution_coordinator_rejects_invalid_request(tmp_path):
    guardian = make_guardian(tmp_path)
    adapter = FakeAdapter()

    request = GuardianRequest(
        target=tmp_path / "file.txt",
        operation="invalid",
    )

    try:
        ExecutionCoordinator(
            guardian=guardian,
            adapter=adapter,
        ).execute(request)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid requests must be rejected by validation")


def test_execution_coordinator_rechecks_authorization_before_adapter_execution(
    tmp_path,
):
    class RevokingGuardian:
        def __init__(self, real_guardian):
            self._real_guardian = real_guardian
            self.calls = 0

        def evaluate(self, request):
            self.calls += 1

            if self.calls == 1:
                return self._real_guardian.evaluate(request)

            from guardian.core import GuardianResult, GuardianStatus

            return GuardianResult(
                status=GuardianStatus.BLOCKED,
                operation=request.operation,
                target=request.normalized_target(),
                message="authorization revoked",
            )

    real_guardian = make_guardian(tmp_path)
    guardian = RevokingGuardian(real_guardian)
    adapter = FakeAdapter()

    request = GuardianRequest(
        target=tmp_path / "file.txt",
        operation="write",
    )

    result = ExecutionCoordinator(
        guardian=guardian,
        adapter=adapter,
    ).execute(request)

    assert result.status is ExecutionStatus.REJECTED
    assert result.message == "authorization revoked"
    assert adapter.calls == []


def test_execution_registry_does_not_execute_incapable_adapter(tmp_path):
    guardian = make_guardian(tmp_path)

    capable = FakeAdapter(capable=True)
    incapable = FakeAdapter(capable=False)

    registry = ExecutionAdapterRegistry()
    registry.register(incapable)
    registry.register(capable)

    request = GuardianRequest(
        target=tmp_path / "file.txt",
        operation="write",
    )

    result = ExecutionCoordinator(
        guardian=guardian,
        registry=registry,
    ).execute(request)

    assert result.status is ExecutionStatus.EXECUTED
    assert incapable.calls == []
    assert len(capable.calls) == 1
    assert capable.calls[0].operation.value == "write"
    assert capable.calls[0].target == request.normalized_target()


def test_execution_registry_discovery_is_immutable(tmp_path):
    registry = ExecutionAdapterRegistry()
    adapter = FakeAdapter()

    registry.register(adapter)

    discovered = registry.discover()

    assert discovered == (adapter,)

    try:
        discovered += (FakeAdapter(),)
    except TypeError:
        pass

    assert registry.discover() == (adapter,)


def test_execution_coordinator_rejects_when_both_adapter_sources_are_ambiguous(
    tmp_path,
):
    guardian = make_guardian(tmp_path)
    registry = ExecutionAdapterRegistry()
    registry.register(FakeAdapter())

    try:
        ExecutionCoordinator(
            guardian=guardian,
            registry=registry,
            adapter=FakeAdapter(),
        )
    except ValueError as exc:
        assert "registry" in str(exc)
    else:
        raise AssertionError(
            "coordinator must reject ambiguous adapter configuration"
        )


def test_authorized_execution_is_immutable(tmp_path):
    from guardian.core import GuardianOperation
    authorization = AuthorizedExecution(
        operation=GuardianOperation.WRITE,
        target=tmp_path / "file.txt",
    )

    try:
        authorization.target = tmp_path / "other.txt"
    except AttributeError:
        pass
    else:
        raise AssertionError("authorized execution must be immutable")


def test_execution_adapter_receives_authorization_not_request(tmp_path):
    guardian = make_guardian(tmp_path)
    adapter = FakeAdapter()

    request = GuardianRequest(
        target=tmp_path / "file.txt",
        operation="write",
    )

    result = ExecutionCoordinator(
        guardian=guardian,
        adapter=adapter,
    ).execute(request)

    assert result.status is ExecutionStatus.EXECUTED
    assert len(adapter.calls) == 1
    assert isinstance(adapter.calls[0], AuthorizedExecution)
    assert adapter.calls[0].operation.value == "write"
    assert adapter.calls[0].target == (tmp_path / "file.txt").resolve()

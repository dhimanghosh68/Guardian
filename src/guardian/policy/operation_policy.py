from guardian.core.operation import GuardianOperation


class OperationPolicy:
    """Define which Guardian operations are currently permitted."""

    blocked_operations: frozenset[GuardianOperation] = frozenset(
        {
            GuardianOperation.DELETE,
        }
    )

    def allows(self, operation: GuardianOperation) -> bool:
        """Return True when the operation is permitted by policy."""
        return operation not in self.blocked_operations

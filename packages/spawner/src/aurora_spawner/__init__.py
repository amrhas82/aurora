"""Aurora Spawner - Subprocess spawning for Aurora framework."""

from aurora_spawner.circuit_breaker import CircuitBreaker, get_circuit_breaker
from aurora_spawner.heartbeat import (
    HeartbeatEmitter,
    HeartbeatEvent,
    HeartbeatEventType,
    HeartbeatMonitor,
    create_heartbeat_emitter,
    create_heartbeat_monitor,
)
from aurora_spawner.models import SpawnResult, SpawnTask
from aurora_spawner.recovery import (
    ErrorCategory,
    ErrorClassifier,
    RecoveryMetrics,
    RecoveryPolicy,
    RecoveryResult,
    RecoveryState,
    RecoveryStateMachine,
    RecoveryStateTransition,
    RecoveryStrategy,
    RecoverySummary,
    TaskRecoveryState,
    get_recovery_metrics,
    reset_recovery_metrics,
)
from aurora_spawner.spawner import (
    spawn,
    spawn_parallel,
    spawn_parallel_tracked,
    spawn_parallel_with_recovery,
    spawn_parallel_with_state_tracking,
    spawn_sequential,
    spawn_with_retry_and_fallback,
)


__all__ = [
    # Spawn functions
    "spawn",
    "spawn_parallel",
    "spawn_parallel_tracked",
    "spawn_parallel_with_recovery",
    "spawn_parallel_with_state_tracking",
    "spawn_sequential",
    "spawn_with_retry_and_fallback",
    # Models
    "SpawnTask",
    "SpawnResult",
    # Circuit breaker
    "CircuitBreaker",
    "get_circuit_breaker",
    # Heartbeat
    "HeartbeatEmitter",
    "HeartbeatEvent",
    "HeartbeatEventType",
    "HeartbeatMonitor",
    "create_heartbeat_emitter",
    "create_heartbeat_monitor",
    # Recovery
    "RecoveryPolicy",
    "RecoveryStrategy",
    "RecoveryResult",
    "RecoverySummary",
    "RecoveryMetrics",
    "RecoveryState",
    "RecoveryStateMachine",
    "RecoveryStateTransition",
    "TaskRecoveryState",
    "ErrorCategory",
    "ErrorClassifier",
    "get_recovery_metrics",
    "reset_recovery_metrics",
]

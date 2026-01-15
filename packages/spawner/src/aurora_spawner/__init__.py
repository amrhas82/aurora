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
from aurora_spawner.spawner import (
    spawn,
    spawn_parallel,
    spawn_sequential,
    spawn_with_retry_and_fallback,
)


__all__ = [
    "spawn",
    "spawn_parallel",
    "spawn_sequential",
    "spawn_with_retry_and_fallback",
    "SpawnTask",
    "SpawnResult",
    "CircuitBreaker",
    "get_circuit_breaker",
    "HeartbeatEmitter",
    "HeartbeatEvent",
    "HeartbeatEventType",
    "HeartbeatMonitor",
    "create_heartbeat_emitter",
    "create_heartbeat_monitor",
]

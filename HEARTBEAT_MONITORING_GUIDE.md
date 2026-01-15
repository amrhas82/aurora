# Heartbeat Monitoring System

## Overview

Aurora's heartbeat mechanism provides real-time status tracking, progress signals, and health checks for agent execution through a thread-safe event stream architecture.

## Architecture

### Components

**HeartbeatEmitter** - Thread-safe event collector
- Collects events during execution via thread-safe queue
- Provides async iteration over event stream
- Supports real-time subscriptions
- Tracks activity for timeout detection

**HeartbeatMonitor** - Health and timeout watchdog
- Monitors for total timeout (no completion within limit)
- Detects activity timeout (no stdout/progress)
- Emits warning signals before timeout
- Provides health check API

**HeartbeatEvent** - Event data structure
- Event type classification
- Timestamp and elapsed time tracking
- Task/agent identification
- Arbitrary metadata support

### Event Types

```python
STARTED          # Process spawned
STDOUT           # Output received
STDERR           # Error output received
PROGRESS         # Progress update
TIMEOUT_WARNING  # Approaching timeout
COMPLETED        # Process finished successfully
FAILED           # Process failed
KILLED           # Process killed by monitor
```

## Usage Examples

### Basic Heartbeat Emission

```python
from aurora_spawner import spawn, create_heartbeat_emitter, SpawnTask

# Create emitter
task_id = "task-123"
emitter = create_heartbeat_emitter(task_id)

# Create task
task = SpawnTask(
    prompt="Analyze this codebase",
    agent="code-reviewer",
    timeout=300
)

# Spawn with heartbeat
result = await spawn(task, heartbeat_emitter=emitter)

# Inspect events
events = emitter.get_all_events()
for event in events:
    print(f"{event.event_type.value}: {event.message}")
```

### Real-Time Event Subscription

```python
from aurora_spawner import create_heartbeat_emitter

emitter = create_heartbeat_emitter("task-456")

# Subscribe to events
def on_event(event):
    elapsed = event.elapsed_since(emitter._start_time)
    print(f"[{elapsed:.1f}s] {event.event_type.value}: {event.message}")

emitter.subscribe(on_event)

# All future events automatically trigger callback
result = await spawn(task, heartbeat_emitter=emitter)
```

### Monitoring with Timeouts

```python
from aurora_spawner import create_heartbeat_emitter, create_heartbeat_monitor

emitter = create_heartbeat_emitter("task-789")
monitor = create_heartbeat_monitor(emitter, timeout=300)

# Start execution in background
task_coro = spawn(task, heartbeat_emitter=emitter)
exec_task = asyncio.create_task(task_coro)

# Monitor until complete or timeout
success, error = await monitor.monitor_until_complete(check_interval=2.0)

if not success:
    print(f"Execution failed: {error}")
    exec_task.cancel()

result = await exec_task
```

### Health Checks

```python
from aurora_spawner import create_heartbeat_emitter, create_heartbeat_monitor

emitter = create_heartbeat_emitter("task-monitor")
monitor = create_heartbeat_monitor(
    emitter,
    total_timeout=300,        # 5 minutes max
    activity_timeout=120,     # 2 minutes without activity
    warning_threshold=0.8     # Warn at 80% of timeout
)

# Periodic health checks
while not done:
    healthy, reason = monitor.check_health()
    if not healthy:
        print(f"Health check failed: {reason}")
        break
    await asyncio.sleep(5)
```

### Streaming Event Iterator

```python
from aurora_spawner import create_heartbeat_emitter

emitter = create_heartbeat_emitter("stream-task")

# Start execution
exec_task = asyncio.create_task(spawn(task, heartbeat_emitter=emitter))

# Stream events as they arrive
async for event in emitter.stream(poll_interval=0.1):
    print(f"{event.event_type.value}: {event.message}")

    if event.event_type in (HeartbeatEventType.COMPLETED,
                            HeartbeatEventType.FAILED):
        break

result = await exec_task
```

### Activity Tracking

```python
emitter = create_heartbeat_emitter("activity-task")

# Check activity metrics
elapsed = emitter.seconds_since_start()
idle = emitter.seconds_since_activity()

print(f"Running for {elapsed:.1f}s, idle for {idle:.1f}s")

# Activity events: STDOUT, PROGRESS
# Last activity timestamp automatically tracked
```

### Custom Event Metadata

```python
emitter = create_heartbeat_emitter("custom-task")

# Emit with custom metadata
emitter.emit(
    HeartbeatEventType.PROGRESS,
    agent_id="code-reviewer",
    message="Analyzing file 5/10",
    file_count=5,
    total_files=10,
    current_file="src/main.py"
)

# Access metadata
latest = emitter.get_latest_event()
progress = latest.metadata.get("file_count", 0)
total = latest.metadata.get("total_files", 0)
```

## Integration with Spawn Functions

### Single Task

```python
from aurora_spawner import spawn, create_heartbeat_emitter

emitter = create_heartbeat_emitter("single-task")
result = await spawn(task, heartbeat_emitter=emitter)

# Events automatically emitted:
# - STARTED when process spawns
# - STDOUT/STDERR on output
# - KILLED if timeout or error pattern
# - COMPLETED/FAILED on finish
```

### Parallel Execution

```python
from aurora_spawner import spawn_parallel, create_heartbeat_emitter

# Create emitter per task
emitters = [create_heartbeat_emitter(f"task-{i}") for i in range(len(tasks))]

# Subscribe to all emitters
for emitter in emitters:
    emitter.subscribe(lambda e: print(f"[{e.task_id}] {e.event_type.value}"))

# Execute with heartbeats
results = await spawn_parallel(
    tasks,
    max_concurrent=5,
    heartbeat_emitter=emitters[0]  # Note: Currently single emitter supported
)
```

### Retry with Fallback

```python
from aurora_spawner import spawn_with_retry_and_fallback, create_heartbeat_emitter

emitter = create_heartbeat_emitter("retry-task")

def on_progress(attempt, max_attempts, status):
    print(f"Attempt {attempt}/{max_attempts}: {status}")

result = await spawn_with_retry_and_fallback(
    task,
    on_progress=on_progress,
    max_retries=2,
    fallback_to_llm=True,
    heartbeat_emitter=emitter  # Note: Need to add this parameter
)
```

## CLI Integration

The `aur spawn` command automatically uses heartbeats internally:

```bash
aur spawn tasks.md --verbose
```

Verbose mode displays heartbeat events:
- Task start/completion status
- Real-time progress updates
- Timeout warnings
- Failure detection

## Event Flow Diagram

```
┌──────────────┐
│   Spawn      │
│   Task       │
└──────┬───────┘
       │
       ▼
┌──────────────┐      emit()      ┌──────────────┐
│  Subprocess  ├─────────────────▶│  Heartbeat   │
│  Execution   │                  │  Emitter     │
└──────────────┘                  └──────┬───────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
                    ▼                    ▼                    ▼
            ┌──────────────┐     ┌──────────────┐    ┌──────────────┐
            │  Real-time   │     │  Heartbeat   │    │   Buffer     │
            │ Subscribers  │     │   Monitor    │    │   (Queue)    │
            └──────────────┘     └──────────────┘    └──────────────┘
```

## Thread Safety

All operations are thread-safe:
- Event emission from subprocess threads
- Subscription callbacks from any thread
- Event retrieval concurrent with emission
- Monitor health checks concurrent with events

Uses:
- `threading.Lock` for queue protection
- `collections.deque` with maxlen for bounded buffer
- Exception isolation in subscriber callbacks

## Performance Characteristics

**Memory**: O(buffer_size) - default 1000 events
**Event emission**: O(1) with lock acquisition
**Event retrieval**: O(n) for full history, O(1) for latest
**Subscriber notification**: O(subscribers) per event

Typical overhead per spawned process:
- Memory: ~100KB for 1000 events
- CPU: <1% for heartbeat emission
- Latency: <1ms per event

## Best Practices

**Buffer Size**: Increase for long-running processes
```python
emitter = HeartbeatEmitter(task_id, buffer_size=5000)
```

**Timeout Configuration**: Scale with task complexity
```python
monitor = create_heartbeat_monitor(
    emitter,
    total_timeout=600,      # 10 minutes for complex tasks
    activity_timeout=180    # 3 minutes idle threshold
)
```

**Subscriber Error Handling**: Isolate failures
```python
def safe_subscriber(event):
    try:
        # Process event
        pass
    except Exception as e:
        logger.error(f"Subscriber error: {e}")

emitter.subscribe(safe_subscriber)
```

**Resource Cleanup**: No explicit cleanup needed
- Emitters are garbage collected when out of scope
- No background threads or resources held
- Subscriber list automatically released

## Troubleshooting

**No Events Received**
- Verify heartbeat_emitter passed to spawn()
- Check emitter.get_all_events() is not empty
- Confirm process actually started (check returncode)

**Subscriber Not Called**
- Subscribe before spawn() execution
- Verify subscriber accepts HeartbeatEvent parameter
- Check for exceptions in subscriber (silently caught)

**Timeout False Positives**
- Increase activity_timeout for bursty output
- Check if STDOUT events are being emitted
- Verify process isn't actually stuck (check stderr)

**Memory Growth**
- Reduce buffer_size for long-running processes
- Clear emitter reference after completion
- Monitor deque size: len(emitter._queue)

## Future Enhancements

- [ ] Multiple emitters for spawn_parallel
- [ ] Persistent event logging to disk
- [ ] Network streaming of events (WebSocket)
- [ ] Prometheus metrics integration
- [ ] Event replay and debugging tools
- [ ] Visual progress dashboard
- [ ] Automated performance profiling

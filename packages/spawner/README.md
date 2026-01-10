# Aurora Spawner

Subprocess spawner for Aurora framework.

## Installation

```bash
pip install aurora-spawner
```

## Usage

```python
from aurora_spawner import spawn, SpawnTask

task = SpawnTask(prompt="Hello world")
result = await spawn(task)
print(result.output)
```

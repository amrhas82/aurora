"""AURORA SOAR Package

Provides agent registry and orchestration capabilities:
- Agent discovery and registration
- Capability-based agent selection
- Agent lifecycle management
- 9-phase SOAR orchestration pipeline
- Headless reasoning mode for autonomous experiments
"""

# Note: Using old import path temporarily to avoid circular dependency during namespace setup
from aurora_soar.agent_registry import AgentInfo, AgentRegistry
from aurora_soar.orchestrator import SOAROrchestrator


__version__ = "0.1.0"
__all__ = ["AgentInfo", "AgentRegistry", "SOAROrchestrator"]

"""
AURORA SOAR Package

Provides agent registry and orchestration capabilities:
- Agent discovery and registration
- Capability-based agent selection
- Agent lifecycle management
"""

from aurora_soar.agent_registry import AgentInfo, AgentRegistry


__version__ = "0.1.0"
__all__ = ["AgentInfo", "AgentRegistry"]

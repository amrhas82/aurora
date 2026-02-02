# Aurora Vision

## Purpose

Aurora is a **memory-first planning and multi-agent orchestration framework** that enhances AI coding assistants with:

- **Cognitive Memory** - ACT-R-based memory model for intelligent code retrieval
- **Systematic Reasoning** - SOAR 9-phase pipeline for goal decomposition
- **Multi-Agent Execution** - CLI-agnostic agent orchestration

## Problem Statement

AI coding assistants lack persistent memory and systematic reasoning. They:
- Forget context between sessions
- Can't prioritize code by usage patterns
- Don't decompose complex goals systematically
- Can't coordinate multiple tools effectively

## Solution

Aurora provides a unified framework that:
1. **Indexes codebases** with cognitive memory (BM25 + ACT-R activation)
2. **Decomposes goals** using SOAR methodology
3. **Orchestrates agents** across multiple CLI tools (Claude, Cursor, Aider, etc.)
4. **Learns patterns** from usage to improve retrieval over time

## Target Users

- **Developers** using AI coding assistants who need better context
- **Teams** coordinating multiple AI tools across projects
- **Power users** who want systematic planning workflows

## Boundaries

**Aurora IS:**
- A CLI tool (`aur` command) and Python library
- Tool-agnostic (works with any CLI-based AI tool)
- Local-first (all data stays on your machine)

**Aurora IS NOT:**
- A replacement for AI coding assistants
- A cloud service
- An IDE plugin (though it can integrate with them)

## Success Metrics

- Memory search: <500ms on 10K+ chunks
- Goal decomposition: <30s with LLM
- CLI startup: <3s for `aur soar`

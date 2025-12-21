# Implementation Tasks: AURORA SOAR Pipeline & Verification (Phase 2)

**Source PRD**: `/home/hamr/PycharmProjects/OneNote/smol/agi-problem/tasks/0003-prd-aurora-soar-pipeline.md`
**Version**: 1.1 (Detailed Sub-Tasks)
**Generated**: December 20, 2025
**Status**: Ready for Implementation
**Dependencies**: Phase 1 (0002-prd-aurora-foundation.md) MUST be complete

---

## Overview

This task list breaks down PRD 0003 (AURORA SOAR Pipeline & Verification) into actionable implementation tasks. Phase 2 implements the 9-phase SOAR orchestrator with multi-stage verification, LLM integration, cost tracking, and agent execution.

**Key Deliverables**:
- 9-phase SOAR orchestrator (Assess → Retrieve → Decompose → Verify → Route → Collect → Synthesize → Record → Respond)
- Verification system (Options A: self-verify, B: adversarial)
- LLM abstraction layer with multi-provider support
- Cost tracking and budget enforcement
- Conversation logging to markdown
- ReasoningChunk full implementation
- Agent execution with parallel support

**Critical Success Criteria**:
- Reasoning accuracy ≥80% on benchmark suite
- Verification catch rate ≥70% of injected errors
- Simple query latency <2s, complex query <10s
- All quality gates passed (≥85% coverage)

---

## Relevant Files

### SOAR Package (`packages/soar/`)
- `packages/soar/src/aurora_soar/orchestrator.py` - Main SOAR orchestrator with 9-phase pipeline coordination
- `packages/soar/src/aurora_soar/phases/__init__.py` - SOAR phases module initialization
- `packages/soar/src/aurora_soar/phases/assess.py` - Phase 1: Complexity assessment (keyword + LLM)
- `packages/soar/src/aurora_soar/phases/retrieve.py` - Phase 2: Context retrieval with budget allocation
- `packages/soar/src/aurora_soar/phases/decompose.py` - Phase 3: Query decomposition with LLM and caching
- `packages/soar/src/aurora_soar/phases/verify.py` - Phase 4: Decomposition verification with retry loop
- `packages/soar/src/aurora_soar/phases/route.py` - Phase 5: Agent routing (placeholder)
- `packages/soar/src/aurora_soar/phases/collect.py` - Phase 6: Agent execution (placeholder)
- `packages/soar/src/aurora_soar/phases/synthesize.py` - Phase 7: Result synthesis (placeholder)
- `packages/soar/src/aurora_soar/phases/record.py` - Phase 8: ACT-R pattern caching (placeholder)
- `packages/soar/src/aurora_soar/phases/respond.py` - Phase 9: Response formatting (placeholder)

### Reasoning Package (`packages/reasoning/`)
- `packages/reasoning/pyproject.toml` - Reasoning package configuration with LLM dependencies
- `packages/reasoning/src/aurora_reasoning/__init__.py` - Package initialization and exports
- `packages/reasoning/src/aurora_reasoning/llm_client.py` - Abstract LLM client interface and implementations
- `packages/reasoning/src/aurora_reasoning/assessment.py` - Complexity assessment logic
- `packages/reasoning/src/aurora_reasoning/decompose.py` - Decomposition logic with JSON validation
- `packages/reasoning/src/aurora_reasoning/verify.py` - Verification logic (Options A/B) with scoring
- `packages/reasoning/src/aurora_reasoning/synthesize.py` - Synthesis logic
- `packages/reasoning/src/aurora_reasoning/prompts/__init__.py` - Prompt templates module
- `packages/reasoning/src/aurora_reasoning/prompts/assess.py` - Complexity assessment prompt
- `packages/reasoning/src/aurora_reasoning/prompts/decompose.py` - Decomposition prompt
- `packages/reasoning/src/aurora_reasoning/prompts/verify_self.py` - Self-verification prompt (Option A)
- `packages/reasoning/src/aurora_reasoning/prompts/verify_adversarial.py` - Adversarial verification prompt (Option B)
- `packages/reasoning/src/aurora_reasoning/prompts/verify_agent_output.py` - Agent output verification prompt
- `packages/reasoning/src/aurora_reasoning/prompts/verify_synthesis.py` - Synthesis verification prompt
- `packages/reasoning/src/aurora_reasoning/prompts/retry_feedback.py` - Retry feedback generation prompt
- `packages/reasoning/src/aurora_reasoning/prompts/examples.py` - Few-shot examples loader

### SOAR Package (`packages/soar/`)
- `packages/soar/src/aurora_soar/orchestrator.py` - Main SOAR orchestrator
- `packages/soar/src/aurora_soar/phases/__init__.py` - SOAR phases module
- `packages/soar/src/aurora_soar/phases/assess.py` - Phase 1: Complexity assessment
- `packages/soar/src/aurora_soar/phases/retrieve.py` - Phase 2: Context retrieval
- `packages/soar/src/aurora_soar/phases/decompose.py` - Phase 3: Query decomposition
- `packages/soar/src/aurora_soar/phases/verify.py` - Phase 4: Decomposition verification
- `packages/soar/src/aurora_soar/phases/route.py` - Phase 5: Agent routing
- `packages/soar/src/aurora_soar/phases/collect.py` - Phase 6: Agent execution
- `packages/soar/src/aurora_soar/phases/synthesize.py` - Phase 7: Result synthesis
- `packages/soar/src/aurora_soar/phases/record.py` - Phase 8: ACT-R pattern caching
- `packages/soar/src/aurora_soar/phases/respond.py` - Phase 9: Response formatting

### Core Package Updates (`packages/core/`)
- `packages/core/src/aurora_core/chunks/reasoning_chunk.py` - Full ReasoningChunk implementation
- `packages/core/src/aurora_core/budget/__init__.py` - Budget tracking module
- `packages/core/src/aurora_core/budget/estimator.py` - Cost estimation
- `packages/core/src/aurora_core/budget/tracker.py` - Budget enforcement
- `packages/core/src/aurora_core/logging/__init__.py` - Logging module
- `packages/core/src/aurora_core/logging/conversation_logger.py` - Conversation logging

### Test Files
- `tests/unit/soar/test_phase_assess.py` - Phase 1 assessment tests (keyword + LLM)
- `tests/unit/soar/test_phase_retrieve.py` - Phase 2 retrieval tests with budget verification
- `tests/unit/reasoning/test_llm_client.py` - LLM client tests
- `tests/unit/reasoning/test_assessment.py` - Assessment logic tests
- `tests/unit/reasoning/test_decompose.py` - Decomposition tests
- `tests/unit/reasoning/test_verify.py` - Verification tests
- `tests/unit/reasoning/test_synthesize.py` - Synthesis tests
- `tests/unit/reasoning/test_prompts.py` - Prompt template tests
- `tests/unit/soar/test_orchestrator.py` - Orchestrator tests
- `tests/unit/soar/test_phase_assess.py` - Assess phase tests
- `tests/unit/soar/test_phase_retrieve.py` - Retrieve phase tests
- `tests/unit/soar/test_phase_decompose.py` - Decompose phase tests
- `tests/unit/soar/test_phase_verify.py` - Verify phase tests
- `tests/unit/soar/test_phase_route.py` - Route phase tests
- `tests/unit/soar/test_phase_collect.py` - Collect phase tests
- `tests/unit/soar/test_phase_synthesize.py` - Synthesize phase tests
- `tests/unit/soar/test_phase_record.py` - Record phase tests
- `tests/unit/soar/test_phase_respond.py` - Respond phase tests
- `tests/unit/core/test_reasoning_chunk.py` - ReasoningChunk tests
- `tests/unit/core/test_cost_estimator.py` - Cost estimator tests
- `tests/unit/core/test_budget_tracker.py` - Budget tracker tests
- `tests/unit/core/test_conversation_logger.py` - Conversation logger tests
- `tests/integration/test_simple_query_e2e.py` - Simple query end-to-end test
- `tests/integration/test_complex_query_e2e.py` - Complex query end-to-end test
- `tests/integration/test_verification_retry.py` - Verification retry flow test
- `tests/integration/test_agent_execution.py` - Agent execution test
- `tests/integration/test_cost_budget.py` - Cost budget enforcement test
- `tests/performance/test_query_benchmarks.py` - Query performance benchmarks
- `tests/fault_injection/test_bad_decomposition.py` - Bad decomposition handling
- `tests/fault_injection/test_agent_failure.py` - Agent failure handling
- `tests/fault_injection/test_llm_timeout.py` - LLM timeout handling
- `tests/fault_injection/test_budget_exceeded.py` - Budget exceeded handling
- `tests/fault_injection/test_malformed_output.py` - Malformed output handling
- `tests/fixtures/benchmark_queries.json` - Benchmark test queries
- `tests/fixtures/calibration_examples.json` - Few-shot calibration examples

### Configuration Files
- `packages/reasoning/examples/example_decompositions.json` - Example decompositions for prompt templates
- `packages/reasoning/examples/example_verifications.json` - Example verifications for calibration

---

## Notes

### Testing Strategy
- Unit tests isolate individual SOAR phases using mocks for LLM and agents
- Integration tests verify end-to-end flows with real LLM calls (use test API keys)
- Performance benchmarks establish latency baselines for simple/complex queries
- Fault injection tests verify error handling and retry logic
- All tests use pytest framework with coverage tracking (target: ≥85%)

### Architectural Patterns
- Abstract LLM interface for provider independence (Anthropic, OpenAI, Ollama)
- Phase separation for testability (each SOAR phase is isolated module)
- Verification checkpoint pattern for quality gates
- Retry with feedback loop for recoverable failures
- Parallel execution using asyncio for independent subgoals
- Cost tracking integrated at each LLM call site

### Performance Considerations
- Keyword assessment bypasses LLM for 60-70% of queries
- Verification Options A vs B selected by complexity (cost vs accuracy tradeoff)
- Parallel agent execution reduces latency for independent subgoals
- Conversation logs written asynchronously (don't block response)
- Budget checks happen before expensive operations

### Error Handling
- Validation errors (user-fixable): clear messages with fix suggestions
- System errors (transient): retry with exponential backoff (max 3 attempts)
- Fatal errors (unrecoverable): return partial results with explanations
- Graceful degradation: always return best-effort results, never fail silently
- Verification failures trigger retry loop (max 2 retries with feedback)

---

## Tasks

- [x] 1.0 Reasoning Package - LLM Integration & Prompt System
  - [x] 1.1 Create reasoning package structure with pyproject.toml and dependencies (anthropic, openai, ollama-python)
  - [x] 1.2 Define abstract LLMClient interface in packages/reasoning/src/aurora_reasoning/llm_client.py (generate, generate_json methods)
  - [x] 1.3 Implement AnthropicClient with API key from environment, error handling, and rate limiting
  - [x] 1.4 Implement OpenAIClient with API key from environment, error handling, and rate limiting
  - [x] 1.5 Implement OllamaClient for local model support with configurable endpoint
  - [x] 1.6 Add LLM response parsing and JSON extraction (handle markdown code blocks, extract JSON from text)
  - [x] 1.7 Implement retry logic with exponential backoff (100ms, 200ms, 400ms) for transient API errors
  - [x] 1.8 Add token counting and cost tracking hooks in each LLM client (track input/output tokens)
  - [x] 1.9 Create prompt template base class in packages/reasoning/src/aurora_reasoning/prompts/__init__.py
  - [x] 1.10 Implement few-shot examples loader in packages/reasoning/src/aurora_reasoning/prompts/examples.py
  - [x] 1.11 Create assess prompt template in packages/reasoning/src/aurora_reasoning/prompts/assess.py (Tier 2 LLM verification)
  - [x] 1.12 Create decompose prompt template in packages/reasoning/src/aurora_reasoning/prompts/decompose.py (with JSON schema)
  - [x] 1.13 Create verify_self prompt template in packages/reasoning/src/aurora_reasoning/prompts/verify_self.py (Option A)
  - [x] 1.14 Create verify_adversarial prompt template in packages/reasoning/src/aurora_reasoning/prompts/verify_adversarial.py (Option B)
  - [x] 1.15 Create verify_agent_output prompt template in packages/reasoning/src/aurora_reasoning/prompts/verify_agent_output.py
  - [x] 1.16 Create verify_synthesis prompt template in packages/reasoning/src/aurora_reasoning/prompts/verify_synthesis.py
  - [x] 1.17 Create retry_feedback prompt template in packages/reasoning/src/aurora_reasoning/prompts/retry_feedback.py
  - [x] 1.18 Add JSON schema enforcement to all prompts (explicit instructions for JSON-only output, no markdown)
  - [x] 1.19 Create example decompositions in packages/reasoning/examples/example_decompositions.json (simple, medium, complex)
  - [x] 1.20 Create calibration examples in packages/reasoning/examples/example_verifications.json for score calibration
  - [x] 1.21 Write unit tests for LLMClient interface (tests/unit/reasoning/test_llm_client.py)
  - [x] 1.22 Write unit tests for each LLM provider (mock API responses, test error handling)
  - [x] 1.23 Write unit tests for prompt templates (tests/unit/reasoning/test_prompts.py) with example rendering
  - [x] 1.24 Test few-shot example scaling by complexity (0/2/4/6 examples for simple/medium/complex/critical)
  - [x] 1.25 Verify JSON parsing works 100% of time with test prompts (no markdown, no extra text)

- [x] 2.0 SOAR Orchestrator - Phase 1-2 (Assess & Retrieve)
  - [x] 2.1 Create SOAR package phase structure with __init__.py files
  - [x] 2.2 Implement SOAROrchestrator skeleton in packages/soar/src/aurora_soar/orchestrator.py with execute() method
  - [x] 2.3 Add orchestrator initialization (store, agent_registry, config, reasoning_llm, solving_llm)
  - [x] 2.4 Implement keyword-based complexity classifier in packages/soar/src/aurora_soar/phases/assess.py (_assess_tier1_keyword)
  - [x] 2.5 Create keyword lists for complexity levels (simple, medium, complex, critical) based on PRD Appendix G
  - [x] 2.6 Implement keyword scoring algorithm (matches / total_keywords, with confidence calculation)
  - [x] 2.7 Implement LLM-based complexity verification in assess.py (_assess_tier2_llm) for borderline cases
  - [x] 2.8 Add decision logic: use keyword if confidence ≥0.8 AND score not in [0.4, 0.6], else use LLM
  - [x] 2.9 Implement context retrieval in packages/soar/src/aurora_soar/phases/retrieve.py (_retrieve_context)
  - [x] 2.10 Add budget allocation by complexity (SIMPLE: 5, MEDIUM: 10, COMPLEX: 15, CRITICAL: 20 chunks)
  - [x] 2.11 Integrate with Phase 1 Store.retrieve_by_activation() method (keyword-based for Phase 2)
  - [x] 2.12 Add retrieval result formatting (code_chunks, reasoning_chunks, timing metadata)
  - [x] 2.13 Implement early exit for SIMPLE queries (bypass decomposition, go directly to solving LLM)
  - [x] 2.14 Write unit tests for keyword classifier (tests/unit/soar/test_phase_assess.py)
  - [x] 2.15 Write unit tests for LLM assessment (mock LLM responses, test borderline cases)
  - [x] 2.16 Write unit tests for context retrieval (tests/unit/soar/test_phase_retrieve.py)
  - [x] 2.17 Test budget allocation logic (verify correct chunk counts by complexity)
  - [x] 2.18 Verify keyword assessment cost optimization (≥60% queries use keyword only)

- [x] 3.0 SOAR Orchestrator - Phase 3-4 (Decompose & Verify)
  - [x] 3.1 Implement decomposition logic in packages/reasoning/src/aurora_reasoning/decompose.py
  - [x] 3.2 Create decomposition method that calls reasoning LLM with decompose prompt template
  - [x] 3.3 Add context injection (retrieved chunks, available agents from registry)
  - [x] 3.4 Implement few-shot example selection by complexity (0/2/4/6 examples)
  - [x] 3.5 Add JSON schema validation for decomposition output (verify all required fields present)
  - [x] 3.6 Implement decompose phase wrapper in packages/soar/src/aurora_soar/phases/decompose.py
  - [x] 3.7 Add decomposition result caching (cache by query hash to avoid re-decomposing identical queries)
  - [x] 3.8 Implement verification logic in packages/reasoning/src/aurora_reasoning/verify.py
  - [x] 3.9 Create verify_decomposition method with Option A (self-verification) support
  - [x] 3.10 Create verify_decomposition method with Option B (adversarial verification) support
  - [x] 3.11 Implement scoring calculation: 0.4*completeness + 0.2*consistency + 0.2*groundedness + 0.2*routability
  - [x] 3.12 Implement verdict logic (PASS: ≥0.7, RETRY: 0.5-0.7 & retry_count<2, FAIL: <0.5 or retry_count≥2)
  - [x] 3.13 Implement retry loop in packages/soar/src/aurora_soar/phases/verify.py with feedback generation
  - [x] 3.14 Add retry feedback generation using retry_feedback prompt template
  - [x] 3.15 Inject retry feedback into decomposition prompt for next attempt
  - [x] 3.16 Implement verification phase wrapper that calls reasoning.verify() with selected option
  - [x] 3.17 Add verification option selection logic (MEDIUM→Option A, COMPLEX→Option B)
  - [x] 3.18 Write unit tests for decomposition logic (tests/unit/reasoning/test_decompose.py)
  - [x] 3.19 Write unit tests for verification logic (tests/unit/reasoning/test_verify.py) with Options A and B
  - [x] 3.20 Write unit tests for decompose phase (tests/unit/soar/test_phase_decompose.py)
  - [x] 3.21 Write unit tests for verify phase (tests/unit/soar/test_phase_verify.py)
  - [x] 3.22 Test retry loop behavior (mock low scores, verify retry with feedback, verify max 2 retries)
  - [x] 3.23 Test verdict logic (verify correct pass/retry/fail decisions)
  - [ ] 3.24 Create fault injection test for bad decomposition (tests/fault_injection/test_bad_decomposition.py)

- [ ] 4.0 SOAR Orchestrator - Phase 5-6 (Route & Collect)
  - [ ] 4.1 Implement routing logic in packages/soar/src/aurora_soar/phases/route.py (_route_subgoals)
  - [ ] 4.2 Add agent lookup from registry (check if suggested agent exists)
  - [ ] 4.3 Implement capability-based agent search if suggested agent not found
  - [ ] 4.4 Add fallback to llm-executor agent if no suitable agent found (with warning log)
  - [ ] 4.5 Implement routing validation (verify all subgoals assigned, no circular dependencies)
  - [ ] 4.6 Add execution order parsing from decomposition (execution_order, parallelizable arrays)
  - [ ] 4.7 Implement agent execution in packages/soar/src/aurora_soar/phases/collect.py (_execute_agents)
  - [ ] 4.8 Add sequential execution logic (wait for dependencies before starting subgoal)
  - [ ] 4.9 Implement parallel execution using asyncio for parallelizable subgoals
  - [ ] 4.10 Add per-agent timeout handling (default 60s, configurable)
  - [ ] 4.11 Add overall query timeout handling (default 5 minutes, configurable)
  - [ ] 4.12 Implement agent response format validation (verify summary, data, confidence fields present)
  - [ ] 4.13 Add agent output verification (call reasoning.verify_agent_output for each response)
  - [ ] 4.14 Implement retry logic for failed agent outputs (max 2 retries, try different agent if available)
  - [ ] 4.15 Add user interaction tracking (capture agent questions and user responses in metadata)
  - [ ] 4.16 Implement graceful degradation (mark subgoal as partial success if agent fails after retries)
  - [ ] 4.17 Add critical subgoal detection (abort entire query if critical subgoal fails)
  - [ ] 4.18 Implement agent execution metadata collection (tools_used, duration_ms, model_used)
  - [ ] 4.19 Write unit tests for routing logic (tests/unit/soar/test_phase_route.py)
  - [ ] 4.20 Test agent lookup and fallback behavior (verify fallback to llm-executor)
  - [ ] 4.21 Write unit tests for agent execution (tests/unit/soar/test_phase_collect.py)
  - [ ] 4.22 Test parallel execution (verify concurrent execution, measure speedup vs sequential)
  - [ ] 4.23 Test timeout handling (simulate agent timeout, verify graceful cancellation)
  - [ ] 4.24 Test agent output verification (mock low scores, verify retry logic)
  - [ ] 4.25 Create fault injection test for agent failure (tests/fault_injection/test_agent_failure.py)
  - [ ] 4.26 Create integration test for agent execution flow (tests/integration/test_agent_execution.py)

- [ ] 5.0 SOAR Orchestrator - Phase 7-9 (Synthesize, Record, Respond)
  - [ ] 5.1 Implement synthesis logic in packages/reasoning/src/aurora_reasoning/synthesize.py
  - [ ] 5.2 Create synthesis method that gathers all agent output.summary fields
  - [ ] 5.3 Add synthesis prompt building (original query, agent summaries, decomposition goal)
  - [ ] 5.4 Implement synthesis LLM call (natural language output, NOT JSON)
  - [ ] 5.5 Add traceability validation (ensure every claim links to agent summary)
  - [ ] 5.6 Implement synthesis verification (call reasoning.verify_synthesis)
  - [ ] 5.7 Add synthesis retry loop (max 2 retries with feedback if score <0.7)
  - [ ] 5.8 Implement synthesis phase wrapper in packages/soar/src/aurora_soar/phases/synthesize.py
  - [ ] 5.9 Add metadata aggregation (subgoals_completed, total_files_modified, user_interactions_count)
  - [ ] 5.10 Implement full ReasoningChunk in packages/core/src/aurora_core/chunks/reasoning_chunk.py
  - [ ] 5.11 Add ReasoningChunk schema fields (pattern, complexity, subgoals, tools_used, tool_sequence, success_score)
  - [ ] 5.12 Implement to_json and from_json methods for ReasoningChunk following PRD schema
  - [ ] 5.13 Add validation logic for ReasoningChunk (success_score range 0-1, required fields)
  - [ ] 5.14 Implement pattern caching logic in packages/soar/src/aurora_soar/phases/record.py (_record_pattern)
  - [ ] 5.15 Add caching policy (score ≥0.5: cache, score ≥0.8: mark as pattern, score <0.5: skip)
  - [ ] 5.16 Implement learning updates (success: +0.2 activation, partial: ±0.05, failure: -0.1)
  - [ ] 5.17 Add ReasoningChunk storage to ACT-R memory via Store.save_chunk()
  - [ ] 5.18 Implement response formatting in packages/soar/src/aurora_soar/phases/respond.py (_format_response)
  - [ ] 5.19 Add QUIET verbosity output (single line with score)
  - [ ] 5.20 Add NORMAL verbosity output (phase progress with key metrics)
  - [ ] 5.21 Add VERBOSE verbosity output (full trace with detailed metadata)
  - [ ] 5.22 Add JSON verbosity output (structured JSON logs for each phase)
  - [ ] 5.23 Implement response structure (answer, confidence, overall_score, reasoning_trace, metadata)
  - [ ] 5.24 Write unit tests for synthesis logic (tests/unit/reasoning/test_synthesize.py)
  - [ ] 5.25 Write unit tests for ReasoningChunk (tests/unit/core/test_reasoning_chunk.py)
  - [ ] 5.26 Write unit tests for record phase (tests/unit/soar/test_phase_record.py)
  - [ ] 5.27 Write unit tests for respond phase (tests/unit/soar/test_phase_respond.py)
  - [ ] 5.28 Test all verbosity levels (verify correct output format for quiet/normal/verbose/JSON)
  - [ ] 5.29 Test pattern caching logic (verify caching thresholds, verify learning updates)
  - [ ] 5.30 Verify ReasoningChunk integrates with Store (save/retrieve round-trip test)

- [ ] 6.0 Cost Tracking & Budget Enforcement
  - [ ] 6.1 Create budget module in packages/core/src/aurora_core/budget/__init__.py
  - [ ] 6.2 Implement CostEstimator class in packages/core/src/aurora_core/budget/estimator.py
  - [ ] 6.3 Add base cost constants (SIMPLE: $0.001 Haiku, MEDIUM: $0.05 Sonnet, COMPLEX: $0.50 Opus)
  - [ ] 6.4 Add complexity multipliers (SIMPLE: 1.0, MEDIUM: 3.0, COMPLEX: 5.0)
  - [ ] 6.5 Implement estimate_query_cost method (base_cost × complexity_multiplier × token_factor)
  - [ ] 6.6 Add token estimation (approximate tokens from query length, context size)
  - [ ] 6.7 Implement BudgetTracker class in packages/core/src/aurora_core/budget/tracker.py
  - [ ] 6.8 Add budget tracker file structure (~/.aurora/budget_tracker.json)
  - [ ] 6.9 Implement budget loading and initialization (create if not exists, load if exists)
  - [ ] 6.10 Add period management (monthly periods, auto-reset on new month)
  - [ ] 6.11 Implement check_budget method (pre-query budget check before expensive operations)
  - [ ] 6.12 Add soft limit warning at 80% (log warning, allow query)
  - [ ] 6.13 Add hard limit blocking at 100% (reject query, return budget status message)
  - [ ] 6.14 Implement record_cost method (track actual cost after query execution)
  - [ ] 6.15 Add get_status method (return current budget state with consumed/remaining/limit)
  - [ ] 6.16 Integrate budget checks into orchestrator execute() method (check before Phase 1)
  - [ ] 6.17 Add cost tracking hooks at each LLM call site (track tokens, calculate cost)
  - [ ] 6.18 Implement cost aggregation in orchestrator (sum all LLM calls for total query cost)
  - [ ] 6.19 Add cost metadata to response (estimated_cost_usd, actual_cost_usd, tokens_used breakdown)
  - [ ] 6.20 Write unit tests for CostEstimator (tests/unit/core/test_cost_estimator.py)
  - [ ] 6.21 Test cost estimation for different query complexities and lengths
  - [ ] 6.22 Write unit tests for BudgetTracker (tests/unit/core/test_budget_tracker.py)
  - [ ] 6.23 Test budget enforcement (verify soft limit warning, hard limit blocking)
  - [ ] 6.24 Test period management (verify monthly reset, carry-over handling)
  - [ ] 6.25 Create integration test for cost budget flow (tests/integration/test_cost_budget.py)
  - [ ] 6.26 Create fault injection test for budget exceeded (tests/fault_injection/test_budget_exceeded.py)

- [ ] 7.0 Conversation Logging & Verbosity System
  - [ ] 7.1 Create logging module in packages/core/src/aurora_core/logging/__init__.py
  - [ ] 7.2 Implement ConversationLogger class in packages/core/src/aurora_core/logging/conversation_logger.py
  - [ ] 7.3 Add log path configuration (~/.aurora/logs/conversations/YYYY/MM/)
  - [ ] 7.4 Implement directory creation (ensure year/month directories exist)
  - [ ] 7.5 Add keyword extraction for filename generation (extract 2 keywords from query)
  - [ ] 7.6 Implement filename generation (keyword1-keyword2-YYYY-MM-DD.md format)
  - [ ] 7.7 Add duplicate filename handling (append -2, -3, etc. if file exists)
  - [ ] 7.8 Implement markdown log formatting (_format_log method)
  - [ ] 7.9 Add front matter with query ID, timestamp, and user query
  - [ ] 7.10 Add phase sections (Phase 1-9 with JSON blocks for phase data)
  - [ ] 7.11 Add execution summary section (duration, score, cached status)
  - [ ] 7.12 Implement log_interaction method (write full SOAR interaction to file)
  - [ ] 7.13 Add async/background writing (don't block response on log write)
  - [ ] 7.14 Implement error handling for log writes (log to stderr if file write fails)
  - [ ] 7.15 Add log rotation (optional: limit log files per month, archive old logs)
  - [ ] 7.16 Integrate conversation logging into orchestrator respond phase
  - [ ] 7.17 Add config option to enable/disable conversation logging
  - [ ] 7.18 Add verbosity level configuration (default: QUIET, configurable via CLI/config)
  - [ ] 7.19 Write unit tests for ConversationLogger (tests/unit/core/test_conversation_logger.py)
  - [ ] 7.20 Test filename generation (verify keyword extraction, duplicate handling)
  - [ ] 7.21 Test markdown formatting (verify all sections present, valid JSON blocks)
  - [ ] 7.22 Test async writing (verify non-blocking behavior)
  - [ ] 7.23 Verify conversation logs can be re-parsed (JSON blocks valid, markdown well-formed)

- [ ] 8.0 End-to-End Integration & Testing
  - [ ] 8.1 Implement orchestrator execute() main flow (tie together all 9 phases)
  - [ ] 8.2 Add phase execution tracking (capture phase outputs, timing, errors)
  - [ ] 8.3 Implement error handling and graceful degradation at orchestrator level
  - [ ] 8.4 Add orchestrator unit tests (tests/unit/soar/test_orchestrator.py) with mocked phases
  - [ ] 8.5 Create simple query E2E test (tests/integration/test_simple_query_e2e.py)
  - [ ] 8.6 Test simple query bypasses decomposition (verify assess → retrieve → solve → respond path)
  - [ ] 8.7 Verify simple query latency <2s
  - [ ] 8.8 Create complex query E2E test (tests/integration/test_complex_query_e2e.py)
  - [ ] 8.9 Test complex query uses full pipeline (verify all 9 phases execute)
  - [ ] 8.10 Verify complex query uses adversarial verification (Option B)
  - [ ] 8.11 Verify complex query latency <10s
  - [ ] 8.12 Create verification retry test (tests/integration/test_verification_retry.py)
  - [ ] 8.13 Test verification catches incomplete decomposition and triggers retry
  - [ ] 8.14 Verify retry includes feedback from previous attempt
  - [ ] 8.15 Create benchmark query suite in tests/fixtures/benchmark_queries.json
  - [ ] 8.16 Add queries covering all complexity levels and domains
  - [ ] 8.17 Create performance benchmark tests (tests/performance/test_query_benchmarks.py)
  - [ ] 8.18 Benchmark all queries in suite, measure latency and cost
  - [ ] 8.19 Verify performance targets met (simple <2s, complex <10s)
  - [ ] 8.20 Create fault injection test for LLM timeout (tests/fault_injection/test_llm_timeout.py)
  - [ ] 8.21 Create fault injection test for malformed output (tests/fault_injection/test_malformed_output.py)
  - [ ] 8.22 Run full test suite and verify ≥85% coverage for reasoning/ and soar/ packages
  - [ ] 8.23 Run fault injection tests and verify error handling works correctly
  - [ ] 8.24 Profile memory usage (verify <100MB for 10K cached reasoning patterns)

- [ ] 9.0 Documentation & Quality Assurance
  - [ ] 9.1 Add docstrings to all public classes and methods in reasoning package (Google style)
  - [ ] 9.2 Add docstrings to all SOAR phases (document inputs, outputs, side effects)
  - [ ] 9.3 Add docstrings to cost tracking and logging modules
  - [ ] 9.4 Create SOAR architecture documentation with phase flow diagram
  - [ ] 9.5 Document verification checkpoint logic with score thresholds
  - [ ] 9.6 Document agent response format and integration guide
  - [ ] 9.7 Create cost tracking guide (explain budgets, limits, estimation)
  - [ ] 9.8 Create troubleshooting guide for common errors (verification failures, agent timeouts, budget issues)
  - [ ] 9.9 Add examples directory with sample queries and expected outputs
  - [ ] 9.10 Create prompt engineering guide (explain few-shot scaling, JSON enforcement)
  - [ ] 9.11 Run mypy type checking (verify 0 errors in strict mode)
  - [ ] 9.12 Run ruff linting (verify 0 critical issues)
  - [ ] 9.13 Run bandit security scan (verify 0 high/critical vulnerabilities)
  - [ ] 9.14 Generate test coverage report (verify ≥85% for reasoning/ and soar/)
  - [ ] 9.15 Review all prompt templates (verify JSON-only output, no markdown)
  - [ ] 9.16 Validate verification calibration (test with known good/bad decompositions)
  - [ ] 9.17 Run performance profiling (identify bottlenecks, optimize if needed)
  - [ ] 9.18 Conduct code review (2+ reviewers, focus on verification logic and error handling)
  - [ ] 9.19 Conduct security audit (review API key handling, input validation, output sanitization)
  - [ ] 9.20 Update root README.md with Phase 2 features and examples
  - [ ] 9.21 Create Phase 3 readiness checklist (verify ReasoningChunk schema stable, activation hooks in place)

- [ ] 10.0 Delivery Verification & Phase Completion
  - [ ] 10.1 Verify all 9 SOAR phases implemented and tested
  - [ ] 10.2 Verify Options A and B verification operational
  - [ ] 10.3 Verify keyword + LLM complexity assessment works (test with benchmark queries)
  - [ ] 10.4 Verify agent routing and execution reliable (test with multiple agents)
  - [ ] 10.5 Verify cost tracking and budget enforcement functional (test soft/hard limits)
  - [ ] 10.6 Verify ReasoningChunk fully implemented and integrates with Store
  - [ ] 10.7 Verify conversation logging operational (check log files created correctly)
  - [ ] 10.8 Verify all unit tests pass with ≥85% coverage
  - [ ] 10.9 Verify all integration tests pass (5 scenarios from PRD Section 6.3)
  - [ ] 10.10 Verify performance benchmarks met (simple <2s, complex <10s)
  - [ ] 10.11 Verify fault injection tests pass (5 scenarios from PRD Section 7.4)
  - [ ] 10.12 Verify reasoning accuracy ≥80% on benchmark suite
  - [ ] 10.13 Verify verification catch rate ≥70% for injected errors
  - [ ] 10.14 Verify score calibration ≥0.7 correlation with correctness
  - [ ] 10.15 Run full CI/CD pipeline and verify all quality gates pass
  - [ ] 10.16 Verify all documentation complete with examples
  - [ ] 10.17 Conduct final code review (ensure all PR feedback addressed)
  - [ ] 10.18 Conduct final security audit (verify no sensitive data leaks)
  - [ ] 10.19 Tag Phase 2 release (v0.2.0) in git with release notes
  - [ ] 10.20 Update project roadmap and prepare Phase 3 dependencies document

---

**Implementation Complete**: Phase 2 is ready for Phase 3 (Advanced Memory Features) when all tasks above are checked off and delivery verification passes.

**Estimated Effort**: 180-220 hours (average 18-22 sub-tasks per parent task × 2-3 hours per sub-task × 10 parent tasks)

**Critical Path**: Tasks 1.0 → 2.0 → 3.0 → 4.0 → 5.0 must be sequential. Tasks 6.0 and 7.0 can proceed in parallel with tasks 4.0-5.0.

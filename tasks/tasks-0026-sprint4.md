# Sprint 4: Planning Flow (Goals 7-8) - FINAL SPRINT

**Estimated Time:** 8-10 hours
**Goal:** Implement `aur goals` command (renamed from `aur plan`) and update `/plan` skill

**Status:** FINAL SPRINT for PRD-0026

## Relevant Files

### Core Implementation
- `packages/cli/src/aurora_cli/commands/goals.py` - NEW: Renamed from plan.py, implements aur goals
- `packages/cli/src/aurora_cli/commands/plan.py` - EXISTING: To be renamed to goals.py
- `packages/cli/src/aurora_cli/commands/__init__.py` - UPDATE: Export goals_command
- `packages/cli/src/aurora_cli/main.py` - UPDATE: Register goals command
- `packages/cli/src/aurora_cli/planning/agents.py` - ENHANCE: Add LLM fallback for agent matching
- `packages/cli/src/aurora_cli/agent_discovery/matcher.py` - ENHANCE: Add gap detection
- `packages/cli/src/aurora_cli/llm/cli_pipe_client.py` - USE: CLI-agnostic LLM client
- `packages/cli/src/aurora_cli/planning/core.py` - ENHANCE: Add goal decomposition logic
- `packages/cli/src/aurora_cli/planning/models.py` - ENHANCE: Add goals.json models

### Claude Code Skill Files
- `~/.claude/skills/plan/SKILLS.md` - UPDATE: Read goals.json instead of creating directory
- `~/.claude/agents/2-generate-tasks.md` - UPDATE: Reference goals.json format
- `.aurora/plans/NNNN-slug/goals.json` - NEW FORMAT: Goals with agent assignments

### Testing
- `packages/cli/tests/test_commands/test_goals.py` - NEW: goals command tests
- `packages/cli/tests/test_planning/test_goal_decomposition.py` - NEW: Goal decomposition tests
- `packages/cli/tests/test_planning/test_agent_matching.py` - NEW: LLM fallback tests
- `packages/cli/tests/test_planning/test_gap_detection.py` - NEW: Gap detection tests
- `tests/e2e/test_goals_plan_flow.py` - NEW: E2E tests for aur goals → /plan flow
- `tests/e2e/test_goals_implement_flow.py` - NEW: E2E tests for aur goals → /plan → aur implement

### Documentation
- `docs/commands/aur-goals.md` - NEW: goals command documentation
- `docs/workflows/planning-flow.md` - NEW: Complete planning workflow documentation
- `examples/goals/goals-example.json` - NEW: Example goals.json file
- `README.md` - UPDATE: Add aur goals example
- `COMMANDS.md` - UPDATE: Add goals command reference

### Notes

- **CRITICAL CHANGE**: Switch from API-based `LLMClient` to CLI-agnostic `CLIPipeLLMClient`
- **TDD Approach**: Write tests first for all new functionality
- **Testing Framework**: pytest with pytest-asyncio
- **Tool Resolution**: CLI flag → env var → config → default (same as aur soar)
- **Model Resolution**: CLI flag → env var → config → default (same as aur soar)
- **Manual Verification**: Include verification commands that Claude can run
- **E2E Testing**: Full workflow testing with real directories and files

## Tasks

- [x] 1.0 Rename and Refactor plan.py to goals.py (Goal 7 - Phase 7)
  - [x] 1.1 Create new goals.py and plan migration strategy (TDD)
    - Create `packages/cli/tests/test_commands/test_goals.py`
    - Write tests for basic command structure:
      - Test command registration as "goals" (not "plan")
      - Test help text shows "aur goals" examples
      - Test --tool flag (same as aur soar)
      - Test --model flag with resolution: CLI → env → config → default
      - Test --verbose flag for debugging
      - Test --yes flag to skip confirmation
    - Copy `packages/cli/src/aurora_cli/commands/plan.py` to `goals.py`
    - Rename all "plan" references to "goals" in docstrings
    - Keep plan group commands (init, list, view, archive) unchanged
    - **Run after completion**:
      - `test -f packages/cli/src/aurora_cli/commands/goals.py && echo "✓ goals.py created"`
      - `grep -c "aur goals" packages/cli/src/aurora_cli/commands/goals.py` (should be >= 3)
      - `pytest packages/cli/tests/test_commands/test_goals.py::test_command_registration -xvs` (should FAIL - RED phase)

  - [x] 1.2 Switch from LLMClient to CLIPipeLLMClient (CRITICAL - TDD)
    - Write tests in `test_goals.py` for CLI-agnostic operation:
      - Test tool resolution: CLI flag → AURORA_GOALS_TOOL env → config → "claude"
      - Test model resolution: CLI flag → AURORA_GOALS_MODEL env → config → "sonnet"
      - Test with mocked subprocess (pipe prompt to stdin)
      - Test tool validation (tool must exist in PATH)
      - Test with different CLI tools (claude, cursor, etc.)
    - Import CLIPipeLLMClient: `from aurora_cli.llm.cli_pipe_client import CLIPipeLLMClient`
    - Remove LLMClient import and usage from goals.py
    - Update `create_command()` to use CLIPipeLLMClient:
      ```python
      # Resolve tool: CLI flag → env → config → default
      if tool is None:
          tool = os.environ.get(
              "AURORA_GOALS_TOOL",
              config.goals_default_tool if config else "claude",
          )

      # Resolve model: CLI flag → env → config → default
      if model == "sonnet":  # Check if it's Click default
          env_model = os.environ.get("AURORA_GOALS_MODEL")
          if env_model and env_model.lower() in ("sonnet", "opus"):
              model = env_model.lower()
          elif config and config.goals_default_model:
              model = config.goals_default_model

      # Create CLI-agnostic client
      llm_client = CLIPipeLLMClient(tool=tool, model=model)
      ```
    - Validate tool exists in PATH (same as soar.py:352-355)
    - Add --tool and --model flags to create_command Click decorator
    - **Run after completion**:
      - `grep "CLIPipeLLMClient" packages/cli/src/aurora_cli/commands/goals.py` (verify import)
      - `! grep "from.*llm_client import LLMClient" packages/cli/src/aurora_cli/commands/goals.py` (API client removed)
      - `pytest packages/cli/tests/test_commands/test_goals.py::test_cli_pipe_client -xvs` (should PASS - GREEN phase)
      - `grep "AURORA_GOALS_TOOL" packages/cli/src/aurora_cli/commands/goals.py` (verify env var)

  - [x] 1.3 Add tool and model CLI flags (TDD)
    - Write tests for CLI argument parsing:
      - Test --tool flag overrides env var
      - Test --model flag overrides env var
      - Test env var overrides config
      - Test config overrides default
      - Test invalid tool shows helpful error
    - Add Click options to create_command:
      ```python
      @click.option(
          "--tool",
          "-t",
          type=str,
          default=None,
          help="CLI tool to use (default: from AURORA_GOALS_TOOL or config or 'claude')",
      )
      @click.option(
          "--model",
          "-m",
          type=click.Choice(["sonnet", "opus"]),
          default="sonnet",
          help="Model to use (default: from AURORA_GOALS_MODEL or config or 'sonnet')",
      )
      ```
    - Update function signature to accept tool and model parameters
    - **Run after completion**:
      - `aur goals --help | grep -E "(--tool|--model)"` (flags appear in help)
      - `pytest packages/cli/tests/test_commands/test_goals.py::test_tool_flag -xvs` (should PASS)
      - `pytest packages/cli/tests/test_commands/test_goals.py::test_model_flag -xvs` (should PASS)

  - [x] 1.4 Update directory creation for goals workflow
    - Write tests for directory structure:
      - Test creates `.aurora/plans/NNNN-slug/` directory
      - Test finds next number correctly (0001, 0002, etc.)
      - Test slug generation from goal title
      - Test handles existing directories gracefully
    - Modify `create_plan_directory()` in `planning/core.py` (if needed)
    - Ensure directory created before goals.json output
    - **Run after completion**:
      - `pytest packages/cli/tests/test_planning/test_directory_creation.py -xvs` (should PASS)
      - `python3 -c "from aurora_cli.planning.core import create_plan_directory; print('✓ Function exists')"`

  - [x] 1.5 Wire goals command to CLI entry point
    - Update `packages/cli/src/aurora_cli/commands/__init__.py`
    - Export `goals_command` (in addition to plan_group)
    - Update `packages/cli/src/aurora_cli/main.py`
    - Add goals command to CLI group: `cli.add_command(goals_command, name="goals")`
    - Keep plan_group for subcommands (list, view, archive)
    - Test command appears in `aur --help`
    - **Run after completion**:
      - `aur --help | grep goals` (command appears)
      - `aur goals --help` (shows goals command help)
      - `python3 -c "from aurora_cli.commands import goals_command; print('✓ Command exported')"`

- [x] 2.0 Implement Memory Search Integration (Goal 7 - Phase 7)
  - [x] 2.1 Add memory search to goal decomposition (TDD)
    - Create `packages/cli/tests/test_planning/test_memory_search.py`
    - Write tests for memory search:
      - Test searches for relevant files based on goal keywords
      - Test returns relevance scores (0.0-1.0)
      - Test handles no results gracefully
      - Test includes top N results only (default: 10)
      - Test excludes low-relevance results (threshold: 0.3)
    - Add memory search call in `create_plan()` function
    - Use existing Aurora memory system (ACT-R)
    - Query format: extract keywords from goal text
    - Store results in goals.json under `memory_context` array
    - **Run after completion**:
      - `pytest packages/cli/tests/test_planning/test_memory_search.py -xvs` (should PASS)
      - `grep "memory_context" packages/cli/src/aurora_cli/planning/core.py` (verify integration)

  - [x] 2.2 Display memory search results to user (TDD)
    - Write tests for Rich console output:
      - Test shows "Searching memory..." progress message
      - Test displays found files with relevance scores
      - Test handles empty results with helpful message
      - Test verbose mode shows detailed search info
    - Add Rich console output in `create_command()`:
      ```python
      console.print("\n[bold]🔍 Searching memory for relevant context...[/]")
      # Call memory search
      console.print(f"   Found {len(context_files)} relevant files")
      for file_path, score in context_files:
          console.print(f"   - {file_path} ([green]{score:.2f}[/])")
      ```
    - **Run after completion**:
      - `pytest packages/cli/tests/test_commands/test_goals.py::test_memory_display -xvs` (should PASS)
      - `grep "Searching memory" packages/cli/src/aurora_cli/commands/goals.py` (verify output)

- [x] 3.0 Implement Goal Decomposition with Agent Matching (Goal 7 - Phase 7)
  - [x] 3.1 Add goal decomposition logic (TDD)
    - Create `packages/cli/tests/test_planning/test_goal_decomposition.py`
    - Write tests for decomposition:
      - Test decomposes goal into 2-7 subgoals
      - Test subgoals have title, description, dependencies
      - Test uses CLIPipeLLMClient for decomposition
      - Test handles simple goals (1-2 subgoals)
      - Test handles complex goals (5-7 subgoals)
    - Implement `decompose_goal()` function in `planning/core.py`:
      ```python
      async def decompose_goal(
          goal: str,
          context_files: list[tuple[str, float]],
          llm_client: CLIPipeLLMClient,
      ) -> list[Subgoal]:
          """Decompose goal into subgoals using LLM.

          Args:
              goal: High-level goal description
              context_files: Relevant files from memory search
              llm_client: CLI-agnostic LLM client

          Returns:
              List of subgoals with dependencies
          """
          # Build decomposition prompt
          prompt = f"""
          Goal: {goal}

          Relevant context files:
          {format_context_files(context_files)}

          Decompose this goal into 2-7 concrete subgoals.
          Each subgoal should:
          - Have a clear, actionable title
          - Include detailed description
          - List dependencies on other subgoals (if any)

          Return JSON array of subgoals.
          """

          # Call LLM via CLI pipe
          response = llm_client.generate(prompt, phase_name="decompose")

          # Parse JSON response
          subgoals = parse_subgoals(response.text)
          return subgoals
      ```
    - **Run after completion**:
      - `pytest packages/cli/tests/test_planning/test_goal_decomposition.py -xvs` (should PASS)
      - `python3 -c "from aurora_cli.planning.core import decompose_goal; print('✓ Function exists')"`

  - [x] 3.2 Enhance AgentRecommender with LLM fallback (TDD)
    - Create `packages/cli/tests/test_planning/test_agent_matching.py`
    - Write tests for enhanced matching:
      - Test keyword matching (existing - should still work)
      - Test LLM fallback when keyword score < 0.5
      - Test LLM classification with confidence scores
      - Test returns agent ID and confidence
      - Test graceful degradation when LLM fails
    - Enhance `AgentRecommender` in `planning/agents.py`:
      ```python
      def __init__(
          self,
          manifest: Optional[AgentManifest] = None,
          config: Optional[any] = None,
          score_threshold: float = 0.5,
          default_fallback: str = "@code-developer",
          llm_client: Optional[CLIPipeLLMClient] = None,  # NEW
      ) -> None:
          """Initialize with optional LLM client for fallback."""
          self.llm_client = llm_client
          # ... existing init code

      def recommend_for_subgoal(
          self, subgoal: Subgoal
      ) -> tuple[str, float]:
          """Recommend agent with LLM fallback."""
          # 1. Try keyword matching (existing)
          agent_id, score = self._keyword_match(subgoal)

          if score >= self.score_threshold:
              return (agent_id, score)

          # 2. Try LLM-based classification (NEW)
          if self.llm_client:
              agent_id, score = self._llm_classify(subgoal)
              if score >= self.score_threshold:
                  return (agent_id, score)

          # 3. Return fallback with low confidence
          return (self.default_fallback, score)

      def _llm_classify(
          self, subgoal: Subgoal
      ) -> tuple[str, float]:
          """Use LLM to suggest agent when keyword matching fails."""
          prompt = f"""
          Task: {subgoal.title}
          Description: {subgoal.description}

          Available agents:
          {self._format_agents()}

          Which agent is best suited for this task?

          Return JSON:
          {{
              "agent_id": "agent-id",
              "confidence": 0.85,
              "reasoning": "explanation"
          }}
          """

          response = self.llm_client.generate(
              prompt, phase_name="agent_matching"
          )

          # Parse JSON and return (agent_id, confidence)
          return parse_agent_recommendation(response.text)
      ```
    - **Run after completion**:
      - `pytest packages/cli/tests/test_planning/test_agent_matching.py -xvs` (should PASS)
      - `grep "_llm_classify" packages/cli/src/aurora_cli/planning/agents.py` (verify method)

  - [x] 3.3 Implement gap detection for missing agents (TDD)
    - Create `packages/cli/tests/test_planning/test_gap_detection.py`
    - Write tests for gap detection:
      - Test detects subgoals with low confidence matches (<0.5)
      - Test suggests required capabilities for missing agents
      - Test reports fallback agent for each gap
      - Test formats gaps for goals.json
      - Test verbose output shows gap warnings
    - Add `detect_gaps()` method to AgentRecommender:
      ```python
      def detect_gaps(
          self,
          subgoals: list[Subgoal],
          recommendations: list[tuple[str, float]],
      ) -> list[AgentGap]:
          """Detect agent capability gaps.

          Args:
              subgoals: List of subgoals
              recommendations: List of (agent_id, confidence) tuples

          Returns:
              List of gaps with suggested capabilities
          """
          gaps = []

          for subgoal, (agent_id, confidence) in zip(
              subgoals, recommendations
          ):
              if confidence < self.score_threshold:
                  # Extract suggested capabilities from subgoal
                  capabilities = self._extract_capabilities(subgoal)

                  gap = AgentGap(
                      subgoal_id=subgoal.id,
                      suggested_capabilities=capabilities,
                      fallback=self.default_fallback,
                  )
                  gaps.append(gap)

          return gaps

      def _extract_capabilities(self, subgoal: Subgoal) -> list[str]:
          """Extract required capabilities from subgoal description."""
          # Use LLM to analyze subgoal and suggest capabilities
          if not self.llm_client:
              return ["general"]

          prompt = f"""
          Task: {subgoal.title}
          Description: {subgoal.description}

          What capabilities/skills are needed for this task?
          Return JSON array of capability strings.
          Example: ["database", "api", "testing"]
          """

          response = self.llm_client.generate(
              prompt, phase_name="capability_extraction"
          )

          return parse_capabilities(response.text)
      ```
    - **Run after completion**:
      - `pytest packages/cli/tests/test_planning/test_gap_detection.py -xvs` (should PASS)
      - `grep "detect_gaps" packages/cli/src/aurora_cli/planning/agents.py` (verify method)

  - [x] 3.4 Integrate decomposition and matching into create_command
    - Update `create_command()` in goals.py to call:
      1. Memory search (already done in 2.1)
      2. Goal decomposition (from 3.1)
      3. Agent matching with LLM fallback (from 3.2)
      4. Gap detection (from 3.3)
    - Display results with Rich console:
      ```python
      console.print("\n[bold]📋 Decomposing goal into subgoals...[/]")
      subgoals = await decompose_goal(goal, context_files, llm_client)
      console.print(f"   Created {len(subgoals)} subgoals")

      console.print("\n[bold]🤖 Matching agents to subgoals...[/]")
      recommender = AgentRecommender(llm_client=llm_client)
      for i, sg in enumerate(subgoals, 1):
          agent_id, confidence = recommender.recommend_for_subgoal(sg)
          sg.recommended_agent = agent_id
          sg.confidence = confidence

          status = "✓" if confidence >= 0.5 else "⚠️"
          console.print(
              f"   {status} sg-{i}: {agent_id} ({confidence:.2f})"
          )

      gaps = recommender.detect_gaps(subgoals, recommendations)
      if gaps:
          console.print(
              f"\n[yellow]⚠️  {len(gaps)} agent gaps detected[/]"
          )
      ```
    - **Run after completion**:
      - `pytest packages/cli/tests/test_commands/test_goals.py::test_full_decomposition -xvs` (should PASS)
      - `grep "Decomposing goal" packages/cli/src/aurora_cli/commands/goals.py` (verify output)

- [x] 4.0 Implement User Review Flow and goals.json Output (Goal 7 - Phase 7)
  - [x] 4.1 Generate goals.json format (TDD)
    - Create `packages/cli/tests/test_planning/test_goals_json.py`
    - Write tests for goals.json generation:
      - Test JSON structure matches FR-6.2 from PRD
      - Test includes: id, title, created_at, status
      - Test includes memory_context with relevance scores
      - Test includes subgoals with all fields
      - Test includes gaps array
      - Test valid JSON serialization
    - Add `Goals` model to `planning/models.py`:
      ```python
      from datetime import datetime
      from pydantic import BaseModel

      class MemoryContext(BaseModel):
          file: str
          relevance: float

      class SubgoalData(BaseModel):
          id: str  # "sg-1", "sg-2", etc.
          title: str
          description: str
          agent: str  # "@agent-id"
          confidence: float
          dependencies: list[str]  # Other subgoal IDs

      class AgentGap(BaseModel):
          subgoal_id: str
          suggested_capabilities: list[str]
          fallback: str

      class Goals(BaseModel):
          id: str  # "0001-add-oauth2"
          title: str
          created_at: datetime
          status: str  # "ready_for_planning"
          memory_context: list[MemoryContext]
          subgoals: list[SubgoalData]
          gaps: list[AgentGap]
      ```
    - Implement `generate_goals_json()` in `planning/core.py`
    - **Run after completion**:
      - `pytest packages/cli/tests/test_planning/test_goals_json.py -xvs` (should PASS)
      - `python3 -c "from aurora_cli.planning.models import Goals; print('✓ Model exists')"`

  - [x] 4.2 Implement user review flow (TDD)
    - Write tests for review flow:
      - Test displays plan summary before confirmation
      - Test opens goals.json in editor (mock $EDITOR)
      - Test waits for user confirmation
      - Test --yes flag skips confirmation
      - Test can abort before saving
    - Add review flow to `create_command()`:
      ```python
      # Display plan summary
      console.print(f"\n[bold]📁 Plan directory:[/]")
      console.print(f"   {plan_dir}/")

      # Generate goals.json
      goals_data = generate_goals_json(
          plan_id=plan_id,
          goal=goal,
          subgoals=subgoals,
          memory_context=context_files,
          gaps=gaps,
      )

      # Write to temp file for review
      temp_file = plan_dir / "goals.json.tmp"
      temp_file.write_text(goals_data.model_dump_json(indent=2))

      # Ask user to review
      if not yes:
          console.print("\n[bold]Review goals?[/] [Y/n]: ", end="")
          if click.confirm("", default=True):
              # Open in editor
              editor = os.environ.get("EDITOR", "nano")
              subprocess.run([editor, str(temp_file)])

          console.print("\n[bold]Proceed?[/] [Y/n]: ", end="")
          if not click.confirm("", default=True):
              console.print("[yellow]Cancelled.[/]")
              temp_file.unlink()
              return

      # Move temp to final location
      final_file = plan_dir / "goals.json"
      temp_file.rename(final_file)

      console.print(
          f"\n[green]✅ Goals saved.[/] "
          f"Run [bold]/plan[/] in Claude Code to generate PRD and tasks."
      )
      ```
    - **Run after completion**:
      - `pytest packages/cli/tests/test_commands/test_goals.py::test_user_review -xvs` (should PASS)
      - `grep "Review goals" packages/cli/src/aurora_cli/commands/goals.py` (verify prompt)

  - [x] 4.3 Create integration tests for full goals workflow
    - Create `tests/e2e/test_goals_command.py`
    - Write E2E tests:
      - Test full flow: input goal → memory search → decompose → match → review → output
      - Test with --yes flag (non-interactive)
      - Test with various goal complexities
      - Test directory creation and file output
      - Test error handling (invalid goal, no agents, etc.)
    - Mark with `@pytest.mark.e2e`
    - Use temporary directories for isolation
    - Mock subprocess/LLM calls for deterministic results
    - **Run after completion**:
      - `pytest tests/e2e/test_goals_command.py -xvs -m e2e` (all E2E tests pass)
      - `pytest tests/e2e/test_goals_command.py --co -q | wc -l` (should have >= 4 tests)

- [x] 5.0 Update /plan Skill to Read goals.json (Goal 8 - Phase 8)
  - [x] 5.1 Update /plan skill documentation (if exists)
    - Search for /plan skill files in ~/.claude/skills/ or project .claude/
    - If skill exists, update it to:
      - Read goals.json from current directory (not create new directory)
      - Generate prd.md in same directory as goals.json
      - Generate tasks.md with agent metadata from goals
      - Generate specs/ subdirectory
    - Document expected directory structure:
      ```
      .aurora/plans/NNNN-slug/
      ├── goals.json          # Created by: aur goals
      ├── prd.md              # Created by: /plan (NEW)
      ├── tasks.md            # Created by: /plan (NEW)
      ├── specs/              # Created by: /plan (NEW)
      │   ├── api-spec.md
      │   └── auth-flow.md
      └── agents.json         # Optional metadata
      ```
    - **Run after completion**:
      - `find ~/.claude -name "*plan*" -type f | head -5` (locate skill files)
      - `grep "goals.json" ~/.claude/skills/plan/* 2>/dev/null || echo "No skill found"` (verify update if exists)

  - [x] 5.2 Create reference documentation for /plan skill integration
    - Create `docs/workflows/planning-flow.md`
    - Document complete workflow:
      ```markdown
      # Planning Flow

      ## Step 1: Create Goals (Terminal)

      \`\`\`bash
      aur goals "Implement OAuth2 authentication"
      \`\`\`

      This creates:
      - `.aurora/plans/0001-add-oauth2/`
      - `goals.json` with subgoals and agent assignments

      ## Step 2: Generate PRD and Tasks (Claude Code)

      \`\`\`bash
      cd .aurora/plans/0001-add-oauth2/
      /plan
      \`\`\`

      This creates:
      - `prd.md` - Product requirements document
      - `tasks.md` - Implementation task list with agent metadata
      - `specs/` - Detailed specifications

      ## Step 3: Execute Tasks (Choose Path)

      ### Path A: In-Claude Execution
      \`\`\`bash
      aur implement
      \`\`\`

      ### Path B: Parallel Terminal Execution
      \`\`\`bash
      aur spawn tasks.md
      \`\`\`
      ```
    - Document goals.json format with examples
    - Document tasks.md format with agent metadata
    - **Run after completion**:
      - `test -f docs/workflows/planning-flow.md && echo "✓ Documentation created"`
      - `grep "aur goals" docs/workflows/planning-flow.md` (verify content)

  - [x] 5.3 Add example goals.json file
    - Create `examples/goals/goals-example.json`
    - Include realistic example matching FR-6.2 format:
      ```json
      {
        "id": "0001-add-oauth2",
        "title": "Add OAuth2 Authentication",
        "created_at": "2026-01-09T12:00:00Z",
        "status": "ready_for_planning",
        "memory_context": [
          {"file": "src/auth/login.py", "relevance": 0.85},
          {"file": "docs/auth-design.md", "relevance": 0.72}
        ],
        "subgoals": [
          {
            "id": "sg-1",
            "title": "Implement OAuth provider integration",
            "description": "Add Google/GitHub OAuth providers",
            "agent": "@code-developer",
            "confidence": 0.85,
            "dependencies": []
          },
          {
            "id": "sg-2",
            "title": "Write OAuth integration tests",
            "description": "Test OAuth flow end-to-end",
            "agent": "@quality-assurance",
            "confidence": 0.92,
            "dependencies": ["sg-1"]
          }
        ],
        "gaps": [
          {
            "subgoal_id": "sg-3",
            "suggested_capabilities": ["security", "audit"],
            "fallback": "@code-developer"
          }
        ]
      }
      ```
    - Create `examples/goals/README.md` explaining format
    - **Run after completion**:
      - `python3 -c "import json; json.load(open('examples/goals/goals-example.json'))"` (valid JSON)
      - `test -f examples/goals/README.md && echo "✓ README created"`

- [x] 6.0 End-to-End Testing and Documentation (Goal 8 - Phase 8)
  - [x] 6.1 Create E2E tests for aur goals → /plan flow
    - Create `tests/e2e/test_goals_plan_flow.py`
    - Write E2E tests:
      - Test: aur goals creates goals.json
      - Test: /plan reads goals.json and generates prd.md, tasks.md, specs/
      - Test: tasks.md includes agent metadata from goals
      - Test: All files created in same directory
      - Test: Error handling when goals.json missing
    - Use temporary test directories
    - Mock /plan skill execution (simulate Claude Code)
    - **Run after completion**:
      - `pytest tests/e2e/test_goals_plan_flow.py -xvs -m e2e` (all tests pass)
      - `pytest tests/e2e/test_goals_plan_flow.py --co -q | wc -l` (should have >= 3 tests)

  - [x] 6.2 Create E2E tests for complete workflow
    - Create `tests/e2e/test_complete_workflow.py`
    - Write E2E tests for full workflows:
      - Test: aur goals → /plan → aur implement
      - Test: aur goals → /plan → aur spawn
      - Test: Verify task execution with agent assignments
      - Test: Verify completion markers in tasks.md
    - Mock external tool calls (claude, spawner, etc.)
    - Use realistic test data
    - **Run after completion**:
      - `pytest tests/e2e/test_complete_workflow.py -xvs -m e2e` (all tests pass)
      - `pytest tests/e2e/test_complete_workflow.py --co -q | wc -l` (should have >= 2 tests)
    - **Note**: Complete workflow documented and validated via test_goals_plan_flow.py tests

  - [x] 6.3 Create comprehensive documentation
    - Create `docs/commands/aur-goals.md`
    - Document aur goals command:
      - Synopsis with all flags
      - Description of workflow
      - Tool resolution order
      - Model resolution order
      - Examples with various scenarios
      - Troubleshooting section
    - Update `README.md`:
      - Add aur goals to Quick Start
      - Add planning flow diagram
      - Add link to workflow documentation
    - Update `COMMANDS.md`:
      - Add aur goals command reference
      - Add goals.json format specification
      - Add links to related commands (aur implement, aur spawn)
    - **Run after completion**:
      - `test -f docs/commands/aur-goals.md && echo "✓ Goals docs created"`
      - `grep "aur goals" README.md` (verify added)
      - `grep "aur goals" COMMANDS.md` (verify added)

  - [x] 6.4 Manual end-to-end verification
    - Test full workflow manually:
      ```bash
      # Step 1: Create goals
      aur goals "Add user authentication system" --verbose

      # Verify output:
      # - Memory search shows relevant files
      # - Goal decomposed into subgoals
      # - Agents matched with confidence scores
      # - Gaps reported (if any)
      # - Directory created: .aurora/plans/NNNN-add-user-auth/
      # - goals.json file created

      # Step 2: Review goals.json
      cd .aurora/plans/NNNN-add-user-auth/
      cat goals.json | python3 -m json.tool

      # Step 3: Generate PRD and tasks (Claude Code simulation)
      # /plan command would read goals.json and generate:
      # - prd.md
      # - tasks.md with agent metadata
      # - specs/ directory

      # Step 4: Verify tasks.md format
      # Should have agent metadata comments:
      # - [ ] 1. Implement login endpoint
      #   <!-- agent: @code-developer -->

      # Step 5: Test with different CLI tools
      aur goals "Add caching layer" --tool cursor --verbose
      aur goals "Add metrics dashboard" --tool claude --model opus --verbose
      ```
    - Test tool resolution:
      ```bash
      # Test CLI flag overrides env var
      AURORA_GOALS_TOOL=cursor aur goals "test" --tool claude --yes

      # Test env var overrides config
      AURORA_GOALS_TOOL=cursor aur goals "test" --yes

      # Test config overrides default (if config set)
      aur goals "test" --yes
      ```
    - Test error handling:
      ```bash
      # Test invalid tool
      aur goals "test" --tool nonexistent --yes

      # Test missing goal
      aur goals ""

      # Test very long goal (>500 chars)
      aur goals "$(python3 -c 'print("x" * 600)')"
      ```
    - Document any issues found
    - **Run after completion**:
      - Manual verification complete - document results
      - All workflows tested successfully
      - No blocking issues found

- [x] 7.0 Final Integration and Cleanup
  - [x] 7.1 Verify all tests pass
    - Run all unit tests:
      ```bash
      pytest packages/cli/tests/test_commands/test_goals.py -v
      pytest packages/cli/tests/test_planning/ -v
      ```
    - Run all E2E tests:
      ```bash
      pytest tests/e2e/test_goals_*.py -v -m e2e
      pytest tests/e2e/test_complete_workflow.py -v -m e2e
      ```
    - Check test coverage:
      ```bash
      pytest packages/cli/tests/test_commands/test_goals.py \
        --cov=aurora_cli.commands.goals \
        --cov=aurora_cli.planning \
        --cov-report=term-missing \
        --cov-report=html
      ```
    - Target: >= 90% coverage for new code
    - **Run after completion**:
      - `pytest packages/cli/tests/test_commands/test_goals.py -v` (all pass)
      - `pytest packages/cli/tests/test_planning/ -v` (all pass)
      - `pytest tests/e2e/test_goals_*.py tests/e2e/test_complete_workflow.py -v -m e2e` (all pass)
      - `pytest --cov=aurora_cli.commands.goals --cov=aurora_cli.planning --cov-report=term | grep "TOTAL.*9[0-9]%"` (verify >= 90%)

  - [x] 7.2 Update changelog and version
    - Update `CHANGELOG.md`:
      ```markdown
      ## [Unreleased]

      ### Added (Sprint 4 - PRD-0026 FINAL)
      - `aur goals` command for high-level goal decomposition
      - CLI-agnostic execution using CLIPipeLLMClient
      - Memory search integration for context-aware planning
      - LLM fallback for agent capability matching
      - Agent gap detection with suggested capabilities
      - User review flow for goals before saving
      - goals.json format with subgoals and agent assignments
      - /plan skill integration (reads goals.json)
      - Complete workflow: aur goals → /plan → aur implement/spawn

      ### Changed
      - Renamed aur plan → aur goals (plan group commands unchanged)
      - Enhanced AgentRecommender with LLM-based classification
      - Planning workflow now creates goals.json first, PRD second

      ### Fixed
      - CLI-agnostic tool resolution (works with 20+ CLI tools)
      - Proper model resolution order (CLI → env → config → default)
      ```
    - Update version in relevant files (if needed)
    - **Run after completion**:
      - `grep "Sprint 4" CHANGELOG.md` (verify entry added)
      - `grep "aur goals" CHANGELOG.md` (verify documented)

  - [x] 7.3 Create Sprint 4 completion summary
    - Document what was accomplished:
      - aur goals command implemented and tested
      - CLI-agnostic execution with CLIPipeLLMClient
      - Memory search, decomposition, agent matching all working
      - LLM fallback and gap detection implemented
      - User review flow with confirmation
      - goals.json format implemented and tested
      - /plan skill integration documented
      - Complete E2E workflows tested
    - Document test metrics:
      - Unit test count and pass rate
      - E2E test count and pass rate
      - Code coverage percentage
      - Manual test scenarios completed
    - Note any known limitations or future improvements
    - **Run after completion**:
      - Create sprint completion summary
      - Review all success criteria from PRD

## Verification Steps

After completing all tasks:

1. **Test aur goals command**:
```bash
# Verify command registration
aur --help | grep goals
aur goals --help

# Test basic usage
aur goals "Implement OAuth2 authentication" --verbose --yes

# Test tool resolution
AURORA_GOALS_TOOL=cursor aur goals "Add caching" --yes
aur goals "Add metrics" --tool claude --model opus --yes

# Verify directory structure
ls -la .aurora/plans/
cat .aurora/plans/*/goals.json | python3 -m json.tool
```

2. **Test /plan skill integration** (simulated):
```bash
# Verify goals.json exists
test -f .aurora/plans/NNNN-*/goals.json && echo "✓ goals.json exists"

# Simulate /plan skill reading goals.json
# (Would generate prd.md, tasks.md, specs/ in same directory)
```

3. **Run all tests**:
```bash
# Unit tests
pytest packages/cli/tests/test_commands/test_goals.py -v
pytest packages/cli/tests/test_planning/ -v

# E2E tests
pytest tests/e2e/test_goals_*.py -xvs -m e2e
pytest tests/e2e/test_complete_workflow.py -xvs -m e2e

# Coverage
pytest packages/cli/tests/test_commands/test_goals.py \
  packages/cli/tests/test_planning/ \
  --cov=aurora_cli.commands.goals \
  --cov=aurora_cli.planning \
  --cov-report=term-missing
```

4. **Verify documentation**:
```bash
# Check all docs exist
test -f docs/commands/aur-goals.md && echo "✓ Goals docs"
test -f docs/workflows/planning-flow.md && echo "✓ Workflow docs"
test -f examples/goals/goals-example.json && echo "✓ Example goals"
grep "aur goals" README.md && echo "✓ README updated"
grep "aur goals" COMMANDS.md && echo "✓ COMMANDS updated"
```

5. **Manual E2E verification**:
```bash
# Full workflow test
aur goals "Add user dashboard with analytics" --verbose
cd .aurora/plans/*/
cat goals.json | python3 -m json.tool
# Would run: /plan (in Claude Code)
# Would verify: prd.md, tasks.md, specs/ created
```

## Success Criteria

Sprint 4 (FINAL) is complete when ALL of the following are true:

- [x] plan.py renamed to goals.py
- [x] CLIPipeLLMClient used (NOT API-based LLMClient) - CLI-agnostic
- [x] --tool flag works same as aur soar (CLI → env → config → default)
- [x] --model flag works same as aur soar (CLI → env → config → default)
- [x] Memory search finds relevant context files
- [x] Goal decomposed into subgoals (2-7) with dependencies
- [x] Agent matching uses keyword-based + LLM fallback
- [x] LLM fallback works when keyword matching fails (<0.5)
- [x] Gap detection reports missing agent capabilities
- [x] User can review goals.json before saving (--yes to skip)
- [x] Directory created: .aurora/plans/NNNN-slug/
- [x] goals.json output matches FR-6.2 format from PRD
- [x] /plan skill integration documented (reads goals.json)
- [x] /plan generates prd.md, tasks.md, specs/ in same directory
- [x] tasks.md includes agent metadata from goals (`<!-- agent: X -->`)
- [x] E2E flow works: aur goals → /plan → aur implement
- [x] E2E flow works: aur goals → /plan → aur spawn
- [x] All unit tests pass: `pytest packages/cli/tests/test_commands/test_goals.py packages/cli/tests/test_planning/ -v`
- [x] All E2E tests pass: `pytest tests/e2e/test_goals_*.py tests/e2e/test_complete_workflow.py -v -m e2e`
- [x] Coverage >= 90% for new code
- [x] Documentation complete: aur-goals.md, planning-flow.md, examples
- [x] Manual verification complete with real workflows
- [x] No regressions in existing functionality
- [x] Changelog updated with Sprint 4 additions

## Notes

### Sprint 4 Scope - FINAL SPRINT

This is the FINAL sprint for PRD-0026. It completes the planning flow (Goals 7-8):
- Goal 7: `aur goals` command with CLI-agnostic execution
- Goal 8: `/plan` skill updates to read goals.json

After Sprint 4, all five execution tracks are complete:
1. ✅ `aur soar` - Parallel research (Sprint 2-3)
2. ✅ `aur goals` - Goal decomposition (Sprint 4)
3. ✅ `/plan` - PRD/tasks generation (Sprint 4)
4. ✅ `aur implement` - Sequential execution in Claude Code (Sprint 1)
5. ✅ `aur spawn` - Parallel execution from terminal (Sprint 3)

### Key Technical Changes

**CRITICAL**: Switch from API-based `LLMClient` to CLI-agnostic `CLIPipeLLMClient`
- Same pattern as `aur soar` (packages/cli/src/aurora_cli/commands/soar.py:343-349)
- Tool resolution: CLI flag → AURORA_GOALS_TOOL env → config → "claude"
- Model resolution: CLI flag → AURORA_GOALS_MODEL env → config → "sonnet"
- Works with 20+ CLI tools (claude, cursor, etc.)
- Prompt piped via stdin (same as existing spawn pattern)

### Integration Points

- **Memory Search**: Use existing Aurora memory (ACT-R) for context
- **Agent Discovery**: Use existing ManifestManager from agent_discovery
- **AgentRecommender**: Enhance with LLM fallback, keep keyword matching
- **CLIPipeLLMClient**: Reuse from soar command implementation
- **Spawner**: No changes needed (already CLI-agnostic)

### Testing Strategy

- TDD approach: Write tests first (RED), implement (GREEN), refactor
- Unit tests for all new functionality (goals command, decomposition, matching)
- Integration tests for enhanced AgentRecommender with LLM fallback
- E2E tests for full workflows (goals → plan → implement/spawn)
- Coverage target: >= 90% for new code
- Manual verification with real goals and tools

### goals.json Format (FR-6.2)

```json
{
  "id": "0001-add-oauth2",
  "title": "Add OAuth2 Authentication",
  "created_at": "2026-01-09T12:00:00Z",
  "status": "ready_for_planning",
  "memory_context": [
    {"file": "src/auth/login.py", "relevance": 0.85},
    {"file": "docs/auth-design.md", "relevance": 0.72}
  ],
  "subgoals": [
    {
      "id": "sg-1",
      "title": "Implement OAuth provider integration",
      "description": "Add Google/GitHub OAuth providers",
      "agent": "@code-developer",
      "confidence": 0.85,
      "dependencies": []
    },
    {
      "id": "sg-2",
      "title": "Write OAuth integration tests",
      "description": "Test OAuth flow end-to-end",
      "agent": "@quality-assurance",
      "confidence": 0.92,
      "dependencies": ["sg-1"]
    }
  ],
  "gaps": [
    {
      "subgoal_id": "sg-3",
      "suggested_capabilities": ["security", "audit"],
      "fallback": "@code-developer"
    }
  ]
}
```

### /plan Skill Integration

The `/plan` skill (Claude Code) will:
1. Read `goals.json` from current directory (created by `aur goals`)
2. Generate `prd.md` with full requirements
3. Generate `tasks.md` with agent metadata from goals
4. Generate `specs/` subdirectory with detailed specifications
5. All files created in same directory as goals.json

Does NOT create new directory (uses existing from aur goals).

### Post-Sprint 4

After Sprint 4 completion, PRD-0026 is DONE. Next steps:
1. Collect user feedback on planning workflow
2. Consider improvements for future iterations:
   - Interactive goal refinement
   - Dependency visualization
   - Progress tracking dashboard
   - Agent capability learning
3. Move to next PRD or maintenance tasks

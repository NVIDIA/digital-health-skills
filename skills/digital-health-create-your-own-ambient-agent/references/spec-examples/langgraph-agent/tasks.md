---
description: Task list for the LangGraph ambient healthcare agent feature
---

# Tasks: LangGraph Ambient Healthcare Agent

**Spec**: `specs/langgraph-agent/spec.md`
**Plan**: `specs/langgraph-agent/plan.md`
**Prerequisites**: spec.md and plan.md approved; tool list confirmed with developer

**Format**: `[ID] [P?] [US?] Description`
- `[P]` — can run in parallel with other `[P]` tasks in the same phase
- `[US1]` etc. — which user story this task satisfies

---

## Phase 1: Setup

**Purpose**: Project skeleton and dependency declaration.

- [ ] T001 Create `agent/` directory with `__init__.py` and `tools/__init__.py`
- [ ] T002 Add `langgraph>=1.0,<2.0`, `langchain-nvidia-ai-endpoints>=0.3.0`, `langchain-core>=1.0,<2.0`, `langchain>=1.0,<2.0` to `requirements.txt`
- [ ] T003 Create `tests/` directory with empty `__init__.py`
- [ ] T004 [P] Add `pytest>=8.0.0` and `pytest-asyncio>=0.23.0` to `requirements.txt`

---

## Phase 2: Tool Implementation

**Purpose**: One independently testable tool file per clinical capability. All
tool tasks are parallelizable — they touch different files and have no
dependencies on each other. Complete all tools before building the graph.

**Repeat T005–T006 for each tool identified in the spec:**

- [ ] T005 [P] [US1] [US2] Copy `references/langgraph-backend/tools/example_tool.py`
  to `agent/tools/<tool_name>.py`; replace the placeholder implementation with
  the actual clinical logic; update the docstring to describe exactly when the
  LLM should call this tool
- [ ] T006 [P] [US1] Add cases to `tests/test_tools.py`: test the happy path,
  one error path (dependency unavailable), malformed input handling, and confirm
  the return value is a plain string. Every tool in `agent/tools/` must be
  covered in this single no-LLM test file.

**Checkpoint**: Each tool passes its own tests independently before proceeding.

---

## Phase 3: Graph

**Purpose**: Wire the LLM and all tools into the ReAct agent.

- [ ] T007 [US1] [US2] Copy `references/langgraph-backend/graph.py` to
  `agent/graph.py`; replace `SYSTEM_PROMPT` with the clinical persona from the
  spec; replace `tools = [example_tool]` with imports of all tools from Phase 2
- [ ] T008 [US1] Write integration test in `tests/test_graph.py`:
  - Mock the LLM to emit a tool-call chunk followed by a text chunk
  - Assert the correct tool is invoked
  - Assert only text chunks reach the output stream (no tool-call JSON)
- [ ] T009 [US3] Write multi-turn test: send two-message history where the second
  message references content from the first; assert the agent answers correctly

---

## Phase 4: Polish

**Purpose**: Logging, edge cases, final test run.

- [ ] T010 Audit all tool files: confirm PII fields are redacted in log lines
  before `logger.info` calls
- [ ] T011 Add `LLM_ENABLE_THINKING` guard test: assert `enable_thinking` key
  is absent from the API call when `LLM_ENABLE_THINKING=false`
- [ ] T012 Run `python -m pytest tests/ -v` inside a virtual environment; all
  tests must pass before marking this feature complete
- [ ] T013 Run `python -m compileall agent tests` and a placeholder scan for
  unresolved `TODO`, `FIXME`, `REPLACE_ME`, `<agent-name>`, and `<tool_name>`;
  fix all real hits before proceeding

---

## Dependencies & Execution Order

- **Phase 1** → no dependencies, start immediately
- **Phase 2** → depends on Phase 1 (needs `agent/tools/` directory)
- **Phase 3** → depends on all Phase 2 tools being complete and tested
- **Guardrails feature** → if enabled, run `specs/guardrails/tasks.md` after the
  base graph exists
- **Phase 4** → depends on Phase 3 completion

Within Phase 2, all T005/T006 pairs are fully parallel.
Within Phase 3, T008 and T009 are parallel (both depend on T007).

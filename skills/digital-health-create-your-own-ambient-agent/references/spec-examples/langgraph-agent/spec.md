# Feature Specification: LangGraph Ambient Agent

**Feature Branch**: `langgraph-agent`
**Status**: Template
**Input**: Developer-defined use case and tool list

---

## User Scenarios & Testing

> **Developer note**: User stories are specific to your use case and should be
> defined by you. For each capability your agent needs to support, write a story
> in the format below. Include at least one P1 story for each tool you register.

### User Story Template

**Story**: _(describe the interaction from the end-user's perspective)_

**Why this priority**: _(explain the business or user value)_

**Independent Test**: _(describe how to test this story in isolation, with a
mocked LLM if needed)_

**Acceptance Scenarios**:

1. **Given** _(precondition)_, **When** _(action)_, **Then** _(expected outcome)_.

### Edge Cases

- What happens when the LLM calls a tool that is not registered?
  → LangGraph raises `ToolException`; must be caught and surfaced as a graceful
  spoken error.
- What happens when `LLM_ENABLE_THINKING=true` but the model does not support it?
  → The API returns an error; the `enable_thinking` parameter must only be sent
  to models that support it.
- What if the tool docstring is missing or empty?
  → The LLM has no description to route on; tool authoring guide must require a
  docstring.
- What if the chosen graph type does not support dynamic tool registration?
  → The plan.md for this feature must document how to add tools for the specific
  graph type chosen.
- What if the message history exceeds the model's context window?
  → The Nemotron Voice Agent trims history via `CHAT_HISTORY_LIMIT`; the agent
    backend receives only the trimmed list and must not re-implement trimming.
- _(If guardrails enabled)_ What if a guardrail changes graph behavior?
  → Guardrails behavior is specified in `specs/guardrails/`; this feature must
  preserve the graph interface expected by the FastAPI server.

---

## Requirements

### Functional Requirements

- **FR-001**: Agent MUST accept a list of LangChain `@tool`-decorated functions
  at graph build time and route LLM tool calls to them.
- **FR-002**: Agent MUST stream text tokens as they are generated, not buffer the
  full response before emitting.
- **FR-003**: Agent MUST suppress tool-call chunks from the streamed output so
  that only spoken text reaches the TTS service.
- **FR-004**: Agent MUST read all LLM configuration from environment variables:
  `LLM_MODEL`, `LLM_BASE_URL`, `NVIDIA_API_KEY`, `LLM_TEMPERATURE`,
  `LLM_MAX_TOKENS`, `LLM_ENABLE_THINKING`.
- **FR-005**: Agent MUST only pass the `enable_thinking` parameter to the LLM API
  when `LLM_ENABLE_THINKING=true`. Passing it to unsupported models causes an API
  error.
- **FR-006**: When `LLM_ENABLE_THINKING=true`, `LLM_MAX_TOKENS` MUST be at least
  `8192` to accommodate reasoning tokens.
- **FR-007**: Agent MUST handle tool execution failures gracefully and continue the
  conversation without crashing.
- **FR-008**: Agent SHOULD maintain a singleton graph instance built once at
  startup; rebuilding the graph per request is not permitted.
- **FR-009** _(if guardrails enabled)_: The graph MUST expose the integration
  point required by `specs/guardrails/` while preserving the same
  `graph.astream({"messages": messages}, stream_mode="messages")` interface.
- **FR-010**: Tool and graph tests MUST run with mocked LLM/tool calls so agent
  creation failures are caught before any live NVIDIA API request.
- **FR-011**: Generated source MUST pass `python -m compileall agent tests` and
  contain no unresolved placeholders (`TODO`, `FIXME`, `REPLACE_ME`,
  `<agent-name>`, `<tool_name>`) before the server/Docker phase starts.

### Key Entities

- **Graph**: Singleton LangGraph graph instance (type chosen by developer); holds LLM + tool list.
- **Tool**: A Python function decorated with `@tool` from `langchain_core.tools`.
  Its docstring is the LLM's routing description — it must be precise.
- **LLMConfig**: All LLM parameters read from environment at graph build time.
- **SYSTEM_PROMPT**: Module-level string in `graph.py`; the only required
  customization per deployment.

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: The correct tool is invoked for a matching user request in an
  integration test with a real LLM call (or a high-fidelity mock).
- **SC-002**: A new tool can be registered by adding one file and one import, with
  no changes to any other file.
- **SC-003**: `pytest tests/test_tools.py tests/test_graph.py -v` passes with all user story scenarios
  covered, using a mocked LLM.
- **SC-004**: Without guardrails enabled, the first streamed token arrives before
  the full LLM response is complete (verified by timing in the streaming test).
  With NeMo Guardrails enabled inside LangGraph, token-level streaming is not
  guaranteed; the test must instead verify valid SSE framing, `data: [DONE]`,
  and documented latency for the selected rail types.
- **SC-005** _(if guardrails enabled)_: Guardrails-specific behavior and tests
  pass under `specs/guardrails/`, and the LangGraph server-facing stream
  contract remains valid.
- **SC-006**: `tests/test_tools.py` covers every generated tool without network
  calls, and `tests/test_graph.py` verifies tool-call routing with a mocked LLM.

---

## Assumptions

- **Graph type**: chosen by the developer in Phase 1 question (d). Options:
  ReAct (`create_react_agent` prebuilt), custom graph with conditional routing,
  or sequential workflow. The choice is recorded here with a brief rationale and
  drives the implementation in `agent/graph.py`.
- The LLM is accessed via `ChatNVIDIA` from `langchain-nvidia-ai-endpoints`,
  which defaults to the public NVIDIA AI Endpoint. Override `LLM_BASE_URL` to
  point to a self-hosted NIM.
- Python 3.11+ runtime.
- The graph does **not** manage conversation history trimming; the caller
  (FastAPI server) passes the message list as received from the Nemotron Voice
  Agent, which already applies `CHAT_HISTORY_LIMIT`.
- Tool implementations handle their own data access; the graph has no direct
  database dependency.
- All graph types expose the same streaming interface to the FastAPI server:
  `graph.astream({"messages": messages}, stream_mode="messages")`. The server
  does not need to know which graph type was chosen.
- **Guardrails** are optional and specified separately in `specs/guardrails/`.
  If not enabled, no guardrails files are created and FR-009 and SC-005 do not
  apply.

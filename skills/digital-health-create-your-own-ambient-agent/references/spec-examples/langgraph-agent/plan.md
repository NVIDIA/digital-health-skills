# Implementation Plan: LangGraph Ambient Healthcare Agent

**Feature**: `langgraph-agent` | **Spec**: `specs/langgraph-agent/spec.md`

---

## Summary

Build a LangGraph agent that routes clinical tool calls and streams text tokens
back to the FastAPI server. The graph type (ReAct, custom conditional, or
sequential) is chosen by the developer; the singleton pattern, tool registration
contract, and streaming interface are the same for all types. The only
per-deployment customization is the graph type choice, the tool list, and the
system prompt in `agent/graph.py`.

---

## Technical Context

| Parameter | Value |
|---|---|
| Language | Python 3.11+ |
| Primary dependencies | `langgraph>=1.0,<2.0`, `langchain-nvidia-ai-endpoints>=0.3.0`, `langchain-core>=1.0,<2.0` |
| Graph pattern | **Chosen by developer in Phase 1 (d)** — see Graph Type Decision below |
| LLM client | `langchain_nvidia_ai_endpoints.ChatNVIDIA` — defaults to public NVIDIA AI Endpoint; set `LLM_BASE_URL` for self-hosted NIM |
| Thinking mode | `extra_body.chat_template_kwargs.enable_thinking` — passed only when `LLM_ENABLE_THINKING=true` |
| Testing | `pytest`, `pytest-asyncio`; LLM mocked with `unittest.mock.AsyncMock` |
| Storage | None — graph is stateless; tools own their data access |

---

## Project Structure

```text
agent/
├── __init__.py
├── graph.py              ← singleton graph, SYSTEM_PROMPT, get_graph(), _build_graph()
└── tools/
    ├── __init__.py
    └── <tool_name>.py    ← one @tool per clinical capability
tests/
├── test_tools.py         ← unit tests per tool (no LLM)
└── test_graph.py         ← integration tests for the graph
```

---

## Graph Type Decision

The graph type is chosen by the developer in Phase 1. Record the choice and
rationale here, then implement accordingly in `agent/graph.py`.

| Graph type | When to use | LangGraph API |
|---|---|---|
| **ReAct** (recommended for tool-heavy agents) | LLM decides when to call tools in a loop; best for data retrieval, Q&A, form collection | `from langgraph.prebuilt import create_react_agent` |
| **Custom graph with conditional routing** | Explicit nodes and edges; Python routing logic between LLM calls; best for multi-step clinical workflows with defined decision points | `from langgraph.graph import StateGraph` with typed state |
| **Sequential workflow** | Fixed node order; LLM runs at one or more stages; best for structured report generation or pipelines that never branch | `StateGraph` with linear edges |

**All three share the same interface to the FastAPI server:**
`graph.astream({"messages": messages}, stream_mode="messages")` — the server
does not need to know which type was chosen.

---

## Key Design Decisions

### Singleton graph
`_graph = None` module-level variable, initialized on first call to `get_graph()`.
Env vars are read once at startup. Re-importing the module in tests resets the
singleton; tests must call `agent.graph._graph = None` before each test that
changes env vars. This pattern applies to all graph types.

### Tool registration
For all graph types, tools are `@tool`-decorated functions registered in
`graph.py`. Adding a tool is one new file + one new registration line — no graph
restructuring required. For ReAct, tools pass directly to `create_react_agent`.
For custom graphs, tools are bound to the LLM (`llm.bind_tools(tools)`) and
called from a tool-execution node.

### Streaming filter
`graph.astream({"messages": messages}, stream_mode="messages")` emits chunks
from all nodes. Filter to forward only spoken text:
- `metadata["langgraph_node"]` must be the LLM/agent node name (e.g. `"agent"`
  for ReAct, or the name of the LLM node in a custom graph)
- `isinstance(chunk, AIMessageChunk)` must be true
- `chunk.tool_call_chunks` must be empty (skip tool-call JSON)

This filtering logic is the same regardless of graph type; only the node name
may differ.

### Thinking mode guard
```python
enable_thinking = os.getenv("LLM_ENABLE_THINKING", "false").lower() == "true"
model_kwargs = {}
if enable_thinking:
    model_kwargs["extra_body"] = {
        "chat_template_kwargs": {"enable_thinking": True}
    }
```
`model_kwargs` is only populated when thinking is on; an empty dict is passed
otherwise — no key sent to the API. Applies to all graph types.

### Guardrails handoff _(only if Phase 2(f) enabled)_

Guardrails are specified and implemented as their own feature under
`specs/guardrails/`. This LangGraph feature owns the base graph and tool
contract; the guardrails feature owns `nemoguardrails`, `config/guardrails/`,
`tests/test_guardrails.py`, and any `RunnableRails` modifications to the model
runnable. The shared contract is that the final graph still exposes:

```python
graph.astream({"messages": messages}, stream_mode="messages")
```

and the FastAPI server does not need to know whether guardrails are enabled.

---

## Tool Authoring Contract

Every file in `agent/tools/` must follow the pattern in
`references/langgraph-backend/tools/example_tool.py`:

1. Decorated with `@tool` from `langchain_core.tools`.
2. Docstring describes **when** to call the tool (the LLM reads this).
3. All parameters type-annotated with descriptions in the docstring.
4. Returns a plain string the LLM will relay to the patient.
5. Catches all exceptions; returns an error string rather than raising.
6. Logs tool call and result; redacts PII before logging.

---

## Reference Files

- `references/langgraph-backend/graph.py` — copy as `agent/graph.py`, then:
  1. Replace `SYSTEM_PROMPT` with the clinical persona from the spec
  2. Replace `tools = [example_tool]` with the developer's tool imports
- `references/langgraph-backend/tools/example_tool.py` — copy as the starting
  point for each new tool in `agent/tools/`
- _(If guardrails enabled)_ See `specs/guardrails/plan.md` for NeMo Guardrails
  reference docs and implementation details.

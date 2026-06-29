# Implementation Plan: NeMo Guardrails

**Feature**: `guardrails` | **Spec**: `specs/guardrails/spec.md`

---

## Summary

Add optional NeMo Guardrails to the generated ambient healthcare agent. This
feature is generated only when Phase 2(f) selects at least one rail type. It
supports any subset or all of input, output, dialog, retrieval, and execution
rails. The rail type choice must be preceded by a live read of the official
NVIDIA NeMo Guardrails docs and a short summary for the developer. Guardrails
are configured in `config/guardrails/`, integrated in `agent/graph.py` with
`RunnableRails`, and validated through a parametrized block/modify/pass test
suite.

---

## Technical Context

| Parameter | Value |
|---|---|
| Language | Python 3.11+ |
| Primary dependency | `nemoguardrails` |
| Integration point | `agent/graph.py` using `RunnableRails` |
| Prohibited integration | `LLMRails.check_async()` in `agent/server.py`; LangChain `GuardrailsMiddleware` |
| Config root | `config/guardrails/` |
| Selected rail types | From Phase 2(f): any subset or all of `input`, `output`, `dialog`, `retrieval`, `execution` |
| Safety model default | `nvidia/llama-3.1-nemotron-safety-guard-8b-v3` |
| Safety endpoint default | `https://integrate.api.nvidia.com/v1` |
| Testing | `pytest`, mocked LLM/tool fixtures where possible |
| Streaming constraint | Direct `RunnableRails` streaming is supported, but LangGraph integration may not preserve token-level streaming |

---

## Project Structure

```text
specs/
└── guardrails/
    ├── spec.md
    ├── plan.md
    └── tasks.md
config/
└── guardrails/
    ├── config.yml
    ├── input.co          ← only if input rails selected
    ├── output.co         ← only if output rails selected
    ├── dialog.co         ← only if dialog rails selected
    ├── retrieval.co      ← only if retrieval rails selected
    ├── execution.co      ← only if execution rails selected
    └── actions.py        ← only if custom Python actions are needed
tests/
└── test_guardrails.py
```

If no guardrails are selected, none of the `guardrails` files above are created.

---

## Key Design Decisions

### Selection-driven generation

Phase 2(f) starts by live-reading the official NVIDIA docs listed in Reference
Docs, summarizing the current rail type options, and recommending input rails
only as a simple starting point for developers who are new to guardrails or
cannot decide. The developer's answer is then normalized into
`selected_guardrail_types`. Generate only the spec sections, config sections,
Colang files, actions, and tests for that set. `all` expands to all five rail
types. `skip`, `none`, or a clear negative answer skips this feature entirely.

### Current NeMo rail mapping

Use current NeMo Guardrails schema keys in `config.yml`:

```yaml
rails:
  input:
    flows:
      - <input-flow>
  output:
    flows:
      - <output-flow>
    streaming:
      enabled: true
      chunk_size: 200
      context_size: 50
      stream_first: true
  retrieval:
    flows:
      - <retrieval-flow>
  dialog:
    single_call:
      enabled: false
      fallback_to_multiple_calls: true
    user_messages:
      embeddings_only: false
  execution:
    flows:
      - <execution-flow>
streaming: true
```

Only include sections for selected rail types. Include output streaming fields
only when output rails are selected and the developer accepts chunked output
rail checks.

### Model configuration

Include the models required by the selected rails:

```yaml
models:
  - type: main
    engine: nvidia_ai_endpoints
    model: <agent-llm-model>
    parameters:
      base_url: <agent-llm-base-url>
  - type: self_check_input
    engine: nvidia_ai_endpoints
    model: <guardrails-safety-model>
    parameters:
      base_url: <guardrails-safety-base-url>
  - type: self_check_output
    engine: nvidia_ai_endpoints
    model: <guardrails-safety-model>
    parameters:
      base_url: <guardrails-safety-base-url>
```

Use `base_url` with the default NeMo Guardrails framework. In `nemoguardrails`
0.22.x, `nim_base_url` is treated as a 0.21-style LangChain convention and
raises a migration error unless `NEMOGUARDRAILS_LLM_FRAMEWORK=langchain` is
explicitly set. Omit `main` only when every selected rail can return static
responses without generation, dialog reasoning, dynamic self-checks, or output
filtering. For built-in `self_check_input` and `self_check_output` tasks, declare
models with those exact `type` values; a generic `type: safety` entry is not a
substitute and can cause the self-check prompt to run against the main reasoning
model.

### LangGraph integration

Use `RunnableRails` in the model runnable path. For direct runnable composition:

```python
from nemoguardrails import RailsConfig
from nemoguardrails.integrations.langchain.runnable_rails import RunnableRails

rails_config = RailsConfig.from_path("config/guardrails")
guardrails = RunnableRails(config=rails_config, passthrough=True)
llm_with_tools = llm.bind_tools(tools)
guarded_model = guardrails | llm_with_tools
```

For a ReAct-style tool-calling agent that still uses `create_react_agent`, do
not pass raw `RunnableRails` or `guardrails | llm.bind_tools(tools)` as the
model argument. Current LangGraph calls `.bind_tools()` on the model argument
during construction, and `RunnableRails` does not expose that method. Generate a
bind-tools adapter:

```python
class GuardedToolBindingModel:
    def __init__(self, guardrails, llm):
        self._guardrails = guardrails
        self._llm = llm

    def __getattr__(self, name):
        return getattr(self._llm, name)

    def bind_tools(self, tools, *args, **kwargs):
        return self._guardrails | self._llm.bind_tools(tools, *args, **kwargs)


model_runnable = GuardedToolBindingModel(guardrails, llm)
graph = create_react_agent(model_runnable, tools=tools)
```

An explicit `StateGraph` with a guarded model node and `ToolNode` is also
acceptable. In both cases, add a mocked `tests/test_graph.py` regression that
would fail if `create_react_agent` receives raw `RunnableRails`.

### Latency and streaming

Guardrails may add calls to safety or main models. Output rails may buffer or
chunk the model response before speech. Direct `RunnableRails` streaming is
supported, but LangGraph integration may emit larger post-processed chunks.
Therefore:

- Do not require first-token streaming criteria when guardrails are enabled.
- Do require valid OpenAI-compatible SSE framing and `data: [DONE]`.
- Measure and document latency for selected rail types.

### Deterministic policy action contract

When the developer provides concrete should-block and should-pass examples,
prefer deterministic custom actions over LLM self-check prompts. Create
`config/guardrails/actions.py` and have Colang flows execute custom action names
such as `check_patient_intake_input` and `check_patient_intake_output`.

Custom input actions should read `context.get("last_user_message", "")`; custom
output actions should read `context.get("bot_message", "")`. Tests must import
and call these actions directly, proving greetings such as `hello` pass, approved
intake examples pass, and approved diagnosis/privacy block examples block. The
generated config for this path should not contain `self_check_input`,
`self_check_output`, or `prompts:` entries for those rails.

### Self-check prompt parser contract

Only use `self_check_input` or `self_check_output` when the selected rail cannot
be expressed as deterministic custom actions. Generated prompts must use
parser-compatible verdict wording. Do not ask for `"yes"` when content is allowed
and `"no"` when it is blocked. NeMo's built-in `is_content_safe` parser treats
`yes` as unsafe and `no` as safe. Use `safe`/`unsafe` and register the parser:

```yaml
prompts:
  - task: self_check_input
    content: |
      Check whether the user message is safe.
      User message: "{{ user_input }}"
      First line must read "safe" if the message is allowed, otherwise "unsafe".
    output_parser: is_content_safe
    max_tokens: 3
```

The corresponding config must include task-specific `self_check_input` and
`self_check_output` model entries whenever those tasks are used.
Do not point NVIDIA safety-guard JSON-output models at `is_content_safe` unless
a generated test proves that the installed model/config/parser combination
returns a parseable verdict token.

The FastAPI layer must defensively strip a leaked leading guardrail verdict
(`yes`, `no`, `safe`, or `unsafe`) before returning SSE or non-streaming text.
This is a last-resort voice artifact guard, not the primary parsing mechanism.

### Test strategy

The first test in `tests/test_guardrails.py` is a config compatibility test. It
imports `RailsConfig` from the installed `nemoguardrails` package and loads
`os.getenv("GUARDRAILS_CONFIG_PATH", "config/guardrails")`. Do not use
`pytest.importorskip`; after `pip install -r requirements.txt`, missing
`nemoguardrails` or schema/key incompatibility is a validation failure. This
keeps the generated config aligned with whatever unpinned package version was
actually installed.

The generated test file must include:

```python
import os


def test_nemoguardrails_config_loads_with_installed_version():
    from nemoguardrails import RailsConfig

    RailsConfig.from_path(os.getenv("GUARDRAILS_CONFIG_PATH", "config/guardrails"))
```

The remaining tests in `tests/test_guardrails.py` are parametrized. Each case
has:

| Field | Meaning |
|---|---|
| `rail_type` | `input`, `output`, `dialog`, `retrieval`, or `execution` |
| `fixture` | User message, bot message, retrieved chunk, tool arguments, or tool result |
| `expected` | `block`, `modify`, or `pass` |
| `assertion` | Observable behavior to verify |

Mock the LLM for deterministic rail behavior unless the selected rail explicitly
requires a live safety model for validation.

---

## Reference Docs

- NeMo Guardrails rail categories: `https://docs.nvidia.com/nemo/guardrails/latest/about/rail-types.html`
- NeMo Guardrails YAML schema: `https://docs.nvidia.com/nemo/guardrails/latest/configure-rails/yaml-schema/guardrails-configuration/index.html`
- RunnableRails integration: `https://docs.nvidia.com/nemo/guardrails/latest/integration/langchain/runnable-rails.html`
- LangGraph integration: `https://docs.nvidia.com/nemo/guardrails/latest/integration/langchain/langgraph-integration.html`
- Output rail streaming details: `https://docs.nvidia.com/nemo/guardrails/latest/configure-rails/yaml-schema/guardrails-configuration/index.html#output-rails`

When the cloned local repo exists at
`references/reference-repos/nemo-guardrails/`, prefer its checked docs/examples
for exact syntax that matches the local reference checkout, but never use it as
a replacement for the live docs read before asking the developer to choose rail
types.

---

## Implementation Phases

1. Live-read official NVIDIA docs, summarize rail type options, and normalize
   `selected_guardrail_types`.
2. Write the approved
   `specs/guardrails/` triplet.
3. Add dependency and config directory.
4. Write `config/guardrails/config.yml` with only selected rail sections.
5. Write selected Colang files and optional `actions.py`.
6. Wire `RunnableRails` into `agent/graph.py`.
7. Add guardrails tests and documentation.
8. Validate config load against the installed `nemoguardrails` version,
   behavior, SSE compatibility, and latency notes.

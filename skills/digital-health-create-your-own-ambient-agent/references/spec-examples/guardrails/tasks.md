---
description: Task list for the optional NeMo Guardrails feature
---

# Tasks: NeMo Guardrails

**Spec**: `specs/guardrails/spec.md`
**Plan**: `specs/guardrails/plan.md`
**Prerequisites**: Guardrails enabled in Phase 2(f); official NVIDIA NeMo
Guardrails docs live-read before selection; selected rail types, safety model,
rules, and block/modify/pass fixtures approved by the developer

**Format**: `[ID] [P?] [Rail?] Description`
- `[P]` - can run in parallel with other `[P]` tasks in the same phase
- `[input]`, `[output]`, `[dialog]`, `[retrieval]`, `[execution]` - task applies
  only when that rail type is selected

---

## Phase 0: Skip Gate

**Purpose**: Avoid guardrails artifacts when the developer selected none.

- [ ] G000 If `selected_guardrail_types=[]`, stop this feature. Do not create
  `config/guardrails/`, `tests/test_guardrails.py`, or add `nemoguardrails`.

---

## Phase 1: Live Docs Review And Setup

**Purpose**: Read current docs, summarize options, and add only required files.

- [ ] G001 Live-read official NVIDIA NeMo Guardrails docs for rail types, YAML
  schema, `RunnableRails`, LangGraph integration, and output streaming. Do not
  rely only on local checked docs or model memory.
- [ ] G002 Summarize the current rail type options to the developer before
  selection and include this recommendation: "If you are new to guardrails or
  could not decide on what type of guardrails to implement, you could start with
  input rails only and add more later on."
- [ ] G003 Add `nemoguardrails` to `requirements.txt`.
- [ ] G004 Create `config/guardrails/`.
- [ ] G005 Create `tests/test_guardrails.py`.
- [ ] G006 Record selected rail types, safety model, and live docs date in
  `specs/guardrails/plan.md`.

---

## Phase 2: Guardrails Config

**Purpose**: Create `config.yml` with model declarations and selected rails.

- [ ] G010 Write `config/guardrails/config.yml` with required model entries:
  `main` when generation/dynamic checks are needed; `self_check_input` and/or
  `self_check_output` when those built-in self-check tasks are selected; and
  other dedicated safety model types only when the selected rail documents that
  exact type. Do not rely on generic `type: safety` for self-check tasks.
- [ ] G011 Use `parameters.base_url` for NVIDIA endpoint base URLs with the
  default NeMo Guardrails framework. Do not use `parameters.nim_base_url` unless
  the generated repo explicitly sets `NEMOGUARDRAILS_LLM_FRAMEWORK=langchain`.
- [ ] G012 [input] Add `rails.input.flows` for selected input rails.
- [ ] G013 [output] Add `rails.output.flows` for selected output rails.
- [ ] G014 [output] If output rail streaming is selected, add top-level
  `streaming: True` and output `streaming.enabled`, `chunk_size`,
  `context_size`, and `stream_first`.
- [ ] G015 [retrieval] Add `rails.retrieval.flows` for selected retrieval rails.
- [ ] G016 [dialog] Add `rails.dialog` settings such as `single_call` or
  `user_messages.embeddings_only` only when needed.
- [ ] G017 [execution] Add `rails.execution.flows` for selected execution rails.
- [ ] G018 Run a config-load smoke check against the installed dependency as
  soon as repo dependencies are available:
  `python -c "import os; from nemoguardrails import RailsConfig; RailsConfig.from_path(os.getenv('GUARDRAILS_CONFIG_PATH', 'config/guardrails'))"`.
  If dependencies are not installed yet, carry this as a mandatory validation
  task; do not mark guardrails ready until it passes.

---

## Phase 3: Colang And Actions

**Purpose**: Implement selected rail behavior.

- [ ] G020 [P] [input] Write `config/guardrails/input.co` with input flows and
  any required input sanitization.
- [ ] G021 [P] [output] Write `config/guardrails/output.co` with output block,
  redaction, filtering, or fact-check flows.
- [ ] G022 [P] [dialog] Write `config/guardrails/dialog.co` with canonical user
  forms, required conversation paths, redirects, and allowed next steps.
- [ ] G023 [P] [retrieval] Write `config/guardrails/retrieval.co` with chunk
  validation or chunk modification flows.
- [ ] G024 [P] [execution] Write `config/guardrails/execution.co` with tool
  argument/result validation flows.
- [ ] G025 [P] Write `config/guardrails/actions.py` for explicit
  should-block/should-pass policy rules, such as diagnosis refusal or other
  patient privacy checks. Keep actions deterministic and unit-testable; use
  `context["last_user_message"]` for input rails and `context["bot_message"]`
  for output rails.
- [ ] G026 Confirm every flow referenced in `config.yml` is defined in Colang or
  supplied by a built-in Guardrails flow.
- [ ] G027 If `self_check_input` or `self_check_output` prompts are generated,
  use parser-compatible verdict wording: first line `safe` for allowed content
  and `unsafe` for blocked content, plus `output_parser: is_content_safe` and
  `max_tokens: 3`. Add matching `models` entries with `type: self_check_input`
  and/or `type: self_check_output`. Do not generate prompts that say
  `Return "yes"` for allowed content, `Return "no"` for blocked content, or
  `Answer (Yes/No)`. Do not use LLM self-check prompts for concrete
  should-block/should-pass policy lists; use custom actions from G025 instead.
  Do not point NVIDIA safety-guard JSON-output models at `is_content_safe`
  unless tests prove the installed model/config/parser combination returns a
  parseable verdict token.

---

## Phase 4: LangGraph Integration

**Purpose**: Wire Guardrails into the graph without changing the FastAPI server
contract.

- [ ] G030 In `agent/graph.py`, load
  `RailsConfig.from_path(os.getenv("GUARDRAILS_CONFIG_PATH", "config/guardrails"))`
  during graph construction when guardrails are enabled.
- [ ] G031 Instantiate `RunnableRails(config=rails_config, passthrough=True)`.
- [ ] G032 For tool-calling graphs, bind tools to the LLM before composing
  `guardrails | llm_with_tools`.
- [ ] G033 For prebuilt ReAct tool-calling graphs, do not pass raw
  `RunnableRails` or `guardrails | llm.bind_tools(tools)` directly to
  `create_react_agent`. Current LangGraph calls `.bind_tools()` on the model
  argument; generate a bind-tools adapter whose `bind_tools()` returns
  `guardrails | llm.bind_tools(tools)`, or replace the prebuilt path with an
  explicit `StateGraph` model node and `ToolNode`.
- [ ] G034 Keep `/v1/chat/completions` and SSE framing in `agent/server.py`
  unchanged except for any necessary error messages; do not implement
  `LLMRails.check_async()` in the server.
- [ ] G035 Ensure startup fails with a clear error if guardrails are enabled and
  config is missing or invalid.

---

## Phase 5: Tests

**Purpose**: Prove both enforcement and non-interference.

- [ ] G040 Write a parametrized case table in `tests/test_guardrails.py` with
  rail type, fixture, expected status, and observable assertion.
- [ ] G040a Add a mandatory config compatibility test in
  `tests/test_guardrails.py` that imports `RailsConfig` from the installed
  `nemoguardrails` package and loads
  `os.getenv("GUARDRAILS_CONFIG_PATH", "config/guardrails")`. Do not wrap this
  in `pytest.importorskip`; dependency or config incompatibility must fail
  validation before handoff. The generated file must include this test function:
  ```python
  def test_nemoguardrails_config_loads_with_installed_version():
      from nemoguardrails import RailsConfig

      RailsConfig.from_path(os.getenv("GUARDRAILS_CONFIG_PATH", "config/guardrails"))
  ```
- [ ] G041 [input] Add at least two should-block/modify and two should-pass
  cases for input rails.
- [ ] G042 [output] Add at least two should-block/modify and two should-pass
  cases for output rails.
- [ ] G043 [dialog] Add at least two blocked/redirected and two allowed
  multi-turn dialog cases.
- [ ] G044 [retrieval] Add at least two excluded/modified and two pass-through
  retrieved chunk cases.
- [ ] G045 [execution] Add at least two blocked/modified and two pass-through
  tool argument/result cases.
- [ ] G046 Add a server-level test confirming guarded responses still produce
  valid OpenAI-compatible SSE and terminate with `data: [DONE]`.
- [ ] G047 Add a tool-calling test confirming `passthrough=True` preserves tool
  call metadata and safe tool calls still execute.
- [ ] G048 Add a mocked `tests/test_graph.py` regression for ReAct plus
  Guardrails plus tools: fake `create_react_agent` must receive a model argument
  with `bind_tools()`, calling it must return the guarded composition, and the
  test must fail for the runtime error
  `AttributeError: 'RunnableRails' object has no attribute 'bind_tools'`.
- [ ] G049 Add tests that prevent guardrail verdict artifacts in voice output:
  for custom action rails, `tests/test_guardrails.py` must import the actions,
  prove `hello` and approved intake cases pass, prove diagnosis/privacy cases
  block, and assert the generated config has no `self_check_input`,
  `self_check_output`, or `prompts:` entries for those rails. For LLM self-check
  rails, it must reject `yes`/`no` verdict prompt wording and require
  `output_parser: is_content_safe` plus task-specific self-check model entries.
  `tests/test_server.py` must verify leading leaked verdict tokens (`yes.`,
  `No:`, `safe -`, `unsafe;`) are stripped from patient-facing text and must
  exercise the non-mock graph streaming path with a fake spoken chunk. It must
  also prove repeated full-message chunks and cumulative chunks are not emitted
  to the UI as duplicated text.

---

## Phase 6: Container And Docs

**Purpose**: Make Guardrails work in Docker and be maintainable by a future
developer or coding agent.

- [ ] G050 If guardrails are enabled, ensure `docker-compose.yml` mounts
  `./config:/app/config:ro` for `agent-backend`. Do not copy `config/` into the
  Docker image.
- [ ] G050a If guardrails are enabled, ensure `Dockerfile` installs
  `build-essential` before `pip install -r requirements.txt` and removes it
  afterward in the same layer. This is required because `nemoguardrails` can pull
  in `annoy`, which compiles a C++ extension and needs `g++` on
  `python:3.11-slim`.
- [ ] G051 Add `GUARDRAILS_ENABLED`, `GUARDRAILS_CONFIG_PATH`,
  `GUARDRAILS_SAFETY_MODEL`, and `GUARDRAILS_SAFETY_BASE_URL` to `.env.example`.
- [ ] G052 Update README with selected rail types, how to edit Colang rules,
  how to run guardrails tests, how to rebuild the stack, and the same first-run
  two-env-file setup gate used by the base stack (`.env` plus
  `../nemotron-voice-agent/config/.env`). Preserve the base static checks and
  `scripts/smoke_voice_connection.py` workflow.
- [ ] G053 Update `.agents/skills/<agent-name>/SKILL.md` with guardrails
  troubleshooting, test commands, and a Start workflow that refuses to run Docker
  Compose until both env files are configured. Preserve `docker compose up --build`
  as the launch command.
- [ ] G054 Document measured latency and streaming behavior for selected rail
  types, especially output rails.

---

## Phase 7: Validation

**Purpose**: Complete the guardrails feature only when behavior is traceable.

- [ ] G060 After `pip install -r requirements.txt`, run the config-load
  compatibility check in the repo virtual environment using the installed
  `nemoguardrails` version:
  `python -c "import os; from nemoguardrails import RailsConfig; RailsConfig.from_path(os.getenv('GUARDRAILS_CONFIG_PATH', 'config/guardrails'))"`.
  A failure is a blocker, not a warning.
- [ ] G061 Run `python -m pytest tests/test_guardrails.py -v`.
- [ ] G062 Run server SSE tests with guardrails enabled.
- [ ] G063 Run one manual adversarial session for every selected rail type.
- [ ] G064 Add any manual bypasses discovered in G063 back to
  `tests/test_guardrails.py`.
- [ ] G065 Confirm every `SC-XXX` in `specs/guardrails/spec.md` maps to a test
  or documented observable behavior.

---

## Dependencies & Execution Order

- Phase 0 decides whether this feature exists.
- Phase 1 precedes all other guardrails work.
- Phase 2 and Phase 3 can overlap after selected rail types are known.
- Phase 4 depends on `config.yml` existing.
- Phase 5 depends on Phase 3 and Phase 4.
- Phase 6 depends on the implemented config and integration.
- Phase 7 is final validation.

Parallel work:
- G020-G025 can run in parallel after G010-G017.
- G041-G045 can run in parallel after the corresponding rail files exist.

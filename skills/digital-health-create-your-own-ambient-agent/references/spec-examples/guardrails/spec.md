# Feature Specification: NeMo Guardrails

**Feature Branch**: `guardrails`
**Status**: Template
**Input**: Phase 2(f) guardrail selection, rules, safety model, and test cases

---

## User Scenarios & Testing

> **Developer note**: This feature is optional. If the developer chooses `skip`,
> `none`, or explicitly declines guardrails, omit this entire feature from the
> output repo. If enabled, include one user story per selected rail type. This
> reference spec covers all five rail types so generated specs can support any
> subset or all of them.

### User Story 1 - Input Rails Validate User Messages (Priority: P1)

The agent validates or sanitizes user input before the model call. Examples
include jailbreak detection, topic control, harmful-content blocking, and PII
masking.

**Why this priority**: Unsafe user input should not reach the model or tools.

**Independent Test**: Run the selected input-rail fixtures through the
guardrails runtime with the LLM mocked when possible. Assert block, modify, and
pass outcomes from this spec.

**Acceptance Scenarios**:

1. **Given** a user message that matches a should-block input case, **When** the
   input rails run, **Then** the agent refuses or redirects before the main model
   answers.
2. **Given** a user message containing data that should be sanitized, **When**
   the input rails run, **Then** the modified input passed forward no longer
   contains the unsafe content.
3. **Given** a legitimate clinical request that resembles a blocked class,
   **When** the input rails run, **Then** the request passes without interception.

### User Story 2 - Output Rails Validate Model Responses (Priority: P1)

The agent evaluates model output before it is returned to the voice interface.
Examples include sensitive-data redaction, final-answer safety checks, and
fact-checking.

**Why this priority**: A healthcare voice agent may have access to sensitive
context; unsafe or private output must not be spoken to the user.

**Independent Test**: Feed representative model outputs into the selected output
rails and assert should-block, should-modify, and should-pass behavior.

**Acceptance Scenarios**:

1. **Given** a model response that violates a configured rule, **When** output
   rails run, **Then** the response is blocked or replaced with the configured
   refusal/redirect.
2. **Given** a response containing content that should be redacted, **When**
   output rails run, **Then** the final spoken text contains the redacted form.
3. **Given** a safe clinical response, **When** output rails run, **Then** the
   response passes unchanged.

### User Story 3 - Dialog Rails Control Multi-Turn Flow (Priority: P1)

The agent enforces required conversation steps across turns. Examples include
confirming patient identity before scheduling, asking required intake questions,
or redirecting off-topic turns back to the configured workflow.

**Why this priority**: Clinical workflows depend on order, consent, and context.

**Independent Test**: Run multi-turn conversation fixtures and assert the next
bot action follows the configured dialog flow.

**Acceptance Scenarios**:

1. **Given** a user tries to skip a required prerequisite, **When** dialog rails
   run, **Then** the agent asks for the missing prerequisite first.
2. **Given** the user completes the prerequisite, **When** dialog rails run,
   **Then** the agent advances to the next allowed step.
3. **Given** a user goes off-topic, **When** dialog rails run, **Then** the agent
   redirects according to the configured flow.

### User Story 4 - Retrieval Rails Filter Context (Priority: P2)

The agent validates retrieved chunks before they are used as model context.
Examples include excluding untrusted sources, masking sensitive data in retrieved
chunks, and checking retrieval relevance.

**Why this priority**: RAG answers should not be grounded in unsafe, irrelevant,
or unauthorized context.

**Independent Test**: Pass retrieved chunk fixtures into the selected retrieval
rails and assert excluded, modified, and pass-through outcomes.

**Acceptance Scenarios**:

1. **Given** a retrieved chunk marked untrusted or unauthorized, **When**
   retrieval rails run, **Then** the chunk is excluded from `$relevant_chunks`.
2. **Given** a retrieved chunk containing data that should be masked, **When**
   retrieval rails run, **Then** the masked chunk is used instead.
3. **Given** a trusted and relevant clinical chunk, **When** retrieval rails run,
   **Then** it remains available to the model.

### User Story 5 - Execution Rails Control Tool Calls (Priority: P1)

The agent validates tool/action calls, arguments, and results. Examples include
blocking a scheduling tool call before patient identity is confirmed, rejecting
unsafe arguments, and filtering sensitive tool results.

**Why this priority**: Tool calls can mutate external systems or expose private
data, so they need explicit controls.

**Independent Test**: Run tool-call argument and result fixtures through the
execution rails and assert block, modify, and pass outcomes.

**Acceptance Scenarios**:

1. **Given** a tool call missing required identity or authorization fields,
   **When** execution rails run, **Then** the tool call is blocked.
2. **Given** a tool result containing data that should not be exposed, **When**
   execution rails run, **Then** the result is redacted or blocked before the
   model can use it.
3. **Given** a valid tool call and safe result, **When** execution rails run,
   **Then** the call/result passes.

### Edge Cases

- What if the developer chooses no guardrails?
  -> Do not generate `specs/guardrails/`, `config/guardrails/`,
  `tests/test_guardrails.py`, or `nemoguardrails` in `requirements.txt`.
- What if the developer chooses all rail types?
  -> Generate all five story sections in the output spec and all five
  corresponding config/test sections.
- What if a selected rail type has no should-pass cases?
  -> Stop and ask for should-pass cases before implementation; testing only
  blocks produces false positives in clinical workflows.
- What if a rail blocks a legitimate clinical request?
  -> Treat it as a P1 false positive and update the should-pass suite.
- What if output rails are enabled with a voice interface?
  -> Measure added latency. If streaming output rails are configured, document
  `chunk_size`, `context_size`, and `stream_first`; otherwise document that the
  response may be buffered before TTS.
- What if the installed NeMo Guardrails schema differs from this reference?
  -> Follow the checked local docs in `references/reference-repos/nemo-guardrails/`
  and record the version-specific deviation in `specs/guardrails/plan.md`.

---

## Requirements

### Functional Requirements

- **FR-001**: The generated agent MUST ask the developer whether to enable NeMo
  Guardrails only after a live read of the official NVIDIA NeMo Guardrails docs.
  The prompt MUST summarize the current rail type options and MUST support
  `none`, any subset, or all five rail types: `input`, `output`, `dialog`,
  `retrieval`, and `execution`.
- **FR-002**: If guardrails are skipped, the repo MUST omit guardrails config,
  guardrails tests, and `nemoguardrails` dependency declarations.
- **FR-003**: If guardrails are enabled, the repo MUST include
  `specs/guardrails/spec.md`, `plan.md`, and `tasks.md` derived from the
  selected rail types and developer-provided rules.
- **FR-004**: `config/guardrails/config.yml` MUST configure only selected rail
  types using current NeMo schema keys: `rails.input.flows`,
  `rails.output.flows`, `rails.retrieval.flows`, `rails.dialog`, and
  `rails.execution.flows`.
- **FR-004a**: Guardrails model entries MUST use `parameters.base_url` with the
  default NeMo Guardrails framework. `parameters.nim_base_url` is a 0.21-style
  LangChain convention in `nemoguardrails` 0.22.x unless the generated repo
  explicitly sets `NEMOGUARDRAILS_LLM_FRAMEWORK=langchain`.
- **FR-005**: `config/guardrails/` MUST include Colang files and optional
  `actions.py` functions for the selected rules. One file per selected rail
  type is preferred for maintainability.
- **FR-006**: Guardrails MUST integrate with LangGraph through
  `RunnableRails` in `agent/graph.py`; do not implement this feature with
  `LLMRails.check_async()` in `agent/server.py` or LangChain
  `GuardrailsMiddleware`.
- **FR-007**: Tool-calling graphs MUST use `RunnableRails(..., passthrough=True)`
  and bind tools before composing the guarded model runnable.
- **FR-007a**: When using `create_react_agent` with tools and Guardrails, the
  model argument passed to `create_react_agent` MUST expose `bind_tools()`.
  Generated code MUST NOT pass raw `RunnableRails` or
  `guardrails | llm.bind_tools(tools)` directly as that model argument because
  LangGraph calls `.bind_tools()` during agent construction.
- **FR-008**: The graph MUST fail fast at startup when guardrails are enabled
  and `config/guardrails/config.yml` is missing or cannot be loaded.
- **FR-009**: `requirements.txt` MUST include `nemoguardrails` only when this
  feature is enabled.
- **FR-010**: Docker Compose MUST mount `config/` into the `agent-backend`
  container when guardrails are enabled. The Docker image MUST NOT copy generated
  `config/` into the image.
- **FR-010a**: The Dockerfile MUST temporarily install `build-essential` before
  `pip install -r requirements.txt` and remove it afterward when guardrails are
  enabled, because `nemoguardrails` may install `annoy`, which compiles a C++
  extension and needs `g++` on `python:3.11-slim`.
- **FR-011**: `tests/test_guardrails.py` MUST include at least two should-block
  or should-modify cases and two should-pass cases per selected rail type.
- **FR-011a**: `tests/test_guardrails.py` MUST include a mandatory config
  compatibility test that imports `RailsConfig` from the installed
  `nemoguardrails` package and loads
  `os.getenv("GUARDRAILS_CONFIG_PATH", "config/guardrails")`. This test MUST NOT
  use `pytest.importorskip`; after dependencies are installed, a missing package
  or schema/key mismatch is a validation failure.
- **FR-011b**: If generated guardrails use `self_check_input` or
  `self_check_output`, the prompts MUST use parser-compatible `safe`/`unsafe`
  verdict wording with `output_parser: is_content_safe`. Generated prompts MUST
  NOT use `yes` for allowed content, `no` for blocked content, or unparsed
  `Answer (Yes/No)` classifier wording.
- **FR-011c**: The FastAPI response path MUST strip leaked leading guardrail
  verdict tokens (`yes`, `no`, `safe`, `unsafe`) from patient-facing text before
  SSE or non-streaming output.
- **FR-011d**: If generated guardrails use `self_check_input` or
  `self_check_output`, `config.yml` MUST include task-specific model entries
  with `type: self_check_input` and/or `type: self_check_output`. A generic
  `type: safety` model entry is not sufficient for those built-in tasks.
- **FR-011e**: Explicit developer-approved should-block/should-pass policy lists
  MUST be implemented as deterministic custom actions rather than LLM
  self-check prompts. Generated tests MUST prove a plain greeting such as
  `hello` passes and the approved block/pass examples behave as specified.
- **FR-011f**: NVIDIA safety-guard JSON-output models MUST NOT be wired to
  NeMo's `is_content_safe` self-check parser unless a generated compatibility
  test proves the installed model/config/parser combination returns a parseable
  verdict token.
- **FR-012**: Guardrails tests MUST assert observable behavior, not just internal
  function calls: refuse/redirect, redaction/filtering, chunk exclusion, tool
  blocking, or pass-through.
- **FR-013**: Output, dialog, retrieval, and execution rails MUST have latency
  implications documented in README and `.agents/skills/<agent-name>/SKILL.md`.
- **FR-014**: If output rail streaming is configured, `config.yml` MUST record
  `streaming: True` and the output rail `streaming` subfields used.
- **FR-015**: Every selected rail type MUST be traceable from
  `specs/guardrails/spec.md` to config files and tests.
- **FR-016**: Guardrails documentation updates MUST preserve the base repo startup
  contract: both `README.md` and `.agents/skills/<agent-name>/SKILL.md` must keep
  the two-env-file setup gate for `.env` and
  `../nemotron-voice-agent/config/.env` before Docker Compose is run.
- **FR-017**: Guardrails additions MUST preserve the base static checks,
  `scripts/smoke_voice_connection.py`, and direct `docker compose up --build`
  launch flow.
- **FR-016**: The developer-facing guardrails prompt MUST include this guidance:
  "If you are new to guardrails or could not decide on what type of guardrails to
  implement, you could start with input rails only and add more later on."

### Key Entities

- **GuardrailSelection**: The normalized set of selected rail types from
  Phase 2(f). Empty means the feature is skipped.
- **LiveDocsSummary**: The concise rail type summary produced from official
  NVIDIA NeMo Guardrails docs immediately before asking the developer to choose
  guardrails.
- **GuardrailRule**: A developer-provided policy to block, redirect, modify, or
  allow specific behavior.
- **RailFlow**: A named Colang flow referenced from `config.yml`.
- **RailsConfig**: Runtime configuration loaded by `RailsConfig.from_path`.
- **RunnableRailsWrapper**: `RunnableRails` instance composed with the LangGraph
  model runnable.
- **SafetyModelConfig**: Model and endpoint used for safety checks. Defaults to
  NVIDIA public cloud endpoints unless the developer overrides them.
- **GuardrailTestCase**: Parametrized fixture with rail type, input fixture,
  expected status (`block`, `modify`, or `pass`), and observable assertion.
- **LatencyMeasurement**: Recorded overhead for selected rail types in local
  test or manual validation.

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: For every selected rail type, `config/guardrails/config.yml`
  contains the corresponding NeMo configuration section and flow references.
- **SC-002**: `RailsConfig.from_path(os.getenv("GUARDRAILS_CONFIG_PATH",
  "config/guardrails"))` loads without errors in a local virtual environment
  after `pip install -r requirements.txt`, using the installed unpinned
  `nemoguardrails` version.
- **SC-003**: `python -m pytest tests/test_guardrails.py -v` passes with
  the mandatory config compatibility test plus should-block, should-modify, and
  should-pass coverage for every selected rail type.
- **SC-004**: False-positive coverage exists: each selected rail type has
  legitimate clinical should-pass cases that resemble blocked cases.
- **SC-005**: The FastAPI SSE endpoint still returns valid OpenAI-compatible SSE
  and terminates with `data: [DONE]` when guardrails are enabled.
- **SC-006**: Tool-calling tests pass with guardrails enabled and
  `passthrough=True`.
- **SC-006a**: A mocked graph-construction regression test passes for ReAct plus
  Guardrails plus tools, proving `create_react_agent` receives a model with
  `bind_tools()` and preventing
  `AttributeError: 'RunnableRails' object has no attribute 'bind_tools'`.
- **SC-006b**: Guardrails implementation tests pass. For deterministic custom
  action rails, tests prove `hello` and approved intake cases pass, approved
  diagnosis/privacy cases block, and no LLM self-check prompts are generated for
  those rails. For LLM self-check rails, prompt tests prove self-check prompts do
  not use `yes`/`no` verdict instructions and do include
  `output_parser: is_content_safe` plus task-specific self-check model entries.
- **SC-006c**: Server response tests pass, proving leaked leading guardrail
  verdict prefixes are removed before patient-facing text is returned.
- **SC-007**: Output rail latency is measured and documented when output rails
  are selected. If streaming output rails are configured, tests verify the
  selected streaming behavior.
- **SC-008**: When guardrails are skipped, no guardrails-only files are generated
  and normal LangGraph/FastAPI tests still pass.
- **SC-009**: README and runnable skill include instructions for editing Colang
  rules, running guardrails tests, rebuilding the Docker stack, and interpreting
  guardrails latency.

---

## Assumptions

- NeMo Guardrails is optional and selected only through Phase 2(f).
- Phase 2(f) always starts with a live read of the official NVIDIA NeMo
  Guardrails docs. Local checked docs are secondary references for installed
  examples and syntax.
- The fixed architecture remains LangGraph plus FastAPI plus Nemotron Voice
  Agent; guardrails are an optional LangGraph graph concern, not a FastAPI
  server middleware concern.
- The current NeMo Guardrails documentation defines five categories: input,
  output, retrieval, dialog, and execution rails.
- The current `config.yml` schema supports `rails.execution.flows` for execution
  rails. If the installed dependency version differs from the current docs, the
  implementation must update the config to match the installed package and
  record the difference.
- `RunnableRails` can stream when used directly, but the LangGraph integration
  may produce larger chunks after node processing; guardrails-enabled validation
  checks valid SSE framing and documented latency rather than first-token timing.
- `passthrough=True` is required for tool-calling compatibility.
- All model services default to NVIDIA public cloud endpoints and use
  `NVIDIA_API_KEY` unless the developer chooses a self-hosted endpoint.

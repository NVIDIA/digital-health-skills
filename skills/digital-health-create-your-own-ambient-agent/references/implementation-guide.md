# Implementation Guide

Use this reference for Phase 4. It covers output repo layout, required
sub-skills, reference code, Docker Compose constraints, documentation
requirements, runnable skill generation, and full-stack startup.

## Contents

- Phase 4: Implement
- Output location and sub-skill gate
- Reference code and output repository structure
- Implementation order
- Architecture constraints
- Documentation requirements
- Generated runnable skill requirements
- Running the full stack
- Phase 4 sub-skill summary

## Phase 4: Implement

### Output Location

Use the `<output-parent>` confirmed in Phase 2(a). The agent backend goes to
`<output-parent>/my-custom-ambient-healthcare-agent/` and the Nemotron Voice
Agent is already cloned at `<output-parent>/nemotron-voice-agent/`.

### Sub-skill Gate

Before writing any output repo files, verify the five dependent sub-skills from
Step 1 are available. This is not optional. If any of these paths are missing,
return to Step 1 and install or verify the sub-skills before continuing:

- `langchain-dependencies`
- `langchain-fundamentals`
- `langgraph-fundamentals`
- `langchain-rag`
- `nemotron-voice-agent-deploy`

During implementation, use the installed sub-skill when the runtime can invoke
it. If the runtime cannot invoke installed skills directly, read the cloned
`SKILL.md` file listed below before writing code in that domain. Record every
sub-skill that was invoked or read in the Phase 4 summary.

### Reference Code

Before writing any code, invoke the relevant installed sub-skills when the
runtime supports skill invocation; otherwise read the referenced cloned
`SKILL.md` files. Then read the reference implementations in this skill:

- Before writing `requirements.txt` — invoke/read **`langchain-dependencies`**
  from the installed skill path or
  `references/reference-repos/langchain-skills/config/skills/langchain-dependencies/SKILL.md`
  — for correct package versions and known incompatibilities.
- Before writing any tool file or `graph.py` with the ReAct pattern —
  invoke/read **`langchain-fundamentals`** from the installed skill path or
  `references/reference-repos/langchain-skills/config/skills/langchain-fundamentals/SKILL.md`
  — for `create_react_agent` and `@tool` decorator usage.
- Before writing `graph.py` for any graph type — invoke/read
  **`langgraph-fundamentals`** from the installed skill path or
  `references/reference-repos/langchain-skills/config/skills/langgraph-fundamentals/SKILL.md`
  — for StateGraph, nodes, edges, reducers, Command, and streaming patterns.
- Before writing any data-retrieval tool if the developer chose NVIDIA RAG —
  invoke/read **`langchain-rag`** from the installed skill path or
  `references/reference-repos/langchain-skills/config/skills/langchain-rag/SKILL.md`.
- Before writing `docker-compose.yml` — invoke/read
  **`nemotron-voice-agent-deploy`** from the installed skill path or
  `references/reference-repos/nemotron-voice-agent/.agents/skills/nemotron-voice-agent-deploy/SKILL.md`
  — for correct service configuration, health check rules, and transport setup.
- Before writing guardrails config (if guardrails enabled in Phase 2(f)) — do a
  live read of the official NVIDIA NeMo Guardrails docs again, then use
  `references/reference-repos/nemo-guardrails/docs/` and
  `references/reference-repos/nemo-guardrails/examples/` for syntax and examples
  that match the installed reference checkout. **Key live docs**:
  `https://docs.nvidia.com/nemo/guardrails/latest/about/rail-types.html`,
  `https://docs.nvidia.com/nemo/guardrails/latest/configure-rails/yaml-schema/guardrails-configuration/index.html`,
  `https://docs.nvidia.com/nemo/guardrails/latest/integration/langchain/runnable-rails.html`,
  and `https://docs.nvidia.com/nemo/guardrails/latest/integration/langchain/langgraph-integration.html`.

Reference files in this skill:

- `references/langgraph-backend/graph.py` — A ReAct agent example using
  `create_react_agent` with `ChatNVIDIA` from `langchain_nvidia_ai_endpoints`.
  Uses the public NVIDIA AI Endpoint by default; set `LLM_BASE_URL` to a local
  NIM URL to switch to a self-hosted model. Use as a starting point for the ReAct
  pattern; use as a structural reference (env var loading, singleton, streaming
  filter) for other graph patterns. Always adapt to the graph pattern chosen in (d).
- `references/langgraph-backend/server.py` — FastAPI server with
  `/v1/chat/completions`, `/v1/models`, and `/health`. Copy as `agent/server.py`.
  **Do not rewrite from scratch** — the streaming and SSE logic is load-bearing.
- `references/langgraph-backend/tools/example_tool.py` — Annotated tool template.
  One file per tool in `agent/tools/`.
- `references/langgraph-backend/requirements.txt` — Minimal dependency set.

The Nemotron Voice Agent is already cloned at `<output-parent>/nemotron-voice-agent/`
from Phase 2(a). Read its `docker-compose.yml` and `.env.example` to confirm
port mappings and env var names before writing the agent docker-compose.

### Output Repository Structure

```
my-custom-ambient-healthcare-agent/
├── specs/
│   ├── langgraph-agent/
│   │   ├── spec.md                  # Approved functional spec (Phase 2)
│   │   ├── plan.md                  # Approved technical plan (Phase 3)
│   │   └── tasks.md                 # Approved task list (Phase 3)
│   ├── fastapi-server/
│   │   ├── spec.md                  # Approved functional spec (Phase 2)
│   │   ├── plan.md                  # Approved technical plan (Phase 3)
│   │   └── tasks.md                 # Approved task list (Phase 3)
│   └── guardrails/                   # Only if guardrails enabled in Phase 2(f)
│       ├── spec.md                  # Selected rail types, rules, examples
│       ├── plan.md                  # RunnableRails + config integration plan
│       └── tasks.md                 # Guardrails implementation and validation tasks
├── README.md                        # Human-readable getting-started guide
├── docker-compose.yml               # Orchestrates backend + voice agent frontend
├── Dockerfile
├── .env.example                     # All required env vars with defaults
├── .gitignore
├── requirements.txt
├── agent/
│   ├── __init__.py
│   ├── graph.py                     # LangGraph agent (pattern from specs/langgraph-agent/plan.md)
│   ├── server.py                    # FastAPI OpenAI-compatible server
│   └── tools/                      # One file per agent capability
│       ├── __init__.py
│       └── <tool_name>.py
├── config/
│   └── guardrails/                  # (only if guardrails enabled in Phase 2(f))
│       ├── config.yml               # NeMo Guardrails runtime config
│       ├── *.co                     # Colang rail definitions (one file per selected rail type)
│       └── actions.py               # Optional custom rail actions, if needed
├── tests/
│   ├── test_tools.py                # Unit tests — each tool in isolation, no LLM
│   ├── test_graph.py                # Graph tests with mocked LLM/tool calls
│   ├── test_server.py               # Integration tests — FastAPI endpoint with real LLM
│   └── test_guardrails.py           # (only if guardrails enabled) parametrized block/modify/pass suite
├── scripts/
│   └── smoke_voice_connection.py    # Verifies running Docker stack wiring, ports, and model id
├── docs/
│   ├── architecture.md              # ASCII/Mermaid diagram + explanation
│   └── voice-integration.md         # API contract with Nemotron Voice Agent
└── .agents/
    └── skills/
        └── <agent-name>/
            └── SKILL.md             # Agent-readable skill: start, stop, test, configure the agent
```

### Implementation Order

Execute tasks in this order: `specs/langgraph-agent/tasks.md`, then
`specs/guardrails/tasks.md` if guardrails were enabled, then
`specs/fastapi-server/tasks.md`. The standard sequence across selected features is:

1. Data layer — schema, seed data, basic CRUD (langgraph-agent tasks)
2. Agent tools — one file per tool, each independently testable; write `tests/test_tools.py` alongside each tool (langgraph-agent tasks)
3. LangGraph graph — wire tools into `graph.py` using the reference as base (langgraph-agent tasks)
4. Guardrails — if enabled in Phase 2(f): add `nemoguardrails` to `requirements.txt`, write Colang files/actions in `config/guardrails/`, wire `RunnableRails` into `agent/graph.py` around the model runnable (`passthrough=True` for tool-calling), and write `tests/test_guardrails.py` using the should-block/modify/pass cases from the spec. The test file must also include a mandatory config compatibility test that imports the installed `nemoguardrails` package and runs `RailsConfig.from_path(os.getenv("GUARDRAILS_CONFIG_PATH", "config/guardrails"))` without `pytest.importorskip`.
5. FastAPI server — copy `references/langgraph-backend/server.py` as `agent/server.py`; write `tests/test_server.py` (fastapi-server tasks)
6. Configuration — `.env.example`, docker-compose (fastapi-server tasks)
7. Documentation — create the human-readable `README.md` and `docs/`
8. Runnable skill — create the agent-readable `.agents/skills/<agent-name>/SKILL.md` (see "Runnable Skill" below)
9. Static reliability checks — compile/import smoke, placeholder scan, and `docker compose config`
10. Docker stack — configure both env files, build images with `docker compose up --build`, and verify the full stack (see "Running the Full Stack" below)

### Architecture Constraints

**Always use WebRTC transport.**
Generate docker-compose with `TRANSPORT=WEBRTC` and `src/pipeline.py`. The
WebSocket UI is a bare dev tool; the WebRTC UI is the full React app.

**Launch contract — Docker Compose stays primary.**
The generated repo's launch path remains direct Docker Compose:

```bash
docker compose up --build
```

Do not replace this with a required wrapper such as `make up`, a preflight
launcher, or an env-generation script. It is fine to generate tests and smoke
scripts, but the README and runnable skill must keep `docker compose up --build`
as the command that starts the stack.

**All ports via env vars — never hardcoded.**

```python
AGENT_PORT = int(os.getenv("AGENT_PORT", "8000"))
```

Every port must appear in `.env.example`:

| Env var | Default | Notes |
|---|---|---|
| `AGENT_PORT` | `8000` | Agent backend FastAPI server |
| `VOICE_AGENT_PORT` | `7860` | **Fixed** — WebRTC React UI hardcodes `:7860/offer` |
| `VOICE_AGENT_UI_PORT` | `9000` | Browser-facing WebRTC UI |

Allowed flexibility:
- `AGENT_PORT` may be changed; docker-compose port mapping, backend runtime port,
  health check, and voice-agent `NVIDIA_LLM_URL` must all track it.
- `VOICE_AGENT_UI_PORT` may be changed; it only controls the browser-facing UI
  host port.
- `VOICE_AGENT_PORT` must remain `7860` for WebRTC unless the upstream
  Nemotron Voice Agent frontend has been rebuilt and verified with a different
  hardcoded WebRTC signalling port.

Use both sides of the port mapping in docker-compose so the container port
tracks the env var:
```yaml
ports:
  - "${AGENT_PORT:-8000}:${AGENT_PORT:-8000}"
```

**VOICE_AGENT_PORT is fixed at 7860.** Remapping the host side breaks browser
WebRTC connectivity. Document this constraint in the README.

**Testing — always use a virtual environment.**
Never install packages or run tests against the system Python. The README and
any Makefile targets must include:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest tests/ -v
```

`.venv/` must be in `.gitignore`. All `pip install` and `pytest` invocations in
docs and automation must activate the venv first or use `.venv/bin/python -m`.

**Docker Compose health checks:**

```yaml
# agent-backend — python is available
healthcheck:
  test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:${AGENT_PORT:-8000}/health').read()\""]
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 30s

# nemotron-voice-agent — use curl + /docs, NOT python, NOT /health
healthcheck:
  test: ["CMD-SHELL", "curl -sf http://localhost:7860/docs || exit 1"]
  interval: 15s
  timeout: 10s
  retries: 5
  start_period: 60s

# voice-agent-ui — delay 15 s to avoid cold-start WebRTC race
# IMPORTANT: use exec form (array), NOT shell form. The frontend image is
# nvcr.io/nvidia/distroless/python — no sh/bash present. Shell form triggers
# the Go shell_wrapper entrypoint which panics with "sh: executable file not found".
command: ["python", "-c", "import time; time.sleep(15); exec(open('start-server.py').read())"]
depends_on:
  nemotron-voice-agent:
    condition: service_healthy
```

**LLM env vars:**

The agent backend uses `ChatNVIDIA` from `langchain_nvidia_ai_endpoints`.
`LLM_BASE_URL` defaults to the public NVIDIA AI Endpoint — no local GPU is
required. Override it with a local NIM URL (e.g. `http://localhost:8000/v1`)
to route requests to a self-hosted model.

| Env var | Default | Notes |
|---|---|---|
| `AGENT_MODEL_NAME` | `<agent-name>` | Model id exposed by `/v1/models`; `NVIDIA_LLM_MODEL` in the voice agent must match this |
| `LLM_MODEL` | `nvidia/nemotron-3-super-120b-a12b` | Any model on build.nvidia.com or a local NIM |
| `LLM_BASE_URL` | `https://integrate.api.nvidia.com/v1` | Optional — this is the `ChatNVIDIA` default; override for self-hosted NIM |
| `NVIDIA_API_KEY` | _(required)_ | From build.nvidia.com; not needed for unauthenticated local NIMs |
| `LLM_ENABLE_THINKING` | `"true"` | Only pass to models that support it (e.g. Nemotron Super) |
| `LLM_TEMPERATURE` | `0.0` | |
| `LLM_MAX_TOKENS` | `8192` | |
| `LLM_MOCK_MODE` | `"false"` | Testing-only deterministic server response; never enable by default in Docker docs |

Only pass `enable_thinking` in the API call when `LLM_ENABLE_THINKING=true`
AND the model supports it. Passing it to unsupported models causes API errors.

The FastAPI server must expose `/v1/models` using `AGENT_MODEL_NAME`. The
`nemotron-voice-agent` Docker Compose service must set
`NVIDIA_LLM_MODEL=${AGENT_MODEL_NAME:-<agent-name>}` so the voice stack and
backend advertise the same model id. Add a non-secret `GET /debug/config`
endpoint that reports effective `AGENT_MODEL_NAME`, `AGENT_PORT`, `LLM_MODEL`,
`LLM_BASE_URL`, `LLM_MOCK_MODE`, `GUARDRAILS_ENABLED`, and `LOG_LEVEL`.

**Logging** — Use Python's `logging` module (never `print`) throughout the agent
backend. Configure with `LOG_LEVEL` env var (default `INFO`). Use
`logger = logging.getLogger(__name__)` per module. Emit a structured log line
for each of these agent events:

| Event | Level | Content |
|---|---|---|
| Request received | INFO | method, path, first 200 chars of body; redact known PII field names |
| Tool call | INFO | tool name, arguments (redact PII field values) |
| Tool result | INFO | tool name, first 200 chars of result |
| LLM response | INFO | first 500 chars of generated text |
| Stream complete | INFO | total chunk count |
| Unhandled exception | ERROR | full traceback |

Add `LOG_LEVEL` to `.env.example`.

**Docker — mount generated source/config at runtime:**
Do not bake generated `agent/` or `config/` directories into the
`agent-backend` image. The Docker image should install Python dependencies only;
`docker-compose.yml` must mount the generated repo directories at runtime so
source and guardrails config edits are picked up by container recreation without
a backend image rebuild:

```yaml
services:
  agent-backend:
    volumes:
      - ./agent:/app/agent:ro
      - ./config:/app/config:ro    # include only when config/ exists
      - ./data:/app/data           # include when generated tools persist files
```

Keep `GUARDRAILS_CONFIG_PATH=config/guardrails` so the in-container path resolves
to `/app/config/guardrails`. If no generated feature creates `config/`, omit the
config mount; do not add `COPY config/` to the Dockerfile.

**Guardrails — Dockerfile must temporarily install `build-essential`:**
When guardrails are enabled, `nemoguardrails` can pull in `annoy`, which may
compile a C++ extension during `pip install`. `python:3.11-slim` does not include
`g++`, so the Docker build fails unless build tools are present. Generate the
Dockerfile so `build-essential` is installed before `pip install` and removed in
the same layer afterward to keep the final image slim:

```dockerfile
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/*
```

Use this temporary build-tool pattern whenever `nemoguardrails` is present in
`requirements.txt`. If guardrails are skipped and no package needs native
compilation, a plain `pip install --no-cache-dir -r requirements.txt` is fine.

**Guardrails config — use `base_url` for the default framework:**
`nemoguardrails` 0.22.x uses the default framework unless
`NEMOGUARDRAILS_LLM_FRAMEWORK=langchain` is explicitly set. With that default
framework, `parameters.nim_base_url` is treated as a 0.21-style LangChain
convention and raises a migration error. Use `parameters.base_url` for NVIDIA
OpenAI-compatible endpoints:
```yaml
models:
  - type: self_check_input
    engine: nvidia_ai_endpoints
    model: nvidia/llama-3.1-nemotron-safety-guard-8b-v3
    parameters:
      base_url: https://integrate.api.nvidia.com/v1
  - type: self_check_output
    engine: nvidia_ai_endpoints
    model: nvidia/llama-3.1-nemotron-safety-guard-8b-v3
    parameters:
      base_url: https://integrate.api.nvidia.com/v1
```
Only use `nim_base_url` if the generated repo also sets
`NEMOGUARDRAILS_LLM_FRAMEWORK=langchain` intentionally.

**Guardrails config — include the models required by the configured rails:**
`RunnableRails` composes with the agent's model runnable, but NeMo config still
needs any models used by the selected rails. Include the `main` model when rails
need generation, dialog reasoning, or dynamic responses. For built-in self-check
rails, include task-specific models named exactly `self_check_input` and/or
`self_check_output`; do not rely on a generic `type: safety` entry for these
tasks, because NeMo selects models by task type and can otherwise fall back to
the main model. Include other dedicated safety model types only when the selected
rail or action documents that exact type. Use static Colang responses only when a
rail can return a fixed refusal or redirect without an extra model call.

**Guardrails explicit policy rails — prefer deterministic custom actions:**
When the developer provides concrete should-block and should-pass examples,
generate deterministic Python actions and Colang flows instead of LLM
`self_check_input` / `self_check_output` prompts. This is required for policies
like "do not diagnose" and "do not reveal other patients' information", where
the approved examples can be expressed as local rules. It also avoids provider
format drift: NVIDIA safety-guard NIMs can return their native JSON safety
schema, which is not parseable by NeMo's `is_content_safe` parser and can
fail-close normal input such as `hello`.

Use `config/guardrails/actions.py` with `@action(is_system_action=True)` and
the context keys `last_user_message` for input rails and `bot_message` for
output rails. The Colang flow should execute those custom action names, for
example `check_patient_intake_input`, instead of executing NeMo's built-in
`self_check_input`.

Generated tests must prove the custom action allows a plain greeting such as
`hello`, allows the approved should-pass intake cases, and blocks the approved
diagnosis/privacy cases. They must also assert the generated guardrails config
does not contain LLM self-check prompts when deterministic custom actions are
used.

**Guardrails config — map rail types to schema keys:**
Use the schema keys supported by the installed `nemoguardrails` version. Current
NeMo Guardrails docs use `rails.input.flows`, `rails.output.flows`,
`rails.retrieval.flows`, `rails.dialog` options, and `rails.execution.flows`.
If the cloned reference repo documents a version-specific difference, follow the
local checked docs and record the deviation in `specs/guardrails/plan.md`.

**Guardrails self-check prompts — never leak classifier verdicts:**
Use this path only when the developer explicitly needs an LLM-based self-check
that cannot be expressed as deterministic custom actions. Do not use this path
for concrete should-block/should-pass policy lists, and do not point
NVIDIA safety-guard JSON-output models at `is_content_safe` unless a generated
test proves the installed model/config/parser combination returns the expected
parser token.

When generating `self_check_input` or `self_check_output` prompts, do not ask the
model to return `"yes"` for allowed content and `"no"` for blocked content.
NeMo's built-in `is_content_safe` parser treats `yes` as unsafe and `no` as
safe, so reversed wording can cause false blocks and visible `yes`/`no` artifacts
in voice responses. Use parser-compatible `safe`/`unsafe` wording and register
the parser explicitly:

```yaml
models:
  - type: self_check_input
    engine: nvidia_ai_endpoints
    model: nvidia/llama-3.1-nemotron-safety-guard-8b-v3
    parameters:
      base_url: https://integrate.api.nvidia.com/v1
  - type: self_check_output
    engine: nvidia_ai_endpoints
    model: nvidia/llama-3.1-nemotron-safety-guard-8b-v3
    parameters:
      base_url: https://integrate.api.nvidia.com/v1

prompts:
  - task: self_check_output
    content: |
      Check whether the response is safe to speak.
      Agent response: "{{ bot_response }}"
      First line must read "safe" if the response is allowed, otherwise "unsafe".
    output_parser: is_content_safe
    max_tokens: 3
```

Generated repos must include tests that reject `Return "yes"`,
`Return "no"`, and `Answer (Yes/No)` in guardrails prompts, assert
`output_parser: is_content_safe` is present for self-check tasks, assert
task-specific `type: self_check_input` and `type: self_check_output` model
entries are present whenever those prompts are present, and assert the server
strips any leaked leading `yes`, `no`, `safe`, or `unsafe` verdict token from
patient-facing responses before SSE or non-streaming output.

**Guardrails + ReAct tool calling — expose `bind_tools` before handoff:**
For generated ReAct graphs that use `create_react_agent`, the model argument
must have a `.bind_tools()` method. Do not pass `RunnableRails` or a
`guardrails | llm.bind_tools(tools)` runnable sequence directly as the
`create_react_agent` model. Use this adapter pattern, or use an explicit
`StateGraph`:

```python
class GuardedToolBindingModel:
    def __init__(self, guardrails, llm):
        self._guardrails = guardrails
        self._llm = llm

    def __getattr__(self, name):
        return getattr(self._llm, name)

    def bind_tools(self, tools, *args, **kwargs):
        return self._guardrails | self._llm.bind_tools(tools, *args, **kwargs)


rails_config = RailsConfig.from_path(os.getenv("GUARDRAILS_CONFIG_PATH", "config/guardrails"))
guardrails = RunnableRails(config=rails_config, passthrough=True)
model_runnable = GuardedToolBindingModel(guardrails, llm)
graph = create_react_agent(model_runnable, tools=tools)
```

Generate a `tests/test_graph.py` regression test for this path. The test should
mock `create_react_agent`, `RunnableRails`, and the LLM, then assert
`create_react_agent` receives a model with `bind_tools()` and that calling it
returns the guarded composition. This catches the runtime error:
`AttributeError: 'RunnableRails' object has no attribute 'bind_tools'`.

**Guardrails — `nemoguardrails` is the pip package name** (not `nemo-guardrails`).

**Known cosmetic issue:** The voice selector shows "No voices found" when using
the NVIDIA cloud TTS endpoint. TTS still works. Document this in the README.

### Documentation

See `references/output-repo-template.md` for the README template. At minimum the
human-readable `README.md` must cover:

- Two setup paths: Docker Compose (primary), local venv for tests only
- Sibling-directory layout diagram (this repo + `../nemotron-voice-agent`)
- A first-run Getting Started / Quick Start path that configures both required env
  files before any startup command:
  - Generated agent backend: `cp .env.example .env`, then fill or confirm
    every value listed in the backend env table: `NVIDIA_API_KEY`,
    `AGENT_MODEL_NAME`, `LLM_MODEL`, `LLM_BASE_URL`, `LLM_ENABLE_THINKING`,
    `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`, `LLM_MOCK_MODE`, `AGENT_PORT`,
    `VOICE_AGENT_PORT`, `VOICE_AGENT_UI_PORT`, `LOG_LEVEL`, plus
    `GUARDRAILS_*`, `TAVILY_API_KEY`, `DATABASE_URL`, or other generated
    feature-specific values when used.
  - Nemotron Voice Agent: create or edit `../nemotron-voice-agent/config/.env`,
    then fill or confirm `NVIDIA_API_KEY`, `NVIDIA_LLM_URL`,
    `NVIDIA_LLM_MODEL`, `TRANSPORT=WEBRTC`, and any ASR/TTS values required by
    the cloned voice-agent `env.example` or selected deployment path.
- Env var reference tables for both repos, including both voice-agent URL modes:
  - Docker Compose: `NVIDIA_LLM_URL=http://agent-backend:${AGENT_PORT:-8000}/v1`
  - Manual local backend: `NVIDIA_LLM_URL=http://localhost:${AGENT_PORT:-8000}/v1`
- Nemotron Voice Agent `.env` override instructions explaining these variables:
  - `NVIDIA_LLM_URL` is the OpenAI-compatible base URL that the voice agent
    calls for chat completions. For Docker Compose it must point at the
    generated backend service, not at a raw NIM:
    `NVIDIA_LLM_URL=http://agent-backend:${AGENT_PORT:-8000}/v1`.
  - `NVIDIA_LLM_MODEL` is the model id the voice agent sends in those
    chat-completion requests. It must be the generated backend agent id, for
    example `NVIDIA_LLM_MODEL=<agent-name>`.
  - The cloned `../nemotron-voice-agent/config/.env` may already contain active
    `NVIDIA_LLM_URL` or `NVIDIA_LLM_MODEL` entries from its upstream model
    option blocks. The README and generated skill MUST instruct the developer to
    comment out any existing active lines for these two variables before adding
    the generated values, so exactly one `NVIDIA_LLM_URL` and one
    `NVIDIA_LLM_MODEL` are active.
- A model-identity contract explaining that the generated backend's
  `AGENT_MODEL_NAME`, the backend `/v1/models` response, and the Nemotron Voice
  Agent repo's `NVIDIA_LLM_MODEL` must all be the same generated agent id. If
  these values diverge, the voice agent may request a model id the backend does
  not advertise, causing confusing startup or chat-completion failures.
- A browser microphone prerequisite before opening the web UI. Relay this exact
  message in README and final handoff: `Note: To enable microphone access in
  Chrome, go to chrome://flags/, enable "Insecure origins treated as secure",
  add http://<machine-ip>:9000 to the list, and restart Chrome.`
- Spinning up Nemotron Voice Agent services, with a callout to invoke the
  **`nemotron-voice-agent-deploy` skill** for hardware-specific deployments
  (Jetson, cloud NIM, workstation GPU)
- Default model configuration: all three services (LLM, ASR, TTS) default to
  **NVIDIA public cloud endpoints** — no local GPU required; document how to
  override each one to a self-hosted NIM
- How to add a new tool
- How to run tests (always inside `.venv`)

### Runnable Skill

Create `.agents/skills/<agent-name>/SKILL.md` in the output repo following the
**[agentskills.io open standard](https://agentskills.io/specification)**. This is
the canonical agent-readable skill file; even if a user asks for `skill.md`, use
the standard uppercase `SKILL.md` filename. This file lets any coding agent (or
the developer) start, stop, test, and configure the agent without reading the full
README.

#### Naming and directory rules (agentskills.io)

- Directory name must match the `name` frontmatter field exactly.
- `name` field: 1–64 chars, lowercase letters/numbers/hyphens only, no leading/
  trailing/consecutive hyphens.
- Body: keep under 500 lines / ~5000 tokens. Move detailed reference material to
  `references/` files within the skill directory if needed.

#### Frontmatter (agentskills.io fields)

```yaml
---
name: <agent-name>                          # must match directory name; lowercase, hyphens only
description: >                              # required; max 1024 chars; describe WHAT + WHEN
  Start, stop, test, and configure the <agent-name> ambient healthcare voice agent.
  This agent [one-sentence capability summary].
  Use when asked to run, start, stop, restart, test, or check the status of the
  agent, or when asked to view logs, inspect saved records, or update configuration.
compatibility: Requires Docker, Docker Compose, Python 3.11+, and an NVIDIA API key from build.nvidia.com. Designed for Claude Code (or similar agent products).
metadata:
  author: <org-or-author>
  version: "1.0"
---
```

`license`, `compatibility`, `metadata`, and `allowed-tools` are all optional per
the spec but recommended for discoverability and reproducibility.

#### Required body sections (adapt to the specific agent)

| Section | Contents |
|---|---|
| Repo layout | Sibling directory diagram (`this-repo/` + `../nemotron-voice-agent/`) |
| Getting started | First-run path that configures both env files: generated backend `.env` from `.env.example`, then `../nemotron-voice-agent/config/.env` |
| Prerequisites | `cp .env.example .env` and nemotron `config/.env` setup (first time only), including all backend and voice-agent env vars listed below; Chrome microphone note for remote WebRTC UI |
| Start | **Env file gate first** — check `.env` and `../nemotron-voice-agent/config/.env` are filled in and ask the user to complete them if not; only then run `docker compose up --build`; service/port table; browser URL |
| Stop | `docker compose down`; volumes variant |
| Status and logs | `docker compose ps`; `docker compose logs` commands |
| Run tests | venv setup + `python -m pytest tests/ -v`; per-file commands |
| Smoke test | `curl` command against `/v1/chat/completions` while stack is running |
| View saved records | `docker compose exec` commands to list/read output files |
| Configuration | Table of key `.env` variables with defaults and descriptions |
| Guardrails (if enabled) | How to edit Colang rules and rebuild |
| Add a new tool | Steps to extend the agent with a new capability |

The skill file must be self-contained — a developer or coding agent reading only
this file should be able to bring up the full stack from scratch.

**Critical rule for the Getting Started and Start sections:** The skill must never
run `docker compose up` without first checking that both `.env` and
`../nemotron-voice-agent/config/.env` are filled in. If either file is missing or
has empty required variables (`NVIDIA_API_KEY`, `NVIDIA_LLM_URL`,
`NVIDIA_LLM_MODEL`), the skill must stop and explicitly ask the user to fill in
the file before proceeding. This prevents confusing startup failures caused by
missing credentials or an unconnected voice-agent LLM endpoint.
The generated skill must also explicitly explain that `NVIDIA_LLM_MODEL` in
`../nemotron-voice-agent/config/.env` must exactly match the generated backend's
`AGENT_MODEL_NAME` in `.env` and the id returned by `/v1/models`.

---

### Running the Full Stack

After all code is written, walk through these steps to wire the Nemotron Voice
Agent to the agent backend and bring up the full container stack.

**Step 1 — Configure the agent backend**

```bash
cp .env.example .env
```

Open `.env` in your editor and fill in the following required values:

| Var | Value |
|---|---|
| `NVIDIA_API_KEY` | Key from build.nvidia.com |
| `AGENT_MODEL_NAME` | Generated agent id; must match voice-agent `NVIDIA_LLM_MODEL` |
| `LLM_MODEL` | From Phase 2(e) |
| `LLM_BASE_URL` | From Phase 2(e) |
| `LLM_ENABLE_THINKING` | From Phase 2(e); only true for models that support it |
| `LLM_TEMPERATURE` | Usually `0.0` |
| `LLM_MAX_TOKENS` | At least `8192` when thinking is enabled |
| `LLM_MOCK_MODE` | `false` for normal runs |
| `AGENT_PORT` | `8000` (or override) |
| `VOICE_AGENT_PORT` | `7860` for WebRTC |
| `VOICE_AGENT_UI_PORT` | `9000` (or override) |
| `LOG_LEVEL` | `INFO` |
| `GUARDRAILS_ENABLED` / `GUARDRAILS_CONFIG_PATH` | Required if guardrails were enabled |
| `TAVILY_API_KEY`, `DATABASE_URL`, or generated tool vars | Required only if the selected tools/data backends need them |

**Ask the developer to confirm before continuing:**

> "Please open `my-custom-ambient-healthcare-agent/.env` and fill in at minimum
> `NVIDIA_API_KEY` and the LLM settings from Phase 2(e). Reply **done** when
> the file is saved and you are ready to configure the Nemotron Voice Agent."

**Do not proceed to Step 2 until the developer confirms.**

---

**Step 2 — Configure the Nemotron Voice Agent**

The docker-compose brings up the Nemotron Voice Agent using the cloned repo at
`../nemotron-voice-agent` as a build context. Its own configuration file lives
at `../nemotron-voice-agent/config/.env` and must be filled in separately —
variables set in the agent backend's `.env` are not automatically inherited.

```bash
cp ../nemotron-voice-agent/config/env.example ../nemotron-voice-agent/config/.env
```

Open `../nemotron-voice-agent/config/.env` in your editor and set:

| Var | Value |
|---|---|
| `NVIDIA_API_KEY` | Same key as above |
| `NVIDIA_LLM_URL` | `http://agent-backend:${AGENT_PORT:-8000}/v1` — routes voice agent LLM calls through the agent backend |
| `NVIDIA_LLM_MODEL` | Same value as `AGENT_MODEL_NAME` from the backend `.env` |
| `TRANSPORT` | `WEBRTC` |
| `ASR_*` / `TTS_*` | Values required by the cloned voice-agent `env.example`; defaults use NVIDIA public cloud endpoints unless overridden |

> For hardware-specific deployments (Jetson Thor, workstation GPU, cloud NIM),
> invoke the **`nemotron-voice-agent-deploy`** skill instead of the plain clone
> approach used here. That skill handles driver setup, container registries, and
> NIM-specific env var differences.

Both services run on the same docker-compose network, so
`http://agent-backend:…` resolves internally without exposing extra ports.

**Ask the developer to confirm before continuing:**

> "Please open `nemotron-voice-agent/config/.env` and fill in `NVIDIA_API_KEY`
> and the `NVIDIA_LLM_URL` / `NVIDIA_LLM_MODEL` values shown above. Reply
> **done** when the file is saved and you are ready to bring up the stack."

**Do not proceed to Step 3 until the developer confirms.**

**Documentation parity requirement:** The generated `README.md` and
`.agents/skills/<agent-name>/SKILL.md` must both reproduce this two-env-file
setup flow before their first Docker Compose startup command. The README is for
human users; the skill file is for coding agents. Both must explicitly show:

- Backend env file: `.env` copied from `.env.example`
- Backend env vars: `NVIDIA_API_KEY`, `AGENT_MODEL_NAME`, `LLM_MODEL`,
  `LLM_BASE_URL`, `LLM_ENABLE_THINKING`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`,
  `LLM_MOCK_MODE`, `AGENT_PORT`, `VOICE_AGENT_PORT`, `VOICE_AGENT_UI_PORT`,
  `LOG_LEVEL`, and any generated feature-specific keys
- Voice env file: `../nemotron-voice-agent/config/.env`
- Voice env vars: `NVIDIA_API_KEY`, `NVIDIA_LLM_URL`, `NVIDIA_LLM_MODEL`,
  `TRANSPORT=WEBRTC`, and required ASR/TTS keys from the voice-agent
  `env.example`
- Docker Compose URL:
  `NVIDIA_LLM_URL=http://agent-backend:${AGENT_PORT:-8000}/v1`
- Manual local URL:
  `NVIDIA_LLM_URL=http://localhost:${AGENT_PORT:-8000}/v1`
- Voice-agent `.env` override rule: explain that upstream
  `../nemotron-voice-agent/config/.env` may already contain active
  `NVIDIA_LLM_URL` or `NVIDIA_LLM_MODEL` settings. The developer must comment
  out existing active lines for those two variables before adding the generated
  `NVIDIA_LLM_URL=http://agent-backend:${AGENT_PORT:-8000}/v1` and
  `NVIDIA_LLM_MODEL=<agent-name>` lines. There must be exactly one active value
  for each variable.
- Model id alignment: backend `AGENT_MODEL_NAME`, voice-agent
  `NVIDIA_LLM_MODEL`, and `/v1/models` all use the same value

---

**Step 3 — Build and run**

```bash
docker compose up --build
```

Expected services and their exposed ports:

| Service | Port | Health check |
|---|---|---|
| `agent-backend` | `${AGENT_PORT:-8000}` | `GET /health` → 200 |
| `nemotron-voice-agent` | `7860` (fixed) | `GET /docs` → 200 |
| `voice-agent-ui` | `${VOICE_AGENT_UI_PORT:-9000}` | starts after nemotron healthy |

Open the Docker-published UI at `http://<machine-ip>:9000` in a browser to test
the full voice-to-agent flow end-to-end. If the Docker host UI port was changed,
use `http://<machine-ip>:<VOICE_AGENT_UI_PORT>` instead.

Before opening the web UI from a remote machine, relay this browser prerequisite
to the developer:

> "Note: To enable microphone access in Chrome, go to chrome://flags/, enable
> "Insecure origins treated as secure", add http://<machine-ip>:9000 to the
> list, and restart Chrome."

---

### Phase 4 complete — sub-skill summary

Once all code, configuration, and documentation has been written, tell the
developer which sub-skills were consulted during this build phase and what each
contributed. Report only the sub-skills that were actually invoked or read —
omit any that were not used (e.g. `langchain-rag` if the developer chose SQLite,
or `nemoguardrails` if guardrails were not enabled).

> "Phase 4 complete. Here are the sub-skills that were used during the build:
>
> | Sub-skill | Used for | Read from |
> |---|---|---|
> | `langchain-dependencies` | Package versions and known incompatibilities in `requirements.txt` | Installed skill path (`~/.claude/skills/` or `~/.codex/skills/`) or `references/reference-repos/langchain-skills/config/skills/langchain-dependencies/SKILL.md` |
> | `langchain-fundamentals` | `@tool` decorator patterns and `create_react_agent` usage in `agent/tools/` and `agent/graph.py` | Installed skill path (`~/.claude/skills/` or `~/.codex/skills/`) or `references/reference-repos/langchain-skills/config/skills/langchain-fundamentals/SKILL.md` |
> | `langgraph-fundamentals` | StateGraph, nodes, edges, and streaming patterns in `agent/graph.py` | Installed skill path (`~/.claude/skills/` or `~/.codex/skills/`) or `references/reference-repos/langchain-skills/config/skills/langgraph-fundamentals/SKILL.md` |
> | `langchain-rag` _(if used)_ | NVIDIA RAG data-retrieval tool implementation | Installed skill path (`~/.claude/skills/` or `~/.codex/skills/`) or `references/reference-repos/langchain-skills/config/skills/langchain-rag/SKILL.md` |
> | `nemotron-voice-agent-deploy` | Docker Compose service configuration, health check rules, transport setup | Installed skill path (`~/.claude/skills/` or `~/.codex/skills/`) or `references/reference-repos/nemotron-voice-agent/.agents/skills/nemotron-voice-agent-deploy/SKILL.md` |
> | `nemoguardrails` _(if enabled)_ | Colang syntax, rail type configuration, `RunnableRails`, and LangGraph integration | `references/reference-repos/nemo-guardrails/docs/` and `references/reference-repos/nemo-guardrails/examples/` |
>
> Ready to move to Phase 5: Validate."

---

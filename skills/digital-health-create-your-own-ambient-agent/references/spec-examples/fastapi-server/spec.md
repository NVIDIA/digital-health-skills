# Feature Specification: FastAPI Server + Docker Deployment

**Feature Branch**: `fastapi-server`
**Status**: Template
**Input**: Approved `specs/langgraph-agent/` feature; developer env var choices

---

## User Scenarios & Testing

### User Story 1 — Nemotron Voice Agent Calls the Server and Receives Streamed Speech Text (Priority: P1)

The NVIDIA Nemotron Voice Agent sends a `POST /v1/chat/completions` request to
this server. The server runs the LangGraph agent and streams back Server-Sent
Events (SSE) that the voice agent feeds to the TTS service, producing speech.

**Why this priority**: This is the integration point that makes the entire stack
work. Without a correct SSE response the voice agent has no text to speak.

**Independent Test**: Can be fully tested with `curl` or `httpx` against a
running server instance with the LangGraph graph mocked to return a fixed string.
The Nemotron Voice Agent itself is not required for this test.

**Acceptance Scenarios**:

1. **Given** the server is running and the LangGraph agent is healthy, **When**
   the Nemotron Voice Agent POSTs `{"messages": [...], "stream": true}` to
   `/v1/chat/completions`, **Then** the response is `text/event-stream`, each
   chunk matches the OpenAI SSE format, and the stream ends with `data: [DONE]`.

2. **Given** the LangGraph agent raises an unhandled exception during streaming,
   **When** the Nemotron Voice Agent POSTs a request, **Then** the server emits
   one SSE chunk with a graceful error message and then `data: [DONE]` — it does
   not return a 500 or drop the connection mid-stream.

3. **Given** `stream: false` in the request, **When** the Nemotron Voice Agent
   POSTs to `/v1/chat/completions`, **Then** the server returns a complete JSON
   response matching the OpenAI non-streaming schema.

### Edge Cases

- What if the incoming request contains a system message from the Nemotron Voice
  Agent's own prompt? → The server MUST strip all incoming `role: system` messages
  and inject its own `SYSTEM_PROMPT` — the voice agent's system prompt must not
  override the clinical persona.
- What if `messages` contains no `role: user` entry? → The server MUST inject a
  synthetic `HumanMessage("Please begin.")` so the LangGraph agent has a trigger.

---

### User Story 2 — Full Stack Starts with One Command (Priority: P1)

A developer (or coding agent) runs `docker compose up` from the repo root and
all three services start in the correct dependency order with no manual steps.

**Why this priority**: Onboarding friction is the most common reason healthcare
agent projects stall. One-command startup is a hard requirement for agent-assisted
development workflows.

**Independent Test**: Run `docker compose up --build` on a machine with Docker
and an `NVIDIA_API_KEY` in `.env`. All three health checks must pass within 90
seconds.

**Acceptance Scenarios**:

1. **Given** `.env` is copied from `.env.example` and `NVIDIA_API_KEY` is set,
   **When** `docker compose up --build` runs, **Then** `agent-backend` passes its
   health check, then `nemotron-voice-agent` passes its health check, then
   `voice-agent-ui` starts after its 15-second warm-up delay.

2. **Given** `agent-backend` fails to start (e.g., bad `NVIDIA_API_KEY`), **When**
   `docker compose up` runs, **Then** `nemotron-voice-agent` does not start
   (depends_on `service_healthy` is enforced).

3. **Given** all services are healthy, **When** a browser navigates to the
   Docker-published UI at `http://<machine-ip>:9000` (or
   `http://<machine-ip>:<VOICE_AGENT_UI_PORT>` if the Docker host UI port was
   changed), **Then** the WebRTC voice UI loads and the microphone button is
   visible.

### Edge Cases

- What if the WebRTC UI shows a connection error on first load? → This is the
  cold-start gRPC race condition. The `sleep 15` in `voice-agent-ui`'s command
  mitigates it. Document the hard-refresh workaround in the README.
- What if `AGENT_PORT` is changed from `8000`? → Both sides of the port mapping
  (`${AGENT_PORT:-8000}:${AGENT_PORT:-8000}`), the health check probe, and
  `NVIDIA_LLM_URL` in the nemotron-voice-agent environment must all use the same
  variable — no hardcoded `8000` anywhere.

---

### User Story 3 — All Ports Configurable via Environment Variables (Priority: P2)

An operator can run multiple stack instances on the same host by setting different
`AGENT_PORT` and `VOICE_AGENT_UI_PORT` values with no code changes.

**Why this priority**: This is a deployment hygiene requirement; without it the
stack cannot be tested in CI alongside another running instance.

**Independent Test**: Start the server with `AGENT_PORT=9001`; confirm the process
listens on 9001 (`ss -tlnp | grep 9001`); confirm `GET http://localhost:9001/health`
returns 200.

**Acceptance Scenarios**:

1. **Given** `AGENT_PORT=9001` in `.env`, **When** the server starts, **Then** it
   listens on port 9001 and the docker-compose health check probes `localhost:9001`.

2. **Given** no `AGENT_PORT` in `.env`, **When** the server starts, **Then** it
   defaults to port 8000.

### Edge Cases

- `VOICE_AGENT_PORT` is **not** fully configurable. The Nemotron Voice Agent React
  UI hardcodes `:7860/offer` in its compiled JavaScript. Changing `VOICE_AGENT_PORT`
  only moves the host-side port mapping; the browser always dials port 7860.
  Document this constraint explicitly and do not attempt to fix it by modifying
  the upstream repo.

---

## Requirements

### Functional Requirements

- **FR-001**: Server MUST expose `POST /v1/chat/completions` implementing the
  OpenAI streaming API contract (SSE chunks with `data: {...}\n\n`, ending with
  `data: [DONE]\n\n`).
- **FR-002**: Server MUST expose `GET /health` returning `{"status": "ok"}` with
  HTTP 200 for Docker health checks.
- **FR-003**: Server MUST expose `GET /v1/models` listing the agent as a model
  entry (required by `NvidiaLLMService` in the Nemotron Voice Agent pipeline).
- **FR-004**: Server MUST strip all `role: system` messages from the incoming
  request and inject its own `SYSTEM_PROMPT` as the sole system message.
- **FR-005**: Server MUST inject a synthetic `HumanMessage("Please begin.")` when
  the prepared message list contains no `HumanMessage`.
- **FR-006**: Server MUST log: request received (message count), tool call (tool
  name; PII fields redacted), tool result (status), LLM response preview (first
  500 chars), unhandled exceptions (full traceback).
- **FR-007**: Docker Compose MUST define three services: `agent-backend`,
  `nemotron-voice-agent`, `voice-agent-ui`.
- **FR-008**: `nemotron-voice-agent` MUST receive `NVIDIA_LLM_URL=http://agent-backend:${AGENT_PORT:-8000}/v1`
  so it routes LLM calls to the agent backend instead of a raw NIM.
- **FR-009**: `TRANSPORT=WEBRTC` MUST be set for both `nemotron-voice-agent` and
  `voice-agent-ui` services.
- **FR-010**: `nemotron-voice-agent` health check MUST use
  `curl -sf http://localhost:7860/docs || exit 1`. Using `python` will fail
  (binary absent from the pipecat container); using `/health` will fail
  (`pipeline.py` does not define that route).
- **FR-011**: `voice-agent-ui` command MUST use exec form:
  `["python", "-c", "import time; time.sleep(15); exec(open('start-server.py').read())"]`.
  This avoids the cold-start WebRTC race condition and does not require a shell
  in the distroless frontend image.
- **FR-012**: `agent-backend` port mapping MUST be
  `"${AGENT_PORT:-8000}:${AGENT_PORT:-8000}"` (both target and source use the
  variable). The health check MUST probe `http://localhost:${AGENT_PORT:-8000}/health`.
- **FR-012a**: The `agent-backend` image MUST NOT copy generated `agent/`,
  `config/`, or `data/` directories into the Docker image. Docker Compose MUST
  mount generated backend source/config/data at runtime: `./agent:/app/agent:ro`,
  `./config:/app/config:ro` when `config/` exists, and `./data:/app/data` when
  generated tools persist files.
- **FR-013**: Configurable ports MUST be read from environment variables. No
  bare integer literals for `AGENT_PORT` or `VOICE_AGENT_UI_PORT` in source code,
  docker-compose, or config files. The only allowed fixed port literals are the
  Nemotron Voice Agent WebRTC container target `7860` and the UI container
  internal target `8000`.
- **FR-014**: The output repo MUST include human-readable `README.md` and
  agent-readable `.agents/skills/<agent-name>/SKILL.md` documentation. Both MUST
  include a Getting Started / Start path that configures the generated backend
  `.env` and `../nemotron-voice-agent/config/.env` before running Docker Compose.
- **FR-015**: Both documentation paths MUST show the correct
  `NVIDIA_LLM_URL` for Docker Compose
  (`http://agent-backend:${AGENT_PORT:-8000}/v1`) and manual local backend runs
  (`http://localhost:${AGENT_PORT:-8000}/v1`).
- **FR-016**: The server MUST expose `/v1/models` using `AGENT_MODEL_NAME`
  from environment, and Docker Compose MUST pass the same value to the voice
  agent as `NVIDIA_LLM_MODEL=${AGENT_MODEL_NAME:-<agent-name>}`.
- **FR-017**: The server MUST expose `GET /debug/config` returning non-secret
  effective config (`AGENT_MODEL_NAME`, `AGENT_PORT`, `LLM_MODEL`,
  `LLM_BASE_URL`, `LLM_MOCK_MODE`, `GUARDRAILS_ENABLED`, `LOG_LEVEL`) for
  deployment troubleshooting.
- **FR-018**: The repo MUST include `scripts/smoke_voice_connection.py` to verify
  a running Docker Compose stack: `/health`, `/v1/models`, `/debug/config`, one
  or more voice-agent-shaped streaming `/v1/chat/completions` requests,
  voice-agent `/docs`, and UI `/`. At minimum, the smoke script MUST send
  `hello` and `Hi I'm here to check in` and verify each returns non-empty
  assistant text rather than only SSE framing or a bare guardrail verdict.
- **FR-019**: `LLM_MOCK_MODE=true` MUST provide a deterministic backend response
  for local smoke tests without a live LLM call; it MUST default to `false`.
- **FR-020**: Server tests MUST cover the non-mock graph streaming path with a
  fake graph that yields a spoken assistant chunk, and the stream MUST emit at
  least one content SSE chunk before `data: [DONE]`.
- **FR-021**: The streaming response path MUST emit OpenAI-style content deltas,
  not repeated cumulative/full assistant messages. If the graph yields the same
  completed assistant message more than once, the server MUST send it only once.

### Key Entities

- **ChatCompletionRequest**: Pydantic model for `/v1/chat/completions` input
  (`model`, `messages`, `stream`, `temperature`, `max_tokens`).
- **MessageParam**: `{role: str, content: str}` — one entry in the messages list.
- **SSE Chunk**: `data: {"id": ..., "object": "chat.completion.chunk", "choices":
  [{"delta": {"content": "..."}}]}\n\n`
- **Service dependency order**: agent-backend → nemotron-voice-agent → voice-agent-ui

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: `curl -s -X POST http://localhost:${AGENT_PORT}/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"<agent-name>","stream":true,"messages":[{"role":"user","content":"You are a helpful assistant. Always answer as helpful, friendly, and polite. Respond with one sentence or less than 75 characters."},{"role":"user","content":"hello"}]}'`
  returns at least one assistant content `data:` line before `data: [DONE]`.
- **SC-002**: `docker compose up --build` completes with all three services
  reporting healthy status within 90 seconds on a machine with a valid
  `NVIDIA_API_KEY`.
- **SC-003**: Browser at the Docker-published UI URL
  `http://<machine-ip>:9000` (or `http://<machine-ip>:<VOICE_AGENT_UI_PORT>`
  if the Docker host UI port was changed) loads the WebRTC voice UI with the
  microphone button visible.
- **SC-004**: End-to-end voice call: patient speech → ASR → `/v1/chat/completions`
  → LangGraph agent → SSE response → TTS → patient hears the agent's reply.
- **SC-005**: `AGENT_PORT=9001 docker compose up` starts the agent backend on
  port 9001 with no code changes; all dependent services connect on the new port.
- **SC-006**: A first-time human user or coding agent can follow either
  `README.md` or `.agents/skills/<agent-name>/SKILL.md` from fresh clone to
  startup without any undocumented env-file step.
- **SC-007**: `docker compose config` renders successfully and shows the same
  model id for backend `AGENT_MODEL_NAME`, voice-agent `NVIDIA_LLM_MODEL`, and
  `/v1/models`.
- **SC-008**: `python scripts/smoke_voice_connection.py` passes after
  `docker compose up --build` reports all services healthy.

---

## Assumptions

- The Nemotron Voice Agent is cloned into `../nemotron-voice-agent` (sibling
  directory). The docker-compose in this repo builds it from that path.
- `VOICE_AGENT_PORT` is documented as fixed at 7860 for WebRTC. The host-side
  port mapping may be changed but the browser will still dial 7860; this is a
  known upstream limitation and must not be "fixed" by modifying the upstream repo.
- The server does not manage ASR or TTS directly; those remain internal to the
  Nemotron Voice Agent pipeline.
- FastAPI CORS middleware is configured with `allow_origins=["*"]` for
  development; tighten for production.
- Python 3.11-slim base image for Docker; no CUDA required (inference is remote).

---
description: Task list for the FastAPI server and Docker deployment feature
---

# Tasks: FastAPI Server + Docker Deployment

**Spec**: `specs/fastapi-server/spec.md`
**Plan**: `specs/fastapi-server/plan.md`
**Prerequisites**: `specs/langgraph-agent/` feature complete and tested

**Format**: `[ID] [P?] [US?] Description`
- `[P]` — can run in parallel with other `[P]` tasks in the same phase
- `[US1]` etc. — which user story this task satisfies

---

## Phase 1: Setup

**Purpose**: Add server dependencies.

- [ ] T001 Add `fastapi>=0.115.0`, `uvicorn[standard]>=0.30.0`, `pydantic>=2.0.0`,
  `httpx>=0.27.0` to `requirements.txt`

---

## Phase 2: Server Implementation

**Purpose**: Build the FastAPI server. All test tasks are parallel — they test
independent routes and can be written and run simultaneously.

- [ ] T002 [US1] Copy `references/langgraph-backend/server.py` to `agent/server.py`.
  **Do not rewrite from scratch.** Update the `FastAPI(title=...)` to match the
  project name. Confirm `SYSTEM_PROMPT` is imported from `agent.graph`.

- [ ] T003 [P] [US1] Write `tests/test_server.py` — `GET /health` returns
  `{"status": "ok"}` with HTTP 200

- [ ] T004 [P] [US1] Write `tests/test_server.py` — `GET /v1/models` returns a
  list containing `AGENT_MODEL_NAME`

- [ ] T005 [P] [US1] Write `tests/test_server.py` — `POST /v1/chat/completions`
  with `stream: false` and mocked graph returns a complete JSON response matching
  the OpenAI non-streaming schema

- [ ] T006 [P] [US1] Write `tests/test_server.py` — `POST /v1/chat/completions`
  with `stream: true` and mocked graph yields at least one `data:` chunk and ends
  with `data: [DONE]`. Include a unit test for the non-mock graph streaming
  helper by monkeypatching `get_graph()` to a fake graph that yields an assistant
  text chunk; this catches dead `yield` paths and over-filtered stream metadata
  that `LLM_MOCK_MODE=true` cannot catch. Include regression tests proving the
  server converts cumulative graph chunks into OpenAI-style deltas and skips
  repeated full-message chunks, e.g. a fake graph yielding
  `Hello! May I have your name, please?` twice must produce that sentence only
  once in the SSE body.

- [ ] T006a [P] [US1] Write `tests/test_server.py` — simulate the Nemotron Voice
  Agent request shape with `stream: true`, `model: AGENT_MODEL_NAME`, a
  voice-agent instruction/context message, and the current user utterance. Test
  both `hello` and `Hi I'm here to check in`; each response must include
  non-empty assistant content and must not be only `yes`, `no`, `safe`, or
  `unsafe`.

- [ ] T007 [P] [US1] Write `tests/test_server.py` — incoming `role: system`
  messages are stripped and `SYSTEM_PROMPT` is injected as the sole system message

- [ ] T008 [P] [US1] Write `tests/test_server.py` — when the graph raises an
  exception during streaming, the server emits one graceful error SSE chunk and
  then `data: [DONE]` (no 500, no dropped connection)

- [ ] T008a [P] [US1] Write `tests/test_server.py` — `GET /debug/config`
  returns non-secret effective config and does not include `NVIDIA_API_KEY`

- [ ] T008b [P] [US1] Write `tests/test_server.py` — with
  `LLM_MOCK_MODE=true`, `/v1/chat/completions` returns a deterministic response
  without calling the live LLM

**Checkpoint**: `pytest tests/test_server.py -v` passes before proceeding to Docker.

---

## Phase 3: Docker + Compose

**Purpose**: Containerize the agent backend and orchestrate the full stack.

- [ ] T009 [US2] Create `Dockerfile` using `python:3.11-slim`:
  ```
  WORKDIR /app
  COPY requirements.txt .
  RUN apt-get update \
      && apt-get install -y --no-install-recommends build-essential \
      && pip install --no-cache-dir -r requirements.txt \
      && apt-get purge -y --auto-remove build-essential \
      && rm -rf /var/lib/apt/lists/*
  ENV PYTHONUNBUFFERED=1
  CMD ["sh", "-c", "python -m uvicorn agent.server:app --host 0.0.0.0 --port ${AGENT_PORT:-8000}"]
  ```
  Use shell-form `CMD` so `${AGENT_PORT:-8000}` expands at runtime. Do not copy
  generated `agent/`, `config/`, or `data/` into the image; those directories
  must be mounted by Docker Compose at runtime. When guardrails are enabled,
  keep the temporary `build-essential` install/remove pattern because
  `nemoguardrails` can pull in `annoy`, which compiles a C++ extension and needs
  `g++` during `pip install`. If guardrails are skipped and no native-extension
  package is required, a plain `pip install --no-cache-dir -r requirements.txt`
  is acceptable.

- [ ] T010 [US2] Create `docker-compose.yml` with three services per the plan:
  - `agent-backend`: build from `.`; port `${AGENT_PORT:-8000}:${AGENT_PORT:-8000}`;
    health check with `python -c "import urllib.request; ..."` probing
    `${AGENT_PORT:-8000}`; pass `AGENT_MODEL_NAME=${AGENT_MODEL_NAME:-<agent-name>}`;
    mount generated source/config/data at runtime:
    `./agent:/app/agent:ro`, `./config:/app/config:ro` when `config/` exists,
    and `./data:/app/data` when generated tools persist files
  - `nemotron-voice-agent`: build from `../nemotron-voice-agent`; `TRANSPORT=WEBRTC`;
    `NVIDIA_LLM_URL=http://agent-backend:${AGENT_PORT:-8000}/v1`;
    `NVIDIA_LLM_MODEL=${AGENT_MODEL_NAME:-<agent-name>}`; health check
    `curl -sf http://localhost:7860/docs`; `depends_on: agent-backend: service_healthy`
  - `voice-agent-ui`: build from `../nemotron-voice-agent/frontend`; command
    `["python", "-c", "import time; time.sleep(15); exec(open('start-server.py').read())"]`;
    `TRANSPORT=WEBRTC`; `depends_on: nemotron-voice-agent: service_healthy`

- [ ] T011 [P] [US2] [US3] Create `.env.example` with all variables listed in
  `specs/fastapi-server/plan.md`; every variable must have a default and a
  one-line comment explaining what it controls and which service uses it

- [ ] T012 [P] [US2] [US3] Create or update human-readable `README.md` and
  agent-readable `.agents/skills/<agent-name>/SKILL.md`. Both must include a
  Getting Started / Start path that configures this repo's `.env` and
  `../nemotron-voice-agent/config/.env` before any `docker compose up` command,
  and both must document:
  - Docker Compose URL: `NVIDIA_LLM_URL=http://agent-backend:${AGENT_PORT:-8000}/v1`
  - Manual local URL: `NVIDIA_LLM_URL=http://localhost:${AGENT_PORT:-8000}/v1`
  - Required voice-agent values: `NVIDIA_API_KEY`, `NVIDIA_LLM_URL`,
    `NVIDIA_LLM_MODEL`, and `TRANSPORT=WEBRTC`
  - Model id alignment: `AGENT_MODEL_NAME`, `/v1/models`, and
    `NVIDIA_LLM_MODEL` must be the same generated agent id

- [ ] T013 [P] [US2] Create `scripts/smoke_voice_connection.py`:
  - Load `.env` without printing secrets
  - Verify `GET /health`
  - Verify `GET /debug/config` has `agent_model_name == AGENT_MODEL_NAME`
  - Verify `GET /v1/models` contains `AGENT_MODEL_NAME`
  - Verify voice-agent-shaped streaming `POST /v1/chat/completions` requests
    for `hello` and `Hi I'm here to check in` return SSE `data:` chunks,
    assistant text content, and `data: [DONE]`
  - Fail if the assistant content is empty, exactly echoes the user utterance,
    or is only a bare classifier/guardrail verdict such as `yes`, `no`, `safe`,
    or `unsafe`
  - Verify `http://localhost:${VOICE_AGENT_PORT:-7860}/docs`
  - Verify the Docker-published UI port responds from the Docker host; document
    the browser URL as `http://<machine-ip>:9000/`, or
    `http://<machine-ip>:<VOICE_AGENT_UI_PORT>/` if the Docker host UI port was
    changed

- [ ] T014 [P] Create `.gitignore`:
  ```
  .venv/
  .env
  __pycache__/
  *.pyc
  agent/data/
  ```

---

## Phase 4: Validation

**Purpose**: Confirm the full stack runs correctly end-to-end.

- [ ] T015 [US2] Run static checks before starting Docker:
  - `python -m compileall agent tests scripts`
  - `python -c "from agent.server import app; print(app.title)"`
  - If guardrails are enabled:
    `python -c "import os; from nemoguardrails import RailsConfig; RailsConfig.from_path(os.getenv('GUARDRAILS_CONFIG_PATH', 'config/guardrails'))"`
    and `python -m pytest tests -v`
  - `! rg -n '^COPY +(agent|config|data)/' Dockerfile`
  - `docker compose config`
  - Rendered compose includes the runtime source mount
    `./agent:/app/agent:ro`; it includes `./config:/app/config:ro` when
    `config/` exists and `./data:/app/data` when generated tools persist files
  - Placeholder scan for unresolved `TODO`, `FIXME`, `REPLACE_ME`,
    `<agent-name>`, and `<tool_name>` in generated files

- [ ] T016 [US2] Run `docker compose build` — must succeed with no errors

- [ ] T017 [US2] Run `docker compose up` only after confirming both env files:
  - `.env` contains a valid `NVIDIA_API_KEY` and selected backend LLM settings
  - `.env` contains `AGENT_MODEL_NAME=<agent-name>` and `LLM_MOCK_MODE=false`
  - `../nemotron-voice-agent/config/.env` contains `NVIDIA_API_KEY`,
    `NVIDIA_LLM_URL=http://agent-backend:${AGENT_PORT:-8000}/v1`, and
    `NVIDIA_LLM_MODEL` matching `AGENT_MODEL_NAME`
  - Confirm `agent-backend` health check passes
  - Confirm `nemotron-voice-agent` health check passes
  - Confirm `voice-agent-ui` starts after the 15-second delay

- [ ] T018 [US1] Smoke test the server endpoint while the stack is running:
  ```bash
  curl -s -X POST http://localhost:${AGENT_PORT:-8000}/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"${AGENT_MODEL_NAME:-ambient-healthcare-agent}\",\"stream\":true,\"messages\":[{\"role\":\"user\",\"content\":\"You are a helpful assistant. Always answer as helpful, friendly, and polite. Respond with one sentence or less than 75 characters.\"},{\"role\":\"user\",\"content\":\"hello\"}]}"
  ```
  Must return at least one `data:` line before `data: [DONE]`.

- [ ] T019 [US2] Run `python scripts/smoke_voice_connection.py` while the stack
  is running — must pass.

- [ ] T020 [US3] Test port override:
  ```bash
  AGENT_PORT=9001 docker compose up agent-backend
  curl http://localhost:9001/health
  ```
  Must return `{"status": "ok"}`.

- [ ] T021 [US2] Open the Docker-published UI at `http://<machine-ip>:9000`
  in a browser, or `http://<machine-ip>:<VOICE_AGENT_UI_PORT>` if the Docker
  host UI port was changed. WebRTC UI must load with the microphone button
  visible.

---

## Dependencies & Execution Order

- **Phase 1** → no dependencies, start immediately
- **Phase 2** → depends on Phase 1 (T002 must exist before tests can import it)
- **Phase 3** → T009 and T010 depend on Phase 2 passing; T011, T012, T013, and T014 are parallel
- **Phase 4** → depends on Phase 3 completion

Within Phase 2, T003–T008b are fully parallel (each tests an independent aspect of server.py).
Within Phase 3, T011, T012, T013, and T014 are parallel (independent files).

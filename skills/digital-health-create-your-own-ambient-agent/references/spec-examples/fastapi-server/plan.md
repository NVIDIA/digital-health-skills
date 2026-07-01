# Implementation Plan: FastAPI Server + Docker Deployment

**Feature**: `fastapi-server` | **Spec**: `specs/fastapi-server/spec.md`
**Depends on**: `specs/langgraph-agent/` feature complete

---

## Summary

Expose the LangGraph agent as an OpenAI-compatible HTTP server so the NVIDIA
Nemotron Voice Agent can call it like any other LLM NIM. Containerize the agent
backend and orchestrate the full three-service stack with Docker Compose.

---

## Technical Context

| Parameter | Value |
|---|---|
| Language | Python 3.11+ |
| Framework | FastAPI + uvicorn[standard] |
| Response format | `text/event-stream` SSE, OpenAI chunk schema |
| Base image | `python:3.11-slim` |
| Orchestration | Docker Compose v2 |
| Integration point | `NVIDIA_LLM_URL=http://agent-backend:${AGENT_PORT:-8000}/v1` on the Nemotron Voice Agent service |
| Testing | `pytest`, `pytest-asyncio`, `httpx` for async HTTP client |
| Performance goals | First SSE token < 2 s from request receipt (network + LLM TTFT) |
| Constraints | No CUDA in agent-backend container; all inference is remote |

---

## Project Structure

```text
agent/
└── server.py           ← FastAPI app; 3 routes; SSE streaming; message prep

Dockerfile              ← single-stage python:3.11-slim; installs requirements.txt; copies agent/
docker-compose.yml      ← 3 services with health checks, depends_on, env passthrough
.env.example            ← all configurable parameters with defaults + inline comments
.gitignore              ← .venv/, .env, __pycache__/, *.pyc, agent/data/
README.md               ← human setup guide; configures both backend and voice env files
.agents/skills/<agent-name>/SKILL.md
                        ← agent-readable setup/start/test guide with same env-file gate
scripts/smoke_voice_connection.py
                        ← verifies running stack wiring, ports, model id, and SSE

tests/
└── test_server.py      ← tests for all 3 routes; streaming and non-streaming paths
```

---

## API Contract

### `POST /v1/chat/completions`

**Request:**
```json
{
  "model": "ambient-healthcare-agent",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user",   "content": "Hello"},
    {"role": "assistant", "content": "Hi there"},
    {"role": "user",   "content": "My name is Jane"}
  ],
  "stream": true
}
```

**Streaming response** (`Content-Type: text/event-stream`):
```
data: {"id":"chatcmpl-abc","object":"chat.completion.chunk","created":1234,"model":"ambient-healthcare-agent","choices":[{"index":0,"delta":{"content":"Hi"},"finish_reason":null}]}

data: {"id":"chatcmpl-abc","object":"chat.completion.chunk","created":1234,"model":"ambient-healthcare-agent","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]

```

**Message preparation rule:** Strip all `role: system` entries from the incoming
list; prepend `SystemMessage(SYSTEM_PROMPT)`. If no `HumanMessage` remains,
append `HumanMessage("Please begin.")`.

### `GET /health`
```json
{"status": "ok"}
```

### `GET /v1/models`
```json
{
  "object": "list",
  "data": [{"id": "ambient-healthcare-agent", "object": "model", "created": 0, "owned_by": "custom"}]
}
```

---

## Docker Compose Architecture

```
agent-backend (this repo)
  image: built from ./Dockerfile
  mount: ./agent:/app/agent:ro
         ./config:/app/config:ro   (when config/ exists)
         ./data:/app/data          (when generated tools persist files)
  port:  ${AGENT_PORT:-8000}:${AGENT_PORT:-8000}
  health: python -c "import urllib.request; urllib.request.urlopen('http://localhost:${AGENT_PORT:-8000}/health')"
  ↓ service_healthy

nemotron-voice-agent
  image: built from ../nemotron-voice-agent/Dockerfile
  port:  ${VOICE_AGENT_PORT:-7860}:7860
  env:   NVIDIA_LLM_URL=http://agent-backend:${AGENT_PORT:-8000}/v1
         NVIDIA_LLM_MODEL=${AGENT_MODEL_NAME:-<agent-name>}
         TRANSPORT=WEBRTC
  health: curl -sf http://localhost:7860/docs || exit 1
  ↓ service_healthy

voice-agent-ui
  image: built from ../nemotron-voice-agent/frontend/Dockerfile
  port:  ${VOICE_AGENT_UI_PORT:-9000}:8000
  cmd:   ["python", "-c", "import time; time.sleep(15); exec(open('start-server.py').read())"]
  env:   TRANSPORT=WEBRTC
```

### Health check rationale

| Service | Tool | Endpoint | Reason |
|---|---|---|---|
| agent-backend | `python` | `/health` | Python available; `/health` defined in server.py |
| nemotron-voice-agent | `curl` | `/docs` | No bare `python` binary in pipecat uv container; `/health` not defined in pipeline.py WebRTC mode |
| voice-agent-ui | `curl` | `/` (port 8000 inside container) | Static file server; root always returns 200 |

### Port mapping rule

`agent-backend` port mapping must use the variable on **both sides**:
```yaml
ports:
  - "${AGENT_PORT:-8000}:${AGENT_PORT:-8000}"
```
A mapping of `${AGENT_PORT:-8000}:8000` (target hardcoded) breaks the health
check when `AGENT_PORT` differs from 8000.

`VOICE_AGENT_PORT` applies only to the **host-side** mapping. The Nemotron Voice
Agent React UI has `:7860/offer` compiled into its JavaScript bundle — the browser
always dials port 7860 regardless of the host mapping. Do not attempt to change
this by modifying the upstream repo.

---

## Dockerfile

Single-stage build:

```dockerfile
FROM python:3.11-slim
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

The `CMD` uses shell form so `${AGENT_PORT:-8000}` is expanded at container
startup from the environment, not baked into the image. Do not `COPY agent/`,
`COPY config/`, or `COPY data/` into the image. The image installs dependencies
only; Docker Compose mounts generated source/config/data at runtime so edits do
not require rebuilding the backend image.

When guardrails are enabled, keep the temporary `build-essential` install/remove
pattern. `nemoguardrails` may install `annoy`, which compiles a C++ extension;
`python:3.11-slim` has no `g++` by default. If guardrails are skipped and no
native-extension package is required, the Dockerfile may use a plain
`RUN pip install --no-cache-dir -r requirements.txt`.

### Agent backend runtime mounts

`docker-compose.yml` must mount generated backend files into the `agent-backend`
container:

```yaml
services:
  agent-backend:
    volumes:
      - ./agent:/app/agent:ro
      - ./config:/app/config:ro    # include only when config/ exists
      - ./data:/app/data           # include when generated tools persist files
```

Keep generated imports rooted at `/app` and keep `GUARDRAILS_CONFIG_PATH` at
`config/guardrails`; with the mount above, that path resolves to
`/app/config/guardrails`. If no feature creates `config/`, omit the config mount
instead of adding `COPY config/` to the Dockerfile.

---

## Environment Variables (`.env.example` contents)

```dotenv
# ── Required ───────────────────────────────────────────────────────────────
NVIDIA_API_KEY=                        # Required for all NVIDIA NIM endpoints

# ── Agent LLM ──────────────────────────────────────────────────────────────
AGENT_MODEL_NAME=<agent-name>
LLM_MODEL=nvidia/nemotron-3-super-120b-a12b
LLM_BASE_URL=https://integrate.api.nvidia.com/v1
LLM_ENABLE_THINKING=true              # Supported: nemotron-3-super-*; NOT llama variants
LLM_TEMPERATURE=0.0
LLM_MAX_TOKENS=8192                   # Must be >=8192 when LLM_ENABLE_THINKING=true
LLM_MOCK_MODE=false                   # Testing-only deterministic response

# ── Agent backend port ──────────────────────────────────────────────────────
AGENT_PORT=8000

# ── ASR (speech-to-text) ───────────────────────────────────────────────────
ASR_SERVER_URL=grpc.nvcf.nvidia.com:443
ASR_MODEL_NAME=parakeet-1.1b-en-US-asr-streaming-silero-vad-sortformer
ASR_CLOUD_FUNCTION_ID=1598d209-5e27-4d3c-8079-4751568b1081

# ── TTS (text-to-speech) ───────────────────────────────────────────────────
TTS_SERVER_URL=grpc.nvcf.nvidia.com:443
TTS_MODEL_NAME=magpie_tts_ensemble-Magpie-Multilingual
TTS_VOICE_ID=Magpie-Multilingual.EN-US.Aria
TTS_LANGUAGE=en-US

# ── Voice agent UI port ─────────────────────────────────────────────────────
# NOTE: VOICE_AGENT_PORT (pipeline port) is fixed at 7860; the WebRTC UI
# has :7860 compiled into its JavaScript. Only VOICE_AGENT_UI_PORT is freely
# configurable.
VOICE_AGENT_UI_PORT=9000
```

The generated `README.md` and `.agents/skills/<agent-name>/SKILL.md` must also
document the Nemotron Voice Agent env file at
`../nemotron-voice-agent/config/.env`. The first-run path must require
`NVIDIA_API_KEY`, `NVIDIA_LLM_URL`, and `NVIDIA_LLM_MODEL` before startup. Use
`NVIDIA_LLM_URL=http://agent-backend:${AGENT_PORT:-8000}/v1` for Docker Compose
and `NVIDIA_LLM_URL=http://localhost:${AGENT_PORT:-8000}/v1` for manual local
backend runs. `NVIDIA_LLM_MODEL` must match this repo's `AGENT_MODEL_NAME`.

Validation must include `docker compose config`, a compile/import smoke check,
a no-placeholder scan, and `scripts/smoke_voice_connection.py` after the stack
is healthy. The smoke script must simulate the Nemotron Voice Agent by POSTing
OpenAI-compatible `stream: true` chat completion requests with the voice-agent
instruction/context plus simple user utterances (`hello` and
`Hi I'm here to check in`), then assert the SSE stream contains non-empty
assistant text. If guardrails are enabled, validation must also load
`config/guardrails/` with `RailsConfig.from_path(...)` and run
`python -m pytest tests -v` after `pip install -r requirements.txt`, before
Docker handoff. The graph tests must include the ReAct plus Guardrails plus
tools regression that proves `create_react_agent` does not receive raw
`RunnableRails`, and the server tests must prove leaked leading guardrail verdict
tokens are stripped from patient-facing text. The launch command itself remains
`docker compose up --build`.

---

## Reference Files

- `references/langgraph-backend/server.py` — copy as `agent/server.py`.
  Do not rewrite from scratch; the SSE framing is load-bearing. Server tests must
  exercise both `LLM_MOCK_MODE=true` and the non-mock graph stream helper with a
  fake spoken chunk so the real graph path cannot silently complete with zero
  content chunks. The stream helper must send OpenAI-style deltas: cumulative
  chunks should be converted to suffixes, and repeated completed assistant
  messages should be skipped so the UI does not concatenate duplicates.
- `references/nemotron-voice-agent-deploy-skill.md` — platform-specific
  deployment notes (Workstation, Jetson, Cloud NIMs).

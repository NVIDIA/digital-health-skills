# Output Repository Templates

Boilerplate content for the files that every ambient healthcare agent repo must include.

---

## README.md Template

```markdown
# [Project Name] — Ambient Healthcare Voice Agent

An ambient healthcare agent powered by NVIDIA Nemotron Voice Agent and LangGraph.

## What It Does

[2–3 sentence description of agent capabilities based on the user's chosen functions.]

## Architecture

```
User ──► Nemotron Voice Agent (STT) ──► Agent Backend ──► Tools ──► Data Layer
                                              │
                                              ▼
User ◄── Nemotron Voice Agent (TTS) ◄── Response Text
```

## Repo Layout

The Nemotron Voice Agent must be a **sibling directory** of this repo:

```
parent-directory/
├── [this-repo]/             ← you are here
└── nemotron-voice-agent/    ← clone here before running Docker Compose
```

## Prerequisites

- Docker and Docker Compose
- NVIDIA API key (get one at build.nvidia.com)
- Python 3.11+ (for local venv setup only)
- NVIDIA GPU with CUDA 12.x (required only if running NIM models locally; cloud NIM endpoints do not require a local GPU)

---

## Quick Start (Docker Compose — Recommended)

### 1. Clone and set up the Nemotron Voice Agent

Clone the Nemotron Voice Agent as a sibling directory of this repo:

```bash
# Run from inside this repo's directory
git clone --recurse-submodules https://github.com/NVIDIA-AI-Blueprints/nemotron-voice-agent ../nemotron-voice-agent
```

The Docker Compose stack in this repo starts the Nemotron Voice Agent services automatically (see step 5). All Nemotron Voice Agent model services — ASR and TTS — default to **NVIDIA public cloud endpoints** and require only an `NVIDIA_API_KEY`; no local GPU is needed.

> **Hardware-specific deployments** (Jetson Thor, workstation GPU, or self-hosted NIMs for ASR/TTS):
> invoke the **`nemotron-voice-agent-deploy`** skill from this repository's directory.
> That skill handles driver setup, container registry auth, and NIM-specific configuration
> for each supported hardware target.

### 2. Configure this agent backend environment

```bash
cp .env.example .env
```

Edit `.env` and fill or confirm these values before startup:

| Variable | Required | Notes |
|---|---|---|
| `NVIDIA_API_KEY` | Yes | NVIDIA API key from build.nvidia.com |
| `AGENT_MODEL_NAME` | Yes | Model id exposed by `/v1/models`; must match voice-agent `NVIDIA_LLM_MODEL` |
| `LLM_MODEL` | Yes | Agent reasoning model |
| `LLM_BASE_URL` | Yes | NVIDIA endpoint or self-hosted NIM base URL |
| `LLM_ENABLE_THINKING` | Yes | Only `true` for models that support thinking |
| `LLM_TEMPERATURE` | Yes | Usually `0.0` |
| `LLM_MAX_TOKENS` | Yes | Use `8192` or higher when thinking is enabled |
| `LLM_MOCK_MODE` | Yes | `false` for normal runs |
| `AGENT_PORT` | Yes | Backend port, default `8000` |
| `VOICE_AGENT_PORT` | Yes | Fixed WebRTC voice-agent port, default `7860` |
| `VOICE_AGENT_UI_PORT` | Yes | Browser UI port, default `9000` |
| `LOG_LEVEL` | Yes | Usually `INFO` |
| `GUARDRAILS_ENABLED` / `GUARDRAILS_CONFIG_PATH` | If guardrails are enabled | Required only for guardrails |
| Generated tool/data keys | If generated tools need them | Examples: `TAVILY_API_KEY`, `DATABASE_URL`, or other generated keys |

### 3. Configure the Nemotron Voice Agent environment

The voice agent has its own env file. Docker Compose does not automatically copy
values from this repo's `.env` into `../nemotron-voice-agent/config/.env`.

```bash
cp ../nemotron-voice-agent/config/env.example ../nemotron-voice-agent/config/.env
```

Edit `../nemotron-voice-agent/config/.env` and set:

```dotenv
NVIDIA_API_KEY=<same key as this repo .env>
NVIDIA_LLM_URL=http://agent-backend:${AGENT_PORT:-8000}/v1
NVIDIA_LLM_MODEL=<same value as AGENT_MODEL_NAME from this repo .env>
TRANSPORT=WEBRTC
```

Also fill or confirm any ASR/TTS keys required by the cloned
`../nemotron-voice-agent/config/env.example`. Defaults use NVIDIA public cloud
endpoints unless you intentionally override them.

Do not start Docker Compose until both `.env` and
`../nemotron-voice-agent/config/.env` exist and contain the required values.

### 4. Validate configuration

```bash
docker compose config >/tmp/<agent-name>-compose.yml
```

Confirm the rendered compose file shows:

```yaml
NVIDIA_LLM_URL: http://agent-backend:8000/v1  # or your configured AGENT_PORT
NVIDIA_LLM_MODEL: <same value as AGENT_MODEL_NAME>
```

### 5. Start all services

```bash
docker compose up --build
```

### 6. Open the voice agent

Note: To enable microphone access in Chrome, go to chrome://flags/, enable "Insecure origins treated as secure", add http://<machine-ip>:9000 to the list, and restart Chrome.

Navigate to `http://<machine-ip>:9000` and speak to the agent. If you changed the Docker host UI port, use `http://<machine-ip>:<VOICE_AGENT_UI_PORT>` instead.

---

## Manual Setup (Local Virtual Environment)

Use this path if you prefer not to use Docker.

### 1. Set up this agent backend

```bash
git clone <this-repo>
cd [this-repo]
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
cp .env.example .env
# Edit .env — set NVIDIA_API_KEY at minimum
```

### 2. Initialize the database (if using SQLite)

```bash
.venv/bin/python agent/data/seed.py
```

### 3. Clone and start the Nemotron Voice Agent

```bash
# Run from inside this repo's directory
git clone --recurse-submodules https://github.com/NVIDIA-AI-Blueprints/nemotron-voice-agent ../nemotron-voice-agent
```

Follow `../nemotron-voice-agent/README.md` for prerequisites and startup.

> For hardware-specific deployments (Jetson, workstation GPU, self-hosted ASR/TTS NIMs),
> invoke the **`nemotron-voice-agent-deploy`** skill from this directory.

### 4. Connect the Nemotron Voice Agent to this backend

Edit `../nemotron-voice-agent/config/.env` (verify the exact file path after cloning):

```dotenv
NVIDIA_API_KEY=<same key as this repo .env>
NVIDIA_LLM_URL=http://localhost:${AGENT_PORT:-8000}/v1   # match AGENT_PORT from this repo's .env
NVIDIA_LLM_MODEL=<same value as AGENT_MODEL_NAME from this repo .env>
TRANSPORT=WEBRTC
```

See [docs/voice-integration.md](docs/voice-integration.md) for exact field names and Docker networking details.

### 5. Start the agent backend

```bash
.venv/bin/python agent/server.py
# Listens on 0.0.0.0:${AGENT_PORT} (default 8000)
```

### 6. Start the Nemotron Voice Agent

```bash
cd ../nemotron-voice-agent
# Follow the frontend's start command from its README
```

Open the voice agent UI in your browser and speak to the agent.

---

## Running Tests

```bash
# No NVIDIA_API_KEY required for static checks and mocked tests
.venv/bin/python -m compileall agent tests scripts
.venv/bin/python -c "from agent.server import app; print(app.title)"
.venv/bin/python -m pytest tests/ -v
```

## Using Coding Agents

Point Claude Code, Codex, or another coding agent at:

```text
.agents/skills/<agent-name>/SKILL.md
```

This is the agent-readable runbook for starting, testing, stopping, and
troubleshooting the repo. If your coding-agent product requires skills to be
installed elsewhere, copy or register that generated `SKILL.md`; it remains the
source of truth.

To install the generated agent skill by copying:

```bash
mkdir -p ~/.claude/skills ~/.codex/skills
cp -R .agents/skills/<agent-name> ~/.claude/skills/
cp -R .agents/skills/<agent-name> ~/.codex/skills/
```

To install it by symlink during development:

```bash
mkdir -p ~/.claude/skills ~/.codex/skills
ln -s "$PWD/.agents/skills/<agent-name>" ~/.claude/skills/<agent-name>
ln -s "$PWD/.agents/skills/<agent-name>" ~/.codex/skills/<agent-name>
```

If either destination already exists, remove or rename the old copy before
using the symlink command. Restart Claude Code or Codex after installing so the
skill list refreshes.

## Environment Variables — Agent Backend

| Variable | Required | Default | Description |
|---|---|---|---|
| `NVIDIA_API_KEY` | Yes | — | NVIDIA NIM API key from build.nvidia.com |
| `AGENT_MODEL_NAME` | No | `<agent-name>` | Model id exposed by `/v1/models`; must match `NVIDIA_LLM_MODEL` in the voice agent config |
| `LLM_MODEL` | No | `nvidia/nemotron-3-super-120b-a12b` | LLM model name for agent reasoning |
| `LLM_BASE_URL` | No | `https://integrate.api.nvidia.com/v1` | Inference endpoint base URL |
| `LLM_ENABLE_THINKING` | No | `true` | Enable chain-of-thought reasoning. Only pass to models that support it. |
| `LLM_TEMPERATURE` | No | `0.0` | Sampling temperature (`0.0` recommended when thinking is on) |
| `LLM_MAX_TOKENS` | No | `8192` | Max response tokens (use `8192`+ when thinking is on) |
| `LLM_MOCK_MODE` | No | `false` | Testing-only deterministic backend response; leave false for normal Docker runs |
| `AGENT_PORT` | No | `8000` | Port the agent backend listens on |
| `VOICE_AGENT_PORT` | No | `7860` | Fixed WebRTC pipeline port |
| `VOICE_AGENT_UI_PORT` | No | `9000` | Browser-facing WebRTC UI port |
| `LOG_LEVEL` | No | `INFO` | Python logging level for the agent backend |
| `GUARDRAILS_ENABLED` | If using Guardrails | `false` | Enables NeMo Guardrails graph integration |
| `GUARDRAILS_CONFIG_PATH` | If using Guardrails | `config/guardrails` | Guardrails config directory |
| `TAVILY_API_KEY` | If using Tavily | — | Tavily search API key |
| `DATABASE_URL` | If using SQLite | `agent/data/agent.db` | Path to SQLite file |

## Environment Variables — NVIDIA Nemotron Voice Agent Frontend

Set these inside `../nemotron-voice-agent/config/.env` (verify the exact path after cloning):

| Variable | Required | Description |
|---|---|---|
| `NVIDIA_API_KEY` | Yes | NVIDIA NIM API key (same value as agent backend) |
| `NVIDIA_LLM_URL` | Yes | Must point to this agent backend. Docker Compose: `http://agent-backend:${AGENT_PORT:-8000}/v1`; manual local backend: `http://localhost:${AGENT_PORT:-8000}/v1` |
| `NVIDIA_LLM_MODEL` | Yes | Must match `AGENT_MODEL_NAME` from this repo's `.env` |
| `TRANSPORT` | Yes | Must be `WEBRTC` for the browser voice UI |
| ASR/TTS variables from `env.example` | Yes | Keep defaults for NVIDIA public cloud endpoints, or override for self-hosted NIMs |

Refer to `../nemotron-voice-agent/README.md` for the complete list — verify variable names after cloning.

## Connection Mechanism Between NVIDIA Nemotron Voice Agent and This Agent

Explanation on the mechanism of how the agent implemented connects to the NVIDIA Nemotron Voice Agent. This will contain different content depending on the agent framework chosen.

## Changing Model Configurations

**All three model services default to NVIDIA public cloud endpoints — no local GPU required.** An `NVIDIA_API_KEY` from [build.nvidia.com](https://build.nvidia.com) is the only credential needed to run the full stack out of the box.

Each service can be switched to a self-hosted NIM by changing the relevant endpoint variable. No code changes are required.

| Service | Default endpoint | Override variable |
|---|---|---|
| Agent LLM | `https://integrate.api.nvidia.com/v1` | `LLM_BASE_URL` |
| ASR | `grpc.nvcf.nvidia.com:443` | `ASR_SERVER_URL` |
| TTS | `grpc.nvcf.nvidia.com:443` | `TTS_SERVER_URL` |

### Agent LLM

Set these in `.env`:

```dotenv
LLM_MODEL=meta/llama-3.3-70b-instruct          # swap to any model at LLM_BASE_URL
LLM_BASE_URL=https://integrate.api.nvidia.com/v1 # or a local NIM URL
LLM_ENABLE_THINKING=false                        # only supported by select models
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2048
```

**Switching to a Llama model (faster, lower latency):**

```dotenv
LLM_MODEL=meta/llama-3.3-70b-instruct
LLM_ENABLE_THINKING=false   # Llama does not support thinking mode
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2048
```

**Switching to a local self-hosted NIM:**

```dotenv
LLM_MODEL=meta/llama-3.1-8b-instruct
LLM_BASE_URL=http://localhost:8080/v1   # your local NIM endpoint
```

**Supported models** (NVIDIA AI Endpoints): see [build.nvidia.com](https://build.nvidia.com) for the full catalog.

---

### ASR (Speech-to-Text)

Set these in `.env` (they are passed to the Nemotron Voice Agent container via `docker-compose.yml`):

```dotenv
# NVIDIA public cloud (default — no local GPU required)
ASR_SERVER_URL=grpc.nvcf.nvidia.com:443
ASR_MODEL_NAME=parakeet-1.1b-en-US-asr-streaming-silero-vad-sortformer
ASR_CLOUD_FUNCTION_ID=1598d209-5e27-4d3c-8079-4751568b1081
```

**Switching to a self-hosted Parakeet NIM:**

```dotenv
ASR_SERVER_URL=localhost:50051          # gRPC address of your local NIM
ASR_MODEL_NAME=parakeet-1.1b           # model name as served by the container
ASR_CLOUD_FUNCTION_ID=                  # leave blank — not used for local NIMs
```

`ASR_CLOUD_FUNCTION_ID` is only required when routing through NVIDIA Cloud Functions (`grpc.nvcf.nvidia.com`). Clear it when pointing at a local NIM.

---

### TTS (Text-to-Speech)

Set these in `.env`:

```dotenv
# NVIDIA public cloud (default — no local GPU required)
TTS_SERVER_URL=grpc.nvcf.nvidia.com:443
TTS_MODEL_NAME=magpie_tts_ensemble-Magpie-Multilingual
TTS_VOICE_ID=Magpie-Multilingual.EN-US.Aria
TTS_LANGUAGE=en-US
```

**Changing the voice** (cloud TTS):

| Voice ID | Language | Style |
|---|---|---|
| `Magpie-Multilingual.EN-US.Aria` | English (US) | Female, neutral (default) |
| `Magpie-Multilingual.EN-US.Ryan` | English (US) | Male, neutral |
| `Magpie-Multilingual.ES-US.Maria` | Spanish (US) | Female |

Verify available voices in the [NVIDIA Magpie TTS documentation](https://build.nvidia.com).

**Switching to a self-hosted Magpie TTS NIM:**

```dotenv
TTS_SERVER_URL=localhost:50052          # gRPC address of your local NIM
TTS_MODEL_NAME=magpie_tts              # model name as served by the container
TTS_VOICE_ID=Aria                       # voice ID supported by your container
```

---

## Guardrails

If NeMo Guardrails were enabled during generation, this repo includes:

```text
config/guardrails/
├── config.yml
├── input.co
├── output.co
├── dialog.co
├── retrieval.co
├── execution.co
└── actions.py
```

Only the rail types selected during generation should be present. To change the
rules, edit the matching Colang file, then run:

```bash
python -m pytest tests/test_guardrails.py -v
python - <<'PY'
from nemoguardrails import RailsConfig
RailsConfig.from_path("config/guardrails")
print("RailsConfig load PASS")
PY
docker compose up --build
```

LangGraph plus `RunnableRails` may buffer more than the unguarded graph. Measure
and document latency when output, dialog, retrieval, or execution rails are
enabled.

Execution rails are the tool/action rail type. In current NeMo Guardrails
configs, use `rails.execution.flows` for execution behavior.

---

## Customizing Agent Tools

To add a new capability to the agent:

1. Create a new file in `agent/tools/` (e.g., `agent/tools/my_new_tool.py`):
   ```python
   def my_new_tool(param: str) -> str:
       """One-line description for the LLM."""
       return result
   ```
2. Register it with the framework:
   - Add it to the `tools` list in `agent/graph.py`
3. Add tests in `tests/test_tools.py`.
4. Update `.env.example` if the tool needs new environment variables.

See `.agents/skills/<agent-name>/SKILL.md` for full step-by-step instructions and examples.

---

## Known Limitations

### Voice selector shows "No voices found"

When using the default NVIDIA public cloud TTS endpoint (`grpc.nvcf.nvidia.com:443`), the voice
selector in the WebRTC UI will show **"No voices found"**. This is cosmetic — the cloud TTS
endpoint does not implement the `list_available_voices()` gRPC method. TTS still works; the
pre-configured `TTS_VOICE_ID` is used for all synthesis.

To populate the voice selector, switch to a self-hosted Magpie TTS NIM and set
`TTS_SERVER_URL=localhost:50051`.

### Blank page or missing assets after switching transport modes

The browser may serve a cached version of the old UI. Hard-refresh with **Ctrl+Shift+R**
(Windows/Linux) or **Cmd+Shift+R** (Mac) after switching between WebSocket and WebRTC modes.

### VOICE_AGENT_PORT must remain 7860 for WebRTC

The React UI build (`frontend/webrtc_ui/src/config.ts`) hardcodes `:7860/offer` for WebRTC
signalling. `VOICE_AGENT_PORT` only shifts the host-side port mapping. Changing it away from
`7860` causes the browser to dial a port with nothing listening and show a connection error.

---

## Troubleshooting

### Voice UI: "Cannot read properties of undefined (reading 'getUserMedia')"

This error means the browser blocked microphone access because the page is not in a **secure context**. Browsers only allow `getUserMedia` on `localhost` or HTTPS. When you access the UI over plain HTTP from a remote host, the API is disabled.

**Fix — add the origin to Chrome's insecure-origins allowlist:**

1. Open `chrome://flags/#unsafely-treat-insecure-origin-as-secure` in a new tab.
2. Add **both** of the following URLs to the text field (comma-separated):
   ```
   http://<host-ip>:<UI_PORT>, http://<host-ip>:<VOICE_AGENT_PORT>
   ```
   Replace `<host-ip>` with the machine's IP address (see next section). Default ports are `9000` (UI) and `7860` (voice agent).
3. Set the flag dropdown to **Enabled**.
4. Click **Relaunch** at the bottom of the page — Chrome must fully restart (close all windows) for the flag to take effect.
5. Reopen the UI at `http://<host-ip>:<UI_PORT>` and click **Start** again.

If `getUserMedia` is still undefined after relaunching, open DevTools (F12) → **Console** and run:

```js
window.isSecureContext        // must be true
typeof navigator.mediaDevices // must be "object", not "undefined"
```

If `window.isSecureContext` returns `false`, the flag was not applied. Double-check that the exact URL (including port) is in the flag list and that you closed and reopened all Chrome windows.

### Voice UI: use the IP address, not the hostname

WebRTC requires that the URL you open in the browser matches exactly what is registered in the Chrome insecure-origins flag. Hostnames (e.g., `myworkstation.local`, `myserver`) will **not** match an IP-based flag entry, so `getUserMedia` will still be blocked.

**Always use the numeric IP address** when accessing the UI from another machine:

```
http://192.168.x.x:<UI_PORT>
```

To find the server's IP address:

```bash
# Linux / macOS
ip addr show   # or: hostname -I
```

Add that IP-based URL to the Chrome flag, not the hostname.
```

---

## Runnable Skill Template (`.agents/skills/<agent-name>/SKILL.md`)

```markdown
---
name: <agent-name>
description: >
  Start, stop, test, and configure the <agent-name> ambient healthcare voice agent.
  This agent [one-sentence capability summary].
  Use when asked to run, start, stop, restart, test, check status, view logs,
  inspect saved records, update Guardrails, or update configuration.
compatibility: Requires Docker, Docker Compose, Python 3.11+, and an NVIDIA API key from build.nvidia.com.
metadata:
  author: <org-or-author>
  version: "1.0"
---

# <Project Name> Ambient Healthcare Agent

This repo contains an ambient healthcare voice agent that connects to the NVIDIA Nemotron Voice Agent
frontend for speech-to-text and text-to-speech. The agent handles [list of functions].
It is built with LangGraph and uses [SQLite / RAG / Tavily / mock fixtures] for data access.

## Repo Layout Assumption

The Nemotron Voice Agent is expected as a **sibling directory** of this repo:

```
parent-directory/
├── [this-repo]/             ← you are here
└── nemotron-voice-agent/    ← ../nemotron-voice-agent
```

If `../nemotron-voice-agent` does not exist, clone it:

```bash
git clone --recurse-submodules https://github.com/NVIDIA-AI-Blueprints/nemotron-voice-agent ../nemotron-voice-agent
```

## Prerequisites

Before starting, verify both env files exist and required credentials are filled in:

```bash
test -s .env
test -s ../nemotron-voice-agent/config/.env
grep -q '^NVIDIA_API_KEY=nvapi-' .env
grep -q '^NVIDIA_API_KEY=nvapi-' ../nemotron-voice-agent/config/.env
grep -q '^NVIDIA_LLM_URL=' ../nemotron-voice-agent/config/.env
grep -q '^NVIDIA_LLM_MODEL=' ../nemotron-voice-agent/config/.env
```

For Docker Compose, `../nemotron-voice-agent/config/.env` must use:

```dotenv
NVIDIA_LLM_URL=http://agent-backend:${AGENT_PORT:-8000}/v1
NVIDIA_LLM_MODEL=<same value as AGENT_MODEL_NAME from .env>
```

For a manual local backend, use:

```dotenv
NVIDIA_LLM_URL=http://localhost:${AGENT_PORT:-8000}/v1
NVIDIA_LLM_MODEL=<same value as AGENT_MODEL_NAME from .env>
```

If any command fails, stop and ask the user to fill in the missing value before running Docker Compose.

## Static Checks

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m compileall agent tests scripts
python -c "from agent.server import app; print(app.title)"
docker compose config >/tmp/<agent-name>-compose.yml
```

Inspect `/tmp/<agent-name>-compose.yml` and confirm
`NVIDIA_LLM_MODEL` matches `AGENT_MODEL_NAME`.

## Start

```bash
docker compose up --build
```

| Service | Command | Port |
|---|---|---|
| Agent backend | `agent/server.py` in container | `${AGENT_PORT:-8000}` |
| Nemotron Voice Agent | WebRTC pipeline | `${VOICE_AGENT_PORT:-7860}` |
| Voice Agent UI | React WebRTC UI | `${VOICE_AGENT_UI_PORT:-9000}` |

Open the Docker-published UI at `http://<machine-ip>:9000`. If you changed the Docker host UI port, use `http://<machine-ip>:<VOICE_AGENT_UI_PORT>` instead.

## Stop

```bash
docker compose down
```

To remove volumes as well:

```bash
docker compose down -v
```

## Status And Logs

```bash
docker compose ps
docker compose logs -f agent-backend
docker compose logs -f nemotron-voice-agent
docker compose logs -f voice-agent-ui
```

## Run Tests

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m compileall agent tests scripts
python -c "from agent.server import app; print(app.title)"
python -m pytest tests/ -v
```

## Smoke Test

```bash
python scripts/smoke_voice_connection.py

curl -N "http://localhost:${AGENT_PORT:-8000}/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"${AGENT_MODEL_NAME:-<agent-name>}\",\"stream\":true,\"messages\":[{\"role\":\"user\",\"content\":\"You are a helpful assistant. Always answer as helpful, friendly, and polite. Respond with one sentence or less than 75 characters.\"},{\"role\":\"user\",\"content\":\"hello\"}]}"
```

## Key Files

| File | Purpose |
|---|---|
| `agent/server.py` | FastAPI server; exposes `/v1/chat/completions` for the Nemotron Voice Agent |
| `agent/graph.py` | LangGraph graph definition |
| `agent/tools/` | One file per agent function; each exposes a callable tool |
| `scripts/smoke_voice_connection.py` | Verifies running stack endpoints, model id, and streaming response |
| `config/guardrails/` | NeMo Guardrails config and Colang files, if enabled |
| `.env.example` | All required environment variables with descriptions |
| `docs/voice-integration.md` | Full API contract and connection guide for the Nemotron Voice Agent |

## How to Add a New Tool

1. Create `my_new_tool.py` in `agent/tools/`:
   ```python
   def my_new_tool(param: str) -> str:
       """One-line description for the LLM."""
       # implementation
       return result
   ```

2. Register the tool in the `tools` list in `agent/graph.py`.

3. Add tests in `tests/test_tools.py`.

4. Update this skill if the tool introduces new environment variables or dependencies.

## Guardrails

If enabled, edit Colang rules and custom actions in `config/guardrails/`, then run:

```bash
python -m pytest tests/test_guardrails.py -v
python - <<'PY'
from nemoguardrails import RailsConfig
RailsConfig.from_path("config/guardrails")
print("RailsConfig load PASS")
PY
docker compose up --build
```

LangGraph plus `RunnableRails` may buffer more than the unguarded graph. Measure and document latency when output, dialog, retrieval, or execution rails are enabled.

## Configuration

| Variable | Default | Description |
|---|---|---|
| `NVIDIA_API_KEY` | — | Required NVIDIA API key |
| `AGENT_MODEL_NAME` | `<agent-name>` | Model id exposed by `/v1/models` and used by `NVIDIA_LLM_MODEL` |
| `LLM_MODEL` | `nvidia/nemotron-3-super-120b-a12b` | Agent reasoning model |
| `LLM_BASE_URL` | `https://integrate.api.nvidia.com/v1` | Agent model endpoint |
| `LLM_MOCK_MODE` | `false` | Testing-only deterministic backend response |
| `AGENT_PORT` | `8000` | Agent backend port |
| `VOICE_AGENT_PORT` | `7860` | Fixed WebRTC pipeline port |
| `VOICE_AGENT_UI_PORT` | `9000` | Browser UI port |
| `LOG_LEVEL` | `INFO` | Agent backend log level |

## Connect A Different Voice Frontend

The backend exposes an OpenAI-compatible REST endpoint:
- **Endpoint**: `POST /v1/chat/completions`
- **Request**: `{"model": "...", "messages": [...], "stream": true}`
- **Response**: OpenAI chat completion object or SSE stream

## Dependencies

See `requirements.txt`. Key packages:

| Package | Purpose |
|---|---|
| `fastapi` | HTTP/REST server for `/v1/chat/completions` (LangGraph only) |
| `uvicorn` | ASGI server (LangGraph only) |
| `langgraph` | Agent graph (LangGraph only) |
| `langchain-nvidia-ai-endpoints` | NIM model access via OpenAI-compatible API |
| `nemoguardrails` | Optional NeMo Guardrails runtime |
```

---

## docker-compose.yml Template

Use this to containerize the agent backend and the Nemotron Voice Agent together. The `nemotron-voice-agent` service is **active** (not commented out) — clone `../nemotron-voice-agent` before running `docker compose up` (Step 1 of the Quick Start in README).

**Always use `TRANSPORT=WEBRTC`.** The WebSocket UI is a bare-bones HTML page; the WebRTC UI is the full React application users expect.

**VOICE_AGENT_PORT must remain 7860.** The WebRTC React UI (`frontend/webrtc_ui/src/config.ts`) hardcodes `:7860/offer` for WebRTC signalling at build time. Changing `VOICE_AGENT_PORT` only shifts the host-side port mapping — the browser will still dial port 7860 and fail to connect.

```yaml
name: <agent-name>

services:

  # --------------------------------------------------------------------------
  # Agent backend — LangGraph + FastAPI
  # --------------------------------------------------------------------------
  agent-backend:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      # IMPORTANT: both sides of the mapping must use ${AGENT_PORT:-8000}.
      # If the target is hardcoded to 8000 but AGENT_PORT is set to something
      # else, the container listens on the wrong port and health checks fail.
      - "${AGENT_PORT:-8000}:${AGENT_PORT:-8000}"
    env_file: .env
    environment:
      - AGENT_PORT=${AGENT_PORT:-8000}
      - AGENT_MODEL_NAME=${AGENT_MODEL_NAME:-<agent-name>}
    volumes:
      - ./agent/data:/app/agent/data
    healthcheck:
      # Use CMD-SHELL so the shell expands ${AGENT_PORT:-8000}.
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:${AGENT_PORT:-8000}/health').read()\""]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"

  # --------------------------------------------------------------------------
  # Nemotron Voice Agent pipeline (WebRTC mode)
  # Uses cloud ASR + TTS; LLM is our agent-backend above.
  # --------------------------------------------------------------------------
  nemotron-voice-agent:
    # Requires ../nemotron-voice-agent to be cloned first (see Quick Start step 1 in README).
    build:
      context: ../nemotron-voice-agent
      dockerfile: Dockerfile
    # pipeline.py is the WebRTC pipeline. Always use this — the WebSocket
    # pipeline (pipeline_websocket.py) only serves a bare-bones HTML UI.
    # The port must be 7860 — the React UI hardcodes it in config.ts.
    command: >
      bash -c "uv run src/pipeline.py --host 0.0.0.0 --port 7860 --workers 1"
    ports:
      # VOICE_AGENT_PORT controls only the host-side mapping.
      # The container ALWAYS listens on 7860 (hardcoded in config.ts build).
      # Do not change the container target from 7860.
      - "${VOICE_AGENT_PORT:-7860}:7860"
    env_file: .env
    environment:
      # Point the voice agent at our agent backend instead of a local NIM
      - NVIDIA_LLM_URL=http://agent-backend:${AGENT_PORT:-8000}/v1
      - NVIDIA_LLM_MODEL=${AGENT_MODEL_NAME:-<agent-name>}
      # Cloud ASR endpoint (no local NIM needed)
      - ASR_SERVER_URL=${ASR_SERVER_URL:-grpc.nvcf.nvidia.com:443}
      - ASR_MODEL_NAME=${ASR_MODEL_NAME:-parakeet-1.1b-en-US-asr-streaming-silero-vad-sortformer}
      - ASR_CLOUD_FUNCTION_ID=${ASR_CLOUD_FUNCTION_ID:-1598d209-5e27-4d3c-8079-4751568b1081}
      # Cloud TTS endpoint (no local NIM needed)
      - TTS_SERVER_URL=${TTS_SERVER_URL:-grpc.nvcf.nvidia.com:443}
      - TTS_MODEL_NAME=${TTS_MODEL_NAME:-magpie_tts_ensemble-Magpie-Multilingual}
      - TTS_VOICE_ID=${TTS_VOICE_ID:-Magpie-Multilingual.EN-US.Aria}
      - TTS_LANGUAGE=${TTS_LANGUAGE:-en-US}
      # Pipeline configuration
      - TRANSPORT=WEBRTC
      - SYSTEM_PROMPT_SELECTOR=nemotron-3-nano/generic_voice_assistant
      - ENABLE_THINKING=false
      - VAD_PROFILE=ASR
      - ENABLE_SPECULATIVE_SPEECH=false
      - CHAT_HISTORY_LIMIT=40
      - NVIDIA_API_KEY=${NVIDIA_API_KEY}
    depends_on:
      agent-backend:
        condition: service_healthy
    healthcheck:
      # IMPORTANT: use curl, not python. The nemotron-voice-agent container
      # uses uv and does not have a bare python binary on its PATH.
      # Use /docs (FastAPI Swagger), not /health — pipeline.py (WebRTC mode)
      # does not expose a /health endpoint.
      test: ["CMD-SHELL", "curl -sf http://localhost:7860/docs || exit 1"]
      interval: 15s
      timeout: 10s
      retries: 5
      start_period: 60s
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"

  # --------------------------------------------------------------------------
  # Nemotron Voice Agent UI (WebRTC frontend — full React UI)
  # --------------------------------------------------------------------------
  voice-agent-ui:
    # Requires ../nemotron-voice-agent to be cloned first (see Quick Start step 1 in README).
    build:
      context: ../nemotron-voice-agent
      dockerfile: frontend/Dockerfile
    # Delay startup so the voice agent has time to warm up its cloud gRPC
    # connections (ASR/TTS) before the browser makes its first WebRTC offer.
    # Without this sleep, the first page load hits a cold-start race and shows
    # a connection error; a reload is then required.
    # IMPORTANT: exec form (array) required — the frontend image is
    # nvcr.io/nvidia/distroless/python (no sh/bash). Shell form causes the
    # Go shell_wrapper entrypoint to panic: "sh: executable file not found".
    command: ["python", "-c", "import time; time.sleep(15); exec(open('start-server.py').read())"]
    ports:
      - "${VOICE_AGENT_UI_PORT:-9000}:8000"
    env_file: .env
    environment:
      - TRANSPORT=WEBRTC
    depends_on:
      nemotron-voice-agent:
        condition: service_healthy
    healthcheck:
      # Use exec form. The UI container is distroless Python and has no shell.
      test: ["CMD", "curl", "-sf", "http://localhost:8000"]
      interval: 15s
      timeout: 10s
      retries: 3
      start_period: 30s
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"

  # Add other backend services here (e.g., a Milvus vector DB for RAG) as needed.
```

---

## scripts/smoke_voice_connection.py Template

Create `scripts/smoke_voice_connection.py` to verify the running Docker Compose
stack without changing the launch command.

```python
#!/usr/bin/env python3
import json
import os
import sys
import urllib.request


def load_env(path=".env"):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def expect_http(url):
    with urllib.request.urlopen(url, timeout=10) as resp:
        if resp.status >= 400:
            raise RuntimeError(f"{url} returned HTTP {resp.status}")
        return resp.read().decode("utf-8", errors="replace")


def get_json(url):
    return json.loads(expect_http(url))


def post_stream(url, payload):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    if "data:" not in body or "data: [DONE]" not in body:
        raise RuntimeError("streaming response did not contain SSE data and [DONE]")
    return body


def extract_sse_text(body):
    parts = []
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("data: "):
            continue
        data = line.removeprefix("data: ").strip()
        if data == "[DONE]":
            continue
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            continue
        for choice in payload.get("choices", []):
            delta = choice.get("delta") or {}
            message = choice.get("message") or {}
            if delta.get("content"):
                parts.append(str(delta["content"]))
            if message.get("content"):
                parts.append(str(message["content"]))
    return "".join(parts).strip()


def assert_reasonable_reply(user_text, reply):
    normalized = reply.strip().lower().strip(" .:;!?")
    if not reply or len(reply.strip()) < 4:
        raise RuntimeError(f"empty or too-short assistant reply for {user_text!r}: {reply!r}")
    if normalized in {"yes", "no", "safe", "unsafe"}:
        raise RuntimeError(f"bare guardrail/classifier verdict for {user_text!r}: {reply!r}")
    if normalized == user_text.strip().lower().strip(" .:;!?"):
        raise RuntimeError(f"assistant only echoed the user utterance: {reply!r}")


def post_voice_agent_turn(base, model, user_text):
    voice_context = (
        "You are a helpful assistant. Always answer as helpful, friendly, and polite. "
        "Respond with one sentence or less than 75 characters."
    )
    body = post_stream(
        f"{base}/v1/chat/completions",
        {
            "model": model,
            "stream": True,
            "temperature": 0,
            "messages": [
                {"role": "user", "content": voice_context},
                {"role": "user", "content": user_text},
            ],
        },
    )
    reply = extract_sse_text(body)
    assert_reasonable_reply(user_text, reply)
    return reply


def main():
    load_env()
    agent_port = int(os.getenv("AGENT_PORT", "8000"))
    voice_port = int(os.getenv("VOICE_AGENT_PORT", "7860"))
    ui_port = int(os.getenv("VOICE_AGENT_UI_PORT", "9000"))
    model = os.getenv("AGENT_MODEL_NAME", "<agent-name>")

    base = f"http://localhost:{agent_port}"
    expect_http(f"{base}/health")
    debug = get_json(f"{base}/debug/config")
    if debug.get("agent_model_name") != model:
        raise RuntimeError(f"AGENT_MODEL_NAME mismatch: {debug.get('agent_model_name')} != {model}")

    models = get_json(f"{base}/v1/models")
    model_ids = [item["id"] for item in models.get("data", [])]
    if model not in model_ids:
        raise RuntimeError(f"{model} not listed by /v1/models: {model_ids}")

    post_voice_agent_turn(base, model, "hello")
    post_voice_agent_turn(base, model, "Hi I'm here to check in")

    expect_http(f"http://localhost:{voice_port}/docs")
    expect_http(f"http://localhost:{ui_port}/")
    print("voice connection smoke PASS")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"voice connection smoke FAIL: {exc}", file=sys.stderr)
        raise
```

---

## Logging Pattern for agent/server.py

The agent backend must emit structured log lines for all significant events. Use Python's `logging` module. Add this pattern at the top of `agent/server.py` (and any tool module that needs per-tool logging):

```python
import logging
import json

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-5s [%(name)s] %(message)s",
)
logger = logging.getLogger("intake")   # replace with the agent/module name
```

Required log events and their format:

```python
# On every call to the /v1/chat/completions endpoint
logger.info("request_received messages=%d", len(body.get("messages", [])))

# When the LLM invokes a tool — redact PII fields before logging
logger.info("tool_call tool=%s args=%s", tool_name, json.dumps(safe_args))

# After the tool returns or raises
logger.info("tool_result tool=%s status=ok", tool_name)
logger.error("tool_result tool=%s status=error", tool_name, exc_info=True)

# First 500 characters of each LLM assistant response
logger.info("llm_response preview=%r", response_text[:500])

# Full traceback for any unhandled exception before returning 500
logger.error("unhandled_exception", exc_info=True)
```

Example output:
```
INFO  [intake] request_received messages=5
INFO  [intake] tool_call tool=summarize_intake fields_collected=6
INFO  [intake] tool_result tool=summarize_intake status=ok
INFO  [intake] llm_response preview="Thank you Jane. I have all the information I need."
ERROR [intake] unhandled_exception ...traceback...
```

**PII redaction:** Before logging tool arguments, replace any field names that may contain patient data (name, dob, date_of_birth, insurance_id, ssn, phone, email, address) with `"[REDACTED]"`.

---

## .env.example Template

```bash
# =============================================================================
# REQUIRED CREDENTIALS
# =============================================================================

# NVIDIA NIM API key — get at build.nvidia.com
NVIDIA_API_KEY=nvapi-...

# Model id exposed by /v1/models. The voice agent's NVIDIA_LLM_MODEL must match.
AGENT_MODEL_NAME=<agent-name>

# =============================================================================
# LLM CONFIGURATION
# =============================================================================

# Model name for agent reasoning.
# Default: NVIDIA Nemotron Super — high-capability model with reasoning support.
# Alternatives: meta/llama-3.3-70b-instruct, meta/llama-3.1-8b-instruct
LLM_MODEL=nvidia/nemotron-3-super-120b-a12b

# Inference endpoint base URL (NVIDIA AI Endpoints, or a local NIM URL)
LLM_BASE_URL=https://integrate.api.nvidia.com/v1

# Enable chain-of-thought reasoning / thinking mode (true/false).
# ONLY supported by select models (e.g., nvidia/nemotron-3-super-120b-a12b).
# Set to false for models that do not support it — passing this parameter to
# an unsupported model will cause an API error.
# When true, LLM_MAX_TOKENS should be >= 8192 to accommodate reasoning tokens.
LLM_ENABLE_THINKING=true

# Sampling temperature.
# Recommended: 0.0 when LLM_ENABLE_THINKING=true (deterministic reasoning).
LLM_TEMPERATURE=0.0

# Maximum tokens in the model response.
# Use >= 8192 when LLM_ENABLE_THINKING=true; 2048 is sufficient otherwise.
LLM_MAX_TOKENS=8192

# Testing-only deterministic backend response. Leave false for normal Docker runs.
LLM_MOCK_MODE=false

# =============================================================================
# AGENT BACKEND SERVER
# =============================================================================

# Agent backend server port
AGENT_PORT=8000

# Port the Nemotron Voice Agent pipeline listens on (used in docker-compose host-side port mapping).
# WARNING: Must remain 7860 when using WebRTC transport. The React UI build hardcodes
# port 7860 in frontend/webrtc_ui/src/config.ts. Changing this value shifts only the
# host-side mapping; the browser still dials port 7860 and will fail to connect.
VOICE_AGENT_PORT=7860

# Port the Nemotron Voice Agent React UI is served on (host-side).
# The container always listens on 8000 internally.
VOICE_AGENT_UI_PORT=9000

# Python logging level for the agent backend.
LOG_LEVEL=INFO

# =============================================================================
# GUARDRAILS CONFIGURATION
# =============================================================================

# Only used when NeMo Guardrails are enabled.
GUARDRAILS_ENABLED=false
GUARDRAILS_CONFIG_PATH=config/guardrails
GUARDRAILS_SAFETY_MODEL=nvidia/llama-3.1-nemotron-safety-guard-8b-v3
GUARDRAILS_SAFETY_BASE_URL=https://integrate.api.nvidia.com/v1

# =============================================================================
# DATA LAYER
# =============================================================================

# SQLite database path (relative to repo root)
DATABASE_URL=agent/data/agent.db

# Tavily API key — only needed if using web search tool
# TAVILY_API_KEY=tvly-...
```

---

## requirements.txt Template

```
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
python-dotenv>=1.0.0

# LangGraph path (1.0 LTS — per langchain-dependencies skill)
langgraph>=1.0,<2.0
langchain>=1.0,<2.0
langchain-core>=1.0,<2.0
langchain-nvidia-ai-endpoints>=0.3.0
# nemoguardrails  # uncomment if guardrails enabled in Phase 2(f)

# Data layer (uncomment as needed)
# sqlalchemy>=2.0      # SQLite ORM
# tavily-python>=0.3   # Tavily web search

# Testing
pytest>=8.0
pytest-asyncio>=0.23
httpx>=0.27           # async HTTP client for FastAPI test client
```

---

## docs/voice-integration.md Template

Document the exact steps needed to clone, configure, and run the Nemotron Voice Agent so it connects to this agent backend. Include:

```markdown
# Connecting to the NVIDIA Nemotron Voice Agent

This agent backend is designed to work with the
[NVIDIA Nemotron Voice Agent](https://github.com/NVIDIA-AI-Blueprints/nemotron-voice-agent),
which provides speech-to-text (STT) and text-to-speech (TTS) capabilities.

## Step 1: Clone the Nemotron Voice Agent

```bash
git clone --recurse-submodules https://github.com/NVIDIA-AI-Blueprints/nemotron-voice-agent ../nemotron-voice-agent
```

## Step 2: Install and configure it

Follow the Nemotron Voice Agent's own README for prerequisites and installation.

## Step 3: Point it at this agent backend

Edit `../nemotron-voice-agent/config/.env` (verify the exact file path after cloning):

```dotenv
NVIDIA_API_KEY=<same key as this repo .env>
NVIDIA_LLM_URL=http://localhost:${AGENT_PORT:-8000}/v1   # match AGENT_PORT from this repo's .env
NVIDIA_LLM_MODEL=<same value as AGENT_MODEL_NAME from this repo .env>
TRANSPORT=WEBRTC
```

[Verify the exact env var names by checking `../nemotron-voice-agent/config/env.example` after cloning.]

## Step 4: Start both services

Start this agent backend first:

```bash
python agent/server.py
# Listens on 0.0.0.0:${AGENT_PORT}
```

Then start the Nemotron Voice Agent per its README.

## API Contract

The Nemotron Voice Agent calls this backend as an OpenAI-compatible LLM service.

**Endpoint:** `POST /v1/chat/completions`

**Request** (sent by the Nemotron Voice Agent on every conversation turn):
```json
{
  "model": "<agent-name>",
  "messages": [
    {"role": "system", "content": "<voice agent system prompt>"},
    {"role": "user",   "content": "Hello"},
    {"role": "assistant", "content": "Hello! May I have the patient's full name?"},
    {"role": "user",   "content": "Jane Doe"}
  ],
  "stream": true
}
```

**Response** (SSE stream — emit complete response as a single chunk):
```
data: {"id":"chatcmpl-...","object":"chat.completion.chunk","choices":[{"delta":{"role":"assistant","content":"What is the patient's date of birth?"},"finish_reason":null}]}

data: {"id":"chatcmpl-...","object":"chat.completion.chunk","choices":[{"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

**Connection parameters:**

| Variable (this repo's `.env`) | Variable (voice agent `.env`) | Description |
|---|---|---|
| `AGENT_PORT` | `NVIDIA_LLM_URL` host/port | Port this backend listens on |
| `AGENT_MODEL_NAME` | `NVIDIA_LLM_MODEL` | Model id exposed by `/v1/models` and passed in requests |
```

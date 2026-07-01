# Design Requirements Guide

Extended guidance for each design requirement phase, including edge cases, follow-up questions, and example answers.

---

## (a) Voice Interface — Nemotron Voice Agent

### What to investigate in the cloned repo

After cloning `nemotron-voice-agent` into a temporary directory (for investigation only — do not copy it into the output repo), read these key files to understand integration points:

- `README.md` — deployment prerequisites and startup
- Any `server.py`, `app.py`, or `main.py` at the repo root — identifies the server framework (FastAPI, Flask, WebSocket)
- The LLM integration point — look for `NVIDIA_LLM_URL` usage (the voice agent routes all LLM calls to an OpenAI-compatible `/v1/chat/completions` endpoint; our agent backend will replace this)
- Message schema — look for Pydantic models or TypedDict definitions used in the chat completions request/response
- Config files (`.env.example`, `config.yaml`) — identify required API keys and ports
- `frontend/webrtc_ui/src/config.ts` — note the hardcoded port 7860 for WebRTC signalling (see transport mode note below)

### Transport mode: always use WebRTC

**Always generate with `TRANSPORT=WEBRTC` and `src/pipeline.py`.** Do not use WebSocket mode unless the user explicitly asks for it.

- `pipeline.py` (WebRTC) → full React UI with microphone button, live transcripts, voice selector
- `pipeline_websocket.py` (WebSocket) → bare-bones two-button HTML page (dev tool only)

**Known upstream limitation:** `frontend/webrtc_ui/src/config.ts` hardcodes `:7860/offer` for WebRTC signalling at build time. The `VOICE_AGENT_PORT` env var only changes the host-side port mapping in `docker-compose.yml` — it does not patch the compiled JavaScript. Do not attempt to fix this by modifying the Nemotron Voice Agent repo.

### Health check rules for Docker Compose

These rules are non-obvious and caused container failures in testing:

- **`nemotron-voice-agent`**: Use `curl -sf http://localhost:7860/docs || exit 1`. Two reasons:
  1. The container is built with `uv` — no bare `python` binary on PATH. `CMD ["python", ...]` fails immediately.
  2. `pipeline.py` (WebRTC mode) exposes `/docs` (FastAPI Swagger) but not `/health`.
- **`agent-backend`**: Use `CMD-SHELL` with `${AGENT_PORT:-8000}` so the probe port matches the actual `AGENT_PORT`. A hardcoded `8000` fails whenever the user sets `AGENT_PORT` to something else.
- **`voice-agent-ui`**: Add `sleep 15` before `python start-server.py`. Cloud gRPC connections (ASR/TTS) are established lazily on the first `run_bot()` call. Without the sleep, the browser connects during the cold-start window and WebRTC ICE times out — showing a connection error that clears only on reload.

### If the user objects to Nemotron Voice Agent

Capture the alternative and confirm:
- Is it a REST or WebSocket interface?
- Does it provide ASR (speech-to-text), TTS (text-to-speech), or both?
- What message format does it use?

Adjust step (e) accordingly.

---

## (b) Agent Functionality — Follow-up Questions

If the user gives a vague list, drill into each function:

If the user is unsure which function to pick, remind them they can define their
own agent capability or choose one or more examples: patient intake, appointment making,
prescription refill requests, Clinical FAQ, or another custom
capability.

**Patient intake:**
- What fields does the intake form have? (name, DOB, insurance, chief complaint, allergies, medications?)
- Is the data saved to a record or just collected and surfaced to a clinician?

**Appointment making:**
- Does the agent need to check real-time availability or use mock slots?
- Does it need to send confirmation (email, SMS) — or just return a confirmation number?
- Can patients reschedule or cancel?

**Prescription refill requests:**
- Does the agent verify the prescription exists in a record, or accept any request?
- Is there an authorization step (e.g., confirm identity)?
- Does it notify a pharmacy or just log the request?

**Clinical FAQ:**
- Which source should the agent use: static FAQ files, clinical policy documents, or a RAG-backed knowledge base?
- Should answers cite the FAQ entry or document section used?
- What should the agent do when the FAQ does not contain a reliable answer?

**Symptom triage:**
- What triage logic applies? (e.g., severity keywords → urgency level)
- What are the routing outcomes? (schedule urgent visit, go to ER, self-care advice)

---

## (c) Database / Data Source — Decision Guide

### SQLite (recommended for demos)

Best when:
- The demo needs to run without cloud infrastructure
- Data is structured (appointments, patients, prescriptions)
- The developer wants to iterate quickly

Schema approach: Create normalized tables with seed data. Provide a `seed.py` script.

### JSON files

Best when:
- The demo needs simple local read/write data without a database
- Data records are small and naturally document-shaped
- The developer wants generated files that are easy to inspect by hand

File approach: Store records under `data/` as one or more `.json` files. Use
atomic writes for updates and keep schemas explicit in the generated spec.

### NVIDIA RAG (NIM + Milvus)

Best when:
- The agent needs to answer questions from unstructured clinical documents (e.g., treatment guidelines, formularies)
- The user has NVIDIA API access

Integration approach: Use LangChain's Milvus integration and NVIDIA NIM
embeddings/retrieval endpoints. Provide a document ingestion script.

### Tavily Web Search

Best when:
- The agent needs live general medical information
- No private/patient data is involved

Integration approach: LangChain `TavilySearchResults` tool or direct Tavily API. Requires `TAVILY_API_KEY`.

### Mock / Hardcoded

Best when:
- Speed of demo is the priority
- The user wants to focus on agent logic, not data infrastructure

Approach: Return hardcoded Python dicts from tool functions. Clearly label as mock.

### Mixing backends

If the user wants different backends per function (e.g., SQLite for appointments, RAG for clinical docs), note this and implement accordingly. Each tool module can use a different data source.

---

## (e) LLM Model Selection — Guidance

### Default recommendation

Present **NVIDIA Nemotron Super** (`nvidia/nemotron-3-super-120b-a12b`) as the default. It is NVIDIA's highest-capability model, served via NVIDIA AI Endpoints, and is the only model in the NVIDIA catalog that supports configurable chain-of-thought reasoning (thinking mode) at the time of writing.

Model page: https://build.nvidia.com/nvidia/nemotron-3-super-120b-a12b

### Alternative models to suggest if the user asks

| Model | Best for | Supports thinking? |
|---|---|---|
| `nvidia/nemotron-3-super-120b-a12b` | Best reasoning, complex multi-step tasks | Yes (`enable_thinking`) |
| `meta/llama-3.3-70b-instruct` | Fast, cost-effective, widely used | No |
| `meta/llama-3.1-8b-instruct` | Low latency, lightweight tasks | No |
| `nvidia/llama-3.3-nemotron-super-49b-v1.5` | Balanced NVIDIA model, supports `/no_think` prefix | Partial (via prompt prefix) |

### Reasoning / thinking mode

**What it is**: When enabled, the model performs internal chain-of-thought reasoning before producing its final response. This typically improves response quality for complex, multi-step tasks (like patient intake that requires tracking many fields) at the cost of increased latency and token usage.

**When to recommend on**: Multi-step reasoning tasks, intake forms with many fields, triage workflows.

**When to recommend off**: Simple Q&A, high-throughput applications where latency matters, models that do not support it.

**Implementation rules** (enforce in generated code):
1. Read `LLM_ENABLE_THINKING` from the environment as a boolean string (`"true"`/`"false"`).
2. Only pass the thinking parameter to the API if the model supports it — check this at startup and log a warning if `LLM_ENABLE_THINKING=true` but the model does not support it.
3. When thinking is enabled, `LLM_MAX_TOKENS` must be at least `8192` (reasoning tokens count against the limit). Set this as the default automatically.
4. Temperature should default to `0.0` when thinking is enabled (deterministic reasoning).

**Example implementation pattern**:
```python
enable_thinking = os.getenv("LLM_ENABLE_THINKING", "true").lower() == "true"
max_tokens = int(os.getenv("LLM_MAX_TOKENS", "8192" if enable_thinking else "2048"))
temperature = float(os.getenv("LLM_TEMPERATURE", "0.0" if enable_thinking else "0.7"))

extra_body = {}
if enable_thinking:
    extra_body["chat_template_kwargs"] = {"enable_thinking": True}

llm = ChatNVIDIA(
    model=os.getenv("LLM_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
    base_url=os.getenv("LLM_BASE_URL", "https://integrate.api.nvidia.com/v1"),
    api_key=os.getenv("NVIDIA_API_KEY"),
    temperature=temperature,
    max_completion_tokens=max_tokens,
    **({"model_kwargs": {"extra_body": extra_body}} if extra_body else {}),
)
```

### If the user specifies a non-NVIDIA provider

Capture the base URL and API key env var name they want to use. Adjust the LangChain client accordingly (e.g., use `ChatOpenAI` with a custom `base_url` for any OpenAI-compatible endpoint). Set `LLM_ENABLE_THINKING=false` and note it is not applicable.

---

## (d) LangGraph Graph Pattern — Guidance

LangGraph is fixed for this skill. Do not offer NeMo Agent Toolkit or another
agent framework as an implementation option.

- **Strengths**: Mature, large community, excellent for stateful multi-step conversations, rich tool ecosystem (LangChain tools, memory, retrieval)
- **Weaknesses**: Slightly larger dependency footprint than NVIDIA-native toolkits
- **NIM integration**: Use `langchain_nvidia_ai_endpoints.ChatNVIDIA(model="nvidia/nemotron-3-super-120b-a12b")` — defaults to the public NVIDIA AI Endpoint; set `base_url` to a local NIM URL for self-hosted
- **State management**: `MessagesState` with `add_messages` reducer; tool nodes via `ToolNode`

---

## (f) Service Endpoint Confirmation — Guidance

### Default public cloud endpoints

Present the following defaults clearly in step (f):

| Service | Env var | Default value | Notes |
|---|---|---|---|
| ASR server | `ASR_SERVER_URL` | `grpc.nvcf.nvidia.com:443` | NVIDIA cloud; requires `NVIDIA_API_KEY` |
| ASR model | `ASR_MODEL_NAME` | `parakeet-1.1b-en-US-asr-streaming-silero-vad-sortformer` | English only |
| ASR cloud function ID | `ASR_CLOUD_FUNCTION_ID` | `1598d209-5e27-4d3c-8079-4751568b1081` | Required for NVCF routing |
| TTS server | `TTS_SERVER_URL` | `grpc.nvcf.nvidia.com:443` | NVIDIA cloud; requires `NVIDIA_API_KEY` |
| TTS model | `TTS_MODEL_NAME` | `magpie_tts_ensemble-Magpie-Multilingual` | Multilingual ensemble |
| TTS voice | `TTS_VOICE_ID` | `Magpie-Multilingual.EN-US.Aria` | US English, female |
| TTS language | `TTS_LANGUAGE` | `en-US` | BCP-47 language tag |

All seven default to NVIDIA's public cloud and require only `NVIDIA_API_KEY` — no local GPU or self-hosted NIM is needed.

### If the user wants a self-hosted ASR NIM

Ask for:
- The gRPC endpoint of the self-hosted container (e.g., `localhost:50051`)
- The model name running in the container
- Whether it still uses `NVIDIA_API_KEY` or a different credential

Set `ASR_SERVER_URL` and `ASR_MODEL_NAME` to the user's values. Leave `ASR_CLOUD_FUNCTION_ID` empty or omit it — it is only used for NVCF cloud routing.

### If the user wants a self-hosted TTS NIM

Ask for:
- The gRPC endpoint (e.g., `localhost:50052`)
- The model name and voice ID supported by the container
- Language tag if non-English

### What to emit in `.env.example`

Even when the user keeps the public cloud defaults, all seven variables must appear in `.env.example` with the defaults pre-filled. Mark each with a comment explaining what it controls:

```dotenv
# =============================================================================
# NEMOTRON VOICE AGENT — ASR (SPEECH-TO-TEXT)
# =============================================================================

# gRPC endpoint for the ASR service.
# Default: NVIDIA public cloud (no local GPU required).
# To self-host: set to your local NIM gRPC address (e.g., localhost:50051).
ASR_SERVER_URL=grpc.nvcf.nvidia.com:443

# ASR model name. Must match the model deployed at ASR_SERVER_URL.
ASR_MODEL_NAME=parakeet-1.1b-en-US-asr-streaming-silero-vad-sortformer

# NVIDIA Cloud Function ID for cloud ASR routing. Leave blank when self-hosting.
ASR_CLOUD_FUNCTION_ID=1598d209-5e27-4d3c-8079-4751568b1081

# =============================================================================
# NEMOTRON VOICE AGENT — TTS (TEXT-TO-SPEECH)
# =============================================================================

# gRPC endpoint for the TTS service.
# Default: NVIDIA public cloud.
# To self-host: set to your local NIM gRPC address (e.g., localhost:50052).
TTS_SERVER_URL=grpc.nvcf.nvidia.com:443

# TTS model ensemble name. Must match the model deployed at TTS_SERVER_URL.
TTS_MODEL_NAME=magpie_tts_ensemble-Magpie-Multilingual

# Voice identifier. Available voices depend on the TTS model.
TTS_VOICE_ID=Magpie-Multilingual.EN-US.Aria

# BCP-47 language tag for TTS synthesis.
TTS_LANGUAGE=en-US
```

---

## (g) Implementation Plan & Frontend Connection — Templates

### Implementation Plan Template

Use this template when drafting the plan for the user:

```
## Proposed Implementation Plan

### Repository Layout
[Show directory tree]

### Agent Functions
For each function from (b):
- **[Function name]**: Implemented as a [LangGraph node / NeMo tool] named `[tool_name]`.
  - Input: [what the agent receives]
  - Output: [what the agent returns to the voice interface]
  - Data access: [which backend, which table/collection/endpoint]

### Data Layer
- Backend: [SQLite / JSON files / RAG / Tavily / mock]
- Schema: [brief table list or collection description]
- Seed data: [what demo data will be pre-loaded]

### Voice Integration
- The agent exposes an OpenAI-compatible `POST /v1/chat/completions` endpoint on port `$AGENT_PORT` via `agent/server.py`
- The Nemotron Voice Agent sends the full conversation history as an OpenAI messages array on each turn
- The agent returns an OpenAI-compatible response (or SSE stream) with the next assistant message
- The Nemotron Voice Agent is run separately as a sibling directory (`../nemotron-voice-agent`); see docs/voice-integration.md

### Configuration
Required environment variables:
- `NVIDIA_API_KEY` — for NIM model inference
- [Others as needed]
```

### Frontend Connection Patterns

#### LangGraph + Nemotron Voice Agent

The Nemotron Voice Agent is cloned and run independently — not bundled into the output repo. It is always expected as a **sibling directory**:

```
parent-directory/
├── [output-repo]/           ← the generated ambient agent repo
└── nemotron-voice-agent/    ← cloned here: ../nemotron-voice-agent
```

Clone command (goes in both README.md and `.agents/skills/<agent-name>/SKILL.md` of the output repo):
```bash
git clone --recurse-submodules https://github.com/NVIDIA-AI-Blueprints/nemotron-voice-agent ../nemotron-voice-agent
```

**Recommended pattern — OpenAI-compatible FastAPI server** (the Nemotron Voice Agent calls `/v1/chat/completions`):

```python
# agent/server.py
import os
from fastapi import FastAPI, Request

AGENT_PORT = int(os.getenv("AGENT_PORT", "8000"))
app = FastAPI()

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    # body["messages"] contains the full conversation history
    response_text = await run_agent(body["messages"])
    return {"choices": [{"message": {"role": "assistant", "content": response_text}}]}
```

**Environment variables** (all ports must be env-var-driven — never hardcoded):
```dotenv
# Port the agent backend HTTP/WebSocket server listens on
AGENT_PORT=8000

# Model id exposed by /v1/models and requested by the voice agent
AGENT_MODEL_NAME=<agent-name>

# Fixed WebRTC pipeline port and browser UI port
VOICE_AGENT_PORT=7860
VOICE_AGENT_UI_PORT=9000
```

**In the Nemotron Voice Agent's config** (e.g., `../nemotron-voice-agent/config/.env`), set:
```dotenv
NVIDIA_API_KEY=<same key as this repo .env>
NVIDIA_LLM_URL=http://agent-backend:${AGENT_PORT:-8000}/v1  # Docker Compose
# NVIDIA_LLM_URL=http://localhost:${AGENT_PORT:-8000}/v1    # manual local backend
NVIDIA_LLM_MODEL=<same value as AGENT_MODEL_NAME>
TRANSPORT=WEBRTC
```

Document this in `docs/voice-integration.md` of the output repo with the exact file path and key names (verify after cloning the voice agent repo).

#### Session State

Maintain per-session state (conversation history, collected intake fields) in a Python dict keyed by `session_id`. For production, use Redis. For demo, in-memory is fine.

#### Streaming

The Nemotron Voice Agent sends requests with `"stream": true`. Return an SSE stream with `Content-Type: text/event-stream`. For simplicity, emit the complete response as a single `data:` chunk followed by `data: [DONE]` — the voice agent processes it the same way as incremental chunks since TTS renders after the full response is received.

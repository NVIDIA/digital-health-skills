---
name: "riva-tts"
license: "Apache-2.0"
description: "Use when the user wants to deploy, run, or test a TTS (speech-synthesis) Riva NIM — cloud-hosted (build.nvidia.com) or self-hosted Magpie / voice cloning."
metadata:
  author: "Mayank Jain <mayjain@nvidia.com>"
  team: riva
  tags:
    - nvidia
    - riva
    - nim
    - tts
    - text-to-speech
    - magpie
    - voice-synthesis
    - grpc
    - http
    - websocket
    - cloud
    - nvcf
  domain: ml
  version: "1.0.0"
---

# Riva TTS NIM

Riva TTS NIMs ship in two deployment shapes: cloud-hosted (managed by build.nvidia.com, no local GPU) and self-hosted (your own GPU plus Docker). Pick the one matching the user's constraints below.

If model choice isn't settled yet, route to `riva-model-selection` first — selection is out of scope for this skill.

> **Agent note:** During multi-step walkthroughs, announce each step before presenting its content (e.g. "**Step 1/4 — Deploy the Container**"). This keeps the user oriented in the four-step self-hosted flow.

---

## Purpose

Stand up an NVIDIA Riva TTS (text-to-speech) NIM and synthesize speech against it. The skill covers both the build.nvidia.com cloud path and the Docker-based self-hosted path, and walks through offline synthesis, streaming, voice cloning, and Kubernetes (Helm) deployment.

## Workflow

Two routes:
- **Cloud (Option A)** — fastest path for testing or no-GPU environments.
- **Self-hosted (Option B)** — for production deployments where you control the GPU. The self-hosted path runs four sequential steps: deploy the container, verify it's healthy, list available voices, then synthesize.

## Prerequisites

- For self-hosted only: `riva-nim-setup` must be completed first (NVIDIA Container Toolkit installed, `NGC_API_KEY` exported, Docker authenticated to `nvcr.io`).
- For cloud-hosted: `pip install -U nvidia-riva-client` and a valid `NVIDIA_API_KEY` issued at build.nvidia.com.
- If the model choice is still open, route to `riva-model-selection` before continuing.

## Instructions

Pick the deployment route up-front:

- **Cloud (Option A):** install the Riva Python client, export `NVIDIA_API_KEY`, then invoke `talk.py` against `grpc.nvcf.nvidia.com:443` with `--use-ssl` plus the function ID from the model table just below.
- **Self-hosted (Option B):** export `CONTAINER_ID` and `NIM_TAGS_SELECTOR` from the TTS support matrix, then walk Steps 1–4 in order (deploy → verify → list voices → synthesize).


## Option A — Cloud-Hosted Inference (build.nvidia.com)

**Setup:** `pip install -U nvidia-riva-client` + clone https://github.com/nvidia-riva/python-clients and `cd` into it.

**Auth:** Set `NVIDIA_API_KEY` from https://build.nvidia.com (different from `NGC_API_KEY`).

**Server:** `grpc.nvcf.nvidia.com:443` — always pass `--use-ssl`.

| Model | Build Page slug | Function ID |
|-------|----------------|-------------|
| Magpie TTS Multilingual | `nvidia/magpie-tts-multilingual` | `877104f7-e885-42b9-8de8-f6e4c6303969` |

If a function-id no longer works, fetch the current one from `https://build.nvidia.com/<org>/<model>/api`.

**Synthesize speech:**

```bash
python python-clients/scripts/tts/talk.py \
    --server grpc.nvcf.nvidia.com:443 --use-ssl \
    --metadata function-id "877104f7-e885-42b9-8de8-f6e4c6303969" \
    --metadata authorization "Bearer $NVIDIA_API_KEY" \
    --language-code en-US \
    --text "Hello from NVIDIA TTS." \
    --voice "Magpie-Multilingual.EN-US.Aria" \
    --output audio.wav
```
> **Security note:** `$NVIDIA_API_KEY` passed as a command-line argument is
> visible in process listings and shell history. Prefix the command with a space
> (`HISTCONTROL=ignorespace`) or store the key in a file with `chmod 600` and
> reference it at runtime.


**List available voices:** add `--list-voices` (drop `--text`, `--voice`, `--output`).

---

## Option B — Self-Hosted NIM Deployment

Complete `riva-nim-setup` first: NVIDIA Container Toolkit, `NGC_API_KEY` exported, Docker logged in to `nvcr.io`. Driver and VRAM minimums: see https://docs.nvidia.com/nim/speech/latest/reference/support-matrix/tts.html. Latency and throughput benchmarks: https://docs.nvidia.com/nim/speech/latest/reference/performances/tts/performance.html

Not sure which TTS model to pick? See `riva-model-selection`.

## Available Models

Current models, voices, languages, and VRAM requirements: https://docs.nvidia.com/nim/speech/latest/reference/support-matrix/tts.html

Note: Magpie TTS Zeroshot and Flow (voice cloning) are **restricted** — apply for access at developer.nvidia.com/riva-tts-zeroshot-models before pulling.

## Step 1 — Deploy the Container

Set variables for your model, then run:

| Model | `CONTAINER_ID` | `NIM_TAGS_SELECTOR` |
|-------|---------------|---------------------|
| Magpie TTS Multilingual | `magpie-tts-multilingual` | `name=magpie-tts-multilingual` |
| Magpie TTS Zeroshot | `magpie-tts-zeroshot` | `name=magpie-tts-zeroshot` |
| Magpie TTS Flow | `magpie-tts-flow` | `name=magpie-tts-flow` |

For a specific batch size: `NIM_TAGS_SELECTOR="name=magpie-tts-multilingual,batch_size=32"`

```bash
export CONTAINER_ID=<from-table>
export NIM_TAGS_SELECTOR=<from-table>
export LOCAL_NIM_CACHE=~/.cache/nim
mkdir -p $LOCAL_NIM_CACHE && chmod 700 $LOCAL_NIM_CACHE

docker run -it --rm --name=$CONTAINER_ID \
  --runtime=nvidia \
  --gpus '"device=0"' \
  --shm-size=8GB \
  -e NGC_API_KEY \
  -e NIM_TAGS_SELECTOR \
  -e NIM_HTTP_API_PORT=9000 \
  -e NIM_GRPC_API_PORT=50051 \
  -p 9000:9000 \
  -p 50051:50051 \
  -v $LOCAL_NIM_CACHE:/opt/nim/.cache \
  nvcr.io/nim/nvidia/$CONTAINER_ID:latest
```

## Step 2 — Verify Readiness

```bash
curl -X GET http://localhost:9000/v1/health/ready
# Expected: {"status":"ready"}
```

## Step 3 — List Available Voices

Before synthesizing, discover available voices on the running NIM.

**gRPC:**

```bash
python3 python-clients/scripts/tts/talk.py \
  --server 0.0.0.0:50051 \
  --list-voices
```

**HTTP:**

```bash
curl -sS http://localhost:9000/v1/audio/list_voices | python3 -m json.tool
```

Voice names follow the pattern: `Magpie-Multilingual.<LANG>.<VoiceName>` (e.g., `Magpie-Multilingual.EN-US.Aria`).

## Step 4 — Run Speech Synthesis

### Offline Synthesis (Full Audio in One Response)

**gRPC:**

```bash
python3 python-clients/scripts/tts/talk.py \
  --server 0.0.0.0:50051 \
  --language-code en-US \
  --text "Deploy and run speech synthesis with NVIDIA TTS NIM." \
  --voice Magpie-Multilingual.EN-US.Aria \
  --output output.wav
```

**HTTP:**

```bash
curl -sS http://localhost:9000/v1/audio/synthesize --fail-with-body \
  -F language=en-US \
  -F text="Deploy and run speech synthesis with NVIDIA TTS NIM." \
  -F voice=Magpie-Multilingual.EN-US.Aria \
  --output output.wav
```

### Streaming Synthesis (Lower Latency, Audio Chunks)

**gRPC:**

```bash
python3 python-clients/scripts/tts/talk.py \
  --server 0.0.0.0:50051 \
  --language-code en-US \
  --text "Deploy and run speech synthesis with NVIDIA TTS NIM." \
  --voice Magpie-Multilingual.EN-US.Aria \
  --stream \
  --output output.wav
```

**HTTP (returns raw LPCM, not WAV):**

```bash
curl -sS http://localhost:9000/v1/audio/synthesize_online --fail-with-body \
  -F language=en-US \
  -F text="Deploy and run speech synthesis with NVIDIA TTS NIM." \
  -F voice=Magpie-Multilingual.EN-US.Aria \
  -F sample_rate_hz=22050 \
  --output output.raw

# Convert to WAV with sox
sox -b 16 -e signed -c 1 -r 22050 output.raw output.wav
```

### WebSocket (Lowest Latency — Realtime)

```bash
python3 python-clients/scripts/tts/realtime_tts_client.py \
  --server localhost:9000 \
  --language-code en-US \
  --text "Deploy and run speech synthesis with NVIDIA TTS NIM." \
  --voice Magpie-Multilingual.EN-US.Aria \
  --output output.wav
```

### Voice Cloning (Zeroshot / Flow)

Provide a 3–10 second audio prompt of the target voice:

```bash
# Zeroshot (gRPC)
python3 python-clients/scripts/tts/talk.py \
  --server 0.0.0.0:50051 \
  --text "This is my cloned voice." \
  --zero_shot_audio_prompt_file /path/to/voice_sample.wav \
  --zero_shot_quality 20 \
  --output cloned_output.wav

# Flow (requires transcript of the audio prompt)
python3 python-clients/scripts/tts/talk.py \
  --server 0.0.0.0:50051 \
  --text "This is my cloned voice." \
  --zero_shot_audio_prompt_file /path/to/voice_sample.wav \
  --zero_shot_transcript "The text spoken in the audio prompt." \
  --output cloned_output.wav
```

## Helm Deployment (Kubernetes)

```yaml
# custom-values.yaml
image:
  repository: nvcr.io/nim/nvidia/magpie-tts-multilingual
  pullPolicy: IfNotPresent
  tag: latest
nim:
  ngcAPISecret: ngc-api
imagePullSecrets:
  - name: ngc-secret
envVars:
  NIM_TAGS_SELECTOR: name=magpie-tts-multilingual
```

```bash
helm install riva-tts <chart> -f custom-values.yaml
```

Substitute `repository` and `NIM_TAGS_SELECTOR` for other models.

## Key Parameters for talk.py

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--server` | gRPC endpoint | `0.0.0.0:50051` |
| `--text` | Text to synthesize | — |
| `--voice` | Voice name | First available |
| `--language-code` | Language code (e.g., `en-US`) | `en-US` |
| `--output` / `-o` | Output WAV file | `output.wav` |
| `--stream` | Enable streaming | `false` |
| `--sample-rate-hz` | Output sample rate | `44100` |
| `--list-voices` | List voices then exit | — |
| `--zero_shot_audio_prompt_file` | Voice cloning audio prompt | — |
| `--zero_shot_quality` | Cloning quality (1–40) | `20` |

## Examples

Two end-to-end invocations — one per deployment route. Both use the Magpie Multilingual Aria voice.

**Cloud (Option A) — Magpie Aria via build.nvidia.com:**
```bash
python python-clients/scripts/tts/talk.py \
    --server grpc.nvcf.nvidia.com:443 --use-ssl \
    --metadata function-id "877104f7-e885-42b9-8de8-f6e4c6303969" \
    --metadata authorization "Bearer $NVIDIA_API_KEY" \
    --text "Hello from NVIDIA TTS." \
    --voice "Magpie-Multilingual.EN-US.Aria" \
    --output audio.wav
```

**Self-hosted (Option B) — offline synthesis against a local NIM:**
```bash
python3 python-clients/scripts/tts/talk.py \
  --server 0.0.0.0:50051 \
  --text "Deploy speech synthesis with NVIDIA TTS NIM." \
  --voice Magpie-Multilingual.EN-US.Aria \
  --output output.wav
```


## Troubleshooting

- **Synthesized audio > 4 MB** → gRPC response cap. Switch to `--stream`, or fall back to the WebSocket client for long-form output.
- **HTTP streaming output won't open in a media player** → the stream is raw LPCM, not a WAV container. Wrap it with `sox` (see the Streaming Synthesis section above).
- **`403` on container pull for Zeroshot / Flow** → these are gated TTS models. Request access via NGC before re-pulling.
- **Voice not found** → voice names are case-sensitive and dot-separated; pass `Magpie-Multilingual.EN-US.Aria` literally, not `aria` or `Aria`.

## Limitations

- x86_64 architecture only; NVIDIA AI Enterprise license required for self-hosting
- gRPC responses are limited to 4 MB — long synthesis requests must use streaming or be chunked
- HTTP streaming returns raw LPCM audio (not WAV) — requires client-side wrapping
- Zeroshot voice cloning requires a reference audio clip; Flow model additionally requires a transcript
- Restricted-access TTS models require explicit NVIDIA approval before use
- Voice names are case-sensitive


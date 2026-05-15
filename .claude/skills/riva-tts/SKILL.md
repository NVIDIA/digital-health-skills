---
name: "riva-tts"
description: >-
  Use this skill when the user wants to deploy, run, or test a TTS (text-to-speech / speech synthesis) Riva NIM — cloud-hosted (build.nvidia.com) or self-hosted. Trigger phrases: "deploy TTS NIM", "run Riva text-to-speech", "Magpie TTS", "Riva voice synthesis", "list Riva voices", "streaming TTS", "voice cloning Riva", "synthesize speech with Riva", "TTS docker run", "cloud TTS NIM", "grpc.nvcf.nvidia.com TTS".
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

Two modes: **cloud-hosted** (no GPU, uses build.nvidia.com) or **self-hosted** (your own GPU + Docker).

Not sure which TTS model to pick? See `riva-model-selection`.

> **Agent:** When walking the user through a multi-step workflow, announce each step before presenting it: **Step N/M — Step Title** (e.g., "**Step 1/4 — Deploy the Container**").

---

## Purpose

Deploy and run NVIDIA Riva TTS (text-to-speech) NIMs for speech synthesis.
Supports cloud-hosted inference via build.nvidia.com and self-hosted deployment.
Covers offline synthesis, streaming, voice cloning, and Kubernetes Helm
deployment.

## Workflow

Choose **Option A** (cloud) for quick testing without a GPU, or **Option B** (self-hosted) for production. Self-hosted follows a 4-step process: deploy container → verify health → list voices → synthesize speech.

## Prerequisites

- Complete `riva-nim-setup`: NVIDIA Container Toolkit, `NGC_API_KEY` exported, Docker logged in to `nvcr.io`
- Cloud-hosted inference: `pip install -U nvidia-riva-client` and a valid `NVIDIA_API_KEY`
- Not sure which TTS model to use? Run `riva-model-selection` first

## Instructions

For **cloud synthesis**: install `nvidia-riva-client`, set `NVIDIA_API_KEY`, and run `talk.py` against `grpc.nvcf.nvidia.com:443` with `--use-ssl` and the function ID from the table below.

For **self-hosted**: set `CONTAINER_ID` and `NIM_TAGS_SELECTOR` from the TTS support matrix, then follow Steps 1–4 below to deploy the container, verify readiness, list available voices, and synthesize speech.


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

**Cloud synthesis — Aria voice:**
```bash
python python-clients/scripts/tts/talk.py \
    --server grpc.nvcf.nvidia.com:443 --use-ssl \
    --metadata function-id "877104f7-e885-42b9-8de8-f6e4c6303969" \
    --metadata authorization "Bearer $NVIDIA_API_KEY" \
    --text "Hello from NVIDIA TTS." \
    --voice "Magpie-Multilingual.EN-US.Aria" \
    --output audio.wav
```

**Self-hosted offline synthesis:**
```bash
python3 python-clients/scripts/tts/talk.py \
  --server 0.0.0.0:50051 \
  --text "Deploy speech synthesis with NVIDIA TTS NIM." \
  --voice Magpie-Multilingual.EN-US.Aria \
  --output output.wav
```


## Troubleshooting

- **gRPC 4 MB limit** — if synthesized audio exceeds 4 MB, switch to `--stream` or use the WebSocket client.
- **HTTP streaming returns raw LPCM** — not a WAV file; use `sox` to convert.
- **Restricted models** — Magpie TTS Zeroshot and Flow require access approval; the pull will fail with 403 otherwise.
- **Voice name format** — must match exactly, including case: `Magpie-Multilingual.EN-US.Aria`, not `aria` or `Aria`.

## Limitations

- x86_64 architecture only; NVIDIA AI Enterprise license required for self-hosting
- gRPC responses are limited to 4 MB — long synthesis requests must use streaming or be chunked
- HTTP streaming returns raw LPCM audio (not WAV) — requires client-side wrapping
- Zeroshot voice cloning requires a reference audio clip; Flow model additionally requires a transcript
- Restricted-access TTS models require explicit NVIDIA approval before use
- Voice names are case-sensitive

---
name: "riva-asr"
license: "Apache-2.0"
description: "Use when the user wants to deploy, run, or test an ASR (speech-to-text) Riva NIM — cloud-hosted (build.nvidia.com) or self-hosted Parakeet/Canary/Whisper."
metadata:
  author: "Mayank Jain <mayjain@nvidia.com>"
  team: riva
  tags:
    - nvidia
    - riva
    - nim
    - asr
    - speech-to-text
    - parakeet
    - canary
    - whisper
    - grpc
    - http
    - cloud
    - nvcf
  domain: ml
  version: "1.0.0"
---

# Riva ASR NIM

> **Agent:** When walking the user through a multi-step workflow, announce each step before presenting it: **Step N/M — Step Title** (e.g., "**Step 1/4 — Set Model Variables**").

---

## Purpose

Deploy and run NVIDIA Riva ASR (speech-to-text) NIMs. Supports cloud-hosted
inference via build.nvidia.com (no GPU required) and self-hosted deployment on
your own GPU using Docker. Covers streaming and offline transcription, word
boosting, and performance benchmarking.

## Workflow

Choose **Option A** (cloud) for quick testing without a GPU, or **Option B** (self-hosted) for production. Self-hosted follows a 4-step process: set model variables → run container → verify health → run inference.

## Prerequisites

- Complete `riva-nim-setup` before self-hosted deployment: NVIDIA Container Toolkit, `NGC_API_KEY` exported, Docker logged in to `nvcr.io`
- Cloud-hosted inference: `pip install -U nvidia-riva-client` and a valid `NVIDIA_API_KEY`
- Not sure which model to use? Run `riva-model-selection` first

## Instructions

1. **Pick a path**: cloud inference (Option A) or self-hosted NIM (Option B).
2. **For cloud inference (Option A)**: install `nvidia-riva-client`, set `NVIDIA_API_KEY`, pick a function ID, run `transcribe_file.py` (streaming) or `transcribe_file_offline.py` (offline) against `grpc.nvcf.nvidia.com:443` with `--use-ssl`.
3. **For self-hosted (Option B)**: look up `CONTAINER_ID` and `NIM_TAGS_SELECTOR` from the ASR support matrix, mount a model cache dir with `chmod 700`, then follow Steps 1–4 below (set vars, run container, verify readiness, run inference).

## Option A — Cloud-Hosted Inference (build.nvidia.com)

**Setup:** `pip install -U nvidia-riva-client` + clone https://github.com/nvidia-riva/python-clients and `cd` into it.

**Auth:** Set `NVIDIA_API_KEY` from https://build.nvidia.com (different from `NGC_API_KEY`).

**Server:** `grpc.nvcf.nvidia.com:443` — always pass `--use-ssl`.

**Canonical command (streaming models):**

```bash
python python-clients/scripts/asr/transcribe_file.py \
    --server grpc.nvcf.nvidia.com:443 --use-ssl \
    --metadata function-id "<FUNCTION_ID>" \
    --metadata "authorization" "Bearer $NVIDIA_API_KEY" \
    --language-code <LANG_CODE> \
    --input-file /path/to/audio.wav
```

For offline-only models use `transcribe_file_offline.py` instead. For Whisper translation add `--custom-configuration "task:translate"`.

**Word timestamps:** All models except Whisper and Canary support `--word-time-offsets`. Accuracy ranking: CTC > TDT > RNNT.

**Note:** Both cloud and self-hosted scripts use `--input-file`, not `--audio-file`.

### Function IDs

If a function-id no longer works, fetch the current one from `https://build.nvidia.com/<org>/<model>/api`.

| Model | Build Page slug | Function ID | Script | Lang code |
|-------|----------------|-------------|--------|-----------|
| Nemotron ASR Streaming | `nvidia/nemotron-asr-streaming` | `bb0837de-8c7b-481f-9ec8-ef5663e9c1fa` | `transcribe_file.py` | *(omit)* |
| Parakeet 1.1B RNNT Multilingual | `nvidia/parakeet-1_1b-rnnt-multilingual-asr` | `71203149-d3b7-4460-8231-1be2543a1fca` | `transcribe_file.py` | `multi` |
| Parakeet TDT 0.6B v2 | `nvidia/parakeet-tdt-0_6b-v2` | `d3fe9151-442b-4204-a70d-5fcc597fd610` | `transcribe_file_offline.py` | `en-US` |
| Whisper Large v3 | `openai/whisper-large-v3` | `b702f636-f60c-4a3d-a6f4-f3568c13bd7d` | `transcribe_file_offline.py` | `en` / `multi` |
| Parakeet CTC 1.1B English | `nvidia/parakeet-ctc-1_1b-asr` | `1598d209-5e27-4d3c-8079-4751568b1081` | `transcribe_file.py` | `en-US` |
| Parakeet CTC 0.6B Spanish | `nvidia/parakeet-ctc-0_6b-es` | `a9eeee8f-b509-4712-b19d-194361fa5f31` | `transcribe_file.py` | `es-US` |
| Parakeet CTC 0.6B Vietnamese | `nvidia/parakeet-ctc-0_6b-vi` | `f3dff2bb-99f9-403d-a5f1-f574a757deb0` | `transcribe_file.py` | `vi-VN` |
| Parakeet CTC 0.6B Mandarin (Simplified) | `nvidia/parakeet-ctc-0_6b-zh-cn` | `9add5ef7-322e-47e0-ad7a-5653fb8d259b` | `transcribe_file.py` | `zh-CN` |
| Parakeet CTC 0.6B Taiwanese (Traditional) | `nvidia/parakeet-ctc-0_6b-zh-tw` | `8473f56d-51ef-473c-bb26-efd4f5def2bf` | `transcribe_file.py` | `zh-TW` |

---

## Option B — Self-Hosted NIM Deployment

Complete `riva-nim-setup` first: NVIDIA Container Toolkit, `NGC_API_KEY` exported, Docker logged in to `nvcr.io`. Driver and VRAM minimums: see https://docs.nvidia.com/nim/speech/latest/reference/support-matrix/asr.html. Latency and throughput benchmarks: https://docs.nvidia.com/nim/speech/latest/reference/performances/asr/performance.html

## Step 1 — Set Model Variables

Get the current `CONTAINER_ID` and `NIM_TAGS_SELECTOR` values from the ASR support matrix (includes all models, modes, VRAM, and deployment profiles):
https://docs.nvidia.com/nim/speech/latest/reference/support-matrix/asr.html

```bash
export CONTAINER_ID=<container-id-from-support-matrix>
export NIM_TAGS_SELECTOR="<selector-from-support-matrix>"
```

`NIM_TAGS_SELECTOR` pattern: `name=<model-name>,mode=<str|offline|all>[,model_type=<prebuilt|rmir>]`

**Prebuilt vs RMIR:** The NIM auto-detects your GPU on startup. For well-known GPUs (A100, H100, select Blackwell), it pulls a prebuilt model repo — a tarball of TensorRT engines already compiled for that GPU via `riva-build` + `riva-deploy`. For unsupported GPUs, it falls back to RMIR (Riva Model Intermediate Representation), which is a portable format that gets compiled into TensorRT engines on your local GPU at first run (slower startup, same runtime performance). You rarely need to set `model_type` explicitly — omit it and the NIM picks the right one automatically.

## Step 2 — Run the Container

```bash
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

Omit `-v $LOCAL_NIM_CACHE:/opt/nim/.cache` to skip caching (re-downloads model on every run).
> **Security note:** `NGC_API_KEY` passed via `-e NGC_API_KEY` inherits from the shell environment. For production, use Docker secrets or a secrets manager instead of env vars; avoid storing API keys in shell history or plaintext config files.

### RMIR Model (Export + Re-run Pattern)

```bash
export NIM_EXPORT_PATH=~/nim_export
mkdir -p $NIM_EXPORT_PATH && chmod 700 $NIM_EXPORT_PATH
export NIM_TAGS_SELECTOR="name=parakeet-1-1b-ctc-en-us,mode=str,model_type=rmir"

# Step 1: Export
docker run -it --rm --name=$CONTAINER_ID \
  --runtime=nvidia --gpus '"device=0"' --shm-size=8GB \
  -e NGC_API_KEY -e NIM_TAGS_SELECTOR \
  -e NIM_HTTP_API_PORT=9000 -e NIM_GRPC_API_PORT=50051 \
  -p 9000:9000 -p 50051:50051 \
  -v $NIM_EXPORT_PATH:/opt/nim/export \
  -e NIM_EXPORT_PATH=/opt/nim/export \
  nvcr.io/nim/nvidia/$CONTAINER_ID:latest

# Step 2: Run from export
docker run -it --rm --name=$CONTAINER_ID \
  --runtime=nvidia --gpus '"device=0"' --shm-size=8GB \
  -e NGC_API_KEY -e NIM_TAGS_SELECTOR \
  -e NIM_DISABLE_MODEL_DOWNLOAD=true \
  -e NIM_HTTP_API_PORT=9000 -e NIM_GRPC_API_PORT=50051 \
  -p 9000:9000 -p 50051:50051 \
  -v $NIM_EXPORT_PATH:/opt/nim/export \
  -e NIM_EXPORT_PATH=/opt/nim/export \
  nvcr.io/nim/nvidia/$CONTAINER_ID:latest
```

## Step 3 — Verify Readiness

```bash
curl -X GET http://localhost:9000/v1/health/ready
# Expected: {"status":"ready"}
```

## Step 4 — Run Inference

### Streaming ASR (Python — gRPC)

```bash
python3 python-clients/scripts/asr/transcribe_file.py \
  --server 0.0.0.0:50051 \
  --input-file /path/to/audio.wav \
  --language-code en-US
```

With diarization and word timestamps:

```bash
python3 python-clients/scripts/asr/transcribe_file.py \
  --server 0.0.0.0:50051 \
  --input-file /path/to/audio.wav \
  --language-code en-US \
  --speaker-diarization \
  --word-time-offsets
```

For real-time microphone streaming:

```bash
python3 python-clients/scripts/asr/transcribe_mic.py \
  --server 0.0.0.0:50051
```

### Offline Transcription (Python — gRPC)

```bash
python3 python-clients/scripts/asr/transcribe_file_offline.py \
  --server 0.0.0.0:50051 \
  --input-file /path/to/audio.wav \
  --language-code en-US
```

### HTTP API

```bash
curl -X POST http://localhost:9000/v1/audio/transcriptions \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/audio.wav" \
  -F "model=asr"
```

### C++ Client

```bash
# Build (requires Bazel in cpp-clients/)
cd cpp-clients
bazel build //riva/clients/asr:riva_asr_client

# Run
./bazel-bin/riva/clients/asr/riva_asr_client \
  --server=0.0.0.0:50051 \
  --audio-file=/path/to/audio.wav
```

### WebSocket (AudioCodes / Telephony)

The `websocket-bridge` repo provides a Node.js bridge for AudioCodes-compatible telephony integrations:

```bash
cd websocket-bridge
npm install
node src/index.js --riva-server=localhost:50051
```

## Port Reference

| Port | Protocol | Use |
|------|----------|-----|
| 9000 | HTTP | REST API, health check |
| 50051 | gRPC | Python/C++ client inference |

## Examples

**Cloud inference — transcribe a file (Nemotron Streaming):**
```bash
python python-clients/scripts/asr/transcribe_file.py \
    --server grpc.nvcf.nvidia.com:443 --use-ssl \
    --metadata function-id "bb0837de-8c7b-481f-9ec8-ef5663e9c1fa" \
    --metadata authorization "Bearer $NVIDIA_API_KEY" \
    --input-file audio.wav
```

**Self-hosted streaming transcription:**
```bash
python3 python-clients/scripts/asr/transcribe_file.py \
  --server 0.0.0.0:50051 --input-file audio.wav --language-code en-US
```


## Troubleshooting

- **Wrong `NIM_TAGS_SELECTOR`** — if the selector doesn't match any available profile, the container exits. Check the support matrix for exact tag values.
- **GPU device index** — `--gpus '"device=0"'` targets GPU 0. Adjust for multi-GPU hosts.
- **Port 8000 conflict** — avoid `NIM_HTTP_API_PORT=8000`; use 9000 (default).
- **Parakeet TDT and word timestamps** — only available via gRPC with `enable_word_time_offsets=True` in the recognition config.

## Customization

### Word Boosting

Bias the model toward domain-specific words at request time. Pass each word as a separate flag:

```bash
python scripts/asr/transcribe_file.py \
  --server 0.0.0.0:50051 \
  --input-file audio.wav \
  --boosted-lm-words 'AntiBERTa' \
  --boosted-lm-words 'Abloopar' \
  --boosted-lm-score 20
```

Boost score ranges: **CTC**: 20–100 (negative scores discourage words) | **RNNT/TDT**: 0.5–2.0 (single score for all words, no negatives, no OOV).

### Token Boosting (CTC only)

Maps the tokens the model *predicts* to the word you *want*. Use when word boosting alone can't overcome the acoustic model (e.g. multi-syllable OOV terms).

**Step 1 — Get the model tokenizer from the running container:**

```bash
docker exec <container> find /data/models -name "*tokenizer.model" | head -5
docker cp <container>:/data/models/<model-dir>/1/<hash>_tokenizer.model /tmp/tokenizer.model
```

**Step 2 — Generate token mapping with SentencePiece:**

```python
import sentencepiece as spm
s = spm.SentencePieceProcessor(model_file='/tmp/tokenizer.model')

word_asr_predicts = "ablooper"       # what the model currently outputs
word_asr_should_predict = "Abloopar" # what you want

tokens = s.encode(word_asr_predicts, out_type=str)
print(word_asr_should_predict + ':' + '/'.join(tokens))
# e.g. Abloopar:▁a/b/lo/op/er
```

**Step 3 — Pass mapping as boosted word:**

```bash
--boosted-lm-words 'Abloopar:▁a/b/lo/op/er' --boosted-lm-score 80
```

**Important:** Always use the actual model tokenizer from inside the container — test tokenizers generate different token sequences and the mapping will silently fail.

## Performance Benchmarking (Self-Hosted)

Use `riva_streaming_asr_client` — a **pre-built binary available in PATH inside the NIM container**. Do not use the Python script from python-clients; run the binary via `docker exec`.

A sample LibriSpeech wav file is bundled at `/opt/riva/examples/asr_lib/1272-135031-0000.wav` inside the container.

### Streaming Models

Run at increasing concurrency levels (1, 2, 4, 8, …). Set `num_iterations` to 3× `num_parallel_requests` for stable results.

```bash
export N=4  # num parallel streams — sweep: 1, 2, 4, 8, ...

docker exec <container_name> riva_streaming_asr_client \
  --riva_uri=0.0.0.0:50051 \
  --language_code=en-US \
  --audio_file=/opt/riva/examples/asr_lib/1272-135031-0000.wav \
  --chunk_duration_ms=160 \
  --simulate_realtime=true \
  --automatic_punctuation=true \
  --num_parallel_requests=$N \
  --num_iterations=$((3 * N)) \
  --word_time_offsets=false \
  --print_transcripts=false \
  --interim_results=false \
  --output_filename=/tmp/output.json
```

### Offline Models

```bash
export N=4  # num parallel requests — sweep: 1, 2, 4, 8, ...

docker exec <container_name> riva_streaming_asr_client \
  --riva_uri=0.0.0.0:50051 \
  --language_code=en-US \
  --audio_file=/opt/riva/examples/asr_lib/1272-135031-0000.wav \
  --automatic_punctuation=true \
  --num_parallel_requests=$N \
  --num_iterations=$((3 * N)) \
  --word_time_offsets=false \
  --print_transcripts=false \
  --interim_results=false \
  --output_filename=/tmp/output.json
```

Note: Omit `--chunk_duration_ms` and `--simulate_realtime` for offline models — they process the full audio in one shot, not in streaming chunks.

**Key flags:**

| Flag | Description |
|------|-------------|
| `--chunk_duration_ms` | Match your deployed `chunk_size` in ms — streaming models only |
| `--simulate_realtime` | Throttle audio to real-time speed — streaming models only |
| `--num_parallel_requests` | Concurrent streams; sweep 1→2→4→8→… to find throughput peak |
| `--num_iterations` | Total requests; use 3× `num_parallel_requests` for stable results |
| `--print_transcripts=false` | Suppress transcripts for clean benchmark output |

**Output metrics:**

| Metric | Description |
|--------|-------------|
| Median / 90th / 95th / 99th latency | Time from chunk sent to partial transcript received (ms) |
| Throughput (RTFX) | Audio processed per second of wall time; >1.0 = faster than real-time |


## Limitations

- x86_64 architecture only — ARM is not supported
- Self-hosted deployment requires an NVIDIA AI Enterprise license
- Cloud-hosted inference requires an active `NVIDIA_API_KEY` and internet access
- Word/token boosting is advisory — does not guarantee transcription of boosted terms
- TDT models have a silence-based end-of-utterance threshold in streaming mode

## Next Steps

- Customize ASR pipeline (VAD, diarization, language model): see `riva-pipelines`
- Deploy a custom-trained model: see `riva-asr-custom`
- Check system requirements: see `riva-ops`

---
name: "clinical-asr-setup"
description: "Stage 1 of the Clinical ASR Flywheel (self-contained): verify NVIDIA_API_KEY, install Python deps, set up NGC + Docker for the NeMo training container, and round-trip a sentence through Magpie TTS + Parakeet/Nemotron ASR to confirm the NVCF stack is reachable. Hands off to /clinical-asr-build."
version: "1.0.0"
author: "Ben Randoing <brandoing@nvidia.com>"
tags:
  - clinical-asr
  - setup
  - flywheel
  - bootstrap
  - self-contained
tools:
  - Read
  - Write
  - Bash
  - Skill
license: Apache-2.0
compatibility: "Self-contained — requires NVIDIA_API_KEY (from build.nvidia.com) for hosted Magpie TTS + ASR NIMs. Stage 4 (fine-tune) additionally needs an NGC API key (from ngc.nvidia.com), Docker, the NVIDIA Container Toolkit, and a CUDA GPU — those can be set up later when the user reaches /clinical-asr-finetune."
metadata:
  author: "Ben Randoing <brandoing@nvidia.com>"
  team: healthcare-tme
  domain: ai-ml
  stage: 1
  variant: self-contained
  next_skill: clinical-asr-build
---

# Clinical ASR Flywheel — Stage 1 (Setup)

You are the **entry point** to the self-contained Clinical ASR Flywheel. Confirm the user's environment is ready — `NVIDIA_API_KEY`, Python deps, NGC + Docker (for Stage 4), GPU access — then round-trip one sentence through Magpie TTS → Parakeet/Nemotron ASR to prove the whole NVCF stack is reachable. Hand off to `/clinical-asr-build`.

The flywheel measures and closes the gap between general-purpose ASR and the clinical terms a clinician actually says. The headline metric across all four stages is **KER (keyword error rate)** on flagged entities — drugs, procedures, anatomy, conditions, labs, roles. Aggregate WER hides what matters clinically.

## Purpose

Bootstrap a clean machine into a working Clinical ASR Flywheel cycle. This skill **does not depend on any other skill** — it inlines the minimum-viable recipes for NGC/Docker auth, NVIDIA Container Toolkit verification, and a Magpie+ASR round-trip self-test.

## When to use this skill

Activate on user phrases like:

- "Set up the Clinical ASR Flywheel"
- "Initialize the clinical-asr eval"
- "I want to evaluate ASR on clinical terminology — where do I start?"
- "Bootstrap my environment for the flywheel"
- "What do I need installed before I run the flywheel?"
- "Confirm Magpie + Parakeet are reachable"

Do **not** activate when:

- The user already has a manifest and wants to score it → `/clinical-asr-eval`
- The user already has the env set up and wants to curate terms → `/clinical-asr-build`
- The user is debugging Docker / NGC / Container Toolkit issues unrelated to this flywheel — those are general NVIDIA infra questions, not flywheel questions.

## Prerequisites (all stages)

| Requirement | Why | When you need it |
|---|---|---|
| `NVIDIA_API_KEY` (`nvapi-…`) from <https://build.nvidia.com> | Hosted Magpie TTS + Parakeet/Nemotron ASR via NVCF | Stage 1 onwards |
| Python ≥ 3.10 | Manifest I/O, scoring, recipe glue | Stage 1 onwards |
| `nvidia-riva-client`, `pandas`, `soundfile`, `numpy` | Riva gRPC client + manifest I/O + audio handling | Stage 1 onwards |
| `NGC_API_KEY` (`nvapi-…`) from <https://ngc.nvidia.com> | Pull the NeMo training container | Stage 4 only — defer if not training |
| Docker ≥ 20.x | Run the NeMo training container | Stage 4 only |
| NVIDIA Container Toolkit | GPU passthrough into the container | Stage 4 only |
| CUDA GPU (24 GB VRAM comfortable; 16 GB workable) | NeMo SFT | Stage 4 only — Brev L40S works |

The `NVIDIA_API_KEY` (build.nvidia.com) and the `NGC_API_KEY` (ngc.nvidia.com) are **different keys** issued by different portals. Hosted inference uses the first; container pulls use the second.

## Workflow

### 1a. Verify `NVIDIA_API_KEY` (length-only — never echo the value)

```bash
# Export NVIDIA_API_KEY in your shell — never echo or commit the value
export NVIDIA_API_KEY=nvapi-...     # from https://build.nvidia.com

# Length-only check; the key value never appears in any log
test -n "$NVIDIA_API_KEY" && echo "NVIDIA_API_KEY len=${#NVIDIA_API_KEY}"
```

A length of ~70 is normal. If the output is empty or shows `len=0`, the user must paste a key from <https://build.nvidia.com>. Do **not** print the key, even truncated. To persist across shell sessions, add the `export` line to your shell rc (`~/.bashrc`, `~/.zshrc`) — or use a per-directory tool like `direnv`.

### 1b. Install Python dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install nvidia-riva-client pandas soundfile numpy
# optional, for reference WER/CER scoring
pip install jiwer
```

`nvidia-riva-client` is the official Python client used by both TTS and ASR recipes in this skill family. It ships with `riva.client.Auth`, `SpeechSynthesisService`, and `ASRService` — everything the flywheel needs for hosted NVCF calls.

### 1c. NGC + Docker auth (Stage 4 prerequisite — defer if not training)

The NeMo training container lives at `nvcr.io/nvidia/nemo:25.11.01`. To pull it:

```bash
# Get an NGC API key at https://ngc.nvidia.com (Setup → Generate API Key)
export NGC_API_KEY=nvapi-...

# Authenticate Docker against nvcr.io
echo "$NGC_API_KEY" | docker login nvcr.io -u '$oauthtoken' --password-stdin

# Pull (this takes 10-20 min, ~12 GB)
docker pull nvcr.io/nvidia/nemo:25.11.01
```

The literal username `$oauthtoken` is required — that's how NGC's Docker registry recognizes the API-key auth mode. Single-quoted in shell so the shell doesn't try to expand it.

### 1d. NVIDIA Container Toolkit (Stage 4 prerequisite — defer if not training)

Verify (after install):

```bash
# Host GPU visibility
nvidia-smi

# GPU visible inside a container
docker run --rm --gpus all nvcr.io/nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
```

If `nvidia-smi` works on the host but the `docker run` form fails, the Container Toolkit isn't installed or the Docker daemon isn't configured to use it. Install steps are OS-specific — see NVIDIA's published guide at <https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html>. Brev instances ship with this pre-configured.

### 1e. Round-trip self-test — Magpie TTS → Parakeet/Nemotron ASR

This is the load-bearing check. If this script runs end-to-end, your whole flywheel stack works.

```python
# selftest.py
import io, os, sys, wave
import numpy as np
import riva.client

API_KEY = os.getenv("NVIDIA_API_KEY")
if not API_KEY:
    sys.exit("Set NVIDIA_API_KEY in your shell first (see step 1a)")
SENTENCE = "The patient was prescribed cefazolin one gram every eight hours."

# ---- TTS: Magpie multilingual on NVCF ----
tts_auth = riva.client.Auth(
    uri="grpc.nvcf.nvidia.com:443", use_ssl=True,
    metadata_args=[
        ["function-id", "877104f7-e885-42b9-8de8-f6e4c6303969"],
        ["authorization", f"Bearer {API_KEY}"],
    ],
)
tts = riva.client.SpeechSynthesisService(tts_auth)
resp = tts.synthesize(
    text=f"<speak>{SENTENCE}</speak>",
    voice_name="Magpie-Multilingual.EN-US.Mia",
    language_code="en-US",
    encoding=riva.client.AudioEncoding.LINEAR_PCM,
    sample_rate_hz=44100,
)
pcm_44k = resp.audio
print(f"TTS OK: {len(pcm_44k)} bytes of LINEAR_PCM @ 44.1 kHz")

# ---- Resample 44.1 kHz → 16 kHz mono for ASR ----
arr_44 = np.frombuffer(pcm_44k, dtype=np.int16)
ratio = 16000 / 44100
idx = (np.arange(int(len(arr_44) * ratio)) / ratio).astype(int)
arr_16 = arr_44[np.clip(idx, 0, len(arr_44) - 1)].tobytes()

# ---- ASR: Nemotron Speech Streaming on NVCF ----
asr_auth = riva.client.Auth(
    uri="grpc.nvcf.nvidia.com:443", use_ssl=True,
    metadata_args=[
        ["function-id", "bb0837de-8c7b-481f-9ec8-ef5663e9c1fa"],
        ["authorization", f"Bearer {API_KEY}"],
    ],
)
asr = riva.client.ASRService(asr_auth)
cfg = riva.client.RecognitionConfig(
    encoding=riva.client.AudioEncoding.LINEAR_PCM,
    sample_rate_hertz=16000, language_code="en-US",
    max_alternatives=1, audio_channel_count=1,
    enable_automatic_punctuation=True,
)
streaming_cfg = riva.client.StreamingRecognitionConfig(
    config=cfg, interim_results=False,
)
parts = []
for resp in asr.streaming_response_generator(
    audio_chunks=iter([arr_16]), streaming_config=streaming_cfg,
):
    for r in resp.results:
        if r.is_final and r.alternatives:
            parts.append(r.alternatives[0].transcript)
hyp = " ".join(parts).strip()
print(f"REF: {SENTENCE!r}")
print(f"HYP: {hyp!r}")
```

Run with `python3 selftest.py`. Within ~10 seconds you should see the reference sentence and a close transcript. If `cefazolin` is mis-transcribed in this self-test — that is *exactly the failure mode this flywheel is built to measure and fix*. Keep going.

If the script raises:
- `grpc.RpcError: UNAUTHENTICATED` → `NVIDIA_API_KEY` is wrong, expired, or scoped to a different account.
- `grpc.RpcError: Unavailable model` from the ASR call → you accidentally called `offline_recognize()` instead of `streaming_response_generator()`. The hosted Nemotron Speech NVCF function is streaming-only.
- `ImportError: riva.client` → `pip install nvidia-riva-client`.

## Example scenarios

**Scenario A — first-time setup, fresh shell.** User: *"I want to start the Clinical ASR Flywheel."* → Run 1a (env-var check), 1b (Python deps), 1e (round-trip self-test). Skip 1c/1d unless the user mentions Stage 4 immediately. On all-green, advise `/clinical-asr-build` as the next stop and mention KER framing so the user arrives at Stage 2 with the right metric in mind.

**Scenario B — user planning to fine-tune.** User: *"I want to set up the flywheel including training."* → Run 1a–1e. Confirm `nvidia-smi` shows a CUDA GPU. Confirm `docker pull nvcr.io/nvidia/nemo:25.11.01` succeeds. The full container is ~12 GB; warn about the download size before pulling.

**Scenario C — Brev box, headless setup.** User: *"I'm on a Brev L40S instance."* → 1d is already done (Brev images ship with the Container Toolkit). Run 1a, 1b, 1c, 1e. The `docker login` step is the only manual touch.

## Artifacts produced

- `NVIDIA_API_KEY` exported in the user's shell (and optionally `NGC_API_KEY` for Stage 4)
- An activated virtualenv with `nvidia-riva-client`, `pandas`, `soundfile`, `numpy`
- *(if Stage 4 is in scope)* `nvcr.io/nvidia/nemo:25.11.01` pulled locally
- *(if Stage 4 is in scope)* Verified GPU-in-container access
- A successful round-trip from `selftest.py` proving the NVCF stack is reachable

## Troubleshooting

- **Length check shows nothing or `len=0`** → `NVIDIA_API_KEY` isn't exported in this shell. Run `export NVIDIA_API_KEY=nvapi-...` and re-check.
- **Variable is set in one shell but not another** → exports don't persist across sessions. Add the `export` line to your shell rc (`~/.bashrc`, `~/.zshrc`), or use a per-directory loader like `direnv`.
- **`docker login nvcr.io` fails with `denied`** → the literal username must be `$oauthtoken` (with the dollar sign), single-quoted so shell doesn't try to expand it. The password is the NGC key, *not* the build.nvidia.com key.
- **`docker pull nvcr.io/nvidia/nemo:25.11.01` is slow or stalls** → the container is ~12 GB. On slow networks, retry with `docker pull --quiet` and let it finish overnight if needed.
- **`docker run --gpus all` fails with `unknown flag: --gpus`** → the NVIDIA Container Toolkit isn't installed *or* Docker hasn't picked it up. Restart the Docker daemon after install.
- **Round-trip self-test hangs at the TTS step** → likely `NVIDIA_API_KEY` is missing from the shell that ran `python3`. Confirm with `echo $NVIDIA_API_KEY | wc -c` (length-only, no value leak).
- **Round-trip self-test fails at the ASR step with `Unavailable model`** → the hosted ASR NVCF function is streaming-only. The recipe in 1e uses `streaming_response_generator()`; do not switch to `offline_recognize()`.
- **`grpc.RpcError: RESOURCE_EXHAUSTED`** → hosted-NIM rate limit. Sleep ~10 s and re-run. The build skill's full Cartesian generation handles this with exponential backoff.

## Limitations

- **Setup only verifies the environment.** It does not validate that the user's specialty / term list / pronunciation overrides make sense — that's the job of `/clinical-asr-build`.
- **English-only by default.** Magpie's en-US phoneme inventory drives Stage 2 IPA validation. Other locales require a different upstream phoneme set + override CSV format.
- **Hosted-first paths assumed.** Self-hosted Magpie NIM and Parakeet/Riva NIM also work — they replace the NVCF endpoint in 1e — but require their own deploy setup.
- **Stage 4 (fine-tune) prerequisites are deferred.** If the user reaches `/clinical-asr-finetune` without the NeMo container pulled, that skill will ask them back to 1c/1d. That's fine — most users won't reach Stage 4.

## Companion software

The runnable scripts that implement the whole flywheel live in the **`voice-eval-flywheel`** repo. This skill family is **self-contained** — every recipe needed to run the flywheel is inlined in the four stage skills. The repo gives you cycle numbering, leaderboard rendering, and pre-built `pronunciation_overrides.csv` but is not required.

## Next steps

- **Forward:** `/clinical-asr-build` — specialty interview, term curation, IPA tagging, NeMo manifest synthesis.
- **Skip ahead** (only if you already have a NeMo-format manifest with `term` / `entity_category` / `ipa_source` fields): `/clinical-asr-eval`.

## References

- [`references/external-services.md`](references/external-services.md) — third-party services the flywheel talks to (NVCF function IDs, container images, key portals), version pinning, ownership boundaries

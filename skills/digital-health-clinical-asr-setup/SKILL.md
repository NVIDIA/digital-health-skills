---
name: "digital-health-clinical-asr-setup"
description: "Stage 1 of Clinical ASR Flywheel. Use when bootstrapping a cycle: NVCF+MW disclosure, NVIDIA_API_KEY check, deps install, TTS+ASR smoke test."
version: "1.1.0"
author: "Ben Randoing <brandoing@nvidia.com>"
tags:
  - clinical-asr
  - setup
  - flywheel
  - bootstrap
tools:
  - Read
  - Write
  - Bash
  - Skill
license: Apache-2.0
compatibility: "NVIDIA_API_KEY (required) for hosted Magpie TTS + Parakeet/Nemotron ASR via NVCF. DICTIONARY_API_KEY (optional) for Merriam-Webster pronunciation lookup. NGC_API_KEY (optional) for Stage 4 fine-tune. Python 3.10+."
metadata:
  author: "Ben Randoing <brandoing@nvidia.com>"
  tags:
    - clinical-asr
    - flywheel
    - setup
    - bootstrap
  team: healthcare-tme
  domain: ai-ml
  stage: 1
  next_skill: digital-health-clinical-asr-build
---

<!--
SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
SPDX-License-Identifier: Apache-2.0
-->

# Clinical ASR Flywheel — Stage 1 (Setup)

> **⚠ Agent: read this entire SKILL.md before answering.** The data-disclosure block, the inlined smoke-test recipe, the upstream-skill ownership matrix, and the explicit hand-off to `/digital-health-clinical-asr-build` are all load-bearing. Do not skim or rely on prior knowledge of Riva / NVCF — the function IDs, env-var conventions, and the smoke-test gate live below.

> **Agent: this file is self-contained.** Every command, env-var, function-id, and recipe needed for Stage 1 lives below. **Do not** run `find`, `ls`, `rg`, `grep`, or any other file-discovery command to "verify" the structure — there is no `install.sh`, no `setup.py`, no other config to find. Read this file top-to-bottom and execute the three numbered steps. If a fact isn't here, route to the named sibling skill rather than searching the repo.

You are the **entry point** to the Clinical ASR Flywheel. Confirm the user's environment is ready — `NVIDIA_API_KEY`, Python deps — then round-trip a single sentence through Magpie TTS + Parakeet/Nemotron ASR to prove the hosted stack is reachable. On success, hand off to `/digital-health-clinical-asr-build`.

The flywheel measures and closes the gap between general-purpose ASR and the clinical terms a clinician actually says. The headline metric across all four stages is **KER (keyword error rate)** on flagged entities — drugs, procedures, anatomy, conditions, labs, roles. Aggregate WER hides what matters clinically.

**No `install.sh`, no `setup.py`, no entry-point script ships with this skill.** Stage 1 is the three inlined steps below (1a key length-check → 1b `pip install` → 1c TTS→ASR smoke test). Everything beyond Stage 1 is composed from sibling skills (`/data-designer`, `/riva-tts`, the inlined Stage 3 ASR recipe, `/riva-asr-custom`). When a user asks "what script do I run to install everything?", surface this fact from this paragraph — do not go searching the repo for an installer.

## Data leaves your environment — disclose this to the user before proceeding

This flywheel sends data to two external services. **Surface this to the user up front** so they can confirm it's acceptable under their organization's data-governance policy before any clinical term list, audio, or text leaves the local machine. **Quote the table below verbatim — do not paraphrase the service names or what gets sent. The literal phrasing is the disclosure; a summary is not.**

| Service | What gets sent | When | Hosted by |
|---|---|---|---|
| **NVIDIA NVCF** (`grpc.nvcf.nvidia.com`) | The clinical sentences you synthesize (text), and the WAV files you transcribe (audio) | Every Stage 2 TTS call and every Stage 3 ASR call | NVIDIA, governed by build.nvidia.com terms |
| **Merriam-Webster** (`dictionaryapi.com` JSON API **or** the public `merriam-webster.com` HTML site) | Individual clinical terms (drug names, anatomy, procedures), one HTTP request per term | Stage 2 IPA tagging — see "Two MW paths" below for which endpoint applies | Merriam-Webster, governed by their API or site terms |

Both endpoints carry **non-PHI synthetic data** by design — the flywheel generates sentences and audio from a term list the user curates, not from real patient encounters. **Do not pass real patient transcripts, real ASR audio, or any PHI through these skills.** If the user's term list itself is sensitive (proprietary drug-codename list, unreleased product names), they should review their organization's external-API policy before continuing. Both APIs can be skipped:

- **No MW at all**: leave `DICTIONARY_API_KEY` unset and don't run a scraper. Stage 2 falls through to Magpie G2P; the pipeline still works with reduced coverage on long-tail clinical terms.
- **No NVCF**: this flywheel cannot run without it — Magpie TTS + Parakeet/Nemotron ASR are the workload. If NVCF is off-limits, this skill family is the wrong tool; use a self-hosted ASR/TTS pipeline instead.

A version of this notice belongs in the workspace `README.md` your user maintains — surface it on first invocation if you don't see it already there.

## Purpose

Bootstrap a clean machine into a working Clinical ASR Flywheel cycle. Confirm `NVIDIA_API_KEY` is present, the Python interpreter and required libraries are available, and the hosted NVCF stack responds. Tell the user which skill to run next.

This skill family is **fully self-contained**. Every TTS, ASR, IPA-tagging, and scoring recipe is inlined inside the four `digital-health-clinical-asr-*` skills — you do not need to install any other agent skill to run the flywheel end-to-end.

The skill assumes the user owns the working directory and chooses their layout. It does not impose `data/eval_sets/cycle<N>/` or any other path convention.

## When to use this skill

Activate on user phrases like:

- "Set up the Clinical ASR Flywheel"
- "Initialize the clinical-asr eval"
- "I want to evaluate ASR on clinical terminology — where do I start?"
- "Bootstrap my environment for the flywheel"
- "What do I need installed before I run the flywheel?"

Do **not** activate when:

- The user already has a manifest and wants to score it → `/digital-health-clinical-asr-eval`
- The user already has the env set up and wants to curate terms → `/digital-health-clinical-asr-build`
- The user is asking about Stage 4 fine-tune NGC/Docker setup specifically → that's covered inside `/digital-health-clinical-asr-finetune`

## Prerequisites

| Requirement | Required? | Why | How |
|---|---|---|---|
| `NVIDIA_API_KEY` (`nvapi-…`) | **Required** | Hosted Magpie TTS + Parakeet/Nemotron ASR via NVCF | Issue at <https://build.nvidia.com>; `export NVIDIA_API_KEY=...` in shell |
| Python ≥ 3.10 | **Required** | NeMo client, scoring, manifest tools | `python3 --version` |
| `nvidia-riva-client`, `pandas`, `soundfile`, `requests` | **Required** | TTS + ASR clients, manifest I/O, MW lookup | `pip install nvidia-riva-client pandas soundfile requests` |
| `DICTIONARY_API_KEY` | Optional | Merriam-Webster Medical Dictionary lookup via the JSON API (Path A in the build skill — recommended) | Free key at <https://dictionaryapi.com>. Path B (HTML scrape of `merriam-webster.com`, no key, brittle) is also documented in the build skill if you can't get a key. Without either path, Stage 2 falls through to Magpie G2P with weaker long-tail coverage. |
| `jiwer` | Optional | Reference WER/CER against the inlined Levenshtein implementation | `pip install jiwer` — the eval skill includes a pure-Python fallback |
| (Stage 4 only) `NGC_API_KEY` + CUDA host + NeMo container | Optional, deferred | Fine-tune workload | Set up inside `/digital-health-clinical-asr-finetune`; defer until the eval shows KER > 0.3 |

## Instructions

**Scope.** This skill performs **read-only environment checks**: confirming a key is exported (length-only), the Python version, that libraries import, and that the hosted NVCF stack responds to a single smoke-test round-trip. It does **not** install system packages, modify shell rc files, write to disk outside an explicit `.venv/`, or attempt to authenticate with the real key value. Validate; never mutate without explicit user direction.

### 1a. Verify `NVIDIA_API_KEY` (length-only — never echo the value)

```bash
# Export NVIDIA_API_KEY in your shell — never echo or commit the value
export NVIDIA_API_KEY=nvapi-...     # from https://build.nvidia.com

# Length-only check; the key value never appears in any log
test -n "$NVIDIA_API_KEY" && echo "NVIDIA_API_KEY len=${#NVIDIA_API_KEY}"
```

A length of 70+ is normal. If the output is empty or shows `len=0`, the user must paste a key from <https://build.nvidia.com>. Do **not** print the key, even truncated. To persist across shell sessions, add the `export` line to your shell rc (`~/.bashrc`, `~/.zshrc`) — or use a per-directory tool like `direnv`.

### 1b. Install Python dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install nvidia-riva-client pandas soundfile requests
# optional
pip install jiwer
```

For Stage 4 (fine-tune) only: `nemo-toolkit` and Docker + NVIDIA Container Toolkit are also required. Defer those to `/digital-health-clinical-asr-finetune` — there is no point installing them up front if the user may never reach Stage 4.

### 1c. Smoke-test the hosted NVCF stack

**`NVIDIA_API_KEY` handling — load-bearing, do not deviate:**

- The agent harness reads `$NVIDIA_API_KEY` from the shell and passes it as an **explicit function argument** to `smoke_test(api_key=…)`.
- Auditors can grep the recipe for every wire crossing — every `api_key` use is visible in `auth_for(...)`.
- Do **not** `echo`, `print`, or log the key value (including truncated). Length-only checks are fine (see §1a).
- Do **not** let the recipe read `os.environ["NVIDIA_API_KEY"]` itself — the explicit-argument pattern is the auditability guarantee.
- Do **not** commit the key to any file, including `.env` examples or notebook outputs.

Verify the `NVIDIA_API_KEY` actually works against Magpie TTS and Parakeet/Nemotron ASR before advancing. The four skills inline every recipe needed; this round-trip just confirms the API key + network path are real.

The agent harness loads the `NVIDIA_API_KEY` shell variable and passes it as an explicit function argument to the helpers below. The recipe code itself does not read environment variables — auditors can see exactly which API keys cross the wire.

```python
import wave, tempfile
import riva.client

NVCF_HOST = "grpc.nvcf.nvidia.com:443"
MAGPIE_FUNCTION_ID    = "877104f7-e885-42b9-8de8-f6e4c6303969"   # Magpie TTS
PARAKEET_FUNCTION_ID  = "d3fe9151-442b-4204-a70d-5fcc597fd610"   # Parakeet TDT 0.6B v2 (offline ASR)

def auth_for(function_id: str, api_key: str) -> riva.client.Auth:
    return riva.client.Auth(
        use_ssl=True, uri=NVCF_HOST,
        metadata_args=[
            ["function-id", function_id],
            ["authorization", f"Bearer {api_key}"],
        ],
    )

def smoke_test(api_key: str) -> str:
    """Caller passes api_key (the harness reads $NVIDIA_API_KEY at the shell;
    this code never touches the environment). Returns the ASR transcript."""

    # 1. TTS: "The patient was prescribed cefazolin."
    tts = riva.client.SpeechSynthesisService(auth_for(MAGPIE_FUNCTION_ID, api_key))
    pcm = b"".join(c.audio for c in tts.synthesize_online(
        text="The patient was prescribed cefazolin.",
        voice_name="Magpie-Multilingual.EN-US.Mia",
        language_code="en-US", sample_rate_hz=16000,
    ))
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        with wave.open(f, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(pcm)
        wav_path = f.name

    # 2. ASR: transcribe the WAV we just synthesized.
    asr = riva.client.ASRService(auth_for(PARAKEET_FUNCTION_ID, api_key))
    with open(wav_path, "rb") as f:
        audio_bytes = f.read()
    config = riva.client.RecognitionConfig(
        encoding=riva.client.AudioEncoding.LINEAR_PCM,
        sample_rate_hertz=16000, language_code="en-US",
        max_alternatives=1, enable_automatic_punctuation=True,
    )
    response = asr.offline_recognize(audio_bytes, config)
    transcript = response.results[0].alternatives[0].transcript if response.results else ""
    print(f"TTS:  The patient was prescribed cefazolin.")
    print(f"ASR:  {transcript}")
    return transcript

# Invoke from the agent (api_key sourced by the harness, not by this code):
# smoke_test(api_key="<NVIDIA_API_KEY value>")
```

**Run the smoke test — don't defer it.** This is the gate that proves Stages 2–4 can reach the hosted stack with the user's current key. "I can run it later" is not an acceptable completion of Stage 1; either invoke `smoke_test(api_key=…)` now or, if the user has explicitly opted out, log the deferral in your closing summary so they know what they're missing.

If the transcript matches the input within ~1 token, the hosted stack is reachable and the user can advance to Stage 2. If either call fails:

- `401 Unauthorized` / `PERMISSION_DENIED` → `NVIDIA_API_KEY` is wrong, expired, or not exported in this shell. Re-export and re-test.
- `404` / `INVALID_ARGUMENT: function not found` → the function ID is stale. Look up the current ID at <https://build.nvidia.com> and update the constant above.
- `RESOURCE_EXHAUSTED` → NVCF rate limit. Retry after 30 seconds; this is normal under load.
- Network/TLS errors → corporate proxy or DNS issue. Test `curl https://build.nvidia.com` first.

### 1d. (Optional) Verify Merriam-Webster lookup

Two paths produce a `merriam-webster`-tagged manifest row in Stage 2. Pick one (or neither — Magpie G2P fall-through is a valid posture):

- **Path A — JSON API + key.** Recommended for standalone use of this skill. Check the key is set:

  ```bash
  test -n "$DICTIONARY_API_KEY" && echo "DICTIONARY_API_KEY len=${#DICTIONARY_API_KEY}" \
    || echo "DICTIONARY_API_KEY not set — Path A is off"
  ```

  Free key issues instantly at <https://dictionaryapi.com>.

- **Path B — HTML scraping.** No API key needed; reachability is the only prerequisite. Brittle to MW site HTML changes; recipe inlined in the build skill's `references/pronunciation-pipeline.md`.

  ```bash
  curl -fsS -o /dev/null -w "merriam-webster.com reachable, HTTP %{http_code}\n" \
    https://www.merriam-webster.com/medical/cefazolin
  ```

  If you don't want to maintain a scraper, use Path A instead.

Remember the data-disclosure note at the top: under either path, each clinical term in your seed list goes out as an HTTP request to a Merriam-Webster endpoint.

## Examples

**Scenario A — first-time setup, fresh shell.** User: *"I want to start the flywheel."* → Surface the data-disclosure block at the top. Walk through 1a (key length check), 1b (venv + pip install), 1c (round-trip smoke test). On all-green, advise `/digital-health-clinical-asr-build` as the next stop and mention the headline KER framing so the user arrives at Stage 2 with the right metric in mind.

**Scenario B — returning user, partial env.** User: *"I already have the env, just confirm I'm good to go."* → Skip 1b. Run 1a and 1c only. If the round-trip succeeds, advance.

## Artifacts produced

- `NVIDIA_API_KEY` exported in the user's shell
- An activated virtualenv with `nvidia-riva-client`, `pandas`, `soundfile`, `requests`
- A confirmed TTS→ASR round-trip on a clinical sentence (proof the hosted stack works)

No manifest, audio, or model artifact is produced at this stage — those come at Stages 2–4.

## Troubleshooting

- **Length check shows nothing or `len=0`** → `NVIDIA_API_KEY` isn't exported in this shell. Run `export NVIDIA_API_KEY=nvapi-...` and re-check.
- **Variable is set in one shell but not another** → exports don't persist across sessions. Add the `export` line to your shell rc (`~/.bashrc`, `~/.zshrc`), or use a per-directory loader like `direnv`.
- **`401 Unauthorized` on the smoke test** → key value is wrong or expired. Re-issue at <https://build.nvidia.com>.
- **`grpc.RpcError: function not found`** → the inlined function IDs need updating against the current NVCF catalog. Check <https://build.nvidia.com> and edit the constants in 1c. The eval skill (`/digital-health-clinical-asr-eval`) provides a catalog of current function IDs in its Step 3a "Other catalog options" list.
- **`StatusCode.INVALID_ARGUMENT` with `CUDA error: an illegal memory access was encountered`** → NVCF-side backend fault on this specific function ID (Triton/PyTorch on NVCF, not your env). Either retry later or temporarily point at a different offline ASR NIM — Whisper Large v3 function-id `b702f636-f60c-4a3d-a6f4-f3568c13bd7d` is the closest drop-in (also offline; pass `language_code="en"` instead of `"en-US"`). For routine eval cycles, prefer to wait for the Parakeet backend to recover so Stage 3 baseline and Stage 4 SFT base stay aligned.
- **`TypeError: Auth.__init__() got an unexpected keyword argument 'ssl_cert'`** → you're on `nvidia-riva-client >= 2.x` where the kwarg was renamed to `ssl_root_cert` (and is no longer needed for hosted NVCF). Drop the `ssl_cert=None,` line from your local copy of the recipe.
- **`ModuleNotFoundError: riva.client`** → step 1b was skipped or the venv isn't activated. `source .venv/bin/activate && pip install nvidia-riva-client`.

## Limitations

- **Setup only verifies the environment.** It does not validate that the user's specialty / term list / pronunciation overrides make sense — that's the job of `/digital-health-clinical-asr-build`.
- **English-only by default.** Magpie's en-US phoneme inventory drives Stage 2 IPA validation. Other locales require a different upstream phoneme set.
- **Hosted-only paths assumed.** Self-hosted NIMs work but require additional setup (covered inside `/digital-health-clinical-asr-finetune` Stage 4d).
- **Non-PHI data only.** This skill family is designed for synthetic clinical-vocabulary benchmarks generated from a term list. Do not pass real patient transcripts or audio through any stage.

## Next steps

**Required hand-off on success:** end your Stage 1 response by **explicitly recommending `/digital-health-clinical-asr-build` as the next skill** the user should invoke, and **name KER (keyword error rate) as the headline metric** they'll see at Stage 3. These two pointers are non-optional — they orient the user inside the four-stage flywheel.

- **Forward:** `/digital-health-clinical-asr-build` — specialty interview, term curation, IPA tagging, NeMo manifest synthesis.
- **Skip ahead** (only if the user already has a NeMo-format manifest with `term` / `entity_category` / `ipa_source` fields): `/digital-health-clinical-asr-eval`.

## References

- [`references/dependency-ownership.md`](references/dependency-ownership.md) — boundary between skill-owned and companion-owned responsibilities.


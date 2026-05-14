---
name: "clinical-asr-eval"
description: "Stage 3 of the Clinical ASR Flywheel (self-contained): transcribe a NeMo-format manifest via the inlined Parakeet/Nemotron ASR NVCF recipe, score WER/CER/KER/SER, produce a five-section leaderboard, and route the user via the post-eval decision tree. Preceded by /clinical-asr-build, followed by /clinical-asr-finetune or back to /clinical-asr-build."
version: "1.0.0"
author: "Ben Randoing <brandoing@nvidia.com>"
tags:
  - clinical-asr
  - eval
  - ker
  - leaderboard
  - flywheel
  - self-contained
tools:
  - Read
  - Write
  - Bash
  - Skill
license: Apache-2.0
compatibility: "Self-contained — requires only NVIDIA_API_KEY (build.nvidia.com), Python 3.10+, and nvidia-riva-client. The ASR recipe is inlined; no upstream skill dependency. A NeMo-format manifest produced by /clinical-asr-build (or an externally-provided manifest carrying the clinical-extension fields) is required."
metadata:
  author: "Ben Randoing <brandoing@nvidia.com>"
  team: healthcare-tme
  domain: ai-ml
  stage: 3
  variant: self-contained
  previous_skill: clinical-asr-build
  next_skill: clinical-asr-finetune
---

# Clinical ASR Flywheel — Stage 3 (Eval)

You are the **score-and-route** stage. The user arrives with a NeMo-format `manifest.jsonl` (either from `/clinical-asr-build` or carried in from elsewhere). You transcribe it via the inlined Parakeet/Nemotron ASR NVCF recipe, score four metrics, produce a five-section leaderboard, and read the decision tree to decide whether the user should advance to `/clinical-asr-finetune`, loop back to `/clinical-asr-build`, or stop and harden the eval.

**This skill does not generate audio.** If the manifest is missing or empty, send the user back to `/clinical-asr-build`.

**Self-contained:** the Parakeet/Nemotron Speech ASR recipe is inlined below — there is no `/transcribe-audio` call.

## Purpose

Score a clinical-ASR manifest with four metrics:

- **WER** — Word error rate (industry-standard, blunt for clinical)
- **CER** — Character error rate (catches near-misses on long compound names)
- **KER** ★ — Keyword error rate: did the flagged `term` appear in the hypothesis? **Headline clinical signal.**
- **SER** — Sentence error rate (1 if any wrong, 0 if perfect; sanity bound)

…then produce a five-section leaderboard whose **by-`ipa_source`** split is the most informative single number in the entire flywheel, and route the user using the post-eval decision tree.

## When to use this skill

Activate on user phrases like:

- "Score my ASR manifest"
- "What's the KER on Parakeet TDT v2?"
- "Run the eval on cycle-N"
- "Compare two ASR models on the clinical benchmark"
- "Generate the leaderboard"
- "I have a manifest.jsonl, how do I score it?"
- "Why is KER 0.4 when WER is 0.07?"
- "Should we fine-tune?" *(the post-eval decision tree lives here)*

Do **not** activate when:

- The user doesn't have a manifest yet → `/clinical-asr-build`
- The user wants to fine-tune *now* with a known KER → `/clinical-asr-finetune`

## Prerequisites

- **A NeMo-format manifest** with the clinical extension fields (`term`, `entity_category`, `ipa_source`, `voice_id`, `noise_level`, `context_type`). Schema documented in the build skill's `references/manifest-schema.md`.
- **`NVIDIA_API_KEY`** exported (Stage 1 prerequisite still applies).
- **Audio files actually present on disk** — run the audio-existence pre-flight from the manifest-schema reference before spending API credits.

## Workflow

### 3a. Pick the ASR NIM

**Default**: `nvidia/parakeet-tdt-0.6b-v2` — NVIDIA's current English ASR recommendation, supported in NeMo's stock SFT recipe so Stage 3 baseline and Stage 4 fine-tune ride the same model family.

Override via env vars (the recipe in 3b reads them):

| Variable | Default | Use when |
|---|---|---|
| `ASR_ENDPOINT` | `grpc.nvcf.nvidia.com:443` | Self-hosted Riva NIM (e.g. `localhost:50051`); takes precedence over NVCF |
| `ASR_NVCF_FUNCTION_ID` | `bb0837de-8c7b-481f-9ec8-ef5663e9c1fa` (Nemotron Speech) | A different hosted NVCF function (Parakeet TDT v2, a fine-tuned NIM, etc.) — get the function ID from <https://build.nvidia.com> for the target model |
| `ASR_MODEL_NAME` | `nemotron-speech-streaming-0.6b` | Leaderboard display name |
| `ASR_USE_SSL` | `true` for NVCF endpoints, `false` otherwise | Override SSL behavior (rarely needed) |

**Other catalog options** (use the function ID from build.nvidia.com):

- `nvidia/parakeet-tdt-1.1b` — higher accuracy, larger model; pick when WER matters more than cost.
- `nvidia/parakeet-ctc-0.6b-v2` — CTC decoder; simpler Riva export path.
- `nvidia/nemotron-speech-streaming-en-0.6b` — real-time partial transcripts. **Eval-only**; do not pair with `/clinical-asr-finetune` (SFT path unreliable).

Echo the chosen NIM and any env-var overrides to the user **before** spending API credits.

### 3b. ASR recipe — Parakeet / Nemotron Speech via NVCF (or self-hosted)

```python
# asr.py
import os
from typing import List
import numpy as np
import soundfile as sf
import riva.client

_HOSTED_SERVER = "grpc.nvcf.nvidia.com:443"
_HOSTED_FUNCTION_ID = "bb0837de-8c7b-481f-9ec8-ef5663e9c1fa"  # Nemotron Speech default

def _load_pcm16_mono_16k(path: str) -> bytes:
    """Read WAV → 16 kHz mono int16 LINEAR_PCM bytes."""
    audio, sr = sf.read(path, dtype="float32", always_2d=False)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)  # downmix to mono
    if sr != 16000:
        # Simple linear resampler — good enough for ASR. For higher quality use librosa.
        idx = (np.arange(int(len(audio) * 16000 / sr)) * sr / 16000).astype(int)
        audio = audio[np.clip(idx, 0, len(audio) - 1)]
    audio_i16 = np.clip(audio * 32767, -32768, 32767).astype(np.int16)
    return audio_i16.tobytes()

def transcribe(audio_path: str, api_key: str,
               endpoint: str = _HOSTED_SERVER,
               function_id: str = _HOSTED_FUNCTION_ID,
               use_ssl: bool = True) -> str:
    """Transcribe one WAV through Parakeet/Nemotron Speech on NVCF (or self-hosted).

    Caller passes `api_key` explicitly — typically read once from the caller's
    own configuration. For self-hosted Riva NIMs, set endpoint to
    e.g. localhost:50051, use_ssl=False, and pass api_key="" (ignored).
    """
    is_nvcf = "nvcf.nvidia.com" in endpoint

    auth_kwargs = {"uri": endpoint, "use_ssl": use_ssl}
    if is_nvcf:
        auth_kwargs["metadata_args"] = [
            ["function-id", function_id],
            ["authorization", f"Bearer {api_key}"],
        ]

    auth = riva.client.Auth(**auth_kwargs)
    asr  = riva.client.ASRService(auth)
    cfg  = riva.client.RecognitionConfig(
        encoding=riva.client.AudioEncoding.LINEAR_PCM,
        sample_rate_hertz=16000,
        language_code="en-US",
        max_alternatives=1,
        audio_channel_count=1,
        enable_automatic_punctuation=True,
    )
    streaming_cfg = riva.client.StreamingRecognitionConfig(
        config=cfg, interim_results=False,
    )

    # CRITICAL: the hosted NVCF function is *streaming-only*. Calling
    # `offline_recognize()` returns "Unavailable model". Use
    # `streaming_response_generator()` even for offline transcription —
    # send the whole file as one chunk.
    audio_pcm = _load_pcm16_mono_16k(audio_path)
    parts: List[str] = []
    for resp in asr.streaming_response_generator(
        audio_chunks=iter([audio_pcm]),
        streaming_config=streaming_cfg,
    ):
        for r in resp.results:
            if r.is_final and r.alternatives:
                parts.append(r.alternatives[0].transcript)
    return " ".join(parts).strip()
```

**Caller wires the credential.** The `transcribe()` recipe above takes `api_key` as an explicit parameter rather than reading the environment itself — that's good practice and keeps the recipe portable (a unit test can pass a fake key). In your driver script, fetch `NVIDIA_API_KEY` from the shell using whatever pattern your codebase prefers — a direct env-var lookup, a config-loader helper, or a secrets manager — and pass the resulting string to `transcribe()`.

**Self-hosted Riva NIM.** Pass `endpoint="localhost:50051"` (or wherever your NIM is listening), `use_ssl=False`, and `api_key=""`. The recipe drops the `function-id` / `authorization` metadata automatically. Self-hosted NIMs usually expose `offline_recognize()` too, but the streaming code path above works on both, so prefer it for portability.

### 3c. Iterate the manifest and write per-sample results

```python
import json

def score_manifest(manifest_path: str, per_sample_out: str):
    with open(manifest_path) as fin, open(per_sample_out, "w") as fout:
        for line in fin:
            row = json.loads(line)
            try:
                hyp = transcribe(row["audio_filepath"])
            except Exception as e:
                hyp = ""  # mark as a miss; investigate before publishing
                print(f"warning: transcribe failed on {row['audio_filepath']}: {e}")
            out = {
                "audio_filepath": row["audio_filepath"],
                "ref": row["text"],
                "hyp": hyp,
                **{k: row[k] for k in (
                    "term", "entity_category", "ipa_source",
                    "voice_id", "noise_level", "context_type",
                ) if k in row},
            }
            fout.write(json.dumps(out) + "\n")
```

### 3d. Score four metrics

For every row, compute:

| Metric | What it measures | Why we keep it |
|---|---|---|
| **WER** | Word error rate (Levenshtein on tokens, after normalization) | Industry standard; blunt instrument for clinical |
| **CER** | Character error rate | Catches near-misses on long compound names |
| **KER** ★ | Keyword error rate — did the flagged `term` appear in the hypothesis (normalized, **contiguous** match)? | **Headline clinical signal** |
| **SER** | Sentence error rate (1 if any wrong, 0 if perfect) | Sanity bound; what the doctor experiences |

**Normalization (apply to both `ref` and `hyp` before all four metrics):**

1. Lowercase.
2. NFKD-normalize (smart quotes → ASCII, etc.).
3. Strip punctuation **except hyphen**.
4. Collapse whitespace runs to a single space.

```python
import re, unicodedata
_PUNCT_RE = re.compile(r"[^\w\s-]", re.UNICODE)
_WS_RE = re.compile(r"\s+")
def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "").lower()
    text = _PUNCT_RE.sub(" ", text)
    return _WS_RE.sub(" ", text).strip()

def ker(ref_term: str, hyp: str) -> int:
    # Strict-contiguous: the term's words must appear in order, adjacent, in the hypothesis.
    term_norm = normalize(ref_term)
    hyp_norm  = normalize(hyp)
    return 0 if term_norm and term_norm in hyp_norm else 1
```

**Strict KER** — term words must appear *in order, adjacent* in the normalized hypothesis. This is conservative: `cefazolin → cefa zolin` counts as a miss. That's the right call clinically — a downstream pharmacy lookup will fail on the misspelled token.

For WER/CER, use the `jiwer` library if you want a tested implementation:

```python
import jiwer
wer_val = jiwer.wer(reference=normalize(ref), hypothesis=normalize(hyp))
cer_val = jiwer.cer(reference=normalize(ref), hypothesis=normalize(hyp))
ser_val = 0 if normalize(ref) == normalize(hyp) else 1
```

### 3e. Breakdowns + leaderboard

Write a five-section markdown leaderboard, **in this order**:

1. **Headline** — overall WER, CER, KER, SER for the chosen model.
2. **KER by `entity_category`** — drug vs procedure vs anatomy vs ... This is what the user actually cares about for deployment.
3. **KER by `ipa_source`** — **the most informative single number in the leaderboard.** The delta between `merriam-webster` and `magpie_g2p` rows is the proof the SSML override pipeline is doing real work. *Read this section aloud to the user.*
4. **KER by `noise_level`** — clinical environments are loud. `snr_5db` rows are closer to reality than `clean`.
5. **Per-term KER** (worst first) — these are your Stage 4 fine-tune targets.

A representative `ipa_source` split looks like:

```
ipa_source           KER     n
merriam-webster      0.05    420
magpie_g2p           0.41    180   ← pronunciation-coverage gap
override             0.03     45
```

The 0.05 vs 0.41 delta tells the deployment story. If the user sees this gap and asks "should we fine-tune?" — the answer is *not yet*. Route them back to `/clinical-asr-build`'s IPA QA pipeline (Step 2d). See the decision tree below.

## Decision tree (after eval)

Read the **priority-category KER** (drug KER for most clinical workflows, procedure KER for surgical workflows) and route:

| KER on priority category | Recommend |
|---|---|
| **> 0.3** | `/clinical-asr-finetune`. Manifest is already NeMo-format-ready. Note: rows ≥ 100 is the minimum for a believable fine-tune signal; if the manifest is smaller, grow it first via `/clinical-asr-build`. |
| **0.1 – 0.3** | Either expand the term list (back to `/clinical-asr-build` with new domain terms — usually surfaces more failures cheaper than tuning) **or** fine-tune. On a *first* eval, expand. On a *later* eval where you've already grown the manifest, tune. |
| **< 0.1** | Strong baseline. Don't tune yet — you'd be optimizing against a saturated metric. Push the eval harder: add voices, noise levels, contexts, adversarial terms. Loop back to `/clinical-asr-build`. |

**Special case — `merriam-webster` rows score well but `magpie_g2p` rows are bad.** That's a pronunciation-hint coverage gap, **not a model gap**. Route back to `/clinical-asr-build` Step 2d (IPA QA review), not to `/clinical-asr-finetune`. Fine-tuning over a TTS-pronunciation gap teaches the model to mis-recognize the model's own mistakes — the wrong fix.

## Example scenarios

**Scenario A — first eval on a fresh cycle-1 manifest.** User: *"I have `manifest.jsonl` with 200 clinical audio rows already. How do I score it?"* → Skip Stage 2 entirely. Run the audio-existence pre-flight. Echo the chosen NIM. Run the inlined `score_manifest()` recipe. Score the four metrics. Produce the five-section leaderboard. Read the by-`ipa_source` split to the user. Apply the decision tree against drug KER.

**Scenario B — interpreting a mixed result.** User: *"Eval shows KER 0.05 on rows tagged `merriam-webster` but 0.40 on rows tagged `magpie_g2p`. Should I fine-tune?"* → No — this is the special case. The model is fine; the pronunciation hints aren't covering the long-tail terms. Route the user back to `/clinical-asr-build` Step 2d to audition the `magpie_g2p` rows and append verified IPA to `pronunciation_overrides.csv`. Re-run Stage 3 after the rebuild before reconsidering Stage 4.

**Scenario C — why-KER question.** User: *"Why do you use KER instead of just WER for clinical ASR?"* → Explain: aggregate WER is dominated by function words (articles, prepositions); a model can have low WER but still be clinically dangerous if drug names are wrong. KER tracks whether the flagged clinical entity was transcribed correctly per row. Concrete example: WER 0.05 with drug KER 0.40 is not deployable. Both metrics are reported; KER is the headline.

## Artifacts produced

- `per_sample.json` — per-row transcription results with all clinical-extension fields preserved
- `results.csv` — per-row WER/CER/KER/SER scores
- `leaderboard_cycle<N>.md` — five-section markdown report

## Troubleshooting

- **"No manifest found"** → the user skipped Stage 2 or pointed at the wrong directory. Route to `/clinical-asr-build`, or confirm `$MANIFEST_PATH`.
- **`grpc.RpcError: Unavailable model`** on the ASR call → you called `offline_recognize()` instead of `streaming_response_generator()`. The hosted Nemotron Speech NVCF function is streaming-only. The inlined recipe above is already correct — don't switch to offline mode.
- **All rows score KER=1** → check normalization. If `ref` and `hyp` are normalized differently (one lowercased, one not; one with punctuation, one without), every contiguous match will fail. Apply the four normalization steps to both sides.
- **All rows score KER=0** but WER is high → KER is finding the term *somewhere* but the rest of the sentence is wrong. Sanity-check by reading a few `(ref, hyp)` pairs by hand. Often this surfaces a misaligned manifest (audio belongs to a different row).
- **`merriam-webster` KER and `magpie_g2p` KER are both high** → not a pronunciation-coverage issue; the ASR model genuinely can't transcribe these terms. Stage 4 is the right route, assuming the manifest has ≥ 100 rows.
- **`merriam-webster` KER low, `magpie_g2p` KER high** → pronunciation-coverage gap. Route to `/clinical-asr-build` Step 2d. **Do not fine-tune** as a first response.
- **WER fine on `clean` but balloons on `snr_5db`** → robustness gap. Expand the eval set with more diverse noise via `/clinical-asr-build`, or accept the limit and document the deployment-noise floor.
- **`grpc.RpcError: UNAUTHENTICATED`** → `NVIDIA_API_KEY` is missing or wrong in the shell. The setup skill's length-only check catches this.
- **`grpc.RpcError: RESOURCE_EXHAUSTED`** on a large manifest → hosted-NIM rate limit. Slice the manifest and re-run the dropped rows after a short pause.

## Limitations

- **English-only by default.** Tokenization + normalization assume Latin script and en-US lexicon.
- **Strict-contiguous KER is conservative.** A near-miss like `cefa zolin` counts as a miss. That's intentional — pharmacy lookups fail on near-misses.
- **One model per eval run.** Comparing two models means running the eval twice and diffing leaderboards.
- **Linear resampler in `_load_pcm16_mono_16k`.** Fine for ASR (the bandwidth that matters is below 8 kHz anyway); for higher-quality processing, swap in `librosa.resample` or `soxr`.
- **Hosted-first paths assumed.** Self-hosted Riva NIMs work — set `ASR_ENDPOINT` — but require their own deploy setup.

## Companion software

Runnable scripts that implement this stage live in the **`voice-eval-flywheel`** repo (`scripts/run_eval.py` drives the full pipeline; `flywheel/leaderboard.py` carries the five-section renderer). You **do not need** the repo to complete this stage — every recipe needed is inlined above.

## Next steps

- **Forward (KER > 0.3, manifest ≥ 100 rows):** `/clinical-asr-finetune`.
- **Back to build (KER 0.1–0.3 on first eval, or `magpie_g2p` gap):** `/clinical-asr-build`.
- **Stop (KER < 0.1):** the eval is saturated. Harden it before declaring victory.

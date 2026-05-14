---
name: "clinical-asr-finetune"
description: "Stage 4 of the Clinical ASR Flywheel (self-contained): stock NeMo SFT on Parakeet TDT v2, term-aware train/val split, offline cycle N+1 re-eval, and optional NIM deploy via inlined riva-build / riva-deploy recipes. No upstream skill dependency. Preceded by /clinical-asr-eval; followed by a return to /clinical-asr-build for the next cycle."
version: "1.0.0"
author: "Ben Randoing <brandoing@nvidia.com>"
tags:
  - clinical-asr
  - finetune
  - sft
  - nemo
  - parakeet
  - riva-build
  - riva-deploy
  - flywheel
  - self-contained
tools:
  - Read
  - Write
  - Bash
  - Skill
license: Apache-2.0
compatibility: "Self-contained — requires a CUDA host (24 GB VRAM comfortable, 16 GB workable with batch_size=4), the NeMo container (nvcr.io/nvidia/nemo:25.11.01), and (for optional NIM deploy) the Riva ServiceMaker container plus a target NIM container family from nvcr.io. No local GPU? Use Brev. NVIDIA_API_KEY required for the offline cycle N+1 eval round-trip; NGC_API_KEY required for the container pulls (covered in /clinical-asr-setup steps 1c-1d)."
metadata:
  author: "Ben Randoing <brandoing@nvidia.com>"
  team: healthcare-tme
  domain: ai-ml
  stage: 4
  variant: self-contained
  previous_skill: clinical-asr-eval
  next_skill: clinical-asr-build
---

# Clinical ASR Flywheel — Stage 4 (Fine-tune)

You are the **adapt-and-measure** stage. The user arrives from `/clinical-asr-eval` with a manifest, a baseline KER number, and the decision-tree's recommendation that fine-tuning is worth the GPU time. You run stock NeMo SFT, do an offline cycle N+1 re-eval to **measure that the loop closed**, and optionally deploy the resulting `.nemo` as a Riva NIM with the inlined `riva-build` / `riva-deploy` recipe.

**The cycle KER from offline eval is the measurement that closes the loop.** Riva NIM deploy validates serving (latency, streaming, scale), not model quality.

> **Empirically verified on the reference manifest** (39 rows, Parakeet TDT v2):
> Baseline KER **0.513** → after 3 epochs of stock SFT: **0.128** (-75% relative).
> Drug names: 0.857 → 0.214. Conditions: 0.500 → 0.000. Procedures: 0.250 → 0.000.

**Self-contained:** the NeMo SFT recipe and the minimum-viable Riva NIM deploy commands are inlined below — there is no `/finetune-asr` or `/riva-asr-custom` call.

## Purpose

Run **stock NeMo SFT** (no custom adapter logic, no patches) in `nvcr.io/nvidia/nemo:25.11.01` against a term-aware row-disjoint train/val split, produce a `.nemo` model, and re-eval offline as cycle N+1. Decide based on the cycle-N → cycle-N+1 KER delta whether to keep the model, grow the manifest, or accept that fine-tuning didn't help. Optionally deploy as a Riva NIM with the inlined deploy recipe.

## When to use this skill

Activate on user phrases like:

- "Fine-tune ASR on my clinical vocabulary"
- "Improve ASR on medication names"
- "We have a KER of 0.4, can we fine-tune?"
- "Run SFT on my Parakeet TDT base"
- "Train a clinical ASR adapter"
- "Compare cycle 1 vs cycle 2 KER"
- "Deploy my fine-tuned model as a NIM" *(this skill carries the inlined deploy recipe)*

Do **not** activate when:

- The user hasn't scored a baseline yet → `/clinical-asr-eval`
- The user doesn't have a manifest → `/clinical-asr-build`

## Prerequisites

- **A cycle-N manifest + cycle-N eval result** from `/clinical-asr-eval`. The priority-category KER must be > 0.3 (Stage 4 gate). The manifest should have ≥ 100 rows total, and ≥ 5 rows per priority `entity_category`, for a believable post-tune signal.
- **A CUDA host** — 24 GB VRAM is comfortable for Parakeet TDT 0.6B at `batch_size=4` with `bf16-mixed`; 16 GB works with smaller batch. Brev L40S 48 GB is the recommended cloud option.
- **The NeMo container**: `nvcr.io/nvidia/nemo:25.11.01`. `docker pull` covered in `/clinical-asr-setup` Step 1c.
- **NVIDIA Container Toolkit + Docker** — covered by `/clinical-asr-setup` Steps 1c-1d.
- **A train/val split** stratified by `entity_category` (Step 4a below).

## Workflow

### 4a. Term-aware train/val split

**Row-disjoint, stratified by `entity_category`, default val fraction 0.2.**

The **same `term`** may appear on both sides via different rows (different voice, context, noise). That's expected and desirable — it measures acoustic + contextual robustness on the trained vocabulary, the standard ASR adaptation metric.

Singleton categories (one row total) get forced to train with a warning. If any priority category has < 5 rows, **bail to `/clinical-asr-build`** — held-out validation will be too noisy.

```python
# split.py
from collections import defaultdict
import json, random, pathlib

def split_manifest(manifest_path: str, out_dir: str, val_frac: float = 0.2, seed: int = 42):
    random.seed(seed)
    rows = [json.loads(line) for line in open(manifest_path)]
    by_cat = defaultdict(list)
    for r in rows:
        by_cat[r["entity_category"]].append(r)

    train, val = [], []
    for cat, cat_rows in by_cat.items():
        random.shuffle(cat_rows)
        if len(cat_rows) < 2:
            train.extend(cat_rows)
            print(f"warning: singleton category {cat}, forced to train")
            continue
        if len(cat_rows) < 5:
            print(f"warning: priority category {cat} has only {len(cat_rows)} rows — held-out signal will be noisy")
        n_val = max(1, int(val_frac * len(cat_rows)))
        val.extend(cat_rows[:n_val])
        train.extend(cat_rows[n_val:])

    out = pathlib.Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    with open(out / "train.jsonl", "w") as f:
        for r in train: f.write(json.dumps(r) + "\n")
    with open(out / "validation.jsonl", "w") as f:
        for r in val: f.write(json.dumps(r) + "\n")
    print(f"train={len(train)}, val={len(val)}")
```

### 4b. Choose the base model

| Base | Decoder | Streaming | SFT viability | Notes |
|---|---|---|---|---|
| **`nvidia/parakeet-tdt-0.6b-v2`** | TDT | ❌ at serve, ✅ via Riva chunking | ✅ **Empirically verified** (KER 0.513 → 0.128 in 3 epochs, -75% relative) | NVIDIA's current English ASR default. Stock NeMo SFT recipe works end-to-end. **Recommended.** |
| `nvidia/parakeet-tdt-1.1b` | TDT | ❌ | Expected (same TDT arch, larger) | Higher accuracy. Bigger; pick when WER matters more than cost. |
| `nvidia/parakeet-ctc-0.6b-v2` | CTC | ❌ | Expected | Simpler decoder; cleanest Riva export path. |
| `nvidia/parakeet-rnnt-0.6b` | RNNT | "Streaming-ready" | Expected | Pick only if you specifically need RNNT serving alignment. |
| `nvidia/stt_en_conformer_ctc_large` | CTC | ❌ | Legacy fallback | Older base; Parakeet TDT v2 is NVIDIA's current recommendation. |
| `nvidia/nemotron-speech-streaming-en-0.6b` | RNNT (cache-aware) | ✅ streaming-only | ❌ **Don't use for SFT** | NVCF function is streaming-only; SFT path unreliable (UNK collapse on validation after first training step). For streaming serving at deploy time, Riva chunks a non-streaming base just fine. |

**Rule of thumb**: if the user asks to fine-tune Nemotron Speech Streaming, **warn about the collapse and recommend Parakeet TDT v2**. The NIM deploy recipe in Step 4e works the same way for any of these — only the container family changes.

Full base-model rationale + hyperparameter notes: `references/stage4-finetune.md`.

### 4c. Stock NeMo SFT recipe

In the NeMo container, invoke `/opt/NeMo/examples/asr/speech_to_text_finetune.py` directly. **No custom adapter logic. No patches.** The stock NeMo SFT script is the verified working recipe.

Hyperparameters (verified on Parakeet TDT v2, 39-row manifest):

```
init_from_pretrained_model: nvidia/parakeet-tdt-0.6b-v2
precision:                  bf16-mixed       # required for TDT numerical stability
lr:                         3e-4             # CosineAnnealing schedule
warmup_steps:               5                # tiny manifest; bump to 500 at production scale
epochs:                     3                # smoke; 10-30 for production
batch_size:                 4                # fits 16 GB VRAM; raise to 16 on L40S 48 GB
gradient_clip_val:          1.0              # defensive
```

**Container invocation** (paths are illustrative — adapt to your layout):

```bash
docker run --gpus all --rm -it \
  -v "$PWD:/workspace" \
  nvcr.io/nvidia/nemo:25.11.01 \
  python /opt/NeMo/examples/asr/speech_to_text_finetune.py \
    --config-path=conf \
    --config-name=speech_to_text_finetune \
    model.train_ds.manifest_filepath=/workspace/train.jsonl \
    model.validation_ds.manifest_filepath=/workspace/validation.jsonl \
    init_from_pretrained_model=nvidia/parakeet-tdt-0.6b-v2 \
    trainer.precision=bf16-mixed \
    trainer.max_epochs=3 \
    model.optim.lr=3e-4 \
    model.optim.sched.warmup_steps=5 \
    model.train_ds.batch_size=4 \
    trainer.gradient_clip_val=1.0
```

**Manifest paths inside the container.** Host paths (e.g. `$HOME/…`) don't resolve in `/workspace`. The rewrite snippet (host → `/workspace/`) is in `references/container-paths.md`.

The training run writes `adapted_model.nemo` and a `training_run_info.json` summary. Both go into a per-cycle subdirectory the user owns.

### 4d. Offline cycle N+1 eval — close the loop

Re-transcribe the cycle's audio with the fine-tuned `.nemo` using NeMo's offline `transcribe()`. **No Riva needed** — this is measurement, not serving. NeMo's offline path runs the same encoder + decoder graph the Riva NIM eventually serves.

Inside the NeMo container:

```python
import nemo.collections.asr as nemo_asr
model = nemo_asr.models.ASRModel.restore_from("/workspace/adapted_model.nemo")
hyps = model.transcribe(["/workspace/audio/row1.wav", "/workspace/audio/row2.wav"])
```

Score the same four metrics (WER/CER/KER/SER) and the same five-section leaderboard the eval skill produces. Use the normalization + KER functions from `/clinical-asr-eval` Step 3d.

**Decision table** — cycle-N+1 vs cycle-N:

| Result | Action |
|---|---|
| KER dropped meaningfully on targeted categories (e.g. drug KER −20% relative or more) | ✅ Keep the `.nemo`. Update the leaderboard. Advance to Step 4e if you want to deploy. |
| KER moved a little, you wanted more | Loop back to `/clinical-asr-build`, expand the manifest. Tiny manifests rarely benefit from hyperparameter tweaks. |
| KER got worse | Overfit on tiny manifest. Bail to `/clinical-asr-build` and grow. Don't tune harder. |
| No measurable change | Some categories may already be in the base model's vocab. Sanity-check per-category numbers before concluding training "didn't help." |

### 4e. Minimum-viable Riva NIM deploy

Two steps: `riva-build` converts `.nemo` → `.rmir` (Riva Model Intermediate Representation); `riva-deploy` materializes the RMIR into a model repository the NIM container serves.

**Pick the right `decoder` flag and target NIM container family by source decoder:**

| Source decoder | `riva-build` `decoder` flag | NIM container family |
|---|---|---|
| Conformer-CTC | `--decoder=greedy_ctc` | `nvcr.io/nim/nvidia/parakeet-*-ctc-*` |
| Conformer-RNNT | `--decoder=nemo` | `nvcr.io/nim/nvidia/parakeet-rnnt-*` |
| **Conformer-TDT (default)** | `--decoder=nemo` | `nvcr.io/nim/nvidia/parakeet-tdt-*` |
| Cache-Aware RNNT (Nemotron streaming) | `--decoder=nemo` | `nvcr.io/nim/nvidia/nemotron-streaming-*` ⚠ SFT broken on this base |

**Step 1 — build the RMIR.** Use the Riva ServiceMaker container:

```bash
# Pull the ServiceMaker image (one-time):
docker pull nvcr.io/nvidia/riva/riva-speech:2.18.0-servicemaker

# Build the RMIR from your .nemo (TDT source assumed):
docker run --gpus all --rm \
  -v "$PWD:/data" \
  nvcr.io/nvidia/riva/riva-speech:2.18.0-servicemaker \
  riva-build speech_recognition \
    /data/asr.rmir:tlt_encrypt \
    /data/adapted_model.nemo:tlt_encrypt \
    --name=parakeet-tdt-clinical \
    --decoder=nemo \
    --acoustic_model_streaming=False \
    --offline=True \
    --language_code=en-US
```

**Step 2 — deploy into a model repository:**

```bash
docker run --gpus all --rm \
  -v "$PWD:/data" \
  nvcr.io/nvidia/riva/riva-speech:2.18.0-servicemaker \
  riva-deploy /data/asr.rmir:tlt_encrypt /data/model_repository
```

**Step 3 — serve with the matching NIM container.** Pick the container family from the table above:

```bash
# Example for a TDT-source .nemo:
docker run --gpus all --rm \
  -v "$PWD/model_repository:/opt/tritonserver/models" \
  -p 50051:50051 \
  -e NIM_HTTP_API_PORT=9000 \
  nvcr.io/nim/nvidia/parakeet-tdt-0.6b-v2:latest
```

**Validate the deployment by re-running `/clinical-asr-eval`** with `ASR_ENDPOINT=localhost:50051`. The served numbers should match the cycle N+1 offline numbers within rounding. Any divergence means the gap is in Riva preprocessing or `riva-build` flags, not the model itself.

**This is the minimum-viable recipe.** Full Riva ServiceMaker options (streaming alignment, beam-search vs greedy, custom vocab boosting, etc.) live in the published Riva docs at <https://docs.nvidia.com/deeplearning/riva/user-guide/docs/tools/riva-build.html>.

## Example scenarios

**Scenario A — fine-tune gate met.** User: *"Our drug KER came back at 0.42. We have 130 manifest rows. Should we fine-tune?"* → Yes: KER > 0.3 and rows ≥ 100 satisfies the Stage 4 gate. Recommend `parakeet-tdt-0.6b-v2` (verified KER 0.513 → 0.128 in 3 epochs on a similar manifest). Walk the user through Step 4a (term-aware split), Step 4c (stock SFT in `nvcr.io/nvidia/nemo:25.11.01`), and Step 4d (offline cycle 2 eval). If cycle-2 drug KER drops ≥ 20% relative, keep the `.nemo`.

**Scenario B — user asks to SFT Nemotron Streaming.** User: *"Can I fine-tune `nvidia/nemotron-speech-streaming-en-0.6b` on my clinical manifest?"* → No: adapter SFT on the streaming Nemotron Speech base is currently broken (UNK collapse on validation after the first training step). Recommend `parakeet-tdt-0.6b-v2` as the substitute. If the user *needs* streaming serving, Riva chunks a non-streaming base just fine — base model doesn't have to be streaming-native.

**Scenario C — cycle 2 KER unchanged.** User: *"Cycle 2 KER barely moved."* → Bail to `/clinical-asr-build`. Tiny manifests rarely benefit from hyperparameter sweeps; signal density beats LR tweaks. If `magpie_g2p` rows are bad and `merriam-webster` rows are good, the real gap is pronunciation-hint coverage, not model capacity.

**Scenario D — deploy the trained model.** User: *"My cycle 2 KER hit 0.12 — how do I deploy this as a NIM?"* → Walk through Step 4e: `riva-build speech_recognition` with `--decoder=nemo` (TDT default), `riva-deploy` into a model repository, run the `parakeet-tdt-*` NIM container with the repo mounted. Validate by re-running `/clinical-asr-eval` against `localhost:50051`.

## Artifacts produced

- `train.jsonl`, `validation.jsonl` — term-aware split (Step 4a)
- `adapted_model.nemo` — fine-tuned model (Step 4c)
- `training_run_info.json` — hyperparameters, dataset stats, end-of-train metrics
- `offline_hyps.jsonl` — cycle-N+1 transcription hypotheses (Step 4d)
- `leaderboard_cycle<N+1>.md` — cycle-N+1 five-section leaderboard
- *(optional, Step 4e)* `asr.rmir`, `model_repository/` — Riva-deployable artifacts
- *(optional, Step 4e)* A serving NIM at `localhost:50051`

## Troubleshooting

- **Stage 4 training collapses to all-UNK after first step** → you're on the cache-aware streaming RNNT base (`nemotron-speech-streaming-en-0.6b`). Route to `nvidia/parakeet-tdt-0.6b-v2`. The streaming RNNT SFT path is broken; do not retry with different hyperparameters.
- **Manifest paths don't resolve inside the NeMo container** → host paths (e.g. `$HOME/…`) need rewriting to `/workspace/…`. See `references/container-paths.md`.
- **Cycle N+1 KER unchanged from cycle N** → on `parakeet-tdt-0.6b-v2` with the recipe above, this almost always means **manifest signal density is too low**. Grow the manifest; don't sweep LR.
- **Cycle N+1 KER got worse** → overfit on a tiny manifest. Bail to `/clinical-asr-build` and grow.
- **Riva-served numbers diverge from offline numbers** → the gap is in `riva-build` flags or the chosen NIM container family. Check the decoder table in Step 4e; passing the wrong `--decoder` for the source architecture silently produces a broken RMIR.
- **`bf16-mixed` precision errors** → some GPUs (older Turing, all Volta) don't support BF16. Drop to `fp32` and reduce `batch_size`. Use `fp16-mixed` only if `fp32` is too slow — fp16 with TDT decoders can produce NaN losses.
- **OOM during training on 24 GB GPU** → drop `batch_size` to 2, raise `accumulate_grad_batches` to 2 to keep the effective batch size constant.
- **`riva-build` complains about unknown decoder flag values** → the flag name varies across ServiceMaker versions. Check the version-matched docs (link in Step 4e); the table above is verified against `riva-speech:2.18.0-servicemaker`.

## Limitations

- **Adapter-style SFT on TDT/RNNT decoders is broken.** Empirically confirmed: an earlier LinearAdapter-mixin recipe produces 72 NaN tensors at any LR on TDT and RNNT decoders. Resolved by switching to NeMo's stock full-model SFT (`speech_to_text_finetune.py`), which is what this recipe uses. Do not attempt adapter SFT on TDT/RNNT bases.
- **Don't SFT `nemotron-speech-streaming-en-0.6b`.** The streaming-only NVCF function's SFT path is unreliable (UNK collapse). For streaming serving at deploy time, Riva chunks a non-streaming base.
- **Tiny manifests overfit fast.** Below ~100 rows total or ~5 rows per priority category, cycle-N+1 numbers are noisy. Grow before trusting a small KER drop.
- **English-only by default.** The base-model table is en-US-specific. Other locales need a different base + a re-validated SFT recipe.
- **Minimum-viable deploy recipe.** Step 4e covers the architecture-matters case (`--decoder` + container family). Streaming alignment, beam-search options, vocab boosting, multi-language deployment all live in the Riva ServiceMaker manual.

## Companion software

Runnable scripts that implement this stage live in the **`voice-eval-flywheel`** repo (`scripts/split_manifest.py`, `scripts/finetune_asr.py` wrapping the stock NeMo SFT script with cycle-aware output paths, `scripts/eval_offline.py` for cycle-N+1 offline eval). You **do not need** the repo to complete this stage — every recipe needed is inlined above.

## Next steps

- **Deploy the `.nemo` as a NIM:** Step 4e above (inlined `riva-build` / `riva-deploy` recipe).
- **Grow the manifest for cycle N+2:** `/clinical-asr-build`.
- **Re-score the cycle:** `/clinical-asr-eval` (against the new endpoint or the new `.nemo` directly).

## References

- [`references/stage4-finetune.md`](references/stage4-finetune.md) — base-model selection table, hyperparameter rationale, decoder → NIM container mapping, decision tree comparing cycle-N+1 to cycle-N
- [`references/container-paths.md`](references/container-paths.md) — host → `/workspace/` path rewriting for cross-host manifest portability (laptop ↔ Brev ↔ NeMo container)

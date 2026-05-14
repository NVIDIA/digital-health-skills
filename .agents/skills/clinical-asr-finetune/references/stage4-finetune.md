# Stage 4 — Fine-tune playbook (detailed)

Companion to `SKILL.md`'s Stage 4 summary. Use this when you actually start fine-tuning.

**Stock NeMo SFT** in a NeMo container, then offline re-eval as cycle N+1. The cycle KER number from offline eval is the *measurement that closes the loop*. Riva NIM deploy validates serving (latency, streaming, scale), not model quality.

> **Empirically verified on the reference manifest** (39 rows, Parakeet TDT v2):
> Baseline KER **0.513** → after 3 epochs of SFT: **0.128** (-75% relative).
> Drug names: 0.857 → 0.214. Conditions: 0.500 → 0.000. Procedures: 0.250 → 0.000.

## 4a. Term-aware train/val split

Row-disjoint, stratified by `entity_category`, default val fraction 0.2. Same term may appear on both sides via different rows (different voices, contexts) — this is the standard ASR adaptation metric (acoustic + contextual robustness on the trained vocabulary).

Singleton categories get forced to train with a warning. If any priority category has < 5 rows, bail to `/clinical-flywheel-build` — held-out validation will be too noisy to attribute movement.

## 4b. Choose the base model

| Base | Decoder | Streaming | SFT in this pipeline | Notes |
|---|---|---|---|---|
| **`nvidia/parakeet-tdt-0.6b-v2`** | TDT | ❌ at serve, ✅ via Riva chunking | ✅ **Empirically verified** (KER 0.513 → 0.128 in 3 epochs, -75% relative) | NVIDIA's current English ASR default. Verified end-to-end with the stock NeMo SFT recipe. **Use this unless you have a strong reason not to.** |
| `nvidia/parakeet-tdt-1.1b` | TDT | ❌ | Expected (same TDT arch, larger) | **Higher accuracy.** Bigger; pick this when WER matters more than cost. Same SFT recipe; raise batch size or split across GPUs. |
| `nvidia/parakeet-ctc-0.6b-v2` | CTC | ❌ | Expected | Simpler decoder, cleanest Riva export path. Pick if you specifically need CTC. |
| `nvidia/parakeet-rnnt-0.6b` | RNNT | "Streaming-ready" (Riva chunking on serve) | Expected | Pick if you specifically need RNNT serving alignment. |
| `nvidia/stt_en_conformer_ctc_large` | CTC | ❌ | Legacy fallback | Older base; Parakeet TDT v2 is now NVIDIA's recommended path. Use only if Parakeet TDT v2 is unavailable in your environment. |
| `nvidia/nemotron-speech-streaming-en-0.6b` | RNNT (cache-aware) | ✅ streaming-only | ❌ **Don't use for SFT** | NVCF function is streaming-only; SFT path unreliable (UNK collapse on validation after first training step). For streaming serving at deploy time, Riva chunks a non-streaming base just fine. |

**Rule of thumb**: if the user asks to fine-tune Nemotron Speech Streaming, warn them about the UNK collapse and offer Parakeet TDT v2. Downstream the `riva-build` / `riva-deploy` recipe works the same way for any of these — only the NIM container family changes (see Section 4e in `SKILL.md`).

## 4c. Stock SFT — hyperparameters

In the NeMo container (`nvcr.io/nvidia/nemo:25.11.01`), invoke `/opt/NeMo/examples/asr/speech_to_text_finetune.py` with these hyperparameters — **no custom adapter logic, no patches**:

```
init_from_pretrained_model: nvidia/parakeet-tdt-0.6b-v2
precision:                  bf16-mixed       # required for TDT numerical stability
lr:                         3e-4             # CosineAnnealing schedule
warmup_steps:               5                # tiny manifest; bump to 500 at production scale
epochs:                     3                # smoke; 10-30 for production
batch_size:                 4                # fits 16 GB VRAM; raise to 16 on L40S 48 GB
gradient_clip_val:          1.0              # defensive
```

**Empirically validated** on Parakeet TDT v2 with 39-row clinical manifests: KER 0.513 → 0.128 in 3 epochs (-75% relative).

### Hyperparameter notes

- **`bf16-mixed` is non-negotiable for TDT.** `fp32` works but is ~2× slower; `fp16-mixed` produces NaN losses with TDT decoders.
- **`lr=3e-4` is the upper end of the comfortable range.** Below 1e-4, training barely moves on small manifests. Above 1e-3, you risk catastrophic forgetting of the base model's general English vocabulary.
- **`warmup_steps=5` is tiny manifest-only.** At 1,000+ row scale, bump to 500 (one epoch's worth).
- **`epochs=3` is a smoke test.** Production runs use 10–30 epochs with early-stopping on validation WER.
- **`batch_size=4` fits 16 GB.** On 48 GB cards (L40S, A6000), raise to 16. Effective batch size also scales via `accumulate_grad_batches` if you're OOM-constrained.

## 4d. Offline cycle N+1 eval (close the loop)

Re-transcribe the cycle's audio with the fine-tuned `.nemo` using NeMo's offline `transcribe()`. Score WER/CER/KER per row + per `entity_category`. **No Riva required** — this is measurement, not serving. NeMo's offline path runs the same encoder + decoder graph the Riva NIM eventually serves.

Compare cycle-N+1 KER against cycle-N:

| Result | Action |
|---|---|
| KER dropped meaningfully on targeted categories (e.g. drug KER −20% relative or more) | ✅ Keep the `.nemo`. Update the leaderboard. |
| KER moved a little, you wanted more | Loop back to `/clinical-flywheel-build`, expand the manifest. Tiny manifests rarely benefit from hyperparameter tweaks. |
| KER got worse | Overfit on tiny manifest. Bail to `/clinical-flywheel-build` and grow. Don't tune harder. |
| No measurable change | Some categories may already be in the base model's vocab. Sanity-check per-category numbers before concluding training "didn't help." |

## 4e. (Optional) Deploy as a Riva NIM

Use the `riva-build` / `riva-deploy` recipe in `SKILL.md` Step 4e. **Pass the source architecture explicitly** — `riva-build` can't reliably detect CTC vs RNNT vs TDT from the `.nemo` alone, and the wrong `--decoder` flag (paired with the wrong NIM container family) produces a broken RMIR with no clear error:

```
Conformer-CTC                          → decoder=greedy_ctc  → parakeet-*-ctc-* image
Conformer-RNNT                         → decoder=nemo        → parakeet-rnnt-* image
Conformer-TDT (default)                → decoder=nemo        → parakeet-tdt-* image
Cache-Aware RNNT (Nemotron streaming)  → decoder=nemo        → nemotron-streaming image
                                                                ⚠ SFT broken on this base
```

After deploy: re-run `/clinical-flywheel-eval` against the new endpoint (`ASR_ENDPOINT=localhost:50051`) to validate that production-serving numbers match offline numbers. Any divergence is in Riva preprocessing / `riva-build` flags, not the model.

## When to stop tuning

- **You've hit a KER floor across multiple cycles.** Two consecutive cycles with KER drop < 5% relative is the signal to stop tuning and either accept the model or rethink the methodology (add a new metric, extend `entity_category`, etc.).
- **You're past 30 epochs without improvement.** TDT bases plateau by ~30 epochs on manifests under ~5,000 rows. Larger manifests merit larger budgets — but verify scaling laws empirically; don't extrapolate from the 3-epoch smoke run.
- **Validation WER trends upward while training loss drops.** Classic overfit. Bail to `/clinical-flywheel-build` or add early-stopping (`patience=3` on validation WER).

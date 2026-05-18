# Stage 4 — Fine-tune playbook (deep dive)

Companion to `SKILL.md`'s Stage 4 sections. Use this for the *why* behind the recipe — hyperparameter rationale, the validated empirical numbers, and when to stop tuning. The *what* (split script, base-model choice, docker invocation, offline eval, riva-build/riva-deploy commands) lives in `SKILL.md` and is not duplicated here.

## Empirical validation

The recipe in `SKILL.md` is verified end-to-end on a reference clinical manifest. The numbers below are the actual measurements, not estimates:

| Manifest | Base model | Recipe | Cycle-1 KER | Cycle-2 KER | Relative reduction |
|---|---|---|---|---|---|
| 39 rows, mixed categories | `nvidia/parakeet-tdt-0.6b-v2` | Stock NeMo SFT, 3 epochs, lr=3e-4, bf16-mixed, batch_size=4 | 0.513 | 0.128 | −75% |

Per-category breakdown on the same manifest (cycle 1 → cycle 2):

| Category | Cycle-1 KER | Cycle-2 KER |
|---|---|---|
| Drug names | 0.857 | 0.214 |
| Conditions | 0.500 | 0.000 |
| Procedures | 0.250 | 0.000 |

Note the asymmetry: drug names start hardest and improve most. Conditions and procedures already had partial coverage in the base model.

## Hyperparameter rationale

The hyperparameter table itself is in `SKILL.md` §4d. The choices below are the *why* — diagnostic notes for tuning, not values to copy.

- **`bf16-mixed` precision is non-negotiable for TDT.** `fp32` works but is ~2× slower. `fp16-mixed` produces NaN losses with TDT decoders — a known TDT numerical-stability issue.
- **`lr=3e-4` is the upper end of the comfortable range.** Below 1e-4, training barely moves on small (<100-row) manifests. Above 1e-3, you risk catastrophic forgetting of the base model's general English vocabulary — recoverable but expensive.
- **`warmup_steps=5` is tiny-manifest-only.** At 1,000+ row scale, bump to ~500 (one epoch's worth of steps). The 5-step value exists because the reference manifest's 39 rows fit in <10 steps total at `batch_size=4`.
- **`epochs=3` is a smoke test.** Production runs use 10–30 epochs with early-stopping on validation WER (`patience=3`). The 3-epoch verified result reflects how quickly TDT picks up clinical vocabulary once the override SSML has gotten the audio right.
- **`batch_size=4` fits a 16 GB VRAM GPU.** On 48 GB cards (L40S, A6000), raise to 16. Effective batch size also scales via `accumulate_grad_batches` if you're OOM-constrained — this is the right escape hatch on 24 GB cards when bs=8 is needed but bs=8 won't fit.
- **`gradient_clip_val=1.0` is defensive.** With this recipe + the verified base, gradients haven't been observed to explode. Keep it on — the cost is zero, and removing it makes diagnosing rare divergences harder.

## When to stop tuning

A multi-cycle loop has natural stopping points. After cycle N+1, evaluate:

- **You've hit a KER floor across multiple cycles.** Two consecutive cycles with KER drop < 5% relative is the signal to stop tuning and either accept the model or rethink the methodology (add a new metric, extend `entity_category` to capture a missed dimension, etc.).
- **You're past 30 epochs without improvement.** TDT bases plateau by ~30 epochs on manifests under ~5,000 rows. Larger manifests merit larger budgets — but verify scaling laws empirically; don't extrapolate from the 3-epoch smoke run.
- **Validation WER trends upward while training loss drops.** Classic overfit. Bail to `/clinical-flywheel-build` and grow the manifest, or add early-stopping (`patience=3` on validation WER).

## Related references

- Base-model selection table → `SKILL.md` §4c
- Stock SFT hyperparameter values → `SKILL.md` §4d
- Decision tree on cycle-N+1 KER → `SKILL.md` §4e
- `riva-build` / `riva-deploy` commands → `SKILL.md` §4f
- Host → container manifest path rewriting → `SKILL.md` "References" section (links `container-paths.md` from the top level)

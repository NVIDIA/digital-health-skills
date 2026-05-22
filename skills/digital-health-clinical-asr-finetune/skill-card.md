# Skill Card — digital-health-clinical-asr-finetune

## Description
Runs stock NeMo SFT on `nvidia/parakeet-tdt-0.6b-v2` in `nvcr.io/nvidia/nemo:25.11.01` against a term-aware row-disjoint train/val split, re-evals offline as cycle N+1 to measure that the loop closed, and optionally hands the `.nemo` to `/riva-asr-custom` for NIM deploy. Stage 4 of the Clinical ASR Flywheel. Empirically verified at KER 0.513 → 0.128 (−75% relative) in 3 epochs on the reference manifest. Ready for commercial/non-commercial use.

## Owner
Ben Randoing <brandoing@nvidia.com>, NVIDIA Healthcare TME.

## License/Terms of Use
Apache 2.0 — see [LICENSE](../../../LICENSE).

## Use Case
ML engineers fine-tuning ASR for clinical vocabularies after Stage 3 surfaces priority-category KER > 0.3 with a manifest of ≥ 100 rows (≥ 5 per priority `entity_category`). Below those thresholds, route back to `/digital-health-clinical-asr-build` first.

## Deployment Geography
Global. NVIDIA NeMo container is publicly available; GPU host can be local CUDA or per-second-billed Brev (L40S 48 GB recommended).

## Known Risks and Mitigations
- **Risk:** `brev create` spins up a billed GPU instance; leaving it idle overnight on L40S costs ~$36.
  **Mitigation:** §4a inserts a mandatory `read -rp "Type YES"` confirmation gate before `brev create` — script exits non-zero on anything but `YES`. Closing-out commands (`brev stop` / `brev delete`) are documented inline.
- **Risk:** SFT on the cache-aware streaming RNNT base (`nvidia/nemotron-speech-streaming-en-0.6b`) produces UNK collapse on validation after step 1.
  **Mitigation:** §4c marks this base ❌ "Don't use for SFT" with the collapse-mechanism note. The skill warns proactively when users propose it and recommends Parakeet TDT v2 instead.

## References
- Source repo: https://gitlab-master.nvidia.com/healthcare-tme/healthcare-solutions/voice-eval-flywheel
- NVCARPS catalog: https://gitlab-master.nvidia.com/ai_tools/ai_rules/-/tree/main/team-skills/healthcare-tme/clinical-flywheel-finetune
- OSRB: https://nvbugspro.nvidia.com/bug/6177622
- NV-BASE reports: ai_rules MR !838 CI artifacts
- Deep-dive playbook: `references/stage4-finetune.md` (hyperparameter rationale, Brev provisioning, cycle-N+1 decision tree).

## Skill Output
- `train.jsonl` + `validation.jsonl` — term-aware stratified split.
- `adapted_model.nemo` — fine-tuned model.
- `training_run_info.json` — hyperparameters, dataset stats, end-of-train metrics.
- `offline_hyps.jsonl`, `leaderboard_cycle<N+1>.md` — offline re-eval artifacts.
- *(optional, via /riva-asr-custom)*: a deployed Riva NIM endpoint.

## Skill Version
1.0.0 (see frontmatter); git SHA at release time.

## Ethical Considerations
Non-PHI synthetic data only. The fine-tuned `.nemo` is a research artifact; clinical deployment requires separate validation against real patient data, bias review across patient demographics, and clinical-governance sign-off. Verified KER improvement on the reference manifest does not generalize to arbitrary clinical settings without re-eval.

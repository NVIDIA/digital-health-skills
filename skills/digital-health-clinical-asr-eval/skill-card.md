# Skill Card — digital-health-clinical-asr-eval

## Description
Scores a NeMo-format clinical manifest with four ASR metrics (WER/CER/KER/SER) via NVCF Parakeet/Nemotron, then produces a five-section leaderboard whose by-`ipa_source` (merriam-webster vs magpie_g2p) split is the headline diagnostic. Stage 3 of the Clinical ASR Flywheel. Ready for commercial/non-commercial use.

## Owner
Ben Randoing <brandoing@nvidia.com>, NVIDIA Healthcare TME.

## License/Terms of Use
Apache 2.0 — see [LICENSE](../../../LICENSE).

## Use Case
Speech engineers running KER-driven evaluation of ASR models on clinical vocabularies before promoting models to Stage 4 fine-tuning. Read the by-`ipa_source` split aloud — a wide merriam-webster vs magpie_g2p gap means *route back to /digital-health-clinical-asr-build*, not fine-tune.

## Deployment Geography
Global. Hosted NVCF Parakeet/Nemotron endpoints are publicly reachable; self-hosted Riva NIM works via `ASR_ENDPOINT` env var.

## Known Risks and Mitigations
- **Risk:** Every manifest row's WAV file + reference text is transmitted to NVCF for ASR.
  **Mitigation:** Audio-disclosure block at the top of SKILL.md; clips must be synthetic Stage-2 output, not real patient audio. PHI is excluded by design.
- **Risk:** Strict contiguous-match KER is conservative — `cefa zolin` counts as a miss on `cefazolin`.
  **Mitigation:** Documented intentionally — pharmacy lookups also fail on split tokens, so the strictness matches deployment reality. Phoneme-level matching is noted as a methodology extension, not a config tweak.

## References
- Source repo: https://gitlab-master.nvidia.com/healthcare-tme/healthcare-solutions/voice-eval-flywheel
- NVCARPS catalog: https://gitlab-master.nvidia.com/ai_tools/ai_rules/-/tree/main/team-skills/healthcare-tme/clinical-flywheel-eval
- OSRB: https://nvbugspro.nvidia.com/bug/6177622
- NV-BASE reports: ai_rules MR !838 CI artifacts

## Skill Output
- `per_sample.json` — per-row transcription (hyp + ref + all clinical-extension metadata).
- `results.csv` — per-row WER / CER / KER / SER scores.
- `leaderboard_cycle<N>.md` — five-section markdown report (headline → KER by entity_category → KER by ipa_source → KER by noise_level → per-term KER worst-first).

## Skill Version
1.1.0 (see frontmatter); git SHA at release time.

## Ethical Considerations
Non-PHI synthetic data only. Audio passed in must be Stage-2 Magpie TTS output; real patient recordings or ASR audio must not be transmitted through this skill. Downstream fine-tuning decisions made on the leaderboard should be reviewed against the special-case rule (MW low / magpie_g2p high → pronunciation-coverage gap, *not* a model gap) before committing GPU time.

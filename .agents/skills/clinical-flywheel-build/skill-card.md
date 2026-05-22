# Skill Card — clinical-flywheel-build

## Description
Curates a clinical specialty term list, tags IPA pronunciation hints via Merriam-Webster + Magpie G2P, and synthesizes a NeMo-format manifest of audio + reference text for downstream clinical ASR scoring. Stage 2 of the Clinical ASR Flywheel. Ready for commercial/non-commercial use.

## Owner
Ben Randoing <brandoing@nvidia.com>, NVIDIA Healthcare TME.

## License/Terms of Use
Apache 2.0 — see [LICENSE](../../../LICENSE).

## Use Case
Speech engineers and clinical informaticists building synthetic-data benchmarks for ASR systems on domain-specific vocabularies — drugs, procedures, anatomy, conditions, labs, roles. The skill is intentionally non-PHI: audio is synthesized from a user-curated term list via Magpie TTS, not derived from real patient encounters.

## Deployment Geography
Global. Hosted NVCF (Magpie TTS) and Merriam-Webster endpoints are publicly reachable; self-hosted Magpie NIM is an option for restricted networks.

## Known Risks and Mitigations
- **Risk:** Curated term list transits external services (NVIDIA NVCF for TTS; Merriam-Webster `dictionaryapi.com` or public site for IPA lookup).
  **Mitigation:** Data-disclosure block surfaced verbatim before the first call; users explicitly accept egress before any term/audio/text leaves the machine. PHI excluded by design.
- **Risk:** Magpie TTS may silently mispronounce long-tail clinical terms, corrupting the Stage 3 KER signal.
  **Mitigation:** Step 2d enforces a fail-closed QA-mode audition gate — one wav per term, user listens before full Cartesian synthesis. Skipping requires explicit deliberate-language opt-out logged in cycle notes.

## References
- Source repo: https://gitlab-master.nvidia.com/healthcare-tme/healthcare-solutions/voice-eval-flywheel
- NVCARPS catalog: https://gitlab-master.nvidia.com/ai_tools/ai_rules/-/tree/main/team-skills/healthcare-tme/clinical-flywheel-build
- OSRB: https://nvbugspro.nvidia.com/bug/6177622
- NV-BASE reports: ai_rules MR !838 CI artifacts

## Skill Output
- `audio/<slug>.wav` — synthesized clips (16-bit PCM mono, 16 kHz).
- `manifest.jsonl` — NeMo schema + clinical extension fields (`term`, `entity_category` from a fixed six-value vocabulary, `ipa_source` ∈ {override, merriam-webster, magpie_g2p}, `voice_id`, `noise_level`, `context_type`).
- `term_seed.csv`, append-only `pronunciation_overrides.csv`.
- Writes confined to the user-chosen `$EVAL_DIR/cycle<N>/`; no environment mutation.

## Skill Version
1.1.0 (see frontmatter); git SHA at release time.

## Ethical Considerations
Non-PHI synthetic data only. Must not transit real patient records, real ASR transcripts, or PHI through NVCF or Merriam-Webster. If a term list itself is sensitive (proprietary drug codenames, unreleased product names), confirm external-API transmission is acceptable under organizational data-governance policy before proceeding.

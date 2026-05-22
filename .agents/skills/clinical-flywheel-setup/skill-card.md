# Skill Card — clinical-flywheel-setup

## Description
Bootstraps a Clinical ASR Flywheel cycle: verifies `NVIDIA_API_KEY`, installs Python deps, smoke-tests the hosted Magpie TTS + Parakeet/Nemotron ASR stack via NVCF, and hands off to `/clinical-flywheel-build` with KER (keyword error rate) named as the headline metric. Ready for commercial/non-commercial use.

## Owner
Ben Randoing <brandoing@nvidia.com>, NVIDIA Healthcare TME.

## License/Terms of Use
Apache 2.0 — see [LICENSE](../../../LICENSE).

## Use Case
Speech/ML engineers and clinical informaticists initializing a Clinical ASR benchmarking environment from a clean machine. Stage 1 of the four-stage flywheel.

## Deployment Geography
Global. Hosted NVCF endpoints and Merriam-Webster are publicly reachable; self-hosted NIMs are an option for restricted networks.

## Known Risks and Mitigations
- **Risk:** `NVIDIA_API_KEY` could be echoed or logged during the smoke test.
  **Mitigation:** §1c codifies a do/don't pattern — harness passes the key as an explicit function argument; the recipe never reads `os.environ`; no print/echo of the value at any point.
- **Risk:** Smoke test transmits a synthesized clinical sentence + audio to NVCF.
  **Mitigation:** Data-disclosure block at the top of SKILL.md is surfaced verbatim before the first call; PHI is excluded by design (synthetic data only).

## References
- Source repo: https://gitlab-master.nvidia.com/healthcare-tme/healthcare-solutions/voice-eval-flywheel
- NVCARPS catalog: https://gitlab-master.nvidia.com/ai_tools/ai_rules/-/tree/main/team-skills/healthcare-tme/clinical-flywheel-setup
- OSRB: https://nvbugspro.nvidia.com/bug/6177622
- NV-BASE reports: ai_rules MR !838 CI artifacts

## Skill Output
- A confirmed environment: `NVIDIA_API_KEY` exported, activated virtualenv with `nvidia-riva-client`, `pandas`, `soundfile`, `requests`.
- A TTS→ASR round-trip transcript proving the hosted stack is reachable.
- No manifest, audio, or model artifact at this stage.

## Skill Version
1.1.0 (see frontmatter); git SHA at release time.

## Ethical Considerations
Non-PHI synthetic data only. Must not transit real patient transcripts, audio, or any other PHI through NVCF or Merriam-Webster. Clinical deployment of any downstream model requires separate validation against real patient data and clinical-governance review.

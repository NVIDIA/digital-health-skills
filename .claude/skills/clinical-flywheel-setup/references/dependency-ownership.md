# Dependency ownership — who owns what

The Clinical ASR Flywheel skill family is **glue + methodology**. The actual work happens across **six upstream skills**, each owned by a different team. When something breaks, route to the right owner — don't open an issue against `clinical-flywheel-*` for a TTS pronunciation bug.

## The six upstream components

| Component | Owner | What it provides | Which flywheel stage calls it |
|---|---|---|---|
| `/read-aloud` (or `/riva-tts`) | Riva team | TTS synthesis (Magpie, etc.); SSML support | Stage 2 (build) |
| `/transcribe-audio` (or `/riva-asr`) | Riva team | ASR transcription (Parakeet TDT/CTC/RNNT, Nemotron Speech, Canary, Whisper) | Stage 3 (eval) |
| `/finetune-asr` | Riva team | Word boosting, n-gram LM fusion, generic SFT recipes | Stage 4 reference + improvement paths |
| `/riva-asr-custom` | Riva team | `.nemo → .riva → RMIR → deployed NIM` pipeline | Stage 4e (optional deploy) |
| `/riva-nim-setup` | Riva team | NGC auth, Docker, NVIDIA Container Toolkit | Pre-req for any self-hosted path |
| `/data-designer` | NeMo team | Synthetic sentence generation around term seeds | Stage 2b (sentence gen) |

If the user reports a problem inside any of these, **the right move is to invoke that skill** for diagnosis rather than trying to debug here. The six upstream skills carry their own error tables, retry logic, and version-pinning that this skill family is intentionally not duplicating.

## What the `clinical-flywheel-*` skills own

- The **clinical-ASR methodology** — KER as headline, two-tier IPA tagging, term-aware split, cycle N+1 close-loop.
- The **decision tree** (post-eval) — when to fine-tune vs grow the manifest vs accept the baseline.
- The **manifest schema extension** — the clinical fields (`term`, `entity_category`, `ipa_source`, …) beyond NeMo's required minimum.
- The **base-model selection table** for fine-tune (Parakeet TDT v2 default; streaming-RNNT-collapse warning).
- The **composition pattern** — how `/data-designer + /read-aloud + /transcribe-audio + /riva-asr-custom` fit together for a clinical workflow.

## What the `clinical-flywheel-*` skills do **NOT** own

- **TTS pronunciation issues on specific terms** → `/read-aloud` (`/riva-tts`). We provide the SSML override mechanism + IPA validation list; we don't fix the underlying neural G2P.
- **ASR streaming vs offline gRPC plumbing** → `/transcribe-audio` (`/riva-asr`). We pick "whole file as one chunk" as a default; protocol-level debugging lives upstream.
- **NeMo container compatibility, Lhotse loader bugs** → NeMo team (via `/riva-asr-custom` if the user is fine-tuning, or directly via the NeMo issue tracker). We document field-tested patterns; we don't promise they'll match future container versions.
- **Riva NIM deploy steps** → `/riva-asr-custom`. We tell the user *which container family* matches their decoder; the deploy mechanics live there.
- **NGC API keys, Docker setup, GPU passthrough** → `/riva-nim-setup`.
- **`NVIDIA_API_KEY` issuance / NVCF function ID rotation** → Riva team's onboarding docs; we just consume the key.

## Version pinning (current)

These are the versions the `clinical-flywheel-*` recipes assume. Bump as upstream skills release.

| Component | Version assumed | If you change it |
|---|---|---|
| NeMo container | `nvcr.io/nvidia/nemo:25.11.01` | Re-test the SFT recipe; container ABI may change. See `/riva-asr-custom` for the canonical recipe per container release. |
| Parakeet TDT (default ASR + SFT base) | `nvidia/parakeet-tdt-0.6b-v2` | Update `ASR_MODEL_NAME` / `ASR_NVCF_FUNCTION_ID` in env. |
| Magpie TTS | `magpie-tts-multilingual` (NVCF function `877104f7-…`) | Validate SSML phoneme support on the new model — see `/read-aloud` / `/riva-tts`. |
| Nemotron Speech Streaming (eval-only, **don't SFT**) | `nvidia/nemotron-speech-streaming-en-0.6b` | Available for streaming eval; SFT path remains unreliable. |
| `/read-aloud`, `/transcribe-audio`, `/finetune-asr`, `/riva-asr-custom`, `/riva-nim-setup` | Whatever NVCARPS publishes | Re-run a Stage 2 → Stage 3 cycle to confirm nothing broke. |
| `/data-designer` | Whatever NVCARPS publishes | Re-validate the sentence-gen brief; output schema must remain `{term, entity_category, sentence, context_type}`. |

## Contact

- **`clinical-flywheel-*` skill family**: Ben Randoing <brandoing@nvidia.com>, healthcare-tme team
- **Riva skills**: Riva team — Slack `#riva-public` (or via the skill-eval-ci owner)
- **NeMo / data-designer**: NeMo team
- **NV-ACES / NVCARPS pipeline**: Astra team — Slack `#nv-aces-skill-eval`

When filing issues, **include**:
1. Which stage skill was active (`clinical-flywheel-setup` / `-build` / `-eval` / `-finetune`).
2. Which upstream skill was being driven (`/read-aloud`, `/transcribe-audio`, etc.).
3. The exact error or symptom — not just "it didn't work."
4. (For Stage 3+) the manifest schema check output from the build skill's `references/manifest-schema.md`.

Most "the flywheel is broken" reports turn out to be `/read-aloud` rate-limits, `/transcribe-audio` auth, or NeMo container version mismatches. Route correctly the first time.

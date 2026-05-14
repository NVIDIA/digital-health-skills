# External services — what this skill family talks to

The self-contained Clinical ASR Flywheel skill family is **glue + methodology** — but unlike the compose-with-upstream variant, it does not call other Claude skills. Instead it calls a small number of NVIDIA-hosted services directly. This file documents those external dependencies, the keys/IDs needed for each, and what the version-pinning story looks like.

## Services

| Service | Where it lives | What it does | Auth |
|---|---|---|---|
| **Magpie TTS Multilingual** | NVCF: `grpc.nvcf.nvidia.com:443`, function ID `877104f7-e885-42b9-8de8-f6e4c6303969` | Synthesize speech from text + SSML for Stage 2 manifest audio | `NVIDIA_API_KEY` bearer + `function-id` metadata |
| **Parakeet TDT 0.6B v2** | NVCF (function ID varies — see <https://build.nvidia.com>); also self-hostable as a Riva NIM | Default ASR for Stage 3 scoring + base model for Stage 4 SFT | `NVIDIA_API_KEY` bearer (NVCF) or local gRPC endpoint (self-hosted) |
| **Nemotron Speech Streaming 0.6B** | NVCF: `grpc.nvcf.nvidia.com:443`, function ID `bb0837de-8c7b-481f-9ec8-ef5663e9c1fa` | Streaming ASR for real-time partial transcripts (eval-only — **don't SFT this**) | Same as Parakeet |
| **NeMo training container** | `nvcr.io/nvidia/nemo:25.11.01` | Stage 4 SFT runs inside this | `NGC_API_KEY` for `docker login nvcr.io` |
| **Riva NIM container family** | `nvcr.io/nim/nvidia/parakeet-*` (TDT, CTC, RNNT variants) | Stage 4e optional deploy of the fine-tuned `.nemo` | `NGC_API_KEY` for the pull; `NVIDIA_API_KEY` not required at serve time |

## Keys / portals

| Key | Portal | Used for |
|---|---|---|
| `NVIDIA_API_KEY` | <https://build.nvidia.com> | Hosted inference (Magpie TTS, Parakeet/Nemotron ASR) via NVCF |
| `NGC_API_KEY` | <https://ngc.nvidia.com> | Docker pulls from `nvcr.io` (NeMo container, NIM containers) |

These are **different keys** issued by **different portals** to potentially different accounts. Hosted inference uses the first; container pulls use the second. The skill recipes assume both are exported when Stage 4 is in scope.

## What this skill family owns

- The **clinical-ASR methodology** — KER as headline, two-tier IPA tagging, term-aware split, cycle N+1 close-loop.
- The **decision tree** (post-eval) — when to fine-tune vs grow the manifest vs accept the baseline.
- The **manifest schema extension** — the clinical fields (`term`, `entity_category`, `ipa_source`, …) beyond NeMo's required minimum.
- The **base-model selection table** for fine-tune (Parakeet TDT v2 default; streaming-RNNT-collapse warning).
- The **glue recipes** — minimum-viable Magpie TTS, Parakeet/Nemotron ASR, NeMo SFT, and Riva NIM deploy as embedded code blocks in each stage skill.

## What this skill family does **NOT** own

- **TTS pronunciation quality on specific terms.** We provide the SSML override mechanism + IPA validation list; we don't fix Magpie's underlying neural G2P.
- **ASR streaming vs offline gRPC plumbing.** The recipe uses `streaming_response_generator()` because the hosted Nemotron Speech NVCF function is streaming-only. Self-hosted Riva NIMs may also support offline mode; we don't document every protocol option.
- **NeMo container internals.** Lhotse loader version-skew, batch-shape oddities, etc. live in the NeMo issue tracker, not here. We pin a single container version (`25.11.01`) and verify the stock SFT recipe against it.
- **Riva NIM deploy ergonomics beyond a minimum-viable recipe.** The `riva-build` / `riva-deploy` flag table in `clinical-asr-finetune` covers the architecture-matters case; the full ServiceMaker manual lives at <https://docs.nvidia.com/deeplearning/riva/user-guide/docs/tools/riva-build.html>.

## Version pinning (current)

| Component | Version assumed | If you change it |
|---|---|---|
| NeMo container | `nvcr.io/nvidia/nemo:25.11.01` | Re-test the SFT recipe (`speech_to_text_finetune.py` API can shift across container releases). |
| Magpie multilingual function ID | `877104f7-e885-42b9-8de8-f6e4c6303969` | Update the function ID in the build skill's TTS recipe and in this file. |
| Nemotron Speech Streaming function ID | `bb0837de-8c7b-481f-9ec8-ef5663e9c1fa` | Update via `ASR_NVCF_FUNCTION_ID` env var or in this file. |
| Parakeet TDT default base | `nvidia/parakeet-tdt-0.6b-v2` | Update via `ASR_MODEL_NAME` and the finetune skill's base-model table. |
| `nvidia-riva-client` | Whatever PyPI publishes; verified against ≥ 2.15 | The `Auth` + `SpeechSynthesisService` + `ASRService` APIs have been stable for several minor versions. |

## What to file vs where

| Issue | Right channel |
|---|---|
| TTS mispronounces a specific term despite override | Magpie / Riva TTS team — Slack `#riva-public` |
| ASR auth / rate-limit on NVCF | Riva team — `#riva-public` |
| NeMo container build / Lhotse loader | NeMo team — issue tracker on `github.com/NVIDIA/NeMo` |
| `riva-build` / `riva-deploy` flag table | Riva ServiceMaker docs (see URL above) |
| **Clinical ASR methodology / KER / IPA pipeline / split strategy** | This skill family — Ben Randoing <brandoing@nvidia.com>, healthcare-tme |

When filing issues, **include**:
1. Which stage skill was active (`clinical-asr-setup` / `-build` / `-eval` / `-finetune`).
2. Which external service was being called (Magpie NVCF, Nemotron Speech NVCF, NeMo container, Riva NIM).
3. The exact error or symptom — not just "it didn't work."
4. (For Stage 3+) the manifest schema check output from the build skill's `references/manifest-schema.md`.

Most "the flywheel is broken" reports turn out to be `NVIDIA_API_KEY` not exported in the shell, NVCF rate-limit drops on big jobs, or an `NGC_API_KEY` mix-up at `docker login nvcr.io`. Check those first.

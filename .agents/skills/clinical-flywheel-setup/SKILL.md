---
name: "clinical-flywheel-setup"
description: "Stage 1 of the Clinical ASR Flywheel. Use when bootstrapping a cycle: verify NVIDIA_API_KEY, Python deps, upstream skills. NOT for NGC/Docker setup (use /riva-nim-setup)."
version: "1.0.0"
author: "Ben Randoing <brandoing@nvidia.com>"
tags:
  - clinical-asr
  - setup
  - flywheel
  - bootstrap
tools:
  - Read
  - Write
  - Bash
  - Skill
license: Apache-2.0
compatibility: "Requires the read-aloud, transcribe-audio, finetune-asr, riva-asr-custom, riva-nim-setup, and data-designer skills installed alongside this one. NVIDIA_API_KEY for hosted NIM access."
metadata:
  author: "Ben Randoing <brandoing@nvidia.com>"
  tags:
    - clinical-asr
    - flywheel
    - setup
    - bootstrap
  team: healthcare-tme
  domain: ai-ml
  stage: 1
  companion_software: "voice-eval-flywheel (internal, optional)"
  next_skill: clinical-flywheel-build
---

# Clinical ASR Flywheel — Stage 1 (Setup)

You are the **entry point** to the Clinical ASR Flywheel. Confirm the user's environment is ready — `NVIDIA_API_KEY`, Python deps, upstream skills — then hand off to `/clinical-flywheel-build`. This skill makes no network calls of its own; it only prepares the runway.

The flywheel measures and closes the gap between general-purpose ASR and the clinical terms a clinician actually says. The headline metric across all four stages is **KER (keyword error rate)** on flagged entities — drugs, procedures, anatomy, conditions, labs, roles. Aggregate WER hides what matters clinically.

## Purpose

Bootstrap a clean machine into a working Clinical ASR Flywheel cycle. Confirm `NVIDIA_API_KEY` is present, the Python interpreter and required libraries are available, and the six upstream skills are installed. Tell the user which skill to run next.

The skill assumes the user owns the working directory and chooses their layout. It does not impose `data/eval_sets/cycle<N>/` or any other path convention — that is a companion-software detail.

## When to use this skill

Activate on user phrases like:

- "Set up the Clinical ASR Flywheel"
- "Initialize the clinical-asr eval"
- "I want to evaluate ASR on clinical terminology — where do I start?"
- "Bootstrap my environment for the flywheel"
- "What do I need installed before I run the flywheel?"

Do **not** activate when:

- The user already has a manifest and wants to score it → `/clinical-flywheel-eval`
- The user already has the env set up and wants to curate terms → `/clinical-flywheel-build`
- The user is asking about NGC / Docker / NVIDIA Container Toolkit specifically → `/riva-nim-setup`
- The user is asking about generic ASR auth / gRPC plumbing → `/riva-asr`

## Prerequisites

| Requirement | Why | How |
|---|---|---|
| `NVIDIA_API_KEY` (`nvapi-…`) | Hosted Magpie TTS + Parakeet/Nemotron ASR via NVCF | Issue at <https://build.nvidia.com>; `export NVIDIA_API_KEY=...` in shell |
| Python ≥ 3.10 | NeMo client, scoring, manifest tools | `python3 --version` |
| `nvidia-riva-client`, `pandas`, `soundfile` | TTS + ASR clients and manifest I/O | `pip install nvidia-riva-client pandas soundfile` |
| Optional: `jiwer` | Reference WER/CER scoring against your own implementation | `pip install jiwer` |
| Six upstream skills installed | This skill *composes*; it doesn't reimplement | See **1c** below |
| (Stage 4 only) CUDA host + NeMo container | Fine-tune workload | Covered in `/clinical-flywheel-finetune` prerequisites — out of scope here |

## Instructions

### 1a. Verify `NVIDIA_API_KEY` (length-only — never echo the value)

```bash
# Export NVIDIA_API_KEY in your shell — never echo or commit the value
export NVIDIA_API_KEY=nvapi-...     # from https://build.nvidia.com

# Length-only check; the key value never appears in any log
test -n "$NVIDIA_API_KEY" && echo "NVIDIA_API_KEY len=${#NVIDIA_API_KEY}"
```

A length of 70+ is normal. If the output is empty or shows `len=0`, the user must paste a key from <https://build.nvidia.com>. Do **not** print the key, even truncated. To persist across shell sessions, add the `export` line to your shell rc (`~/.bashrc`, `~/.zshrc`) — or use a per-directory tool like `direnv`.

### 1b. Install Python dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install nvidia-riva-client pandas soundfile
# optional
pip install jiwer
```

For Stage 4 (fine-tune) only: `nemo-toolkit` and Docker + NVIDIA Container Toolkit are also required. Defer those to `/clinical-flywheel-finetune` — there is no point installing them up front if the user may never reach Stage 4.

### 1c. Confirm upstream skills are installed

This skill is **composition + methodology**. The actual work happens in six upstream skills. Ask the user to invoke each one once and confirm it responds:

| Skill | Owner | Why this flywheel needs it |
|---|---|---|
| `/read-aloud` (or `/riva-tts`) | Riva team | Stage 2 TTS synthesis (Magpie, SSML IPA) |
| `/transcribe-audio` (or `/riva-asr`) | Riva team | Stage 3 ASR transcription |
| `/finetune-asr` | Riva team | Word boosting, LM fusion, generic SFT references |
| `/riva-asr-custom` | Riva team | Stage 4 optional NIM deploy after SFT |
| `/riva-nim-setup` | Riva team | NGC + Docker + Container Toolkit (self-hosted paths only) |
| `/data-designer` | NeMo team | Stage 2 synthetic sentence generation |

If any are missing, point the user at NVCARPS to install before continuing. The flywheel can run with hosted-only paths (no `/riva-nim-setup` needed) but cannot run without `/read-aloud`, `/transcribe-audio`, and `/data-designer`.

A full ownership map — who fixes what, version pinning, contact channels — is in `references/dependency-ownership.md`.

### 1d. Sanity check — round-trip one phrase

Once `NVIDIA_API_KEY` is set and `/read-aloud` + `/transcribe-audio` are confirmed:

> Ask `/read-aloud` to synthesize the single sentence *"The patient was prescribed cefazolin."* Ask `/transcribe-audio` to transcribe the resulting WAV. Echo both texts back. If they match within ~1 token, the flywheel's TTS→ASR loop is intact and the user can advance to Stage 2.

If the round-trip fails: the failure is in *upstream skill territory*, not in this skill. Route to the responsible upstream skill (`/read-aloud` for TTS-side issues, `/transcribe-audio` for ASR-side).

## Examples

**Scenario A — first-time setup, fresh shell.** User: *"I want to start the flywheel."* → Ask for `NVIDIA_API_KEY` presence, run the length check, list the six skills, ask the user to confirm each. On all-green, advise `/clinical-flywheel-build` as the next stop and mention the headline KER framing so the user arrives at Stage 2 with the right metric in mind.

**Scenario B — returning user, partial env.** User: *"I already have the env, just confirm I'm good to go."* → Skip the install steps; run 1a and 1c only. If any of the six skills isn't installed, name it and the upstream registry path.

## Artifacts produced

- `NVIDIA_API_KEY` exported in the user's shell
- An activated virtualenv with the three required libraries
- Confirmation (verbal, in conversation) that the six upstream skills are present

No manifest, audio, or model artifact is produced at this stage — those come at Stages 2–4.

## Troubleshooting

- **Length check shows nothing or `len=0`** → `NVIDIA_API_KEY` isn't exported in this shell. Run `export NVIDIA_API_KEY=nvapi-...` and re-check.
- **Variable is set in one shell but not another** → exports don't persist across sessions. Add the `export` line to your shell rc (`~/.bashrc`, `~/.zshrc`), or use a per-directory loader like `direnv`.
- **Upstream skill doesn't respond when invoked** → it isn't installed. Point the user at NVCARPS; do not try to reimplement here.
- **Round-trip sanity check fails** → identify whether TTS or ASR is broken; route to `/read-aloud` or `/transcribe-audio` respectively. Most reports turn out to be auth (key not exported in this shell) or NVCF rate-limit drops.

For anything not in this list, identify which upstream skill is implicated and route there. See `references/dependency-ownership.md`.

## Limitations

- **Setup only verifies the environment.** It does not validate that the user's specialty / term list / pronunciation overrides make sense — that's the job of `/clinical-flywheel-build`.
- **English-only by default.** Magpie's en-US phoneme inventory drives Stage 2 IPA validation. Other locales require a different upstream phoneme set.
- **Hosted-only paths assumed.** Self-hosted NIMs work but require `/riva-nim-setup` first.

## Companion software

Runnable scripts that implement the whole flywheel live in the (currently internal) **`voice-eval-flywheel`** repo. The skill alone is sufficient to run Stages 1–3 by composing the upstream skills. See `references/dependency-ownership.md` for the boundary between skill-owned and companion-owned responsibilities.

## Next steps

- **Forward:** `/clinical-flywheel-build` — specialty interview, term curation, IPA tagging, NeMo manifest synthesis.
- **Skip ahead** (only if the user already has a NeMo-format manifest with `term` / `entity_category` / `ipa_source` fields): `/clinical-flywheel-eval`.
- **Lateral** for NGC / Docker / Container Toolkit setup: `/riva-nim-setup`.

## References

- [`references/dependency-ownership.md`](references/dependency-ownership.md) — full ownership map, version pinning, contact routing, what this family of skills does **not** own

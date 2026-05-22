# AGENTS.md — NVIDIA Digital Health Examples

This repository hosts **agent skills** for clinical AI workflows from NVIDIA Digital Health. If you are an AI coding assistant (Claude Code, Codex, Cursor, Windsurf, etc.) and this file is loaded, here is what's here and how to use it.

## What's in the repo

Four self-contained agent skills under `.agents/skills/`, all following the [agentskills.io specification](https://agentskills.io/specification):

| Skill slug | Stage | What it does |
|------------|-------|--------------|
| `digital-health-clinical-asr-setup` | 1 | Verifies `NVIDIA_API_KEY`, installs Python deps, sets up NGC + Docker for the NeMo training container, smoke-tests the NVCF stack with Magpie TTS + Parakeet/Nemotron ASR. Hands off to `/digital-health-clinical-asr-build`. |
| `digital-health-clinical-asr-build` | 2 | Specialty interview, term curation, two-tier IPA tagging (Merriam-Webster + Magpie G2P), NeMo-format manifest synthesis. Inlines a complete Magpie TTS NVCF recipe and a Merriam-Webster lookup recipe. Hands off to `/digital-health-clinical-asr-eval`. |
| `digital-health-clinical-asr-eval` | 3 | Transcribes a NeMo manifest via Parakeet/Nemotron ASR, scores WER/CER/KER/SER (pure-Python Levenshtein inline; `jiwer` optional), produces a five-section leaderboard, routes via the post-eval decision tree. Hands off to `/digital-health-clinical-asr-finetune` or back to `/digital-health-clinical-asr-build`. |
| `digital-health-clinical-asr-finetune` | 4 | Stock NeMo SFT on Parakeet TDT v2, term-aware train/val split, offline cycle N+1 re-eval, optional Riva NIM deploy. Returns to `/digital-health-clinical-asr-build` for the next cycle. |

Each skill folder contains `SKILL.md` (workflow guide), optional `references/*.md` (deeper detail loaded on demand), and `evals/evals.json` (trigger / behavior / boundary cases).

## Important property: self-containment

These skills are **fully self-contained**. They inline every recipe an agent needs: Magpie TTS SSML synthesis via `riva.client`, Parakeet ASR via the same SDK, Merriam-Webster Medical Dictionary HTTP lookup, MW-respelling-to-IPA conversion, Magpie phoneme live-probe validation, pure-Python WER/CER/KER/SER scoring, and SSML `<phoneme>`/`<sub>` wrapping rules for IPA overrides.

**You should not need to look outside this repository** to follow them. If a skill names a sibling NVCARPS skill (e.g., `/read-aloud`, `/transcribe-audio`), treat that as historical context, not a hard dependency — the recipe needed is already inlined in the current `SKILL.md`. If you ever find yourself wanting to invoke a sibling skill that isn't installed, generate the code directly from the inlined recipe instead.

## Required environment

Set these before invoking the skills:

| Env var | Used by | Required? |
|---------|---------|-----------|
| `NVIDIA_API_KEY` | All stages (Magpie TTS + Parakeet/Nemotron ASR via NVCF) | **Yes** — get one at [build.nvidia.com](https://build.nvidia.com). Free tier is sufficient for benchmark generation. |
| `DICTIONARY_API_KEY` | `digital-health-clinical-asr-build` (Merriam-Webster lookup) | Optional. If unset, the IPA pipeline falls through to Magpie G2P for un-overridden terms. Free key at [dictionaryapi.com](https://dictionaryapi.com). |
| `NGC_API_KEY` | `digital-health-clinical-asr-finetune` only (pulls NeMo training container) | Optional. Skip if you're only running stages 1–3. |

## How to invoke (Claude Code example)

```bash
git clone -b main https://github.com/NVIDIA/digital-health-skills.git
cd digital-health-skills

# Optional: symlink the skills into Claude Code's skills dir if your launcher
# doesn't auto-discover .agents/skills/ from the working directory.
mkdir -p ~/.claude/skills
ln -s "$(pwd)/skills/digital-health-clinical-asr-setup"    ~/.claude/skills/
ln -s "$(pwd)/skills/digital-health-clinical-asr-build"    ~/.claude/skills/
ln -s "$(pwd)/skills/digital-health-clinical-asr-eval"     ~/.claude/skills/
ln -s "$(pwd)/skills/digital-health-clinical-asr-finetune" ~/.claude/skills/

# Then in your agent session:
/digital-health-clinical-asr-setup
```

Skills hand off explicitly. Start with `/digital-health-clinical-asr-setup`; each stage tells you which skill comes next.

## When NOT to use these skills

- Generic ASR work (no clinical vocabulary) → use upstream ASR skills directly, not these
- TTS quality work without a benchmarking goal → use a TTS-specific skill
- Single-pass transcription with no eval → use a basic ASR skill, not the flywheel
- Non-English clinical ASR → these skills target English (Magpie en-US phoneme set); other locales need a different upstream phoneme set

## License + security

- License: Apache 2.0 (see `LICENSE`).
- Security disclosure: see `SECURITY.md` — never file security issues as public GitHub issues.
- Contributions: see `CONTRIBUTING.md` — DCO sign-off required on every commit.

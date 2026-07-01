# NVIDIA Digital Health Examples

Agent skills and worked examples for healthcare AI workflows from NVIDIA Digital Health.

This repository hosts **agent skills** — markdown-based workflow guides consumable by AI coding assistants (Claude Code, Cursor, GitHub Copilot, and any client that supports the [agentskills.io specification](https://agentskills.io/specification)).

The skills cover a **clinical ASR (automatic speech recognition) evaluation workflow**: term curation, synthetic clinical-speech benchmark generation, KER (Keyword Error Rate) / entity-level scoring, and fine-tune guidance; the skills also cover a custom ambient healthcare voice-agent creation.

These skills are **agent workflow guides**. Some are docs-only runbooks; others include bundled references, scripts, or templates that an agent reads while generating or validating files in the user's own environment. They may require NVIDIA APIs, NIMs at `build.nvidia.com`, NeMo or Riva containers, Docker, or local project files depending on the workflow.

## Skills in this repo

| Skill | Area | What it guides |
|-------|------|----------------|
| [`digital-health-clinical-asr-setup`](skills/digital-health-clinical-asr-setup/) | Clinical ASR flywheel Stage 1| Verify `NVIDIA_API_KEY`, install Python deps, set up NGC + Docker for the NeMo training container, smoke-test the NVCF stack with Magpie TTS + Parakeet/Nemotron ASR. |
| [`digital-health-clinical-asr-build`](skills/digital-health-clinical-asr-build/) | Clinical ASR flywheel Stage 2| Specialty interview, term curation, two-tier IPA tagging, NeMo-format manifest synthesis. Inlines a Magpie TTS NVCF recipe. |
| [`digital-health-clinical-asr-eval`](skills/digital-health-clinical-asr-eval/) | Clinical ASR flywheel Stage 3| Transcribe a NeMo manifest via Parakeet/Nemotron ASR, score WER/CER/KER/SER, produce a five-section leaderboard, route via the post-eval decision tree. |
| [`digital-health-clinical-asr-finetune`](skills/digital-health-clinical-asr-finetune/) | Clinical ASR flywheel Stage 4| Stock NeMo SFT on Parakeet TDT v2, term-aware train/val split, offline cycle N+1 re-eval, optional Riva NIM deploy. |
| [`digital-health-create-your-own-ambient-agent`](skills/digital-health-create-your-own-ambient-agent/) | Ambient healthcare agents | Build a custom ambient healthcare voice-agent repo with Nemotron Voice Agent, a FastAPI `/v1/chat/completions` backend, LangGraph tools, Docker Compose, and optional NeMo Guardrails through a spec-driven workflow. |

Each skill folder contains `SKILL.md` (workflow guide), optional `references/*.md` (deeper detail loa
ded on demand), optional `scripts/`, and `evals/evals.json` (trigger / behavior / boundary cases).

## Getting started

Skills are loaded by your agent's skill loader. For Claude Code:

```bash
git clone git@github.com:NVIDIA/digital-health-skills.git
cd digital-health-skills

# Either symlink or copy the skill folders you need into your Claude Code skills dir:
mkdir -p ~/.claude/skills
ln -s "$(pwd)/skills/digital-health-clinical-asr-setup"    ~/.claude/skills/
ln -s "$(pwd)/skills/digital-health-clinical-asr-build"    ~/.claude/skills/
ln -s "$(pwd)/skills/digital-health-clinical-asr-eval"     ~/.claude/skills/
ln -s "$(pwd)/skills/digital-health-clinical-asr-finetune" ~/.claude/skills/
ln -s "$(pwd)/skills/digital-health-create-your-own-ambient-agent" ~/.claude/skills/
```

Then invoke the skill you need from your agent, for example:

- `/digital-health-clinical-asr-setup` to start the clinical ASR flywheel. Then `/digital-health-clinical-asr-build`, `/digital-health-clinical-asr-eval`, `/digital-health-clinical-asr-finetune`.
- `/digital-health-create-your-own-ambient-agent` to scaffold a custom ambient healthcare voice agent.


## Requirements

Requirements vary by skill. Common dependencies include:

- An `NVIDIA_API_KEY` from [build.nvidia.com](https://build.nvidia.com) for hosted NVIDIA NIMs such as Magpie TTS, Parakeet/Nemotron ASR, Nemotron LLMs, and safety models. (free tier is sufficient)
- An `NGC_API_KEY` from [ngc.nvidia.com](https://ngc.nvidia.com) when pulling NVIDIA containers for self-hosted Riva, NeMo, or fine-tuning workflows such as `digital-health-clinical-asr-finetune`.
- Python 3.10+ for local scripts and generated backend projects.
- Docker for containerized Riva, NeMo, Nemotron Voice Agent, and generated ambient-agent stacks.
- A CUDA host with the NeMo container (`nvcr.io/nvidia/nemo:25.11.01`) for `digital-health-clinical-asr-finetune` Stage 4. Brev cloud GPUs supported.
## Support

- **Level:** Experimental — the skills are new and evolving; expect rough edges.
- **Issues:** Use this repository's [Issues](../../issues) for bug reports and feature requests. Do **not** file security issues there (see `SECURITY.md`).

## Contributing

This is a reference samples repo maintained by the NVIDIA Digital Health team — **external pull requests are not accepted**. See [CONTRIBUTING.md](CONTRIBUTING.md) for the full policy and what to do if you found a bug (open an [Issue](../../issues)) or want to adapt the skills for your own use (fork under the Apache 2.0 license).

## Security

See [SECURITY.md](SECURITY.md) for the NVIDIA vulnerability disclosure process. Report security issues to `psirt@nvidia.com`, not via GitHub.

## License

Apache License 2.0 — see [LICENSE](LICENSE).

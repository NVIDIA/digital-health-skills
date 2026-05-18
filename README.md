# NVIDIA Digital Health Examples

Agent skills and worked examples for healthcare AI workflows from NVIDIA Digital Health.

This repository hosts **agent skills** — markdown-based workflow guides consumable by AI coding assistants (Claude Code, Cursor, GitHub Copilot, and any client that supports the [agentskills.io specification](https://agentskills.io/specification)).

The first set covers a **clinical ASR (automatic speech recognition) evaluation workflow**: term curation, synthetic clinical-speech benchmark generation, KER (Keyword Error Rate) / entity-level scoring, and fine-tune guidance.

These skills are **docs-only workflow guides**. They do not ship companion runtime code; an agent following them will use the user's own environment and any required NVIDIA APIs (NIMs at `build.nvidia.com`, NeMo containers, etc.).

## Skills in this repo

| Skill | Stage | What it guides |
|-------|-------|----------------|
| [`clinical-flywheel-setup`](.agents/skills/clinical-flywheel-setup/) | 1 | Verify `NVIDIA_API_KEY`, install Python deps, set up NGC + Docker for the NeMo training container, smoke-test the NVCF stack with Magpie TTS + Parakeet/Nemotron ASR. |
| [`clinical-flywheel-build`](.agents/skills/clinical-flywheel-build/) | 2 | Specialty interview, term curation, two-tier IPA tagging, NeMo-format manifest synthesis. Inlines a Magpie TTS NVCF recipe. |
| [`clinical-flywheel-eval`](.agents/skills/clinical-flywheel-eval/) | 3 | Transcribe a NeMo manifest via Parakeet/Nemotron ASR, score WER/CER/KER/SER, produce a five-section leaderboard, route via the post-eval decision tree. |
| [`clinical-flywheel-finetune`](.agents/skills/clinical-flywheel-finetune/) | 4 | Stock NeMo SFT on Parakeet TDT v2, term-aware train/val split, offline cycle N+1 re-eval, optional Riva NIM deploy. |

Each skill folder contains `SKILL.md` (the workflow guide), optional `references/*.md` (deeper detail loaded on demand), and `evals/evals.json` (trigger / behavior / boundary test cases).

## Getting started

Skills are loaded by your agent's skill loader. For Claude Code:

```bash
git clone git@github.com:NVIDIA/digital-health-examples.git
cd digital-health-examples

# Either symlink or copy the four skill folders into your Claude Code skills dir:
mkdir -p ~/.claude/skills
ln -s "$(pwd)/.agents/skills/clinical-flywheel-setup"    ~/.claude/skills/
ln -s "$(pwd)/.agents/skills/clinical-flywheel-build"    ~/.claude/skills/
ln -s "$(pwd)/.agents/skills/clinical-flywheel-eval"     ~/.claude/skills/
ln -s "$(pwd)/.agents/skills/clinical-flywheel-finetune" ~/.claude/skills/
```

Then invoke them from your agent: `/clinical-flywheel-setup`, `/clinical-flywheel-build`, `/clinical-flywheel-eval`, `/clinical-flywheel-finetune`.

The skills walk the agent through each stage and hand off to the next. Start with `/clinical-flywheel-setup`.

## Requirements

To use the skills end-to-end you will need:

- An `NVIDIA_API_KEY` from [build.nvidia.com](https://build.nvidia.com) — for hosted Magpie TTS + Parakeet/Nemotron ASR via NVCF (free tier is sufficient).
- An `NGC_API_KEY` from [ngc.nvidia.com](https://ngc.nvidia.com) — only needed for Stage 4 (fine-tune), to pull the NeMo training container.
- Python 3.10+ for client-side scripting (the agent installs deps via your skill of choice).
- A CUDA host with the NeMo container (`nvcr.io/nvidia/nemo:25.11.01`) for Stage 4. Brev cloud GPUs supported.

## Support

- **Level:** Experimental — the skills are new and evolving; expect rough edges.
- **Issues:** Use this repository's [Issues](../../issues) for bug reports and feature requests. Do **not** file security issues there (see `SECURITY.md`).

## Contributing

PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md). All contributions require DCO sign-off (`git commit -s`).

## Security

See [SECURITY.md](SECURITY.md) for the NVIDIA vulnerability disclosure process. Report security issues to `psirt@nvidia.com`, not via GitHub.

## License

Apache License 2.0 — see [LICENSE](LICENSE).

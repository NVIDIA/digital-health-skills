# Contributing to NVIDIA Digital Health Examples

Thanks for your interest. This repository hosts agent skills for clinical/healthcare AI workflows.

## What lives here

- `.agents/skills/<skill-name>/` — agent skills following the [agentskills.io specification](https://agentskills.io/specification). Each skill is a self-contained workflow guide in markdown (`SKILL.md`), optional `references/*.md`, and `evals/evals.json`.
- Repo-level docs: `README.md`, `LICENSE`, `SECURITY.md`, this file.

This repo does not host runtime code. Skills guide an agent through a workflow; the agent uses the user's own environment to do the work.

## Adding or modifying a skill

1. **Pick a name.** Use kebab-case, prefix by domain (e.g., `clinical-asr-*`, `radiology-*`). The directory name must equal the `name` field in `SKILL.md` frontmatter.
2. **Write or edit `SKILL.md`.** Keep it under 500 lines. Move long content into `references/*.md` and link from `SKILL.md`. Required frontmatter fields: `name`, `description`, `version`, `tags`, `license`.
3. **Author or update `evals/evals.json`.** Cover the three classes of cases:
   - **Trigger** — phrases that should activate the skill
   - **Behavior** — expected agent behavior when invoked
   - **Boundary** — phrases that should *not* activate the skill (so the skill stays in lane)
4. **Verify locally.**
   - Frontmatter is well-formed YAML
   - No secrets, internal URLs, absolute user paths, or PHI in any file
   - `SKILL.md` reads cleanly as a workflow guide (not as software)
5. **Commit with DCO sign-off.** This is mandatory.
   ```bash
   git commit -s -m "feat(skill-name): short description"
   ```
   The `-s` flag adds the `Signed-off-by` trailer required by the [Developer Certificate of Origin](https://developercertificate.org/).

## Pull request flow

1. Fork the repo (or branch off `main` if you have write access).
2. Make changes on a feature branch named `feature/<skill-name>` or `fix/<short-desc>`.
3. Open a PR against `main`. Include in the description:
   - What the skill does (or what changed)
   - Trigger phrases the skill responds to
   - Any external NVIDIA APIs the skill expects (NIM endpoint, container image, etc.)
4. CI checks must pass before merge.

## Style guidelines

- **Be honest about scope.** If a skill guides a workflow but doesn't ship runtime, say so explicitly in the skill description.
- **Don't claim companion software exists publicly if it doesn't.** Reference internal NVIDIA repos only when an external user can reasonably access them.
- **Pin versions where it matters.** Container tags, model names, API versions — exact strings, not "latest".
- **Defer to other public skills.** If another skill in this repo or the broader [NVIDIA/skills](https://github.com/NVIDIA/skills) catalog already handles a sub-task, reference it instead of duplicating.

## License

By contributing, you license your contribution under [Apache License 2.0](LICENSE) and certify the DCO. For substantial third-party content, please open an issue first to discuss licensing review.

## Security

Do not file security issues here. See [SECURITY.md](SECURITY.md) for the NVIDIA vulnerability disclosure process.

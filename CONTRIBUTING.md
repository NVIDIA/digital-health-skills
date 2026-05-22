# Contributing

This repository is a **reference samples repository** maintained by the NVIDIA Digital Health team. **It is not open to external contributions** — pull requests from outside the maintaining team will not be reviewed or merged.

## If you want to use these skills

- Clone or fork the repo and follow [README.md](README.md). The install path (symlinking from `skills/` into your agent's skills directory) is documented there.
- Fork and adapt the skills for your own purposes under the [Apache License 2.0](LICENSE).

## Reporting bugs and stale content

[Issues](../../issues) are open for bug reports — a stale NVCF function ID, a broken install command, a recipe that no longer runs on a current `nvidia-riva-client`, etc. The maintainers triage as time allows; this is a samples repo, not a supported product, so there is no SLA.

## Security

Do **not** file security issues via GitHub Issues. See [SECURITY.md](SECURITY.md) for the NVIDIA vulnerability disclosure process — report to `psirt@nvidia.com`.

---

## For maintainers (NVIDIA Digital Health team)

### Workflow

- Branch-and-MR on this repo against `main`.
- Commits signed off with `git commit -s` per the [Developer Certificate of Origin](https://developercertificate.org/).
- Branch naming: `feature/<short-desc>`, `fix/<short-desc>`, or `release/<topic>` for grouped work.

### Adding or modifying a skill

1. **Pick a name.** Use kebab-case, prefix by domain (e.g., `digital-health-clinical-asr-*`, `radiology-*`). The directory name must equal the `name` field in `SKILL.md` frontmatter.
2. **Write or edit `SKILL.md`.** Keep it under 500 lines. Move long content into `references/*.md` and link from `SKILL.md`. Required frontmatter fields: `name`, `description`, `version`, `tags`, `license`.
3. **Author or update `evals/evals.json`.** Cover the three classes of cases:
   - **Trigger** — phrases that should activate the skill
   - **Behavior** — expected agent behavior when invoked
   - **Boundary** — phrases that should *not* activate the skill
4. **Verify locally.**
   - Frontmatter is well-formed YAML
   - No secrets, internal URLs, absolute user paths, or PHI in any file
   - `SKILL.md` reads cleanly as a workflow guide (not as software)
   - If you touch any skill content, mirror the change is unnecessary — the canonical location is `skills/` only; there is no `.claude/skills/` duplicate in this repo (end users symlink themselves; see README).

### Style guidelines

- **Be honest about scope.** If a skill guides a workflow but doesn't ship runtime, say so explicitly in the skill description.
- **Don't claim companion software exists publicly if it doesn't.** Reference internal NVIDIA repos only when a reader of this repo can reasonably access them. If in doubt, drop the reference and inline the recipe.
- **Pin versions where it matters.** Container tags, model names, NVCF function IDs, API versions — exact strings, not "latest".
- **Defer to other public skills.** If another skill in this repo or the broader [NVIDIA/skills](https://github.com/NVIDIA/skills) catalog already handles a sub-task, reference it instead of duplicating.

### Signing Your Work

- We require that all contributors "sign-off" on their commits. This certifies that the contribution is your original work, or you have rights to submit it under the same license, or a compatible license.
  - Any contribution which contains commits that are not Signed-Off will not be accepted.
- To sign off on a commit you simply use the `--signoff` (or `-s`) option when committing your changes:
  ```bash
  $ git commit -s -m "Add cool feature."
  ```
  This will append the following to your commit message:
  ```
  Signed-off-by: Your Name <your@email.com>
  ```
- Full text of the DCO (https://developercertificate.org/):
  ```
    Developer Certificate of Origin
    Version 1.1

    Copyright (C) 2004, 2006 The Linux Foundation and its contributors.

    Everyone is permitted to copy and distribute verbatim copies of this
    license document, but changing it is not allowed.


    Developer's Certificate of Origin 1.1

    By making a contribution to this project, I certify that:

    (a) The contribution was created in whole or in part by me and I
        have the right to submit it under the open source license
        indicated in the file; or

    (b) The contribution is based upon previous work that, to the best
        of my knowledge, is covered under an appropriate open source
        license and I have the right under that license to submit that
        work with modifications, whether created in whole or in part
        by me, under the same open source license (unless I am
        permitted to submit under a different license), as indicated
        in the file; or

    (c) The contribution was provided directly to me by some other
        person who certified (a), (b) or (c) and I have not modified
        it.

    (d) I understand and agree that this project and the contribution
        are public and that a record of the contribution (including all
        personal information I submit with it, including my sign-off) is
        maintained indefinitely and may be redistributed consistent with
        this project or the open source license(s) involved.
  ```

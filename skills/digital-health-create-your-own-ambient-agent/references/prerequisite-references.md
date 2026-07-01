# Prerequisite References

Use this reference for Phase 1. It covers cloning required source repos,
verifying dependent sub-skills, optional symlinking for future sessions, and the
summary to show before Phase 2.

## Contents

- Step 1: Prerequisite References and Skill Dependencies
- 1a: Inform and get confirmation
- 1b: Check what is already present
- 1c: Clone source repos into `references/`
- 1d: Verify and optionally install sub-skills
- 1e: Confirm and summarise

## Step 1: Prerequisite References and Skill Dependencies

**Run this before any other phase.** This skill depends on sub-skills and
reference content sourced from three GitHub repos. The prerequisite references
step is a hard prerequisite: do not proceed to Phase 2 until the five dependent
sub-skills are installed or directly readable for the active coding agent, and
the reference repos are cloned.

1. All source repos are cloned into the `references/` directory alongside this
   `SKILL.md`. This is the permanent location any agent can read from directly.
2. The LangChain and Nemotron sub-skill files are verified from the cloned
   reference repos. When possible, symlink them into the active coding-agent
   skill directory (`~/.claude/skills/` for Claude Code, `~/.codex/skills/` for
   Codex) for future sessions. This symlink step is optional for the current
   session: if the skills directory is not writable or newly linked skills are
   not discoverable until restart, continue by reading the cloned `SKILL.md`
   files directly before using each domain.

### 1a — Inform and get confirmation

Tell the developer:

> "This skill depends on sub-skills and reference content sourced from three
> GitHub repos:
>
> | Sub-skill | Purpose | Used when |
> |---|---|---|
> | `langgraph-fundamentals` | StateGraph, nodes, edges, streaming patterns | Always |
> | `langchain-fundamentals` | `create_react_agent`, `@tool` decorator usage | Always |
> | `langchain-dependencies` | Correct package versions and known incompatibilities | Always |
> | `langchain-rag` | NVIDIA RAG data-retrieval tools | Always |
> | `nemotron-voice-agent-deploy` | Docker Compose config, health checks, hardware targets | Always |
> | `nemoguardrails` | Colang syntax, `RunnableRails` integration, and rail type configuration | Only if guardrails enabled in Phase 2(f) |
>
> All three repos will be fully cloned with recursive submodules into
> `references/`. The five dependent sub-skill `SKILL.md` files will be verified
> from the cloned `references/` paths. When possible, the skill will also
> symlink those sub-skills into the active coding-agent skill directory for
> future sessions (`~/.claude/skills/` for Claude Code, `~/.codex/skills/` for
> Codex). The current session can continue from the cloned reference files even
> if that optional symlink step is skipped or fails. The NeMo Guardrails repo is
> read directly from `references/` by all agents. Anything already present will
> be skipped.
>
> Do you want to proceed? (yes / no)"

**Wait for explicit confirmation before continuing.**
If the developer says no, stop and do not proceed with any installation or with
Phase 2.

### 1b — Check what is already present

Tell the developer:

> "Checking what is already in `references/`…"

```bash
ls references/reference-repos/ 2>/dev/null || echo "(references/reference-repos/ does not exist yet)"
```

Report the output. The three repos needed are:

| Directory | Source |
|---|---|
| `references/reference-repos/langchain-skills/` | github.com/langchain-ai/langchain-skills |
| `references/reference-repos/nemotron-voice-agent/` | github.com/NVIDIA-AI-Blueprints/nemotron-voice-agent |
| `references/reference-repos/nemo-guardrails/` | github.com/NVIDIA/NeMo-Guardrails |

If all three are already present, skip to Step 1d. Otherwise continue.

### 1c — Clone source repos into `references/`

Tell the developer:

> "Cloning source repos into `references/` with full history and recursive
> submodules. These stay permanently so any agent can read the sub-skill content
> directly."

```bash
mkdir -p references/reference-repos

if [ ! -d "references/reference-repos/langchain-skills" ]; then
    echo "Cloning langchain-ai/langchain-skills with recursive submodules..."
    git clone --recurse-submodules \
        https://github.com/langchain-ai/langchain-skills \
        references/reference-repos/langchain-skills \
        && echo "✓ langchain-skills cloned  →  references/reference-repos/langchain-skills" \
        || { echo "✗ Failed to clone langchain-skills"; exit 1; }
else
    echo "⚠ Skipping langchain-skills — references/reference-repos/langchain-skills already exists"
fi

if [ ! -d "references/reference-repos/nemotron-voice-agent" ]; then
    echo "Cloning NVIDIA-AI-Blueprints/nemotron-voice-agent (with submodules)..."
    git clone --recurse-submodules \
        https://github.com/NVIDIA-AI-Blueprints/nemotron-voice-agent \
        references/reference-repos/nemotron-voice-agent \
        && echo "✓ nemotron-voice-agent cloned  →  references/reference-repos/nemotron-voice-agent" \
        || { echo "✗ Failed to clone nemotron-voice-agent"; exit 1; }
else
    echo "⚠ Skipping nemotron-voice-agent — references/reference-repos/nemotron-voice-agent already exists"
fi

if [ ! -d "references/reference-repos/nemo-guardrails" ]; then
    echo "Cloning NVIDIA/NeMo-Guardrails with recursive submodules..."
    git clone --recurse-submodules \
        https://github.com/NVIDIA/NeMo-Guardrails \
        references/reference-repos/nemo-guardrails \
        && echo "✓ nemo-guardrails cloned  →  references/reference-repos/nemo-guardrails" \
        || { echo "✗ Failed to clone NeMo-Guardrails"; exit 1; }
else
    echo "⚠ Skipping nemo-guardrails — references/reference-repos/nemo-guardrails already exists"
fi
```

If any clone fails, stop and report the error to the developer. Do not continue.

### 1d — Verify and optionally install sub-skills

Tell the developer:

> "Verifying sub-skill reference files and optionally symlinking them for future
> coding-agent sessions. This session can continue as long as the cloned
> `SKILL.md` files are readable."

```bash
set -e
NEW_INSTALLS=0
INSTALL_WARNINGS=0

TARGET_SKILL_DIRS=()
if [ -d "$HOME/.claude" ]; then
    TARGET_SKILL_DIRS+=("$HOME/.claude/skills")
fi
if [ -d "$HOME/.codex" ]; then
    TARGET_SKILL_DIRS+=("$HOME/.codex/skills")
fi
if [ "${#TARGET_SKILL_DIRS[@]}" -eq 0 ]; then
    INSTALL_WARNINGS=1
    echo "  ⚠ No known agent home detected; skipping optional skill-directory symlinks"
fi

install_skill() {
    local name="$1"
    local src="$2"
    if [ ! -d "$src" ] || [ ! -f "$src/SKILL.md" ]; then
        echo "  ✗ $name not found at $src"
        exit 1
    fi
    local src_abs
    src_abs="$(cd "$src" && pwd)"
    echo "  ✓ Verified readable source for $name  →  $src/SKILL.md"
    for skill_dir in "${TARGET_SKILL_DIRS[@]}"; do
        if ! mkdir -p "$skill_dir" 2>/dev/null; then
            INSTALL_WARNINGS=1
            echo "  ⚠ Could not create $skill_dir; continuing with readable source for $name"
            continue
        fi
        local dst="$skill_dir/$name"
        if [ -e "$dst" ] || [ -L "$dst" ]; then
            echo "  ⚠ Skipping $name — already present at $dst"
        else
            if ln -s "$src_abs" "$dst"; then
                NEW_INSTALLS=1
                echo "  ✓ Symlinked $name  →  $dst"
            else
                INSTALL_WARNINGS=1
                echo "  ⚠ Could not symlink $name to $dst; continuing with readable source"
            fi
        fi
    done
}

for skill in langgraph-fundamentals langchain-fundamentals langchain-dependencies langchain-rag; do
    SRC="references/reference-repos/langchain-skills/config/skills/$skill"
    install_skill "$skill" "$SRC"
done

NEMOTRON_SRC="references/reference-repos/nemotron-voice-agent/.agents/skills/nemotron-voice-agent-deploy"
install_skill "nemotron-voice-agent-deploy" "$NEMOTRON_SRC"

echo "SUBSKILL_REFERENCES_READY=true"
if [ "$NEW_INSTALLS" -eq 1 ]; then
    echo "SUBSKILLS_SYMLINKED_FOR_FUTURE_SESSION=true"
else
    echo "SUBSKILLS_ALREADY_PRESENT_OR_REFERENCE_ONLY=true"
fi
if [ "$INSTALL_WARNINGS" -eq 1 ]; then
    echo "SUBSKILL_OPTIONAL_INSTALL_WARNINGS=true"
fi
echo "CURRENT_SESSION_USES_REFERENCE_SKILLS=true"
```

Report every `✓` and `⚠` line to the developer as it runs.
If any `✗` line appears, stop and report the error. Do not continue to Phase 2.
If optional symlinking fails or the script prints
`SUBSKILL_OPTIONAL_INSTALL_WARNINGS=true`, prompt the developer:

> "Optional standalone sub-skill installation was not successful. You can install
> or symlink the sub-skills into `~/.claude/skills/` or `~/.codex/skills/` and
> start a new coding-agent session if you want to use them as standalone skills.
> Otherwise, I can proceed in this session by reading the verified reference
> `SKILL.md` files directly. Do you want to stop here to install and restart, or
> proceed with references?"

Wait for the developer's answer. If they choose to stop, stop the workflow. If
they choose to proceed, continue to Phase 2 using the verified reference
`SKILL.md` files.
If the script prints `SUBSKILLS_SYMLINKED_FOR_FUTURE_SESSION=true`, tell the
developer that the symlinked sub-skills may require a future coding-agent
session restart before they appear as standalone skills, but this workflow does
not need to stop because the cloned reference files are already readable.

### 1e — Confirm and summarise

Tell the developer a structured summary of everything that happened in this
prerequisite references step. Report actual results — distinguish newly
cloned/installed from already-present.

End the summary with "Ready to begin Phase 2." Use this format:

> "Prerequisite references complete. Here is what was set up:
>
> **Cloned into `references/reference-repos/`**
>
> | Repo | Source | Status |
> |---|---|---|
> | `langchain-skills/` | github.com/langchain-ai/langchain-skills | ✓ Cloned / ⚠ Already present |
> | `nemotron-voice-agent/` | github.com/NVIDIA-AI-Blueprints/nemotron-voice-agent | ✓ Cloned / ⚠ Already present |
> | `nemo-guardrails/` | github.com/NVIDIA/NeMo-Guardrails | ✓ Cloned / ⚠ Already present |
>
> **Sub-skill sources verified and optionally symlinked**
>
> | Sub-skill | Source path | Status |
> |---|---|---|
> | `langgraph-fundamentals` | `references/reference-repos/langchain-skills/config/skills/langgraph-fundamentals/` | ✓ Source verified; ✓ Symlinked / ⚠ Already present / ⚠ Symlink skipped |
> | `langchain-fundamentals` | `references/reference-repos/langchain-skills/config/skills/langchain-fundamentals/` | ✓ Source verified; ✓ Symlinked / ⚠ Already present / ⚠ Symlink skipped |
> | `langchain-dependencies` | `references/reference-repos/langchain-skills/config/skills/langchain-dependencies/` | ✓ Source verified; ✓ Symlinked / ⚠ Already present / ⚠ Symlink skipped |
> | `langchain-rag` | `references/reference-repos/langchain-skills/config/skills/langchain-rag/` | ✓ Source verified; ✓ Symlinked / ⚠ Already present / ⚠ Symlink skipped |
> | `nemotron-voice-agent-deploy` | `references/reference-repos/nemotron-voice-agent/.agents/skills/nemotron-voice-agent-deploy/` | ✓ Source verified; ✓ Symlinked / ⚠ Already present / ⚠ Symlink skipped |
>
> **Note:** `nemoguardrails` (the reference repo `nemo-guardrails/`) is not
> installed as a local sub-skill — all agents read it directly from
> `references/reference-repos/nemo-guardrails/`. It will only be used if
> guardrails are enabled in Phase 2(f).
>
> Sub-skills symlinked into `~/.claude/skills/` or `~/.codex/skills/` are for
> future sessions and may not be discoverable as standalone skills until the
> coding agent restarts. This session will use the verified reference `SKILL.md`
> files directly.
>
> All reference content is readable under `references/reference-repos/`. Ready to begin Phase 2."

**Do not proceed to Phase 2 until the `references/reference-repos/` clones are
confirmed present and all five dependent sub-skill `SKILL.md` files are
readable from the cloned references. Direct installation into the coding-agent
skills directory is not required for this session.**

---

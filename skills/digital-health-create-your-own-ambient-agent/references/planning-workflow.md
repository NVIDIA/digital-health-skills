# Planning Workflow

Use this reference for Phase 3. It covers deriving `plan.md` and `tasks.md` from
approved feature specs and enforcing approval before implementation.

## Phase 3: Derive the Plan

For each selected feature, write `plan.md` then `tasks.md` interactively —
present each file and wait for approval before writing the next. The selected
features are always `langgraph-agent` and `fastapi-server`, plus `guardrails`
when Phase 2(f) enabled it. Repeat the loop for every selected feature before
proceeding to implementation.

### Per-feature loop (repeat for `langgraph-agent`, `fastapi-server`, and `guardrails` if enabled)

**Step 1 — Write `plan.md`**

Derive `specs/<feature>/plan.md` from the approved `spec.md`. Use the
corresponding example in this skill's `references/spec-examples/` as the
structural model.

`plan.md` must cover:
1. **Technical Context** — language, primary dependencies, testing framework,
   performance goals, constraints
2. **Project structure** — directory tree of the files this feature creates
3. **Key design decisions** — patterns chosen and why (e.g. singleton graph,
   shell-form `CMD` for env var expansion at runtime)
4. **API contracts** — request/response schemas for any HTTP interface
5. **Reference files** — which files in `references/` to copy and how to adapt them

Present the plan and ask:

> "Here is `specs/<feature>/plan.md` — the technical plan for how we will build
> this feature. It describes the stack, architecture, and key decisions derived
> from the approved spec. Does this approach look right to you?"

**Wait for explicit approval before writing `tasks.md`.**

---

**Step 2 — Write `tasks.md`**

Derive `specs/<feature>/tasks.md` from the approved `plan.md`. Use the
corresponding example in this skill's `references/spec-examples/` as the
structural model.

`tasks.md` must cover (YAML frontmatter + phased task list):
1. **Phase 1 — Setup**: directory creation, dependency declarations
2. **Phase 2 — Foundational / Implementation**: the core feature work; mark `[P]`
   on tasks that touch independent files and have no mutual dependency; mark
   `[US1]` etc. to link each task to its spec user story
3. **Phase N — Validation**: end-to-end verification steps
4. **Dependencies section**: explicit blocking relationships between phases

Present the task list and ask:

> "Here is `specs/<feature>/tasks.md` — the ordered task list for this feature.
> Tasks marked `[P]` can run in parallel. Each task references the user story it
> satisfies. Does this look complete?"

**Wait for explicit approval before moving to the next feature or to Phase 4.**

---

**Do not proceed to Phase 4 until every selected feature has approved `spec.md`,
`plan.md`, and `tasks.md` files.**

---

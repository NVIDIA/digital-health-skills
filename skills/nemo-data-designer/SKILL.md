---
name: nemo-data-designer
license: "Apache-2.0"
description: "Use when generating synthetic tabular datasets via Data Designer — sampler columns, LLM columns, custom generators. Not for ASR audio."
argument-hint: [describe the dataset you want to generate]
metadata:
  author: "Voice Eval Flywheel team <brandoing@nvidia.com>"
  tags:
    - nvidia
    - data-designer
    - synthetic-data
    - dataset-generation
    - llm
    - sampler
---

## Purpose

Produce a synthetic tabular dataset by authoring a NeMo Data Designer config (`data_designer.config`), previewing the output, then committing to a full run. The agent first picks a conversation mode (Interactive vs. Autopilot), drives the user through config construction, and ends at a written-to-disk dataset.

## Instructions

The flow is five steps, in order:

1. Decide on **conversation mode**. Default is Interactive — ask the user clarifying questions as you build. Switch to Autopilot whenever the user signals they want an opinionated build with minimal back-and-forth ("just build it", "you decide", "surprise me").
2. Open the matching per-mode runbook — `workflows/interactive.md` or `workflows/autopilot.md` — and follow it. The runbooks are the source of truth for which questions to ask and what defaults to pick.
3. Author a Python config module exposing `load_config_builder()` that returns a `DataDesignerConfigBuilder`. The Output Template section near the end of this file shows the skeleton (PEP 723 deps header + samplers + LLM columns + optional Pydantic schema + custom generators).
4. Preview before generating: run `data-designer preview` against the config and show the user the sample rows.
5. After approval, run `data-designer run` (the `run_script` entry point) for the full generation. If the dataset references person attributes, first inspect the person-object schema via `python3 scripts/get_person_object_schema.py`.

## Examples

Worked example dialogues live in the per-mode runbooks; the SKILL.md doesn't duplicate them:

- For a question-driven build with full user collaboration → `workflows/interactive.md`.
- For a hands-off "you decide" build → `workflows/autopilot.md`.

A representative Python config — sampler column + LLM column + Pydantic-typed output + custom column generator — is laid out in the Output Template section further down.

## Scripts

| Script | Purpose |
|---|---|
| `scripts/get_person_object_schema.py` | Inspect the Data Designer person-object field schema (names, demographics, addresses) before adding person-sampler columns to a config. Invoke via `python3 scripts/get_person_object_schema.py`. |

## Prerequisites

- A Python ≥ 3.10 virtualenv (Data Designer requires it).
- The `data-designer` package itself — install via `pip install data-designer`.
- If the config you build references LLM columns or LLM judges, the user must have valid LLM credentials configured per Data Designer's own auth conventions.
- `pydantic` is only needed when the config declares structured outputs; the PEP 723 header in the generated script will fetch it automatically.

## Limitations

- Output domain is tabular synthetic data exclusively — no audio, images, or unstructured documents. Clinical-ASR audio benchmarks belong to `/digital-health-clinical-asr-build`, not here.
- The skill writes the Python config file but does not invoke the generation pipeline on the user's behalf — the user runs `data-designer preview` and `data-designer run` themselves.
- LLM columns require network reachability at preview and run time. In sandboxed environments those calls may be blocked; see Troubleshooting for the sandbox-disable handshake.

## Brief to satisfy

$ARGUMENTS

The brief above is what you need to translate into a Data Designer config. Don't open additional workspace files to "look around" — the selected workflow runbook walks you through any context-gathering you actually need (its Learn step). Trust the runbook over instinct here.

## Mode selection + runbook

A simple heuristic: if the user's framing is opinionated-and-hands-off ("be opinionated", "you decide", "make reasonable assumptions", "just build it", "surprise me", and similar), pick **Autopilot**. For everything else, default to **Interactive** so the user shapes column choices.

After selecting, read *only* that mode's runbook and execute it linearly:

- Interactive path → `workflows/interactive.md`.
- Autopilot path → `workflows/autopilot.md`.

## Authoring rules

A handful of constraints that hold regardless of which mode you're in:

- Output column retention defaults to *keep everything*. Only drop a column when the user explicitly asks, or when the column is a pure intermediate (e.g., a person-object sampler whose fields you extract into discrete columns downstream). Err toward keeping; the user can always trim later.
- Seed datasets are never suggested unilaterally. Only wire one in when the user volunteers seed data or asks to build off existing records. If they do, consult `references/seed-datasets.md` before configuring the seed source.
- Person attributes (names, demographics, addresses) require the person-sampling reference — read `references/person-sampling.md` before adding any person columns.
- If a config script already in the workspace matches the brief, surface the conflict to the user and ask whether to edit it in place or author a new one. Never silently overwrite.

## Usage Tips and Common Pitfalls

- **Sampler / validation columns require both a type and a params object.** Pair `sampler_type="category"` with `params=dd.CategorySamplerParams(...)`; either alone won't validate.
- **Jinja2 in `prompt`, `system_prompt`, and `expr`** — top-level columns are `{{ column_name }}`, nested fields are `{{ column_name.field }}`.
- **`SamplerColumnConfig` constructor takes `params`** — not `sampler_params`. Easy to typo if you're new to the library.
- **Reading LLM-judge scores.** `LLMJudgeColumnConfig` returns a nested dict shaped `{score_name: {reasoning: str, score: int}}`. To pull the integer score in a Jinja template for a judge column `quality` with score `correctness`, write `{{ quality.correctness.score }}`. Dropping the trailing `.score` yields the full dict, which is almost never what you want.

## Troubleshooting

- **`data-designer: command not found`** → the package isn't installed in this environment. Tell the user, confirm they're on Python ≥ 3.10, and offer to create a venv + run `pip install data-designer` for them — but wait for explicit permission before installing.
- **Preview fails on network errors** → most likely a sandbox is blocking outbound calls to the LLM endpoint. Ask whether to retry with the sandbox disabled. If that still fails, ask the user to run the command in their own shell.

## Output Template

The deliverable from any successful run of this skill is one Python file placed in the user's working directory. It must export a `load_config_builder()` function that returns a `DataDesignerConfigBuilder` instance. Pick a filename that describes the dataset (`customer_reviews.py`, `medical_term_seeds.py`, etc.) rather than a generic one. Declare runtime dependencies with a PEP 723 inline metadata header so the file is runnable with `data-designer run` out of the box.

Below is the canonical skeleton. Strip the Pydantic model / custom generator / seed-dataset blocks if the brief doesn't call for them — keep this file as small as the task allows.

```python
# /// script
# dependencies = [
#   "data-designer", # always required
#   "pydantic", # only if this script imports from pydantic
#   # add additional dependencies here
# ]
# ///
import data_designer.config as dd
from pydantic import BaseModel, Field


# Use Pydantic models when the output needs to conform to a specific schema
class MyStructuredOutput(BaseModel):
    field_one: str = Field(description="...")
    field_two: int = Field(description="...")


# Use custom generators when built-in column types aren't enough
@dd.custom_column_generator(
    required_columns=["col_a"],
    side_effect_columns=["extra_col"],
)
def generator_function(row: dict) -> dict:
    # add custom logic here that depends on "col_a" and update row in place
    row["name_in_custom_column_config"] = "custom value"
    row["extra_col"] = "extra value"
    return row


def load_config_builder() -> dd.DataDesignerConfigBuilder:
    config_builder = dd.DataDesignerConfigBuilder()

    # Seed dataset (only if the user explicitly mentions a seed dataset path)
    # config_builder.with_seed_dataset(dd.LocalFileSeedSource(path="path/to/seed.parquet"))

    # config_builder.add_column(...)
    # config_builder.add_processor(...)

    return config_builder
```

Only include Pydantic models, custom generators, seed datasets, and extra dependencies when the task requires them.


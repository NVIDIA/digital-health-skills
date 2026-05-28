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

## Before You Start

Skip workspace exploration entirely. The selected workflow runbook walks you through the Learn step and surfaces every piece of context you need.

## Goal

Author a synthetic dataset config using NeMo Data Designer that satisfies this brief:

$ARGUMENTS

## Workflow

Mode selection rule: any user phrasing along the lines of "be opinionated", "you decide", "make reasonable assumptions", "just build it", or "surprise me" routes to **Autopilot**. Everything else defaults to **Interactive**.

Open **only** the runbook for the selected mode and execute it end-to-end:

- Interactive mode → `workflows/interactive.md`.
- Autopilot mode → `workflows/autopilot.md`.

## Rules

- Default to keeping every column in the final output. The two valid reasons to drop a column are (a) explicit user request, or (b) the column exists purely as an intermediate helper for deriving other columns (e.g., a person-object sampler whose fields get extracted into separate columns). When unsure, keep it.
- Do not raise seed datasets unless the user introduces them first. If the user does supply seed data, read `references/seed-datasets.md` before building the config.
- For datasets needing person attributes (names, demographics, addresses), consult `references/person-sampling.md`.
- When a dataset script matching the brief already exists in the workspace, ask the user whether to edit it in place or write a new one — don't pick silently.

## Usage Tips and Common Pitfalls

- **Sampler / validation columns require both a type and a params object.** Pair `sampler_type="category"` with `params=dd.CategorySamplerParams(...)`; either alone won't validate.
- **Jinja2 in `prompt`, `system_prompt`, and `expr`** — top-level columns are `{{ column_name }}`, nested fields are `{{ column_name.field }}`.
- **`SamplerColumnConfig` constructor takes `params`** — not `sampler_params`. Easy to typo if you're new to the library.
- **Reading LLM-judge scores.** `LLMJudgeColumnConfig` returns a nested dict shaped `{score_name: {reasoning: str, score: int}}`. To pull the integer score in a Jinja template for a judge column `quality` with score `correctness`, write `{{ quality.correctness.score }}`. Dropping the trailing `.score` yields the full dict, which is almost never what you want.

## Troubleshooting

- **`data-designer: command not found`** → the package isn't installed in this environment. Tell the user, confirm they're on Python ≥ 3.10, and offer to create a venv + run `pip install data-designer` for them — but wait for explicit permission before installing.
- **Preview fails on network errors** → most likely a sandbox is blocking outbound calls to the LLM endpoint. Ask whether to retry with the sandbox disabled. If that still fails, ask the user to run the command in their own shell.

## Output Template

Drop a Python file into the current directory exporting `load_config_builder()` → `DataDesignerConfigBuilder`. Give it a descriptive filename (e.g., `customer_reviews.py`) and use a PEP 723 inline metadata header for its dependencies.

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


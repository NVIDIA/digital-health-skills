---
name: data-designer
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

Build a synthetic tabular dataset using the Data Designer library (`data_designer.config`). The agent selects between Interactive and Autopilot modes, runs `data-designer preview` to inspect, then `data-designer run` to generate the full dataset.

## Instructions

1. **Pick a mode**: Interactive (default — ask the user questions) or Autopilot (when the user signals "you decide" / "just build it").
2. **Read the matching workflow file** (these are the per-mode runbooks):
   - Interactive → `workflows/interactive.md`
   - Autopilot → `workflows/autopilot.md`
3. **Build the config** by writing a Python file with `load_config_builder()` returning a `DataDesignerConfigBuilder` (see Output Template section below).
4. **Preview the output** via the `data-designer preview` CLI before committing to a full generation run.
5. **Run the script** via the `data-designer run` CLI (run_script entry point) once the preview looks right. Optionally invoke `scripts/get_person_object_schema.py` if the dataset needs person/demographic columns.

## Examples

See the workflow runbooks under `workflows/` for end-to-end example dialogues:
- `workflows/interactive.md` — Q&A walkthrough with the user.
- `workflows/autopilot.md` — opinionated build with minimal user input.

The Output Template section below also includes a representative Python config skeleton with a sampler column, an LLM column, a Pydantic structured output, and a custom column generator.

## Scripts

| Script | Purpose |
|---|---|
| `scripts/get_person_object_schema.py` | Inspect the Data Designer person-object field schema (names, demographics, addresses) before adding person-sampler columns to a config. Invoke via `python3 scripts/get_person_object_schema.py`. |

## Prerequisites

- Python ≥ 3.10 in a virtualenv.
- `data-designer` package installed (`pip install data-designer`).
- LLM credentials configured per Data Designer's own setup if your config uses LLM columns or LLM judges.
- Optional: `pydantic` if your config defines structured outputs (PEP 723 dep header will pull it in).

## Limitations

- This skill produces tabular synthetic data only — not audio, images, or unstructured documents. For clinical ASR audio benchmarks see `/digital-health-clinical-asr-build`.
- Output config is a Python file the user runs themselves; this skill does not execute the generation pipeline directly.
- Network access is required at preview/run time for any LLM columns; sandboxed environments may need the sandbox disabled for those calls (see Troubleshooting).

## Before You Start

Do not explore the workspace first. The workflow's Learn step gives you everything you need.

## Goal

Build a synthetic dataset using the Data Designer library that matches this description:

$ARGUMENTS

## Workflow

Use **Autopilot** mode if the user implies they don't want to answer questions — e.g., they say something like "be opinionated", "you decide", "make reasonable assumptions", "just build it", "surprise me", etc. Otherwise, use **Interactive** mode (default).

Read **only** the workflow file that matches the selected mode, then follow it:

- **Interactive** → read `workflows/interactive.md`
- **Autopilot** → read `workflows/autopilot.md`

## Rules

- Keep all columns in the output by default. The only exceptions for dropping a column are: (1) the user explicitly asks, or (2) it is a helper column that exists solely to derive other columns (e.g., a sampled person object used to extract name, city, etc.). When in doubt, keep the column.
- Do not suggest or ask about seed datasets. Only use one when the user explicitly provides seed data or asks to build from existing records. When using a seed, read `references/seed-datasets.md`.
- When the dataset requires person data (names, demographics, addresses), read `references/person-sampling.md`.
- If a dataset script that matches the dataset description already exists, ask the user whether to edit it or create a new one.

## Usage Tips and Common Pitfalls

- **Sampler and validation columns need both a type and params.** E.g., `sampler_type="category"` with `params=dd.CategorySamplerParams(...)`.
- **Jinja2 templates** in `prompt`, `system_prompt`, and `expr` fields: reference columns with `{{ column_name }}`, nested fields with `{{ column_name.field }}`.
- **`SamplerColumnConfig`:** Takes `params`, not `sampler_params`.
- **LLM judge score access:** `LLMJudgeColumnConfig` produces a nested dict where each score name maps to `{reasoning: str, score: int}`. To get the numeric score, use the `.score` attribute. For example, for a judge column named `quality` with a score named `correctness`, use `{{ quality.correctness.score }}`. Using `{{ quality.correctness }}` returns the full dict, not the numeric score.

## Troubleshooting

- **`data-designer` CLI not found:** Tell the user that `data-designer` is not installed in this environment (requires Python >= 3.10). Ask if they would like you to create a virtual environment and install it, or if they prefer to do it themselves. Do not install anything without the user's permission.
- **Network errors during preview:** A sandbox environment may be blocking outbound requests. Ask the user for permission to retry the command with the sandbox disabled. Only as a last resort, if retrying outside the sandbox also fails, tell the user to run the command themselves.

## Output Template

Write a Python file to the current directory with a `load_config_builder()` function returning a `DataDesignerConfigBuilder`. Name the file descriptively (e.g., `customer_reviews.py`). Use PEP 723 inline metadata for dependencies.

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

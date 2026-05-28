# Output template — canonical Data Designer config skeleton

The deliverable from a successful run of `nemo-clinical-data-designer` is a single Python file in the user's working directory that exports a `load_config_builder()` function returning a `DataDesignerConfigBuilder`. Pick a filename that describes the dataset itself (`customer_reviews.py`, `medical_term_seeds.py`, etc.) rather than something generic like `config.py`. Declare runtime dependencies with a PEP 723 inline metadata header so the resulting script is runnable directly with `data-designer run`.

Strip the Pydantic model, custom generator, and seed-dataset blocks from the skeleton below when the brief doesn't call for them — keep the generated file as small as the task allows.

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

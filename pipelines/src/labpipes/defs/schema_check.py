"""S1: the schema_contract check on trip_files.

Compare the landed file's Parquet footer (the DataBucket resource reads it) with
contracts/trips.schema.yaml, before raw_trips copies anything. contracts/platform.yaml says this check
is blocking. Patterns: pipelines/reference/patterns.py. Decision point: what counts as a mismatch?
"""

from dataclasses import asdict

import dagster as dg

from ..contracts import trips_schema
from ..partitions import trip_months
from ..resources import DataBucket
from .trip_files import trip_files


@dg.asset_check(
    asset=trip_files,
    partitions_def=trip_months,
    blocking=True,
    description="Landed Parquet footer matches contracts/trips.schema.yaml in column count, names and types.",
)
def schema_contract(context: dg.AssetCheckExecutionContext, data_bucket: DataBucket) -> dg.AssetCheckResult:
    month = context.partition_key
    footer = data_bucket.footer(month)
    expected = trips_schema()

    errors = []
    if len(footer.columns) != len(expected):
        errors.append(f"column count mismatch: got {len(footer.columns)}, expected {len(expected)}")
    else:
        for idx, (got, exp) in enumerate(zip(footer.columns, expected, strict=True)):
            if got.name.lower() != exp.name.lower():
                errors.append(f"col {idx}: name mismatch got {got.name!r}, expected {exp.name!r}")
            if got.type != exp.type:
                errors.append(f"col {idx} ({got.name}): type mismatch got {got.type!r}, expected {exp.type!r}")

    passed = len(errors) == 0
    return dg.AssetCheckResult(
        passed=passed,
        severity=dg.AssetCheckSeverity.ERROR,
        description="Schema matches contract" if passed else "; ".join(errors),
        metadata={
            "errors": dg.MetadataValue.json(errors),
            "footer_columns": dg.MetadataValue.json([asdict(c) for c in footer.columns]),
            "expected_columns": dg.MetadataValue.json([asdict(c) for c in expected]),
        },
    )

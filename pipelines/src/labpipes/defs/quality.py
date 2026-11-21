"""S1: data-quality checks on stg_trips (nulls, ranges, duplicates, row counts).

Decision points: which checks block downstream and which only warn, and every threshold. Base them on
what real months look like (scripts/verify/results/tlc-stats-2024-01-04.md is the instructor's
baseline; measure your own in Redshift) and on what gameday's corrupt month would look like.
"""

import dagster as dg

from ..partitions import trip_months
from ..resources import RedshiftData
from .staging import stg_trips


@dg.asset_check(
    asset=stg_trips,
    partitions_def=trip_months,
    blocking=True,
    description="Staged trips month must not be empty.",
)
def non_empty_month(context: dg.AssetCheckExecutionContext, redshift: RedshiftData) -> dg.AssetCheckResult:
    month = context.partition_key
    rows = redshift.scalar(f"select count(*) from staging.stg_trips where trip_month = '{month}'")
    passed = int(rows) > 0
    return dg.AssetCheckResult(
        passed=passed,
        severity=dg.AssetCheckSeverity.ERROR,
        description=f"{rows} rows loaded" if passed else "0 rows loaded",
        metadata={"rows": dg.MetadataValue.int(int(rows))},
    )


@dg.asset_check(
    asset=stg_trips,
    partitions_def=trip_months,
    blocking=True,
    description="Mandatory timestamps (pickup_at, dropoff_at) must not be null.",
)
def non_null_timestamps(context: dg.AssetCheckExecutionContext, redshift: RedshiftData) -> dg.AssetCheckResult:
    month = context.partition_key
    bad = redshift.scalar(
        f"select count(*) from staging.stg_trips where trip_month = '{month}' "
        f"and (pickup_at is null or dropoff_at is null)"
    )
    passed = int(bad) == 0
    return dg.AssetCheckResult(
        passed=passed,
        severity=dg.AssetCheckSeverity.ERROR,
        description=f"{bad} rows with null timestamps" if not passed else "All timestamps present",
        metadata={"null_rows": dg.MetadataValue.int(int(bad))},
    )


@dg.asset_check(
    asset=stg_trips,
    partitions_def=trip_months,
    blocking=False,
    description="Trip duration must be positive and not exceed 24 hours (1440 min).",
)
def plausible_duration(context: dg.AssetCheckExecutionContext, redshift: RedshiftData) -> dg.AssetCheckResult:
    month = context.partition_key
    bad = redshift.scalar(
        f"select count(*) from staging.stg_trips where trip_month = '{month}' "
        f"and (duration_min <= 0 or duration_min > 1440)"
    )
    total = redshift.scalar(f"select count(*) from staging.stg_trips where trip_month = '{month}'") or 1
    pct = (int(bad) / int(total)) * 100.0
    passed = pct <= 1.0
    return dg.AssetCheckResult(
        passed=passed,
        severity=dg.AssetCheckSeverity.WARN,
        description=f"{bad} implausible duration rows ({pct:.2f}%)",
        metadata={
            "bad_rows": dg.MetadataValue.int(int(bad)),
            "bad_pct": dg.MetadataValue.float(float(pct)),
        },
    )


@dg.asset_check(
    asset=stg_trips,
    partitions_def=trip_months,
    blocking=False,
    description="TLC pickup and dropoff zone IDs should be within standard range (1..263).",
)
def valid_zones(context: dg.AssetCheckExecutionContext, redshift: RedshiftData) -> dg.AssetCheckResult:
    month = context.partition_key
    bad = redshift.scalar(
        f"select count(*) from staging.stg_trips where trip_month = '{month}' "
        f"and (pickup_zone_id not between 1 and 263 or dropoff_zone_id not between 1 and 263)"
    )
    total = redshift.scalar(f"select count(*) from staging.stg_trips where trip_month = '{month}'") or 1
    pct = (int(bad) / int(total)) * 100.0
    passed = pct <= 1.0
    return dg.AssetCheckResult(
        passed=passed,
        severity=dg.AssetCheckSeverity.WARN,
        description=f"{bad} invalid zone rows ({pct:.2f}%)",
        metadata={
            "bad_rows": dg.MetadataValue.int(int(bad)),
            "bad_pct": dg.MetadataValue.float(float(pct)),
        },
    )

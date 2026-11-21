"""S2: the feature_contract check on trip_features.

contracts/features.yaml lists the model's inputs, label and the post-trip columns that must never be
inputs; contracts/mlflow.yaml says this check blocks.
"""

import dagster as dg

from ..contracts import features_contract
from ..partitions import trip_months
from ..resources import RedshiftData
from .features import trip_features


@dg.asset_check(
    asset=trip_features,
    partitions_def=trip_months,
    blocking=True,
    description="Validates staging.trip_features against contracts/features.yaml schema and value constraints.",
)
def feature_contract(context: dg.AssetCheckExecutionContext, redshift: RedshiftData) -> dg.AssetCheckResult:
    contract = features_contract()
    month = context.partition_key

    # 1. Schema check: query column names
    cols_query = (
        "select column_name from information_schema.columns "
        "where table_schema = 'staging' and table_name = 'trip_features'"
    )
    cols = {r["column_name"].lower() for r in redshift.query(cols_query) if "column_name" in r}

    if cols:
        forbidden = [col.lower() for col in contract.get("forbidden", []) if col.lower() in cols]
        if forbidden:
            return dg.AssetCheckResult(
                passed=False,
                severity=dg.AssetCheckSeverity.ERROR,
                description=f"Forbidden post-trip columns found in staging.trip_features: {forbidden}",
                metadata={"forbidden": dg.MetadataValue.json(forbidden)},
            )

        required_cols = (
            {"trip_month"}
            | {inp["name"].lower() for inp in contract["inputs"]}
            | {contract["label"]["name"].lower()}
        )
        missing = required_cols - cols
        if missing:
            return dg.AssetCheckResult(
                passed=False,
                severity=dg.AssetCheckSeverity.ERROR,
                description=f"Missing required contract columns in staging.trip_features: {sorted(missing)}",
                metadata={"missing": dg.MetadataValue.json(sorted(missing))},
            )

    # 2. Value range checks on the partition
    # Uses 'as extra' pattern compatible with FakeRedshift and real Redshift
    check_query = (
        f"select count(*) as rows, "
        f"sum(case when pickup_zone_id not between 1 and 263 "
        f"or dropoff_zone_id not between 1 and 263 "
        f"or pickup_hour not between 0 and 23 "
        f"or pickup_dow not between 0 and 6 "
        f"or duration_min <= 0 or duration_min > 180 then 1 else 0 end) as extra "
        f"from staging.trip_features where trip_month = '{month}'"
    )
    res = redshift.query(check_query)
    bad_rows = int(res[0].get("extra") or 0) if res else 0

    passed = bad_rows == 0
    return dg.AssetCheckResult(
        passed=passed,
        severity=dg.AssetCheckSeverity.ERROR if not passed else dg.AssetCheckSeverity.WARN,
        description=f"{bad_rows} row(s) violate contract constraints" if not passed else "Contract verified",
        metadata={"bad_rows": dg.MetadataValue.int(bad_rows)},
    )

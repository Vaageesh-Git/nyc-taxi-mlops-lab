"""S2: training_set, trained_model, eval_report, the challenger gate and the challenger asset.

- training_set: UNLOAD a window of staging.trip_features (and the holdout month) to the artifact bucket.
  The zone-pair distance lookup (contracts/features.yaml, est_distance_miles) comes from the window only.
- trained_model: fit tripmodel.LightGBMModel (the given v2), log it to MLflow as a pyfunc with
  tripmodel.model_signature() and the tripmodel package bundled, register a version of the model named
  in contracts/mlflow.yaml, and tag it as that contract says.
- eval_report: tripmodel.evaluate the new version and the champion (or the v1 baseline before there is
  one) on the same holdout; log the metrics.
- A blocking check that guards a `challenger` asset, which sets the alias. The pipeline never moves
  `champion`.
"""

import os
from pathlib import Path

import dagster as dg
import mlflow

import tripmodel
from tripmodel import LightGBMModel, model_signature

from ..contracts import features_contract, mlflow_contract
from ..resources import ArtifactBucket, MlflowTracking, RedshiftData
from .features import trip_features
from .zones import taxi_zones


@dg.asset(deps=[trip_features, taxi_zones], group_name="model", kinds={"redshift", "s3"}, pool="redshift")
def training_set(artifacts: ArtifactBucket, redshift: RedshiftData) -> dg.MaterializeResult:
    train_sql = (
        "unload ('select pickup_zone_id, dropoff_zone_id, pickup_hour, pickup_dow, duration_min "
        "from staging.trip_features where trip_month in (\'\'2024-01\'\', \'\'2024-02\'\', \'\'2024-03\'\')') "
        f"to '{artifacts.uri('training/train/')}' "
        "iam_role default format as parquet allowoverwrite"
    )
    holdout_sql = (
        "unload ('select pickup_zone_id, dropoff_zone_id, pickup_hour, pickup_dow, duration_min "
        "from staging.trip_features where trip_month in (\'\'2024-04\'\')') "
        f"to '{artifacts.uri('training/holdout/')}' "
        "iam_role default format as parquet allowoverwrite"
    )
    dist_sql = (
        "unload ('select pickup_zone_id, dropoff_zone_id, median(trip_distance) as est_distance_miles "
        "from staging.stg_trips where trip_month in (\'\'2024-01\'\', \'\'2024-02\'\', \'\'2024-03\'\') "
        "group by pickup_zone_id, dropoff_zone_id') "
        f"to '{artifacts.uri('training/distances/')}' "
        "iam_role default format as parquet allowoverwrite"
    )
    redshift.execute(train_sql, holdout_sql, dist_sql)

    counts = redshift.query(
        "select count(case when trip_month in ('2024-01', '2024-02', '2024-03') then 1 end) as train, "
        "count(case when trip_month in ('2024-04') then 1 end) as holdout from staging.trip_features"
    )[0]
    return dg.MaterializeResult(
        metadata={
            "training_window": "2024-01..2024-03",
            "holdout_month": "2024-04",
            "train_rows": dg.MetadataValue.int(int(counts.get("train") or 0)),
            "holdout_rows": dg.MetadataValue.int(int(counts.get("holdout") or 0)),
        }
    )


@dg.asset(deps=[training_set], group_name="model", kinds={"mlflow"})
def trained_model(artifacts: ArtifactBucket, tracking: MlflowTracking) -> dg.MaterializeResult:
    train_df = artifacts.read_parquet("training/train")
    dist_df = artifacts.read_parquet("training/distances")

    model = LightGBMModel().fit(train_df, dist_df)

    mlflow.set_tracking_uri(tracking.tracking_uri)
    contract = mlflow_contract()
    mlflow.set_experiment(contract["experiment"])
    git_sha = os.environ.get("GIT_SHA", "unknown")

    with mlflow.start_run() as run:
        info = mlflow.pyfunc.log_model(
            name="model",
            python_model=model,
            signature=model_signature(),
            code_paths=[str(Path(tripmodel.__file__).parent)],
            registered_model_name=contract["registered_model"],
        )
        run_id = run.info.run_id
        model_version = str(info.registered_model_version)

    client = tracking.client()
    client.set_model_version_tag(contract["registered_model"], model_version, "training_window", "2024-01..2024-03")
    client.set_model_version_tag(contract["registered_model"], model_version, "holdout_month", "2024-04")
    client.set_model_version_tag(contract["registered_model"], model_version, "features_version", str(features_contract()["version"]))
    client.set_model_version_tag(contract["registered_model"], model_version, "git_sha", git_sha)

    return dg.MaterializeResult(
        metadata={
            "run_id": run_id,
            "model_version": model_version,
            "training_window": "2024-01..2024-03",
            "holdout_month": "2024-04",
        }
    )


@dg.asset(deps=[trained_model], group_name="model", kinds={"mlflow"})
def eval_report(artifacts: ArtifactBucket, tracking: MlflowTracking, redshift: RedshiftData) -> dg.MaterializeResult:
    holdout_df = artifacts.read_parquet("training/holdout")
    dist_df = artifacts.read_parquet("training/distances")
    train_df = artifacts.read_parquet("training/train")

    rows = redshift.query("select location_id, borough from ingest.taxi_zones")
    boroughs = {int(r["location_id"]): r["borough"] for r in rows if "location_id" in r and "borough" in r}

    contract = mlflow_contract()
    client = tracking.client()
    versions = client.search_model_versions(f"name = '{contract['registered_model']}'")
    latest = max(versions, key=lambda v: int(v.version))
    model_version = str(latest.version)
    run_id = latest.run_id

    model = mlflow.pyfunc.load_model(f"models:/{contract['registered_model']}/{model_version}")
    metrics = tripmodel.evaluate(lambda df: model.predict(df), holdout_df, boroughs)

    try:
        client.get_model_version_by_alias(contract["registered_model"], "champion")
        champ_model = mlflow.pyfunc.load_model(f"models:/{contract['registered_model']}@champion")
        champ_metrics = tripmodel.evaluate(lambda df: champ_model.predict(df), holdout_df, boroughs)
        champ_mae = champ_metrics["mae_min"]
    except Exception:
        baseline = tripmodel.BaselineModel().fit(train_df, dist_df)
        base_metrics = tripmodel.evaluate(lambda df: baseline.predict(None, df), holdout_df, boroughs)
        champ_mae = base_metrics["mae_min"]

    # Log metrics to MLflow run
    client.log_metric(run_id, "mae_min", float(metrics["mae_min"]))
    client.log_metric(run_id, "champion_mae_min", float(champ_mae))
    client.log_metric(run_id, "p95_latency_ms", float(metrics["p95_latency_ms"]))
    for k in ("mae_min.airport", "mae_min.manhattan", "mae_min.outer", "mae_min.night"):
        if k in metrics:
            client.log_metric(run_id, k, float(metrics[k]))

    # Set version tags
    client.set_model_version_tag(contract["registered_model"], model_version, "mae_min", f"{metrics['mae_min']:.4f}")
    client.set_model_version_tag(contract["registered_model"], model_version, "p95_latency_ms", f"{metrics['p95_latency_ms']:.2f}")
    client.set_model_version_tag(contract["registered_model"], model_version, "champion_mae_min", f"{champ_mae:.4f}")

    return dg.MaterializeResult(
        metadata={
            "model_version": model_version,
            "mae_min": dg.MetadataValue.float(metrics["mae_min"]),
            "champion_mae_min": dg.MetadataValue.float(champ_mae),
            "p95_latency_ms": dg.MetadataValue.float(metrics["p95_latency_ms"]),
        }
    )


@dg.asset_check(
    asset=eval_report,
    blocking=True,
    description="Guards the challenger alias: requires mae_min < champion_mae_min and p95_latency_ms < 50ms.",
)
def beats_champion(tracking: MlflowTracking) -> dg.AssetCheckResult:
    contract = mlflow_contract()
    client = tracking.client()
    versions = client.search_model_versions(f"name = '{contract['registered_model']}'")
    latest = max(versions, key=lambda v: int(v.version))
    tags = latest.tags

    mae_min = float(tags.get("mae_min", 999.0))
    champ_mae = float(tags.get("champion_mae_min", 0.0))
    latency = float(tags.get("p95_latency_ms", 999.0))

    passed = (mae_min < champ_mae) and (latency < 50.0)
    return dg.AssetCheckResult(
        passed=passed,
        severity=dg.AssetCheckSeverity.ERROR if not passed else dg.AssetCheckSeverity.WARN,
        description=f"mae_min: {mae_min:.4f} vs champion: {champ_mae:.4f}, p95_latency: {latency:.2f}ms",
        metadata={
            "mae_min": dg.MetadataValue.float(mae_min),
            "champion_mae_min": dg.MetadataValue.float(champ_mae),
            "p95_latency_ms": dg.MetadataValue.float(latency),
        },
    )


@dg.asset(deps=[eval_report], group_name="model", kinds={"mlflow"})
def challenger(tracking: MlflowTracking) -> dg.MaterializeResult:
    contract = mlflow_contract()
    client = tracking.client()
    versions = client.search_model_versions(f"name = '{contract['registered_model']}'")
    latest = max(versions, key=lambda v: int(v.version))
    model_version = str(latest.version)

    client.set_registered_model_alias(contract["registered_model"], "challenger", model_version)
    return dg.MaterializeResult(metadata={"challenger_version": model_version})


train_model = dg.define_asset_job(
    "train_model",
    selection=dg.AssetSelection.assets(training_set, trained_model, eval_report, challenger),
    description="Train LightGBM model, evaluate against baseline/champion, and set challenger alias.",
)

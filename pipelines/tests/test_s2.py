"""Tests for S2: feature_contract check, training_set, trained_model, eval_report, challenger."""

import dagster as dg
from fakes import fake_redshift, unloading_redshift, LocalArtifacts

from labpipes.defs.feature_check import feature_contract
from labpipes.defs.training import training_set, trained_model, eval_report, beats_champion, challenger
from labpipes.resources import MlflowTracking


def test_feature_contract_check_passes_on_valid_data():
    rs = fake_redshift()
    context = dg.build_asset_context(
        partition_key="2024-01",
    )
    res = feature_contract(context, rs)
    assert res.passed


def test_s2_training_pipeline_materialization(tmp_path):
    root = str(tmp_path / "artifacts")
    db_path = str(tmp_path / "mlflow.db")
    tracking_uri = f"sqlite:///{db_path}"

    rs = unloading_redshift(root)
    artifacts = LocalArtifacts(bucket="artifacts", root=root)
    tracking = MlflowTracking(tracking_uri=tracking_uri)

    res = dg.materialize(
        [training_set, trained_model, eval_report, challenger],
        resources={
            "redshift": rs,
            "artifacts": artifacts,
            "tracking": tracking,
        },
    )
    assert res.success

    # Verify check
    check_res = beats_champion(tracking)
    assert check_res.passed

    # Verify MLflow challenger alias
    client = tracking.client()
    challenger_ver = client.get_model_version_by_alias("trip-duration", "challenger")
    assert challenger_ver is not None
    assert "mae_min" in challenger_ver.tags
    assert "p95_latency_ms" in challenger_ver.tags
    assert challenger_ver.tags["training_window"] == "2024-01..2024-03"
    assert challenger_ver.tags["holdout_month"] == "2024-04"

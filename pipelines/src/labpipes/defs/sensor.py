"""S1: the S3 sensor (and the job it starts).

Watch trips/ in the data bucket (DataBucket.trip_files). When a month's file appears or changes, add
the month to the trip_months partitions and request a run that goes from trip_files to zone_hour_stats.
Patterns: pipelines/reference/patterns.py.
"""

import json

import dagster as dg

from ..partitions import trip_months
from ..resources import DataBucket
from .features import trip_features
from .marts import zone_hour_stats
from .raw_trips import raw_trips
from .staging import stg_trips
from .trip_files import trip_files

ingest_month = dg.define_asset_job(
    "ingest_month",
    selection=dg.AssetSelection.assets(trip_files, raw_trips, stg_trips, trip_features, zone_hour_stats),
    description="Ingest one month from S3 Parquet landing through marts and features.",
)


@dg.sensor(
    job=ingest_month,
    minimum_interval_seconds=60,
    description="Detects new or updated monthly Parquet files in S3 and triggers ingestion.",
)
def new_trip_files(context: dg.SensorEvaluationContext, data_bucket: DataBucket):
    # Cursor stores {month: etag} mapping
    cursor_state = json.loads(context.cursor or "{}")
    current_files = data_bucket.trip_files()

    new_partitions = []
    run_requests = []
    updated_cursor = dict(cursor_state)

    for f in current_files:
        prev_etag = cursor_state.get(f.month)
        if prev_etag != f.etag:
            if f.month not in cursor_state:
                new_partitions.append(f.month)
            run_requests.append(dg.RunRequest(partition_key=f.month, run_key=f"{f.month}-{f.etag}"))
            updated_cursor[f.month] = f.etag

    if not run_requests:
        return dg.SkipReason("No new or modified trip files detected in S3")

    dynamic_partitions_requests = [trip_months.build_add_request(new_partitions)] if new_partitions else []

    return dg.SensorResult(
        run_requests=run_requests,
        dynamic_partitions_requests=dynamic_partitions_requests,
        cursor=json.dumps(updated_cursor, sort_keys=True),
    )

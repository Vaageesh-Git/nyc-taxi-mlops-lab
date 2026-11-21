"""S1: the raw_trips asset.

One partition per month (partitions.trip_months), depending on trip_files. COPY the month's file into
Redshift with the LabRole attached to the cluster (`iam_role default`), so that re-running a month never
duplicates its rows. The landing columns come from contracts/trips.schema.yaml
(contracts.redshift_columns). Decision points: COPY vs Spectrum; dist and sort keys.
"""

import dagster as dg

from ..contracts import redshift_columns, trips_schema
from ..partitions import check_month, source_file, trip_months
from ..resources import DataBucket, RedshiftData


@dg.asset(
    partitions_def=trip_months,
    deps=["trip_files"],
    group_name="ingest",
    kinds={"redshift"},
    pool="redshift",
)
def raw_trips(
    context: dg.AssetExecutionContext,
    redshift: RedshiftData,
    data_bucket: DataBucket,
) -> dg.MaterializeResult:
    month = context.partition_key
    check_month(month)
    file_name = source_file(month)
    uri = data_bucket.trip_uri(month)
    columns_ddl = redshift_columns(trips_schema())

    # Create table if not exists with DISTSTYLE EVEN and compound SORTKEY (source_file, tpep_pickup_datetime)
    # Perform idempotent replacement in a single batch transaction using a temp table
    redshift.execute(
        "create schema if not exists ingest",
        f"create table if not exists ingest.raw_trips ("
        f"source_file varchar(64) not null, {columns_ddl}) "
        f"diststyle even sortkey (source_file, tpep_pickup_datetime)",
        f"create temp table stage_trips ({columns_ddl})",
        f"copy stage_trips from '{uri}' iam_role default format as parquet",
        f"delete from ingest.raw_trips where source_file = '{file_name}'",
        f"insert into ingest.raw_trips (source_file, {', '.join(c.name.lower() for c in trips_schema())}) "
        f"select '{file_name}', * from stage_trips",
    )

    rows = redshift.scalar(f"select count(*) from ingest.raw_trips where source_file = '{file_name}'")
    return dg.MaterializeResult(
        metadata={
            "rows": dg.MetadataValue.int(int(rows)),
            "source_file": file_name,
            "uri": uri,
        }
    )

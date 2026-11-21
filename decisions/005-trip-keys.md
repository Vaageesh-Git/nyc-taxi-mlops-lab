# 005: Distribution and sort keys for trip tables

Stage: S1 · Date: 2026-11-21 · Author: Vaageesh · Drafted by agent: yes

## Choice

Use `DISTSTYLE EVEN` for `ingest.raw_trips` and a compound `SORTKEY (source_file, tpep_pickup_datetime)`. For `staging.stg_trips`, use `SORTKEY (pickup_at)`.

## Rejected alternative

Using `DISTKEY (pulocationid)` or `DISTSTYLE ALL` for trip tables.

## Why

Trip data contains millions of rows per month. `DISTSTYLE EVEN` distributes rows evenly across all cluster compute slices, avoiding partition skew that occurs when certain high-traffic taxi zones (e.g. JFK or Midtown) receive a disproportionate share of rides. The sort key on `(source_file, tpep_pickup_datetime)` enables 1MB block zone map pruning for monthly deletion cleanup (`where source_file = '{file}'`) and chronological queries during feature engineering and aggregation.

## What would show this was wrong

If queries joining `raw_trips` or `stg_trips` with `taxi_zones` on zone ID became the dominant cluster bottleneck due to cross-slice redistribution network traffic, which would favor co-locating on a common distribution key.

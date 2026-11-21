# 006: Data-quality check severity on stg_trips

Stage: S1 · Date: 2026-11-21 · Author: Vaageesh · Drafted by agent: yes

## Choice

Enforce blocking checks for non-empty row counts (`rows > 0`) and mandatory timestamps (`pickup_at is not null and dropoff_at is not null`). Use warning-severity checks for plausible durations (`0 < duration_min <= 1440`) and valid TLC zone identifiers (`1 <= pickup_zone_id <= 263`).

## Rejected alternative

Making all quality checks blocking (or conversely, making all checks warning-only).

## Why

A missing partition or corrupted file that loads zero rows must never propagate downstream, as wiping out existing data or generating empty statistics in `marts.zone_hour_stats` would break production serving and the MCP assistant. However, real-world TLC taxi data inherently contains a tiny fraction (typically < 0.2%) of taxi meter recording glitches, negative trip durations, or unassigned zone IDs (e.g. 264/265). Making range and zone checks blocking would unnecessarily fail valid monthly pipeline runs on benign anomalies. Warning severity surfaces the anomalies in Dagster asset metadata while permitting downstream marts to build.

## What would show this was wrong

If corrupt upstream files with extreme percentages of invalid durations or broken zones silently corrupted downstream model training features or mart statistics without stopping the pipeline run.

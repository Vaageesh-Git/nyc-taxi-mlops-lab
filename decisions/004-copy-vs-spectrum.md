# 004: Ingest mechanism (COPY vs Redshift Spectrum)

Stage: S1 · Date: 2026-11-21 · Author: Vaageesh · Drafted by agent: yes

## Choice

Use Redshift `COPY` to ingest monthly Parquet files from S3 into managed Redshift tables (`ingest.raw_trips`) within an atomic transaction.

## Rejected alternative

Querying the landed Parquet files directly in S3 using Redshift Spectrum external tables.

## Why

Loading data into Redshift managed storage (`ra3.large` RMS) provides significantly higher query performance for feature generation and aggregation queries downstream. Additionally, Redshift `COPY` supports full transactional semantics: deleting a partition's previous rows and inserting new ones inside a single batch transaction guarantees idempotent loads without data duplication. Redshift Spectrum introduces per-query S3 scan latencies, cannot perform transactional updates or deletions, and relies on AWS Glue Data Catalog permissions that are constrained under AWS Academy Learner Lab.

## What would show this was wrong

If S3 storage costs or Redshift cluster managed storage limits were exceeded by keeping historical raw tables in the warehouse, necessitating querying cold partitions directly from object storage.

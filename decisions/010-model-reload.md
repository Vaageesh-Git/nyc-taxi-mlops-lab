# 010: Model reload mechanism on promotion

Stage: S3 · Date: 2026-11-22 · Author: Vaageesh · Drafted by agent: yes

## Choice

Use in-process atomic reloading via `POST /reload` on the serving container to pick up new champion model versions. The container loads and verifies the new model artifacts from MLflow in the background while continuing to serve incoming inference requests using the existing model. Once ready, the memory reference is swapped atomically.

## Rejected alternative

Restarting the container (`docker compose restart serving-champion`) whenever the champion alias is promoted or updated.

## Why

Restarting the container introduces an unavoidable 5 to 15 second availability outage where HTTP requests fail or fall back to the degraded static median while the container reboots, imports dependencies, and downloads model weights. In-process reloading guarantees zero downtime, avoids request drops or latency spikes during promotion, and keeps rider experience seamless.

## What would show this was wrong

If repeated in-process model loads cause Python memory fragmentation or memory leaks over time, or if library version mismatches between successive model versions necessitate a clean container process restart.

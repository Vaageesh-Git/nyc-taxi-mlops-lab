# 014: Series budget

Stage: S5 · Date: 2026-11-22 · Author: Vaageesh · Drafted by agent: yes

## Choice

Apply aggressive Prometheus relabelling in `budget.alloy` to keep only essential host metrics (CPU, memory, root filesystem), filter container metrics strictly to lab containers while dropping the ephemeral `id` and `image` labels, and keep bounded service metrics from `contracts/metrics.yaml` and Traefik service metrics.

## Rejected alternative

Moderate relabelling that retains full cAdvisor container metadata, per-device block I/O, and ephemeral virtual network interface metrics.

## Why

Grafana Cloud's free tier imposes a strict 10,000 active series limit across all hosts together (app, platform, and upcoming LLM host in S6). Without aggressive filtering, cAdvisor and node_exporter produce $> 3,000$ series per host, and every container redeployment mints new series with new container IDs. By stripping the ephemeral `id` and container label bloat, restarted or redeployed containers map to the same stable series (`name="lab-app-app-blue-1"`), keeping series count below ~300 per host ($< 1,000$ total), leaving $> 90\%$ safety margin for S6.

## What would show this was wrong

If an operational incident cannot be diagnosed because a critical low-level metric (e.g. disk write latency per device or container network packet drops) was pruned by relabelling.

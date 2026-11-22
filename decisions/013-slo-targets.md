# 013: SLO targets

Stage: S5 · Date: 2026-11-22 · Author: Vaageesh · Drafted by agent: yes

## Choice

Adopt a 99.0% 30-day availability objective on `/predict` (measured as quotes served by the ML model vs total quotes) and a 95.0% latency objective ($\le 250\text{ms}$). Alerts use multi-window multi-burn-rate tracking (14.4x over 1h/5m for critical page, 6x over 6h/30m for warning ticket).

## Rejected alternative

A strict 99.9% availability objective and 99% $\le 100\text{ms}$ latency objective.

## Why

In AWS Academy Learner Lab, resources run on burstable ARM Graviton instances (`t4g.large`), lab sessions reset every 4 hours, and deployments incur cold-start latency through Traefik and Python container initializations. A 99.0% availability target provides a ~7.2-hour monthly error budget, absorbing transient session reboots while promptly detecting genuine failures (e.g. champion model crash or fallback reversion). A 250ms p95 latency threshold ensures an interactive rider quote experience while allowing realistic network hops between Traefik and Uvicorn.

## What would show this was wrong

If rider satisfaction drops due to frequent fallbacks escaping notice, or if operational stability consistently maintains $> 99.9\%$ uptime over sustained weeks, prompting a tighter objective.

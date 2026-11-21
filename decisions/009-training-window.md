# 009: Training window and holdout split

Stage: S2 · Date: 2026-11-21 · Author: Vaageesh · Drafted by agent: yes

## Choice

Use a 3-month training window (`2024-01..2024-03`) to fit the model and compute zone-pair distance lookups, and reserve the subsequent month (`2024-04`) strictly as the holdout test set for out-of-time evaluation.

## Rejected alternative

Using a random train/test split across all four months, or using a shorter 1-month training window (`2024-03`).

## Why

In time-series and real-world ride forecasting, future events must never leak into past training data. Random cross-validation leaks temporal patterns (such as holidays or weather events) between train and test sets, yielding overly optimistic evaluation metrics. Splitting chronologically with the test set occurring strictly after the training window simulates real production deployment. A 3-month window provides sufficient historical depth to cover seasonal shifts, day-of-week distributions, and infrequent pickup/dropoff zone pairs.

## What would show this was wrong

If concept drift or seasonal changes (e.g. spring vs winter traffic dynamics) render older months unhelpful or harmful to model accuracy, indicating that a rolling single-month window or recency-weighted training would perform better.

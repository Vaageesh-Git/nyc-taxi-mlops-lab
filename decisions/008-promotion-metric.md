# 008: Model promotion metric and gating margin

Stage: S2 · Date: 2026-11-21 · Author: Vaageesh · Drafted by agent: yes

## Choice

Use Mean Absolute Error in minutes (`mae_min`) on the held-out month as the primary promotion metric, requiring the new model to strictly beat the champion (or baseline v1 model if no champion exists) by `mae_min < champion_mae_min` (margin >= 0.0 minutes), while satisfying a latency threshold of `p95_latency_ms < 50.0 ms`.

## Rejected alternative

Using Root Mean Squared Error (RMSE) as the promotion metric, or requiring a large fixed improvement margin (e.g. >= 0.5 minutes).

## Why

Trip durations contain extreme positive outliers (such as forgotten meters or traffic incidents taking up to 3 hours). RMSE squares errors, which makes the metric dominated by a handful of extreme outlier trips rather than typical ride accuracy. MAE penalizes prediction error linearly, aligning directly with passenger ride expectations. Requiring any positive improvement without an artificially high margin avoids blocking steady, incremental model gains while the strict latency constraint guarantees serving stability.

## What would show this was wrong

If minor statistical noise between model versions leads to frequent challenger turnover without real serving gains, or if tail prediction errors cause severe passenger dissatisfaction that warrants quadratic or asymmetric error weighting.

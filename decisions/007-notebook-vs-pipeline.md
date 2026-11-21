# 007: Notebook vs pipeline boundary

Stage: S2 · Date: 2026-11-21 · Author: Vaageesh · Drafted by agent: yes

## Choice

The Jupyter notebook is restricted to offline data exploration, visualization, and rapid candidate modeling experiments. The automated Dagster pipeline owns feature engineering with schema/contract validation, training set export (`UNLOAD`), model training, holdout evaluation, tagging, and assigning the `challenger` alias behind a blocking gate.

## Rejected alternative

Running training directly in the notebook and allowing the notebook to register models and assign MLflow aliases to candidate models.

## Why

Notebook-driven model registration lacks reproducibility, auditability, and guardrails. It introduces the risk of dirty state, uncommitted code, manual errors, or accidental promotion of models that did not pass contract and latency checks. Encapsulating training and promotion in version-controlled Dagster assets ensures that every registered model version is traceable to a specific git commit, uses contract-validated features, and only advances to `challenger` after satisfying objective gating criteria.

## What would show this was wrong

If exploratory experimentation becomes excessively slowed down by the pipeline cycle, requiring lightweight interactive shadow deployments for manual human evaluation before full pipeline automation.

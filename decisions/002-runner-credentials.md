# 002: GitHub Actions self-hosted runner credentials

Stage: S0 · Date: 2026-11-21 · Author: Vaageesh · Drafted by agent: yes

## Choice

Use the EC2 instance profile (`LabInstanceProfile`) via the AWS Instance Metadata Service (IMDSv2) for the self-hosted runner to access AWS resources, rather than storing static AWS session credentials in GitHub Secrets.

## Rejected alternative

Storing temporary AWS session credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_SESSION_TOKEN`) as GitHub repository secrets.

## Why

In AWS Academy Learner Lab, session tokens are temporary and expire every ~4 hours. If workflows relied on GitHub Secrets, scheduled runs and deployments would fail repeatedly after session timeouts until manually refreshed. The instance profile is automatically provisioned and managed by AWS, requires zero secret rotation across Learner Lab session restarts, and prevents secret leakage in repository settings or workflow logs.

## What would show this was wrong

If a runner task required permissions outside what `LabInstanceProfile` grants, or if CI/CD jobs were moved to external GitHub-hosted or multi-cloud runners where EC2 IMDS is inaccessible.

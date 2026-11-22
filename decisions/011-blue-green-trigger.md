# 011: Blue-green deployment switch trigger

Stage: S3 · Date: 2026-11-22 · Author: Vaageesh · Drafted by agent: yes

## Choice

Trigger the blue-green traffic switch automatically in the CD pipeline upon successful completion of automated smoke tests against the idle color. The pipeline provisions the idle color, executes smoke tests via internal `X-Lab-Color` routing headers (checking `/version` git SHA and validating `/predict`), and immediately switches 100% traffic to the new color via Traefik weighted service configuration while keeping the previous color alive for rapid rollback.

## Rejected alternative

Requiring a manual human approval gate or manual CLI command to switch traffic after the idle color is deployed.

## Why

Automating the switch behind robust end-to-end smoke tests eliminates human delay, streamlines continuous delivery, and ensures that every passing commit seamlessly reaches riders. Keeping the previously live container running in the background preserves instantaneous, zero-rebuild rollback capability in case unexpected runtime issues emerge post-switch.

## What would show this was wrong

If complex edge-case defects pass the automated smoke tests and reach riders unnoticed, or if the system requires manual canary observation and human sign-off before full production exposure.

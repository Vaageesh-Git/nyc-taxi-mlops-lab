# 001: Ingress scope for the app host

Stage: S0 · Date: 2026-11-21 · Author: Vaageesh · Drafted by agent: yes

## Choice

Restrict ingress on port 80 (Traefik / App) to specific trusted CIDRs via `var.ingress_cidrs`: the student's IP (`115.244.141.202/32`) and designated grader/instructor CIDRs.

## Rejected alternative

Opening ingress on port 80 to `0.0.0.0/0` (the entire public internet).

## Why

The app host has a public Elastic IP on AWS. Opening port 80 to `0.0.0.0/0` exposes the unauthenticated endpoint to automated port scanners, crawlers, and denial of service attacks that could exhaust EC2 network bandwidth and AWS Academy Learner Lab budget credits. Restricting ingress to explicit client and grader CIDRs enforces the principle of least privilege while still allowing direct development and grading access.

## What would show this was wrong

Frequent client IP changes (such as roaming across networks or dynamic ISP reassignment) that block access, or external automated grading systems failing to reach the app because their IP addresses were not pre-configured in `ingress_cidrs`.

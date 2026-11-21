# 003: Container image tag scheme

Stage: S0 · Date: 2026-11-21 · Author: Vaageesh · Drafted by agent: yes

## Choice

Tag all deployable container images pushed to GHCR using immutable short Git commit SHA tags (`sha-<git_sha_7>`), matching the scheme used across the lab (`platform.yaml`, `serving.yaml`).

## Rejected alternative

Using mutable tags (such as `latest`) or manual semantic versioning (`vX.Y.Z`) on every build.

## Why

An immutable Git commit SHA provides 1-to-1 deterministic traceability from a running container back to the exact code commit in git. Mutable tags like `latest` cause Docker layer caching ambiguities where hosts run stale images without a force-pull, and make rollbacks unpredictable. With SHA-based tags, rollbacks are trivial and deterministic: pointing `IMAGE_TAG` to the previous commit SHA guarantees deployment of that exact artifact.

## What would show this was wrong

If downstream external consumers or business release governance required strict semantic versioning (semver) guarantees for public API consumers.

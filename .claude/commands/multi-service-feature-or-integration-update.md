---
name: multi-service-feature-or-integration-update
description: Workflow command scaffold for multi-service-feature-or-integration-update in fleshrag.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /multi-service-feature-or-integration-update

Use this workflow when working on **multi-service-feature-or-integration-update** in `fleshrag`.

## Goal

Implements or updates a feature that affects multiple backend services, Docker configurations, and frontend components, often including CUDA/GPU enablement, API migrations, and test additions.

## Common Files

- `backend/app/api/*.py`
- `backend/app/indexer/*.py`
- `backend/app/db/*.py`
- `backend/Dockerfile`
- `embed-service/Dockerfile`
- `embed-service/server.py`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Update backend service code (e.g., API, indexer, db, config)
- Update or add Dockerfiles and docker-compose.yml for new/changed services
- Update environment files (.env, .env.example)
- Update or add frontend components as needed
- Add or update tests (integration, smoke)

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.
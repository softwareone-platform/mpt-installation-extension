# Documentation

This repository follows the shared documentation standard:

- [standards/documentation.md](https://github.com/softwareone-platform/mpt-extension-skills/blob/main/standards/documentation.md)

This file documents repository-specific documentation rules only.

## Repository Rules

- `README.md` must stay short and act as the main human entry point.
- `AGENTS.md` must stay operational and tell AI agents which files to read first.
- Topic-specific behavior must live in the matching file under [`docs/`](.).
- `.github/copilot-instructions.md` must remain a thin adapter that points back to [`AGENTS.md`](../AGENTS.md).
- When runtime, testing, migration, or setup behavior changes, update the corresponding document in the same change.

## Current Documentation Map

- [`README.md`](../README.md): human entry point, overview, quick start, and documentation map
- [`AGENTS.md`](../AGENTS.md): AI entry point and reading order
- [`architecture.md`](architecture.md): runtime components, event flow, pipeline boundaries, and design decisions
- [`local-development.md`](local-development.md): local Docker workflow, devmock usage, and Postman collection entry point
- [`deployment.md`](deployment.md): runtime configuration and deployment model
- [`external-integrations.md`](external-integrations.md): Marketplace API, local mock, and notification integration boundaries
- [`contributing.md`](contributing.md): repository-specific development workflow
- [`testing.md`](testing.md): testing strategy and command mapping
- [`migrations.md`](migrations.md): migration workflow and migration-specific constraints

## Documentation Change Rule

When documentation changes, prefer updating the smallest relevant document instead of creating overlapping summary files.

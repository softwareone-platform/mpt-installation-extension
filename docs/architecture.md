# Architecture

Keep this document focused on actual architecture decisions for the repository.

If the repository does not yet have stable architectural decisions, keep this file short and avoid speculative descriptions.

## What To Document Here

When architecture details become relevant, document:

- the main runtime components
- repository boundaries and responsibility split
- extension entry points
- data flow between API handlers, event listeners, pipelines, and external services
- any persistence model and migration boundaries
- important design decisions or tradeoffs

## Runtime Components

- [`backend/mpt_installation_extension/app.py`](../backend/mpt_installation_extension/app.py) creates the SDK `ExtensionApp` and registers the agreement event router.
- [`backend/mpt_installation_extension/routers/events/agreements.py`](../backend/mpt_installation_extension/routers/events/agreements.py) declares the agreement activation event subscription as a task-based route (`router.task`) and delegates execution to the installation pipeline.
- [`backend/mpt_installation_extension/pipelines/agreement_installation.py`](../backend/mpt_installation_extension/pipelines/agreement_installation.py) coordinates installation steps and shared side effects through SDK pipeline hooks.
- [`backend/mpt_installation_extension/pipelines/steps/install_agreement_extensions.py`](../backend/mpt_installation_extension/pipelines/steps/install_agreement_extensions.py) drives installation for the extensions configured for the agreement product and owns the recoverable/non-recoverable error classification.
- [`backend/mpt_installation_extension/services/extension_installation.py`](../backend/mpt_installation_extension/services/extension_installation.py) holds `ExtensionInstallationCreatorService`, the shared installation logic used by both the reactive step and the backfill migration. A create returning `409 CONFLICT` is treated as an existing installation, so installs are idempotent without a separate existence check.
- [`backend/mpt_installation_extension/services/mpt_api_service.py`](../backend/mpt_installation_extension/services/mpt_api_service.py) subclasses the SDK `MPTAPIService`, adding reconciliation queries to its services: `agreements.active_account_ids(product_id)` and `installations.accounts_with_extension(extension_id)`. It is wired through `ExtensionApp(mpt_api_service_type=...)`.
- [`backend/mpt_installation_extension/settings.py`](../backend/mpt_installation_extension/settings.py) loads the product-to-extension mapping (used by the event subscription, the step, and the migration) and, via `MigrationExtensionSettings`, the migration-only operations account id.

Data migrations live in [`backend/migrations/`](../backend/migrations) and reuse the same services; see [migrations.md](migrations.md).

## Agreement Activation Flow

1. The SDK receives `platform.commerce.agreement.status_changed` on `/events/v2/agreements/complete`. The route is task-based, so every delivery carries a Marketplace task and the SDK starts it before running the handler.
2. The router filters events to active agreements whose product id is present in `EXT_MPT_PRODUCT_EXTENSION_MAPPING`.
3. The SDK adapts the base agreement context into `InstallationAgreementContext`, adding `installation_state`.
4. `AgreementInstallationPipeline` runs `InstallAgreementExtensionsStep`.
5. The step reads the configured extension ids for the agreement product, skips products with no mapping, and processes configured extensions concurrently.
6. For each extension, the step calls `ExtensionInstallationCreatorService.create_installation`, which creates the installation from the target extension modules returned by the Marketplace Integration API.
7. A `409 CONFLICT` from the create means the installation already exists and is treated as a no-op, so re-processing the same account is safe.
8. The step records each extension's outcome and a message describing it in `installation_state.installations`. In a `finally` block around the pipeline, the handler writes those messages to the task log (`Info` for created or existing, `Warning` for retried, `Error` for permanent failures), using the task service authenticated with the extension token.
9. The SDK completes the task when the pipeline finishes without errors.

## Failure Handling

Recoverable Marketplace failures are converted into `DeferStepError`; the SDK pipeline/router contract then reschedules the task for retry.

For non-recoverable Marketplace failures, the step records a single aggregated `InstallationAction` on `ctx.installation_state.action`.
When the step succeeds, the pipeline `on_step_succeeded` hook logs the failure, sends a Microsoft Teams notification through the shared notification package, and raises `FailError`,
so the SDK marks the task as failed. If the same run also had recoverable failures, the step defers before `on_step_succeeded` runs, so this run sends no notification and the task is rescheduled. Each retry starts with a new `InstallationState`: the notification and task failure happen only if the permanent failure recurs on the retry that finishes the step.
See [external-integrations.md](external-integrations.md) for the notification transport and its configuration.

## Boundaries

The handler owns routing, subscription metadata, and the platform task log. Installation orchestration lives in the pipeline, and the step owns per-event orchestration and the recoverable/non-recoverable error classification.

The pipeline owns shared reactions to step outcomes. Steps declare intent through `installation_state.action` instead of performing cross-cutting notification behavior directly.

Installation business logic lives in `ExtensionInstallationCreatorService` so the reactive step and the backfill migration share one implementation. The repository defines no persistence model; the only migrations are data migrations that reconcile installations (see [migrations.md](migrations.md)).

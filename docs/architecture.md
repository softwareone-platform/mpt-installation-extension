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
- [`backend/mpt_installation_extension/routers/events/agreements.py`](../backend/mpt_installation_extension/routers/events/agreements.py) declares the agreement activation event subscription and delegates execution to the installation pipeline.
- [`backend/mpt_installation_extension/pipelines/agreement_installation.py`](../backend/mpt_installation_extension/pipelines/agreement_installation.py) coordinates installation steps and shared side effects through SDK pipeline hooks.
- [`backend/mpt_installation_extension/pipelines/steps/install_agreement_extensions.py`](../backend/mpt_installation_extension/pipelines/steps/install_agreement_extensions.py) drives installation for the extensions configured for the agreement product and owns the recoverable/non-recoverable error classification.
- [`backend/mpt_installation_extension/services/extension_installation.py`](../backend/mpt_installation_extension/services/extension_installation.py) holds `ExtensionInstallationCreatorService`, the shared installation logic used by both the reactive step and the backfill migration. A create returning `409 CONFLICT` is treated as an existing installation, so installs are idempotent without a separate existence check.
- [`backend/mpt_installation_extension/services/agreement_query.py`](../backend/mpt_installation_extension/services/agreement_query.py) holds `AgreementQueryService`, which resolves the client accounts with an active agreement for a product.
- [`backend/mpt_installation_extension/settings.py`](../backend/mpt_installation_extension/settings.py) loads the product-to-extension mapping used by the event subscription condition, the installation step, and the backfill migration.

Data migrations live in [`backend/migrations/`](../backend/migrations) and reuse the same services; see [migrations.md](migrations.md).

## Agreement Activation Flow

1. The SDK receives `platform.commerce.agreement.status_changed` on `/events/v2/agreements/complete`.
2. The router filters events to active agreements whose product id is present in `EXT_MPT_PRODUCT_EXTENSION_MAPPING`.
3. The SDK adapts the base agreement context into `InstallationAgreementContext`, adding `installation_state`.
4. `AgreementInstallationPipeline` runs `InstallAgreementExtensionsStep`.
5. The step reads the configured extension ids for the agreement product, skips products with no mapping, and processes configured extensions concurrently.
6. For each extension, the step calls `ExtensionInstallationCreatorService.create_installation`, which creates the installation from the target extension modules returned by the Marketplace Integration API.
7. A `409 CONFLICT` from the create means the installation already exists and is treated as a no-op, so re-processing the same account is safe.

## Failure Handling

Recoverable Marketplace failures are converted into `DeferStepError`; the SDK pipeline/router contract then defers the event for retry.

Non-recoverable Marketplace failures do not fail the event. The step records a single aggregated `InstallationAction` on `ctx.installation_state.action`. Pipeline hooks handle that action after success or before defer by logging the failure and sending a Microsoft Teams notification through the shared notification package. See [external-integrations.md](external-integrations.md) for the notification transport and its configuration.

## Boundaries

The handler owns routing and subscription metadata only. Installation orchestration lives in the pipeline, and installation business work lives in the step.

The pipeline owns shared reactions to step outcomes. Steps declare intent through `installation_state.action` instead of performing cross-cutting notification behavior directly.

Installation business logic lives in `ExtensionInstallationCreatorService` so the reactive step and the backfill migration share one implementation. The repository defines no persistence model; the only migrations are data migrations that reconcile installations (see [migrations.md](migrations.md)).

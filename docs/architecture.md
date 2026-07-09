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
- [`backend/mpt_installation_extension/pipelines/steps/install_agreement_extensions.py`](../backend/mpt_installation_extension/pipelines/steps/install_agreement_extensions.py) performs the idempotent installation work for the extensions configured for the agreement product.
- [`backend/mpt_installation_extension/settings.py`](../backend/mpt_installation_extension/settings.py) loads the product-to-extension mapping used both by the event subscription condition and the installation step.

## Agreement Activation Flow

1. The SDK receives `platform.commerce.agreement.status_changed` on `/events/v2/agreements/complete`.
2. The router filters events to active agreements whose product id is present in `EXT_MPT_PRODUCT_EXTENSION_MAPPING`.
3. The SDK adapts the base agreement context into `InstallationAgreementContext`, adding `installation_state`.
4. `AgreementInstallationPipeline` runs `InstallAgreementExtensionsStep`.
5. The step reads the configured extension ids for the agreement product, skips products with no mapping, and processes configured extensions concurrently.
6. For each extension, the step checks whether an installation already exists for the agreement client account. Existing installations are skipped.
7. Missing installations are created from the target extension modules returned by the Marketplace Integration API.

## Failure Handling

Recoverable Marketplace failures are converted into `DeferStepError`; the SDK pipeline/router contract then defers the event for retry.

Non-recoverable Marketplace failures do not fail the event. The step records a single aggregated `InstallationAction` on `ctx.installation_state.action`. Pipeline hooks handle that action after success or before defer by logging the failure and sending a Microsoft Teams notification through the shared notification package. See [external-integrations.md](external-integrations.md) for the notification transport and its configuration.

## Boundaries

The handler owns routing and subscription metadata only. Installation orchestration lives in the pipeline, and installation business work lives in the step.

The pipeline owns shared reactions to step outcomes. Steps declare intent through `installation_state.action` instead of performing cross-cutting notification behavior directly.

The repository does not define a persistence model or migrations for this flow.

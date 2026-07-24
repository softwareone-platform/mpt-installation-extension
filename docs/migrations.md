# Migrations

Use this document only for migration details that are specific to the repository.

Shared migration knowledge lives in:

- [knowledge/migrations.md](https://github.com/softwareone-platform/mpt-extension-skills/blob/main/knowledge/migrations.md)
- [knowledge/make-targets.md](https://github.com/softwareone-platform/mpt-extension-skills/blob/main/knowledge/make-targets.md)

If the repository does not yet have repository-specific migration rules, keep this file short and rely on the shared migration knowledge above.

## Migration Files

Data migrations live in [`backend/migrations/`](../backend/migrations) and use the repository make targets (`make migrate-new-data`, `make migrate-data`, `make migrate-list`, `make migrate-check`). See the shared migration knowledge for the tooling and the storage backends selectable via `MPT_TOOL_STORAGE_TYPE`.

## Installing Missing Extensions

The extension installs vendor extensions reactively when an agreement becomes `Active`. That flow only acts going forward, so clients with **already-active** agreements do not receive an extension that is added to `EXT_MPT_PRODUCT_EXTENSION_MAPPING` later. A data migration closes that gap for the accounts that are missing it.

### Adding one

When a new extension or product is added:

1. Update `EXT_MPT_PRODUCT_EXTENSION_MAPPING` so the reactive flow covers future activations. The product/extension ids differ per environment, so the migration reads this mapping instead of hardcoding ids.
2. Scaffold a migration: `make migrate-new-data name=install_missing_extensions`.
3. In the generated file, reconcile the current mapping from settings (see the existing migration): build `ExtensionInstallationCreatorService` from `self.mpt_api_service` and call `create_missing_installations(get_extension_settings().product_extension_mapping)`.
4. Deploy. `make migrate-data` runs the pending migrations.

The migration installs each configured extension on every account that has an `Active` agreement of the corresponding product and lacks the installation. It is idempotent (a create returning `409 CONFLICT` counts as already installed), and it raises (so it can be re-run) if any installation fails permanently. It requires `MPT_API_BASE_URL` and `MPT_API_TOKEN` in the execution environment, with permission to create installations.

## Documentation Rule

When repository-specific migration behavior is introduced or changed, update this document in the same change.

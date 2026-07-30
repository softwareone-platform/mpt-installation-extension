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

### Authentication

The migration runs as the **operations account**. Instead of storing an account token, it mints an account-scoped token from the extension's own API key (`SDK_EXTENSION_API_KEY`) via `MPTAPIServiceMixin.account_scoped_service(account_id)`. Operations has global visibility over agreements and installations. This requires:

- `EXT_OPERATIONS_ACCOUNT_ID` — the operations account id (per environment).
- `SDK_EXTENSION_API_KEY`, `MPT_API_BASE_URL`, `SDK_EXTENSION_ID` (already present).
- The extension must be installed on the operations account (otherwise the account-scoped token cannot be minted).

No `MPT_API_TOKEN` is needed.

### Adding one

When a new extension or product is added:

1. Update `EXT_MPT_PRODUCT_EXTENSION_MAPPING` so the reactive flow covers future activations. The product/extension ids differ per environment, so the migration reads this mapping instead of hardcoding ids.
2. Scaffold a migration: `make migrate-new-data name=install_missing_extensions`.
3. In the generated file, reconcile the current mapping (see the existing migration): use `MPTAPIServiceMixin.account_scoped_service`, build `ExtensionInstallationCreatorService`, and call `create_missing_installations(get_migration_settings().product_extension_mapping)`.
4. Deploy. `make migrate-data` runs the pending migrations.

For each configured extension the migration first lists the accounts that already have it (`installations` filtered by `extension.id`) and only creates the installation for accounts with an `Active` agreement that are missing it — avoiding a create attempt per already-installed account. Creation stays idempotent (a `409 CONFLICT` counts as already installed, as a safety net) and concurrency is bounded. Failures — a permanent per-account error, or an extension that cannot be resolved — do not abort the run: they are aggregated and logged at `error` level, and the migration still completes.

## Documentation Rule

When repository-specific migration behavior is introduced or changed, update this document in the same change.

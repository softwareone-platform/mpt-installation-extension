# Deployment

This document describes runtime configuration.

It is the source of truth for environment parameters referenced by local development and deployment flows.

## Configuration Source

The repository runtime expects environment variables, typically provided through `.env` for local Docker Compose usage.

Local setup instructions live in [docs/local-development.md](local-development.md).

## Core Application Settings

| Environment Variable | Default | Example | Description |
| --- | --- | --- | --- |
| `EXT_MPT_PRODUCT_EXTENSION_MAPPING` | - | `{"PRD-1111-1111":["EXT-1111-1112"]}` | JSON object mapping Marketplace product ids to one or more required extension ids |
| `EXT_MSTEAMS_WEBHOOK_URL` | - | `https://example.test/teams-webhook` | HTTPS Teams Workflows webhook URL used to notify non-recoverable installation failures; required and validated (`https://`) when notifications are enabled |
| `EXT_MSTEAMS_NOTIFICATIONS_ENABLED` | `false` | `true` | Master switch for the Teams channel; when `false` the channel is not registered and the extension logs a warning instead of sending |
| `SDK_EXTENSION_API_KEY` | - | `<extension-api-key>` | API key used by the SDK extension runtime |
| `SDK_EXTENSION_ID` | - | `EXT-1111-1111` | Marketplace extension id used by the SDK runtime |
| `SDK_EXTENSION_URL` | - | `http://devmock:8000` | Base URL where the SDK runtime reaches the extension service or local mock |
| `MPT_API_BASE_URL` | `http://localhost:8000` | `http://devmock:8000` | SoftwareOne Marketplace API base URL |
| `MPT_TOOL_STORAGE_TYPE` | `local` | `local` | Storage type for MPT tools |
| `MPT_TOOL_STORAGE_AIRTABLE_API_KEY` | - | `<fake-airtable-api-key>` | Airtable API key when Airtable storage is enabled |
| `MPT_TOOL_STORAGE_AIRTABLE_BASE_ID` | - | `<fake-storage-airtable-base-id>` | Airtable base id when Airtable storage is enabled |
| `MPT_TOOL_STORAGE_AIRTABLE_TABLE_NAME` | - | `<fake-storage-airtable-table-name>` | Airtable table name when Airtable storage is enabled |

## Local Example

Example `.env` snippet:

```env
EXT_MPT_PRODUCT_EXTENSION_MAPPING={"PRD-1111-1111":["EXT-1111-1112"]}
EXT_MSTEAMS_NOTIFICATIONS_ENABLED=false
SDK_EXTENSION_API_KEY=<extension-api-key>
SDK_EXTENSION_ID=EXT-1111-1111
SDK_EXTENSION_URL=http://devmock:8000
MPT_API_BASE_URL=http://devmock:8000
MPT_TOOL_STORAGE_TYPE=local
MPT_TOOL_STORAGE_AIRTABLE_API_KEY=<fake-airtable-api-key>
MPT_TOOL_STORAGE_AIRTABLE_BASE_ID=<fake-storage-airtable-base-id>
MPT_TOOL_STORAGE_AIRTABLE_TABLE_NAME=<fake-storage-airtable-table-name>
```

`EXT_MPT_PRODUCT_EXTENSION_MAPPING` is parsed at startup. Each object key is a Marketplace
product id. Each value is expected to contain the extension ids that must be installed for client
accounts when agreements for that product become active. The extension subscribes only to agreement
activation events for the configured product ids.

The `MPT_TOOL_STORAGE_*` variables mirror the storage configuration documented in `mpt-tool`. When `MPT_TOOL_STORAGE_TYPE=local`, the Airtable variables may use local fake values. When `MPT_TOOL_STORAGE_TYPE=airtable`, set `MPT_TOOL_STORAGE_AIRTABLE_API_KEY`, `MPT_TOOL_STORAGE_AIRTABLE_BASE_ID`, and `MPT_TOOL_STORAGE_AIRTABLE_TABLE_NAME` together.

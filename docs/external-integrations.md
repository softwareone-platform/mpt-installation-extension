# External Integrations

This document describes repository-specific external integration boundaries.

Shared extension design guidance lives in:

- [standards/extensions-best-practices.md](https://github.com/softwareone-platform/mpt-extension-skills/blob/main/standards/extensions-best-practices.md)

## Local Mock

Local development uses WireMock under [`peripherals/devmock/`](../peripherals/devmock/).

The devmock fixtures are intentionally minimal. They support the agreement activation path used by the local Postman collection and should be updated when the local event flow needs additional Marketplace behavior.

The current local happy path returns an active agreement for product `PRD-1111-1111`, an empty installation search result, extension module data, and a created installation response.

The Teams webhook is not mocked locally: the shared notification package requires an `https://` webhook URL with a valid certificate, while devmock serves plain HTTP. Local setup keeps `EXT_MSTEAMS_WEBHOOK_URL` unset, so the non-recoverable failure requests in the Postman collection exercise the notification code path and the backend logs a warning instead of sending. To test a real delivery, point `EXT_MSTEAMS_WEBHOOK_URL` at a test Teams channel webhook and set `EXT_MSTEAMS_NOTIFICATIONS_ENABLED=true`.

## Notification Integration

Non-recoverable installation failures are represented as an `InstallationAction` handled by the pipeline hook. The hook sends a Microsoft Teams notification through the shared [`mpt-extension-contrib-custom-notifications`](https://github.com/softwareone-platform/mpt-extension-python-contrib/tree/main/custom-notifications) package (`teams` extra).

The notification is an Adaptive Card posted to a Teams Workflows webhook. It contains the extension id, agreement id, product id, client id, a timestamp, and one entry per failed extension with the error type and message.

Configuration:

- `EXT_MSTEAMS_WEBHOOK_URL`: HTTPS webhook URL. When unset or not an `https://` URL, the hook logs a warning instead of sending.
- `EXT_MSTEAMS_NOTIFICATIONS_ENABLED`: when `false` (default), the channel skips sends without failing the flow.

Webhook delivery errors are logged by the shared package and never interrupt the installation pipeline.

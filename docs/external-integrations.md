# External Integrations

This document describes repository-specific external integration boundaries.

Shared extension design guidance lives in:

- [standards/extensions-best-practices.md](https://github.com/softwareone-platform/mpt-extension-skills/blob/main/standards/extensions-best-practices.md)

## Local Mock

Local development uses WireMock under [`peripherals/devmock/`](../peripherals/devmock/).

The devmock fixtures are intentionally minimal. They support the agreement activation path used by the local Postman collection and should be updated when the local event flow needs additional Marketplace behavior.

The current local happy path returns an active agreement for product `PRD-1111-1111`, an empty installation search result, extension module data, and a created installation response.

## Notification Integration

Non-recoverable installation failures are currently represented as an `InstallationAction` handled by the pipeline hook. The Teams notification transport is not implemented in this repository change and should be documented here when it is added.

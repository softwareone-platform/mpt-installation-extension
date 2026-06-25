# External Integrations

This document describes repository-specific external integration boundaries.

Shared extension design guidance lives in:

- [standards/extensions-best-practices.md](https://github.com/softwareone-platform/mpt-extension-skills/blob/main/standards/extensions-best-practices.md)

## Notification Integration

Non-recoverable installation failures are currently represented as an `InstallationAction` handled by the pipeline hook. The Teams notification transport is not implemented in this repository change and should be documented here when it is added.

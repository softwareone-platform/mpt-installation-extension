# Local Development

This document describes how to run the repository locally in the supported Docker workflow.

## Prerequisites

- Docker with the `docker compose` plugin
- `make`

## Setup

Build the development image and install dependencies:

```bash
make build
```

## Running the Service

Start the service with Docker Compose:

```bash
make run
```

The service is exposed on `http://localhost:8080`.

Useful helper commands:

```bash
make bash
make shell
make down
```

## Running With Devmock

The local compose override starts WireMock as `devmock` on `http://localhost:8000`.

The sample environment in [`backend/.env.sample`](../backend/.env.sample) points `MPT_API_BASE_URL` and `SDK_EXTENSION_URL` to `http://devmock:8000` and configures product `PRD-1111-1111` to install extension `EXT-1111-1112`.

For a local event run, the mocked Marketplace fixtures provide:

- agreement lookup for `/public/v1/commerce/agreements/{agreement_id}`
- extension lookup for `/public/v1/integration/extensions/{extension_id}`
- empty installation lookup for `/public/v1/integration/installations`
- installation creation for `/public/v1/integration/installations`

The Postman collection in [`backend/docs/postman_collection.json`](../backend/docs/postman_collection.json) contains a local agreement activation event that matches these fixtures.

## Environment Parameters

Local startup requires an `.env` file consumed by Docker Compose.

The parameter reference lives in [docs/deployment.md](deployment.md). Use that document for:

- required and optional environment variables
- example values
- runtime-specific notes for Marketplace integration, webhook secrets, Airtable, and AppInsights

Do not duplicate the parameter reference in this file.

Adjust startup commands, URLs, and helper commands in this file if the target repository differs from the defaults documented here.

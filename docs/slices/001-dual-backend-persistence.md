---
type: slice
id: SLICE-DEMO-PERSISTENCE-ISOLATION
status: active
created: 2026-10-11
updated: 2026-10-11
owner: temperature-iot-system-demo
maturity: DISCOVERY
domains: [temperature, composition]
---

# Slice 001: Two backends, two databases

## Purpose

Prove the smallest disposable composition of the existing Temperature IoT backend:

```text
POST Home A reading → PostgreSQL A contains it → PostgreSQL B does not
POST Home B reading → PostgreSQL B contains it → PostgreSQL A does not
```

Both backends run the same container image. Only `DATABASE_*` and the Docker network change.

This slice stops before messaging. A producer, topic, queue, and consumer are the next slice.

## Scope

- Docker networks `home-a` and `home-b`
- `postgres:16` containers `postgres-a` and `postgres-b`
- Two containers from image `temperature-iot-backend:demo`
- Host HTTP endpoints published only on `127.0.0.1`
- Deterministic readings for `home-a` / living-room / 72.4 F and `home-b` / kitchen / 20.5 C
- Direct `psql` evidence, plus Docker DNS checks for the names each backend is allowed to use
- Scripts: start, status, seed, verify, stop, clean

## Non-goals

- Copying backend or Commons source into this repository
- Changing backend domain behavior
- SNS, SQS, Terraform, AWS, Ansible
- Kubernetes, NetworkPolicy, namespaces, or a second cluster
- A messaging emulator, producer, or consumer
- Authentication, persistent production data, or a shared database

## Acceptance criteria

- `backend-a` and `backend-b` use the same image id
- `backend-a` is configured with `DATABASE_HOST=postgres-a` and `DATABASE_NAME=temperature_a`
- `backend-b` is configured with `DATABASE_HOST=postgres-b` and `DATABASE_NAME=temperature_b`
- The Home A reading is present in PostgreSQL A and absent from PostgreSQL B
- The Home B reading is present in PostgreSQL B and absent from PostgreSQL A
- `backend-a` resolves `postgres-a` and does not resolve `postgres-b`
- `backend-b` resolves `postgres-b` and does not resolve `postgres-a`
- Contract tests reject a compose file that points both backends at one database or one network

## Risks / Guardrails

- `house_id` is application data. This backend will store whatever house id is posted. Isolation here is deployment isolation: which process and which database received the call.
- Published HTTP ports are an observation path for the host. Docker network separation does not stop the host from calling either port.
- A container that can reach the host gateway might also reach the other published port. This slice does not claim Kubernetes NetworkPolicy or host-firewall isolation.
- The local database password is disposable demo material. It is not a production secret and must not be reused outside this composition.
- The image build reads the external backend and Commons checkouts. It does not vendor them here.
- Repeated `seed` appends another row when the deterministic reading is already present only if the ensure check fails. The ensure check skips a POST when that exact reading is already stored.

## Resume point

Stage 4: add a local topic and two queues. Then a dumb producer and a consumer that POSTs `TemperatureReading` to the backend HTTP API. Do not write PostgreSQL from the consumer.

# Temperature IoT system demo

This directory composes the existing Temperature IoT backend into a disposable local system.

It is not the backend and not the UML model. The folder currently sits at `33_Architecture/temperature-iot` because that is the working directory opened for this project. The parent architecture space describes systems. These files are the demonstration. AWS messaging for this demo is an isolated Terraform root under `infra/aws-messaging`. It does not call the shared module repository.

```text
33_Architecture              describes logical architecture
temperature-iot-system-demo  this directory: local compositions and proofs
temperature-iot-backend      ingestion and query behavior
01_Terraform                 reusable infrastructure modules
```

## What is running in slice 001

```text
127.0.0.1:18081 → backend-a → postgres-a / temperature_a
127.0.0.1:18082 → backend-b → postgres-b / temperature_b
```

Both backends are the image `temperature-iot-backend:demo`, built from the external backend checkout. Home A and Home B differ by Docker network and `DATABASE_*` only.

Messaging, producers, and consumers are not in this slice. The host posts directly to each backend. That is the stand-in for a later consumer.

## Reuse

| Existing piece | How this demo uses it |
| --- | --- |
| `21_PythonProjects/temperature-iot-backend` | Image build input. `POST /temperatures`, `TemperatureReading`, `DATABASE_*`, `serve --host --port`. |
| `06_Common/compute-manager` and `uapi-adapter` | Installed into that image because the backend already depends on them. |
| `postgres:16` | The database named in the backend's local run instructions. Two containers, not the already running `temperature-iot-postgres`. |
| `01_Terraform` SNS, SQS, EKS, and RDS modules | Named in `architecture/uml-handoff.md` only. Not copied or applied. |
| `34_UML/architectures/messaging` | Existing SNS/SQS module references for the later handoff. Not modified. |

No backend Dockerfile, Kubernetes manifest, or temperature Terraform composition existed to reuse. This demo supplies the Dockerfile and Compose file. It does not copy application source into the tree.

## Isolation that exists

- Separate Docker networks, so `backend-a` cannot resolve `postgres-b`
- Separate PostgreSQL servers and database names
- Separate `DATABASE_HOST` and `DATABASE_NAME`

The backend does not reject a foreign `house_id`. A reading posted to backend A is stored in database A. The host can call both published HTTP ports; that is how the proof is observed.

## Commands

From this directory:

```powershell
.\scripts\start.ps1
.\scripts\seed.ps1
.\scripts\verify.ps1
.\scripts\status.ps1
.\scripts\stop.ps1
.\scripts\clean.ps1
```

Bash equivalents are `scripts/start.sh` and the matching names. `start --rebuild` builds the image again.

Overrides for the image build:

```text
TEMPERATURE_IOT_BACKEND
COMMONS_REPO
```

The local database password is `local-demo-pw`. It is disposable and must not be reused outside this composition.

Contract checks, with or without the stack:

```powershell
python -m tests.contract.test_reading_catalog
python -m tests.contract.test_compose_topology
```

Details: `docs/slices/001-dual-backend-persistence.md` and `architecture/`.

## AWS messaging

Slice 002 prepares SNS `temperature-readings` and queues `temperature-home-a` and `temperature-home-b`, plus a dead-letter queue for each home. Commands and teardown are in `infra/aws-messaging/README.md`.

Slice 003 adds one local SQS adapter, `python -m temperature_demo.sqs_adapter`. Home A and Home B are two processes with different environment variables. The adapter POSTs `/temperatures`. It does not open PostgreSQL, and the backend does not import boto3.

```powershell
python -m tests.contract.test_messaging_root
python -m tests.contract.test_sqs_adapter
python -m temperature_demo.sqs_adapter --help
```

Apply the queues only after `aws sts get-caller-identity --profile temperature-iot-terraform` shows account `206858211930` and the Terraform plan has been reviewed. The live fan-out procedure is in `docs/slices/003-sqs-consumer-adapter.md`.

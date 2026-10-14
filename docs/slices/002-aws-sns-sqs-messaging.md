---
type: slice
id: SLICE-DEMO-AWS-MESSAGING
status: active
created: 2026-10-14
updated: 2026-10-14
owner: temperature-iot-system-demo
maturity: DISCOVERY
domains: [temperature, messaging, aws]
---

# Slice 002: SNS to two SQS queues

## Purpose

Stand up one isolated AWS messaging path for the existing Temperature IoT demo:

```text
Temperature Event Producer
          |
          v
    SNS temperature-readings
          |
     +----+----+
     |         |
     v         v
  SQS home-a  SQS home-b
```

One publish must arrive, independently, in both queues, with raw message delivery. Consumers stay undeployed.

## Repository assessment

Observed before this slice wrote any infrastructure.

| Piece | Where | What exists | What this slice does with it |
| --- | --- | --- | --- |
| Local composition | this directory | Two containers of `temperature-iot-backend:demo`, two PostgreSQL 16 databases, host ports `127.0.0.1:18081` and `127.0.0.1:18082` | Leave it alone |
| Backend application | `C:\Users\jonat\Projects\20_Applications\21_PythonProjects\temperature-iot-backend` | `TemperatureReading` (`house_id`, `sensor_id`, `temperature`, `unit`, `observed_at`), `POST /temperatures`, `DATABASE_*`, entry `python -m temperature_iot_backend serve` | Do not modify |
| Backend AWS adapter | that repository | None. No boto, SNS, SQS, or MQTT in `src` or `pyproject.toml` | Do not add one |
| Image build | `docker/backend.Dockerfile` | `python:3.12-slim-bookworm`, copies the external backend plus Commons `compute-manager` and `uapi-adapter`, entrypoint `python -m temperature_iot_backend` | Do not change |
| Default backend path | `temperature_demo.config.DEFAULT_BACKEND_RELATIVE` | `../../21_PythonProjects/temperature-iot-backend`, which resolves under `00_System` and is not present | Document only. The checkout that exists is `20_Applications\21_PythonProjects\temperature-iot-backend` |
| Shared Terraform SNS module | `10_Infrastructure\01_Terraform\terraform-modules\modules\aws\messaging\sns` | Topic name and tags. Outputs `topic_arn`, `topic_name`. A `.terraform` directory is already inside the module | Not a prerequisite |
| Shared Terraform SQS module | `...\messaging\sqs` | Queue name and tags. Outputs ARN, URL, and name. No DLQ, no redrive, no queue policy. A `.terraform` directory is already inside the module | Not a prerequisite |
| SNS to SQS binding module | `...\messaging\sns-sqs-binding`, named by `34_UML\architectures\messaging\architecture.yaml` | Directory is absent | Not a prerequisite |
| This directory before the slice | — | No `.tf` files | Add an isolated root under `infra/aws-messaging` |

The shared modules are thin and were not applied from this demo. They do not express subscriptions, raw delivery, dead-letter queues, or a topic-scoped queue policy. This slice does not edit `01_Terraform` or the backend.

## Scope

- Isolated Terraform root `infra/aws-messaging`
- SNS topic `temperature-readings`
- SQS queues `temperature-home-a` and `temperature-home-b`
- Dead-letter queues `temperature-home-a-dlq` and `temperature-home-b-dlq`
- One SNS subscription per queue, `raw_message_delivery = true`
- Queue policy: `sqs:SendMessage` only for `sns.amazonaws.com` when `aws:SourceArn` is this topic
- Region and names configurable. Defaults: `us-west-2` and the names above
- Outputs for topic ARN, queue URLs, queue ARNs, and DLQ URLs
- Operator command `python -m temperature_demo.aws_verify`
- AWS CLI profile name `temperature-iot-demo` (region only until keys exist)

## Non-goals

- Editing `temperature-iot-backend`, Commons, `01_Terraform`, or `34_UML`
- Consuming the shared SNS or SQS modules
- EKS, RDS, ECR, AWS IoT Core, MQTT, or Kubernetes
- Changing the running Compose services or the backend image
- A consumer process
- Static credentials in Git or in Terraform
- Applying infrastructure before `aws sts get-caller-identity` returns the intended new account

## Acceptance criteria

Local, without an AWS account:

- `python -m tests.contract.test_messaging_root` passes
- `python -m temperature_demo.aws_verify --help` does not call AWS
- `terraform fmt -check`, `terraform init`, `terraform validate`, and `terraform test` succeed in `infra/aws-messaging`

After the new account is on profile `temperature-iot-demo`:

- `aws sts get-caller-identity` prints that account
- `terraform plan` shows only the topic, two queues, two dead-letter queues, two policies, and two subscriptions
- After an approved apply, one publish of `events/demo-001.json` is accepted by SNS
- Home A and Home B each receive that JSON as the message body, not an SNS envelope
- Each queue policy names this topic ARN and has no public principal
- Both messages can be deleted

## Observed 2026-10-14

Local checks passed. AWS was not changed.

- AWS CLI 2.24.2. Terraform 1.10.5. Provider lock `hashicorp/aws` 5.100.0.
- Profile `temperature-iot-demo` has region `us-west-2` and no access key.
- `aws sts get-caller-identity --profile temperature-iot-demo` returned `Unable to locate credentials`.
- `terraform fmt -check`, `terraform init`, `terraform validate`, and `terraform test` passed. The test run is `fanout_is_raw_and_named`.
- `terraform plan -input=false` failed with `No valid credential sources found` for the AWS provider. No resources were planned to completion and nothing was applied.
- SNS publish was not run. Queue delivery was not observed.

## Risks / Guardrails

- The demo event is not a `TemperatureReading`. It has `event_id` and `device_id`. The backend requires `house_id` and `sensor_id`. A future consumer maps `device_id` to `sensor_id` and sets `house_id` from `HOME_ID`. It does not POST the SNS body unchanged.
- Both queues receive the same event. House identity is the consumer configuration, not a field that differs inside one fan-out.
- The consumer must call the backend HTTP API. It must not open PostgreSQL. That boundary is already true for slice 001's host client.
- Dead-letter redrive stays in the same account. The DLQ allow policy uses `byQueue` and the source queue ARN. SNS does not write to the DLQ.
- Queue policies grant send only to this topic. They do not grant `Principal *`.
- Terraform state is local. It is gitignored. It can contain account identifiers. Do not commit it.
- Do not point this root at `peptide-tracker`, `simple-peptide`, `n8n-manager`, or any other existing CLI profile.
- SNS, SQS, and a few CLI calls are the only AWS cost. Do not add EKS or RDS under this slice.

## Future container configuration

Same image `temperature-iot-backend:demo`. No image change in this slice.

```text
Consumer A
  HOME_ID=home-a
  SQS_QUEUE_URL=<home-a queue url>
  BACKEND_BASE_URL=http://127.0.0.1:18081
  AWS_REGION=us-west-2

Consumer B
  HOME_ID=home-b
  SQS_QUEUE_URL=<home-b queue url>
  BACKEND_BASE_URL=http://127.0.0.1:18082
  AWS_REGION=us-west-2
```

Proposed lifecycle, not implemented:

1. Long-poll `ReceiveMessage` on `SQS_QUEUE_URL`.
2. Parse the body as JSON. Reject an SNS envelope (`Type` = `Notification`).
3. Require `event_id`, `device_id`, `temperature`, `unit`, and `observed_at`.
4. Build a `TemperatureReading`: `house_id` from `HOME_ID`, `sensor_id` from `device_id`, and copy `temperature`, `unit`, and `observed_at`.
5. `POST /temperatures` on `BACKEND_BASE_URL`.
6. Delete the SQS message only after HTTP success.
7. Leave the message in flight on failure. After `max_receive_count` (5), SQS moves it to that home's DLQ.

Credentials for a later workload come from an IAM role, not from this Terraform root.

## Later infrastructure

Documented only:

1. Containerized SQS consumers using the environment above
2. ECR publication of `temperature-iot-backend:demo`
3. RDS PostgreSQL in place of the two local `postgres:16` containers, still behind `DATABASE_*`
4. EKS deployments of the same image, one configuration per home
5. IAM roles for Kubernetes service accounts
6. AWS IoT Core and MQTT in front of the SNS topic
7. Observability and scaling

Moving the working resources into `01_Terraform` waits until that module tree is reviewed against this root. Environment names, region, and profile stay outside reusable modules.

## Resume point

`temperature-iot-demo` is region `us-west-2` and has no access keys. `aws sts get-caller-identity` did not return an account. Do not apply. After the new account is configured on that profile and `sts get-caller-identity` shows it, review `terraform plan`, then apply, then `python -m temperature_demo.aws_verify`.

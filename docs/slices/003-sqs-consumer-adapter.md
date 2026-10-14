---
type: slice
id: SLICE-DEMO-SQS-ADAPTER
status: active
created: 2026-10-14
updated: 2026-10-14
owner: temperature-iot-system-demo
maturity: DISCOVERY
domains: [temperature, messaging]
---

# Slice 003: SQS consumer adapter

## Purpose

Run one Python program twice. Each process reads one SQS queue, maps the event with its own `HOME_ID`, and POSTs a `TemperatureReading` to that home's existing backend.

```text
SQS queue
    |
    v
Python adapter  (same code, different environment)
    |
    v
POST /temperatures
    |
    v
temperature-iot-backend
    |
    v
PostgreSQL
```

The backend stays unaware of SNS, SQS, and boto3.

## Scope

- Package `temperature_demo.sqs_adapter`
- Environment: `HOME_ID`, `SQS_QUEUE_URL`, `BACKEND_URL`, `AWS_REGION`, optional `AWS_PROFILE`
- Validate the queue event, transform it, POST it, delete the SQS message only after HTTP success
- Unit tests with a fake queue and a fake HTTP poster
- Operator instructions for two local processes and for a later live fan-out

## Non-goals

- Editing `temperature-iot-backend` or adding boto3 there
- Editing `01_Terraform`
- Container images, Lambda, ECS, EKS, RDS, ECR, MQTT, or IoT Core
- Recreating the destroyed SNS/SQS resources inside this slice's implementation step
- Durable idempotency in PostgreSQL

## Acceptance criteria

- `python -m tests.contract.test_sqs_adapter` passes with no AWS account and no running backend
- `python -m temperature_demo.sqs_adapter --help` does not read queue URLs or call AWS
- `process_message` validates, transforms, and POSTs, and does not import boto3
- A successful POST deletes that receipt handle
- A validation error, malformed body, or HTTP failure leaves the receipt handle in place
- The posted `house_id` is the configured `HOME_ID`, including when the event carries a different `house_id`
- Missing `observed_at`, missing identifiers, unsupported units, and timezone-less timestamps fail
- The same function serves Home A and Home B when the arguments differ

Live AWS proof is separate. It is not met until both HTTP responses, both database rows, and both SQS deletes have been observed.

## Risks / Guardrails

- SQS is at-least-once. The backend `temperature_reading` table has no uniqueness on the producer event. `id` is a new UUID on every `record` call. `event_id` is not a column. A crash after a successful POST and before `DeleteMessage` stores a second row on redelivery. This slice does not change that schema.
- Failed processing does not delete. The queue visibility timeout hides the message, then SQS delivers it again. `max_receive_count` is 5, so the sixth failure path moves it to that home's dead-letter queue (`temperature-home-a-dlq` or `temperature-home-b-dlq`). The adapter does not read the dead-letter queue.
- Raw delivery is required. An SNS envelope (`Type` = `Notification`) is a failure and is left on the queue.
- Credentials come from the AWS CLI chain. `AWS_PROFILE` selects a profile when set. The program never stores access keys.
- The adapter does not open PostgreSQL. Isolation remains the backend's `DATABASE_*` configuration.
- Slice 004: if an event includes `house_id`, it must equal `HOME_ID`. A mismatch is not posted and not deleted. Events that omit `house_id` still use `HOME_ID`, which keeps the broadcast samples valid.

## Message mapping

```text
HOME_ID           → house_id
event.device_id   → sensor_id
event.temperature → temperature
event.unit        → unit
event.observed_at → observed_at
```

`event_id` is required and logged. It is not sent to the backend.

## Processing

```text
long-poll one message
    → decode JSON
    → validate
    → POST /temperatures with a 10 second timeout
    → HTTP success: DeleteMessage
    → failure: log and leave the message
```

Long polling waits 20 seconds, so an empty queue does not spin. Ctrl+C stops the loop. A receive that is already in flight returns when SQS answers or the wait ends.

## Later deployments

Same `process_message` function. Not implemented here.

- Compose runs two containers of one image. `BACKEND_URL` uses the Compose service name (`http://backend-a:8000`, `http://backend-b:8000`).
- Lambda receives an SQS batch from an event source mapping and calls `process_message` per record. Lambda must not call `DeleteMessage`. Return the failed message ids in the batch-item failure response so AWS retries those records.
- EKS runs two deployments, each with `HOME_ID`, `SQS_QUEUE_URL`, and an IAM role that can receive and delete on that queue only.

## Observed 2026-10-14

`python -m tests.contract.test_sqs_adapter` passed without the backends. `python -m temperature_demo.sqs_adapter --help` exited locally.

`aws sts get-caller-identity --profile temperature-iot-terraform` returned account `206858211930`. `terraform plan -input=false -var="aws_profile=temperature-iot-terraform"` reported `Plan: 9 to add, 0 to change, 0 to destroy` in `us-east-2` (topic, two queues, two dead-letter queues, two policies, two raw subscriptions). That plan was not applied. SNS publish, HTTP responses, PostgreSQL rows, and SQS deletes for `demo-002` were not observed.

## Resume point

Review `terraform plan -input=false -var="aws_profile=temperature-iot-terraform"` for account `206858211930` in `us-east-2`. Apply only after that review. Then start both backends and both adapter processes, publish `events/demo-002.json`, and record HTTP, PostgreSQL, and SQS results.

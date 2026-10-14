# AWS messaging demo

Isolated SNS → SQS root for the Temperature IoT demo. It does not deploy EKS, RDS, or the application containers.

```text
SNS temperature-readings
        |
   +----+----+
   |         |
   v         v
 home-a    home-b
   |         |
  DLQ       DLQ
```

Both queues get the same event. Raw message delivery is on, so the SQS body is the published JSON.

## Account

Use profile `temperature-iot-terraform` in region `us-east-2`. The account for this demo is `206858211930`. Do not reuse peptide, n8n, or other project profiles.

```powershell
aws sts get-caller-identity --profile temperature-iot-terraform
```

Stop if the account id is not `206858211930`. Access keys stay in the AWS CLI configuration, not in this directory.

The Terraform default profile in `variables.tf` is still `temperature-iot-demo`. Pass the profile explicitly:

```powershell
terraform plan -input=false -var="aws_profile=temperature-iot-terraform"
```

## Deploy

From this directory (`infra/aws-messaging`):

```powershell
terraform fmt -check
terraform init
terraform validate
terraform test
terraform plan -input=false -var="aws_profile=temperature-iot-terraform"
```

Review the plan. It should add one topic, two queues, two dead-letter queues, two queue policies, and two subscriptions. Apply only after that review:

```powershell
terraform apply -input=false -var="aws_profile=temperature-iot-terraform"
```

Useful outputs:

```powershell
terraform output topic_arn
terraform output home_a_queue_url
terraform output home_b_queue_url
terraform output consumer_a_environment
terraform output consumer_b_environment
```

Copy `terraform.tfvars.example` to `terraform.tfvars` only when overriding region, profile, or names. `terraform.tfvars` is gitignored.

## Publish and prove delivery

From the repository root, after apply:

```powershell
python -m temperature_demo.aws_verify --profile temperature-iot-terraform --region us-east-2
```

The command publishes `events/demo-001.json`, reads each queue, checks that the body equals that JSON, checks that the queue policy allows only this topic, and deletes both messages.

Equivalent AWS CLI, from this directory, after substituting the outputs:

```powershell
aws sns publish --profile temperature-iot-terraform --region us-east-2 `
  --topic-arn <topic_arn> `
  --message file://events/demo-001.json

aws sqs receive-message --profile temperature-iot-terraform --region us-east-2 `
  --queue-url <home_a_queue_url> --max-number-of-messages 1 --wait-time-seconds 10

aws sqs receive-message --profile temperature-iot-terraform --region us-east-2 `
  --queue-url <home_b_queue_url> --max-number-of-messages 1 --wait-time-seconds 10
```

A raw body looks like the file. An SNS envelope has top-level `Type` = `Notification` and `TopicArn`. That means raw delivery is off.

Delete with the `ReceiptHandle` from each receive:

```powershell
aws sqs delete-message --profile temperature-iot-terraform --region us-east-2 `
  --queue-url <queue_url> --receipt-handle <receipt_handle>
```

## Teardown

```powershell
terraform destroy
```

Review the destroy plan before confirming. Local state is `terraform.tfstate` in this directory. Do not commit it.

## Local consumers

One program, two processes. From the repository root, start the backends with `.\scripts\start.ps1`. Install `boto3` in the interpreter that runs the adapter. The unit tests do not import it, and the backend image does not need it.

```powershell
$env:HOME_ID = "home-a"
$env:SQS_QUEUE_URL = "<home_a_queue_url>"
$env:BACKEND_URL = "http://127.0.0.1:18081"
$env:AWS_REGION = "us-east-2"
$env:AWS_PROFILE = "temperature-iot-terraform"
python -m temperature_demo.sqs_adapter
```

Home B uses `HOME_ID=home-b`, the Home B queue URL, and `BACKEND_URL=http://127.0.0.1:18082`.

`HOME_ID` becomes `house_id`. `device_id` becomes `sensor_id`. `temperature`, `unit`, and `observed_at` are copied. `event_id` is required and is not sent to the backend. Broadcast events omit `house_id`, and the adapter fills it from `HOME_ID`. If the event includes `house_id`, it must equal `HOME_ID`; a mismatch is left on the queue and is not posted. The home-filtered topic is `infra/aws-messaging-routing`.

The worker long-polls for 20 seconds, one message at a time. The HTTP timeout is 10 seconds. It deletes the SQS message only after `POST /temperatures` returns that same `house_id`. Validation errors, malformed JSON, SNS envelopes, and HTTP failures leave the message in place. The queue visibility timeout then makes it visible again. After 5 receives, SQS moves it to that home's dead-letter queue. The adapter does not read the dead-letter queue.

SQS can deliver the same message again when the process stops after the POST and before the delete. The backend inserts a new row and a new id on every successful POST. `event_id` is not a stored column, so a repeated delivery can create a second row. Ctrl+C stops the loop after the current long poll returns.

## Live fan-out

Run this only after `python -m tests.contract.test_sqs_adapter` passes and a human has reviewed the plan. The earlier queues were destroyed.

1. Confirm account `206858211930` with `aws sts get-caller-identity --profile temperature-iot-terraform`.
2. Review and apply with `-var="aws_profile=temperature-iot-terraform"`.
3. Read `topic_arn`, `home_a_queue_url`, and `home_b_queue_url`.
4. Start both backends.
5. Start both adapter processes.
6. Publish `events/demo-002.json` to the topic.
7. Both adapters log `outcome=deleted`.
8. PostgreSQL A contains the Home A row and PostgreSQL B contains the Home B row: `sensor_id` `thermostat-001`, `72.4`, `F`, `2026-10-14T15:00:00Z`.
9. Both source queues are empty.
10. Stop one backend, publish again, and confirm that home logs `outcome=retained` while its queue still holds the message.

The unit tests already cover delete-on-success and retain-on-failure. They do not replace steps 7–10.

Compose, Lambda, and EKS can call `process_message` later. Lambda must not delete messages itself; it reports batch item failures. Those deployments are not in this slice.

Details: `docs/slices/003-sqs-consumer-adapter.md`.

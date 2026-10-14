# Home-routed AWS messaging

Selective SNS to SQS deployment. It is separate from the broadcast root `infra/aws-messaging`.

```text
SNS temperature-readings-routing
        |
        |  message body house_id
        +------------------+
        |                  |
        v                  v
 temperature-routing-   temperature-routing-
 home-a                 home-b
```

Shared modules:

```text
10_Infrastructure/01_Terraform/terraform-modules/modules/aws/messaging/sns
10_Infrastructure/01_Terraform/terraform-modules/modules/aws/messaging/sqs
10_Infrastructure/01_Terraform/terraform-modules/modules/aws/messaging/sns-sqs-binding
```

The map key in `homes` is the filter value. `home-a` is not built into the modules.

## Account

```powershell
aws sts get-caller-identity --profile temperature-iot-terraform
```

Stop unless the account is `206858211930`. Region `us-east-2`. This directory has its own state. Do not copy state from `infra/aws-messaging`.

## Check and plan

From this directory:

```powershell
terraform fmt -check
terraform init
terraform validate
terraform test
terraform plan -input=false "-out=create.tfplan"
terraform show create.tfplan
```

`create.tfplan` is gitignored. Apply only after the plan is reviewed:

```powershell
terraform apply -input=false create.tfplan
```

The plan should add one topic, two queues, two dead-letter queues, two queue policies, and two filtered subscriptions. It should not name `temperature-readings`, `temperature-home-a`, or `temperature-home-b`.

## Samples

| File | `house_id` | Expected queue |
| --- | --- | --- |
| `events/routing-home-a-001.json` | `home-a` | Home A only |
| `events/routing-home-b-001.json` | `home-b` | Home B only |
| `events/routing-unknown-001.json` | `unknown` | neither |
| `events/routing-missing-house-001.json` | absent | neither |

Wait briefly after apply before treating a missing message as proof. SNS filter policies can lag.

Publish with the topic ARN from `terraform output -raw topic_arn`. Read each queue with its own URL and a unique `event_id`. Do not delete a message until the body has been recorded.

## Adapters

Same program as the broadcast path. `HOME_ID` must match a present `house_id`. An event with no `house_id` still uses `HOME_ID`, which is how `infra/aws-messaging` stays compatible. A mismatch is not posted and not deleted.

```powershell
$env:HOME_ID = "home-a"
$env:SQS_QUEUE_URL = "<home_a_queue_url>"
$env:BACKEND_URL = "http://127.0.0.1:18081"
$env:AWS_REGION = "us-east-2"
$env:AWS_PROFILE = "temperature-iot-terraform"
python -m temperature_demo.sqs_adapter
```

Home B uses `home-b`, the Home B queue URL, and `http://127.0.0.1:18082`.

## Destroy

After the live check, save a destroy plan and read it before applying:

```powershell
terraform plan -destroy -input=false "-out=destroy.tfplan"
terraform show destroy.tfplan
terraform apply -input=false destroy.tfplan
```

Confirm the plan names only `temperature-readings-routing` and the `temperature-routing-home-*` queues.

## IAM

The binding module writes the queue policy that allows this topic to send. It does not create roles.

Deployment uses the CLI profile to create and delete topics, queues, subscriptions, and queue policies, plus `sts:GetCallerIdentity`.

The adapter needs receive, delete, change-visibility, and get-attributes on its queue. A publisher needs `sns:Publish` on this topic. Those grants are not in this root.

Details: `docs/slices/004-sns-home-routing.md`.

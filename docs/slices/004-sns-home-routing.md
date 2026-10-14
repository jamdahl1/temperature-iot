---
type: slice
id: SLICE-DEMO-SNS-HOME-ROUTING
status: active
created: 2026-10-14
updated: 2026-10-14
owner: temperature-iot-system-demo
maturity: DISCOVERY
domains: [temperature, messaging, terraform]
---

# Slice 004: Home-routed SNS delivery

## Purpose

Deliver each temperature event to the SQS queue whose home matches `house_id`, using shared Terraform modules. The broadcast root `infra/aws-messaging` stays as it is.

```text
SNS temperature-readings-routing
        |
        |  message body filter house_id
        |
        +------------------+
        |                  |
        v                  v
 temperature-routing-   temperature-routing-
 home-a                 home-b
        |                  |
       DLQ                DLQ
```

## Module boundaries

Shared modules live in `10_Infrastructure/01_Terraform/terraform-modules/modules/aws/messaging`. They do not own state and do not name homes.

| Module | Owns | Leaves to the deployment |
| --- | --- | --- |
| `sns` | One topic. Inputs: `name`, `tags`. Outputs: `topic_arn`, `topic_name`. | Subscriptions |
| `sqs` | One queue. Inputs: `name`, `tags`, optional `redrive_policy`, optional `redrive_allow_policy`. Outputs: `queue_arn`, `queue_url`, `queue_name`. | Which queue is the dead-letter target |
| `sns-sqs-binding` | One subscription, raw delivery, and an SQS policy that allows `sqs:SendMessage` only from `topic_arn`. Optional `filter_policy` plus `filter_policy_scope`. Output: `subscription_arn`. | The filter values, including `house_id` |

A dead-letter queue is another `sqs` instance. The routing root passes the source queue ARN into the DLQ allow policy and the DLQ ARN into the source queue redrive policy. That avoids a second queue implementation.

`infra/aws-messaging` keeps its inline resources. Moving it onto these modules would change resource addresses in a root that already has state. No `moved` blocks are added there.

## Scope

- Extend `sqs` with optional redrive arguments. Defaults stay unset.
- Add `sns-sqs-binding`.
- Rewrite only `infra/aws-messaging-routing` so it calls those modules.
- Names: `temperature-readings-routing`, `temperature-routing-home-a`, `temperature-routing-home-b`, and matching `-dlq` queues.
- Sample events with `house_id`.
- Adapter rule: a present `house_id` must equal `HOME_ID`. An absent `house_id` still uses `HOME_ID`, so the broadcast events keep working.

## Non-goals

- Editing `infra/aws-messaging` resource addresses or its state
- Applying or destroying either root in this slice
- Copying `.terraform/` or `terraform.tfstate`
- Importing broadcast resources
- Backend changes, IoT Core, MQTT, Lambda, EKS, RDS
- An IAM role for Terraform or for the adapter

## Acceptance criteria

- `terraform fmt -check`, `init`, `validate`, and `test` pass in `infra/aws-messaging-routing` without creating AWS resources
- The routing test checks topic name, both queues, both DLQs, raw delivery, `MessageBody` filters for `home-a` and `home-b`, topic-scoped send, and names that differ from the broadcast root
- `python -m tests.contract.test_sqs_adapter` passes
- A present mismatched `house_id` is not posted and not deleted
- An event with no `house_id` still posts `HOME_ID`
- `terraform plan -out=create.tfplan` for the routing root is reviewed and not applied

## State

Both `terraform.tfstate` files currently list zero resources and share lineage `945f3168-0dca-2528-3124-79a0ad37e4d2`. The routing file is a copy of the broadcast file. Nothing live is tracked, so this slice does not migrate addresses. The routing root keeps its own file. Later applies must use different AWS names, which this composition does.

## IAM

The queue policy is the SNS-to-SQS grant. It is not a deployment role and not the adapter's role.

Deployment identity needs to create and destroy topics, queues, queue policies, and subscriptions, and to call `sts:GetCallerIdentity`. Useful operations: `sns:CreateTopic`, `sns:DeleteTopic`, `sns:GetTopicAttributes`, `sns:Subscribe`, `sns:Unsubscribe`, `sns:GetSubscriptionAttributes`, `sns:SetSubscriptionAttributes`, `sns:TagResource`, `sns:UntagResource`, `sqs:CreateQueue`, `sqs:DeleteQueue`, `sqs:GetQueueAttributes`, `sqs:SetQueueAttributes`, `sqs:GetQueueUrl`, `sqs:TagQueue`, `sqs:UntagQueue`, `sqs:ListQueueTags`.

The running adapter needs `sqs:ReceiveMessage`, `sqs:DeleteMessage`, `sqs:ChangeMessageVisibility`, and `sqs:GetQueueAttributes` on its one queue. A publisher needs `sns:Publish` on the routing topic. Those roles are not created here.

`house_id` in the event is a routing label. A later gateway should set it from authenticated device ownership. The adapter still refuses a value that disagrees with `HOME_ID`.

## Risks / Guardrails

- Broadcast and routing are different contracts. Broadcast events omit `house_id`. Routing events include it. The adapter rejects a mismatch instead of rewriting it.
- SNS filter changes can take a short time to apply. A negative delivery check that runs immediately can be wrong.
- Do not apply `infra/aws-messaging` and this root against the same topic or queue names.
- `create.tfplan` and state stay untracked.
- Destroy only after `terraform plan -destroy -out=destroy.tfplan` shows this root's resources.

## Observed 2026-10-14

`terraform fmt -check`, `validate`, and `test` passed in `infra/aws-messaging-routing`. `python -m tests.contract.test_routing_composition` and `python -m tests.contract.test_sqs_adapter` passed.

`aws sts get-caller-identity --profile temperature-iot-terraform` returned account `206858211930`. `terraform plan -input=false -out=create.tfplan` reported `Plan: 9 to add, 0 to change, 0 to destroy` for `temperature-readings-routing` and the `temperature-routing-home-*` queues. The plan was not applied. Queue delivery was not observed.

## Resume point

Review `infra/aws-messaging-routing/create.tfplan`. Apply only after that review. Then publish the sample events and record which queue received each one before starting the two adapter processes.

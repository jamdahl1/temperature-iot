# UML handoff

The demo does not edit the Architecture/UML model.

A later update can add a temperature system whose logical nodes have more than one implementation. The messaging model already records SNS and SQS module references. Reuse those references. Do not invent a second copy of the Terraform modules.

Validation below is for slice 001. `validated` means `verify` passed on the local Docker run of 2026-10-11.

| Logical node | Local implementation | Deployment mode | Network relationship | Validation | Possible Terraform reference |
| --- | --- | --- | --- | --- | --- |
| `temperature-producer` | none yet | — | will publish to the topic | planned | not a Terraform concern until a device path exists |
| `messaging-topic` | none yet | — | one topic, two queues | planned | `01_Terraform/terraform-modules/modules/aws/messaging/sns` |
| `home-a-queue` | none yet | — | subscribed to the topic, consumed by Home A | planned | `01_Terraform/terraform-modules/modules/aws/messaging/sqs` |
| `home-b-queue` | none yet | — | subscribed to the topic, consumed by Home B | planned | `01_Terraform/terraform-modules/modules/aws/messaging/sqs` |
| `home-a-consumer` | none yet | — | will POST to `home-a-backend` | planned | EKS workload, not defined here |
| `home-b-consumer` | none yet | — | will POST to `home-b-backend` | planned | EKS workload, not defined here |
| `home-a-backend` | container `temperature-demo-backend-a`, image `temperature-iot-backend:demo` | Docker network `temperature-demo-home-a` | listens on container port 8000; host `127.0.0.1:18081`; `DATABASE_HOST=postgres-a` | validated | `01_Terraform/terraform-modules/modules/aws/compute/eks` for a later workload, image still built from `temperature-iot-backend` |
| `home-b-backend` | container `temperature-demo-backend-b`, same image | Docker network `temperature-demo-home-b` | host `127.0.0.1:18082`; `DATABASE_HOST=postgres-b` | validated | same EKS module, different configuration |
| `home-a-database` | `postgres:16` container `temperature-demo-postgres-a`, database `temperature_a` | Docker network `temperature-demo-home-a` | port 5432 on that network only; not published on the host | validated | `01_Terraform/terraform-modules/modules/aws/data/rds` |
| `home-b-database` | `postgres:16` container `temperature-demo-postgres-b`, database `temperature_b` | Docker network `temperature-demo-home-b` | port 5432 on that network only; not published on the host | validated | `01_Terraform/terraform-modules/modules/aws/data/rds` |

Implementation kinds the model should be able to attach to one logical node:

```text
home-a-backend
    docker              temperature-demo-backend-a
    kubernetes-local    not deployed
    eks                 not deployed

home-a-database
    postgres-container  temperature-demo-postgres-a
    postgres-kubernetes not deployed
    rds                 not deployed

home-a-queue
    local-emulator      not deployed
    aws-sqs             module reference only
```

External owners, unchanged by this demo:

| Owner | Path | What this demo consumes |
| --- | --- | --- |
| Backend application | `21_PythonProjects/temperature-iot-backend` | HTTP API, `TemperatureReading`, `DATABASE_*`, `serve --host --port` |
| Commons | `06_Common/compute-manager`, `06_Common/uapi-adapter` | already required by the backend image |
| UML messaging | `34_UML/architectures/messaging/architecture.yaml` | SNS, SQS, and SNS→SQS module refs for the later handoff |
| Terraform | `01_Terraform/terraform-modules` | not invoked |

Slice 002 keeps an isolated root at `infra/aws-messaging` because the shared SNS and SQS modules do not yet express fan-out, raw delivery, dead-letter queues, or a topic-scoped queue policy. The messaging model's `sns-sqs-binding` module path is not present on disk. Do not point the UML module refs at this demo root.

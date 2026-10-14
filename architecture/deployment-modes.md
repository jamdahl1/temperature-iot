# Deployment modes

The same logical nodes are the point. The implementations differ.

## Mode A — Docker networks

Status: validated in slice 001.

```text
docker network temperature-demo-home-a
    backend-a
    postgres-a

docker network temperature-demo-home-b
    backend-b
    postgres-b
```

There is no shared messaging network yet, because there is no messaging process.

Isolation that this mode actually has:

| Boundary | What is true now |
| --- | --- |
| Network | Separate Docker bridges. `backend-a` is not attached to Home B, so `postgres-b` does not resolve there. |
| Database | Two PostgreSQL servers and two database names. |
| Configuration | Different `DATABASE_HOST` and `DATABASE_NAME`. Same image. |
| Application | No house filter. A reading posted to backend A is stored in database A, whatever `house_id` it carries. |

Isolation this mode does not have:

- Kubernetes NetworkPolicy
- a firewall between the host and the published HTTP ports
- queue isolation
- authentication

The host is supposed to reach `127.0.0.1:18081` and `127.0.0.1:18082`. That is the observation path.

## Mode B — one Kubernetes cluster

Status: planned.

One namespace, two Deployments of the same backend image, two Services, two PostgreSQL workloads, ConfigMaps, and Secrets. Prove the same readings and the same image id under Kubernetes.

kubectl 1.32 is installed on this machine. k3d and kind are not. Use the current local cluster when this mode starts. Do not install a distribution only to begin the proof.

## Mode C — namespace isolation

Status: planned. Do not start until Mode B is validated.

## Mode D — separate clusters

Status: planned. A demonstration of deployment independence, not a production recommendation.

## AWS

Status: isolated messaging root prepared in `infra/aws-messaging`. Not applied. The new-account CLI profile is not authenticated yet.

The shared modules under `01_Terraform` were inspected and were not used. The SNS module creates a topic. The SQS module creates a queue. Neither creates a subscription, raw delivery, a dead-letter queue, or a topic-scoped queue policy. The UML binding path `messaging/sns-sqs-binding` is not in that tree. Copying those modules into this demo remains out of scope.

Later mapping, still owned by `01_Terraform` after that tree is reviewed against the working root:

| Local | Later AWS | Existing module path |
| --- | --- | --- |
| topic emulator | SNS | `terraform-modules/modules/aws/messaging/sns` |
| queue emulator | SQS | `terraform-modules/modules/aws/messaging/sqs` |
| local Kubernetes | EKS | `terraform-modules/modules/aws/compute/eks` |
| PostgreSQL container | RDS | `terraform-modules/modules/aws/data/rds` |

Do not copy those modules here.

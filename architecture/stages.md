# Stages

These are experimental architecture stages. They are not release versions.

| Stage | Name | Status |
| --- | --- | --- |
| 0 | Logical architecture documented | validated |
| 1 | Backend A + PostgreSQL A | validated |
| 2 | Backend B + PostgreSQL B | validated |
| 3 | Direct API calls prove database separation | validated |
| 4 | Local messaging emulator | planned |
| 5 | Producer A → queue A → consumer A | planned |
| 6 | Producer B → queue B → consumer B | planned |
| 7 | Full Docker composition validated | planned |
| 8 | Single Kubernetes cluster | planned |
| 9 | Kubernetes network isolation | planned |
| 10 | Namespace-separated deployment | planned |
| 11 | Optional multi-cluster deployment | planned |
| 12 | Terraform/AWS handoff documented | planned |

Stages 1–3 are one slice. They were not given separate partial deployments. `verify` on 2026-10-11 proved both homes together: same image id, separate `DATABASE_*`, each reading present in only its own PostgreSQL, and Docker DNS limited to that home's network.

## Next slice

Slice 002 adds the AWS topic and the two home queues in `infra/aws-messaging`. Slice 003 adds the local SQS adapter that POSTs `TemperatureReading`. The live fan-out still waits on a reviewed plan for account `206858211930` in `us-east-2`. Stages 4–6 remain the place where that path is proved against both databases.

Stage 4 should add the smallest topic and two queues with publish, receive, and acknowledge. Routing may key off `house_id` or an explicit `partition_ref`. Queue identity stays visible: queue A and queue B, even if one emulator process hosts both. On AWS, both queues receive the same SNS event and `HOME_ID` supplies `house_id`.

Stage 5–6 add a deterministic producer and a consumer. The consumer calls `POST /temperatures`. It does not open PostgreSQL.

# Networking

## Mode A path

```text
host acceptance script
    → 127.0.0.1:18081
    → backend-a:8000          network temperature-demo-home-a
    → postgres-a:5432         same network

host acceptance script
    → 127.0.0.1:18082
    → backend-b:8000          network temperature-demo-home-b
    → postgres-b:5432         same network
```

PostgreSQL is not published on the host. Evidence queries use `docker exec` into the database container.

Service DNS names inside a network are the Compose service names: `postgres-a`, `backend-a`, `postgres-b`, `backend-b`.

## Checks

| Check | Expected | Kind of isolation |
| --- | --- | --- |
| `backend-a` resolves `postgres-a` | yes | the configured path exists |
| `backend-b` resolves `postgres-b` | yes | the configured path exists |
| `backend-a` resolves `postgres-b` | no | Docker network |
| `backend-b` resolves `postgres-a` | no | Docker network |
| `DATABASE_HOST` on backend A | `postgres-a` | configuration |
| `DATABASE_HOST` on backend B | `postgres-b` | configuration |

## Not claimed

This is not NetworkPolicy. The two HTTP ports are reachable from the host on purpose. Nothing in this slice authenticates callers. Nothing in the backend refuses a `house_id` that "belongs" to the other home.

## Later Kubernetes path

```text
producer Pod
    → messaging Service
    → consumer Pod
    → backend Service
    → backend Pod
    → postgres Service
    → postgres Pod
```

That path is not deployed. When it is, DNS checks should name the Services, and NetworkPolicy should be a separate stage from "the manifest does not point at the other Service."

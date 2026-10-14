# Logical system

The logical path stays fixed while the deployment changes.

```text
Temperature Producer
        ↓
Publish/Subscribe Transport
        ↓
Queue
        ↓
Consumer
        ↓
Temperature Backend
        ↓
Database
```

The first local proof implements only the last two nodes, twice:

```text
HTTP client (stand-in for a later consumer)
        ↓
Temperature Backend A          Temperature Backend B
        ↓                              ↓
PostgreSQL A                   PostgreSQL B
```

Identity in this slice:

| Concept | Home A | Home B |
| --- | --- | --- |
| `partition_ref` | `home-a` | `home-b` |
| `backend_ref` | `backend-a` | `backend-b` |
| `database_ref` | `postgres-a` / `temperature_a` | `postgres-b` / `temperature_b` |
| `queue_ref` | not deployed | not deployed |

`partition_ref` is a deployment label owned by this demo. `house_id` inside a reading is application data owned by `temperature-iot-backend`. This slice uses the same strings for both so the proof is easy to read. The backend has no home-a or home-b code.

Later partitions can be `partition-a` / houses 1–1000 without forking the backend. Consumers should bind `partition_ref` to `queue_ref`, `backend_ref`, and `database_ref` from configuration.

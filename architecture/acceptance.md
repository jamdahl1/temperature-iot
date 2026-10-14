# Acceptance

## Slice 001 readings

Home A:

```json
{
  "house_id": "home-a",
  "sensor_id": "living-room",
  "temperature": 72.4,
  "unit": "F",
  "observed_at": "2026-10-11T16:00:00Z"
}
```

Home B:

```json
{
  "house_id": "home-b",
  "sensor_id": "kitchen",
  "temperature": 20.5,
  "unit": "C",
  "observed_at": "2026-10-11T16:00:00Z"
}
```

`POST` each reading only to that home's backend.

## Positive proof

Query each database with `psql`:

```text
temperature_reading in temperature_a contains the Home A row
temperature_reading in temperature_b contains the Home B row
```

## Negative proof

```text
temperature_a does not contain the Home B row
temperature_b does not contain the Home A row
```

The query is against PostgreSQL, not only the HTTP list API. Both backends could otherwise hide a shared database.

## Commands

From this directory, after Docker is running:

```powershell
.\scripts\start.ps1
.\scripts\seed.ps1
.\scripts\verify.ps1
.\scripts\status.ps1
.\scripts\stop.ps1
.\scripts\clean.ps1
```

`verify` writes a sanitized summary under `evidence/runs/`. That directory is gitignored.

Contract tests that do not need the running stack:

```powershell
python -m tests.contract.test_reading_catalog
python -m tests.contract.test_compose_topology
```

The system proof:

```powershell
python -m tests.isolation.test_database_isolation
python -m tests.networking.test_docker_dns
```

`verify` runs the contract tests and both system proofs.

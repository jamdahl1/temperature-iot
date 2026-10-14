# Docker composition

Mode A runs two isolated Docker networks. Each network has one PostgreSQL 16 container and one backend container. Both backends use the image `temperature-iot-backend:demo`.

## Image

The backend repository has no Dockerfile. This directory builds one as a development convenience.

Named build contexts, staged outside this repo so virtualenvs are not sent to the daemon:

| Context | Checkout |
| --- | --- |
| `backend` | `temperature-iot-backend` (`TEMPERATURE_IOT_BACKEND`, or `../../21_PythonProjects/temperature-iot-backend`) |
| `commons` | `06_Common` (`COMMONS_REPO`, or `../../06_Common`) |

The staged trees are `pyproject.toml`, `README.md`, and the package `src` directory. Application source is not copied into this repository.

`scripts/start.ps1` builds the image when the tag is missing. `start --rebuild` builds it again.

## What the networks isolate

`backend-a` and `postgres-a` share `temperature-demo-home-a`.

`backend-b` and `postgres-b` share `temperature-demo-home-b`.

No service is attached to both networks. `postgres-b` therefore has no DNS name on Home A's network.

The HTTP ports `127.0.0.1:18081` and `127.0.0.1:18082` are published for the acceptance script. Database ports are not published.

The password `local-demo-pw` is local demo material used by both PostgreSQL and `DATABASE_PASSWORD`. Do not reuse it anywhere else.

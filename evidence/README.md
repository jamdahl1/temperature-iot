# Evidence

`verify` writes `evidence/runs/stage-3-isolation.txt`.

That file is generated. It is gitignored. It contains the deterministic readings, the database each one landed in, the shared image id, and the DNS results. It does not contain the demo database password.

Do not commit container logs, passwords, or raw `docker inspect` dumps. A short sanitized summary is the record.

# Restore Ledgr.io from Postgres Backup

## Prerequisites
- Docker and docker compose installed and working
- Access to the backup file (`ledgrio-<timestamp>.sql.gz`)
- Working directory: repo root (where `docker-compose.yml` lives)

## Procedure

### 1. Stop the entire stack

```bash
docker compose down
```

### 2. Wipe the postgres data volume

```bash
docker volume rm ledgrio_pgdata
```

If the volume name is different, find it with `docker volume ls | grep ledgrio`.

### 3. Start only the postgres service

```bash
docker compose up -d postgres
```

### 4. Wait for postgres to be ready

```bash
until docker compose exec postgres pg_isready -U ledgrio -d ledgrio; do
  sleep 1
done
```

### 5. Restore the dump

```bash
gunzip -c /path/to/ledgrio-<timestamp>.sql.gz | \
  docker compose exec -T postgres psql -U ledgrio ledgrio
```

Replace `/path/to/ledgrio-<timestamp>.sql.gz` with the actual backup file path.

### 6. Start the remaining services

```bash
docker compose up -d
```

### 7. Smoke test

```bash
curl -s http://localhost:8000/api/v1/health/ | python3 -m json.tool
```

Expected output: `"database": "ok"` and `"redis": "ok"`.

## Drill log

| Date | Operator | Result | Notes |
|------|----------|--------|-------|
| _not yet executed_ | — | — | Run once before going to production |

An untested backup is not a backup. Record the first drill in this table.

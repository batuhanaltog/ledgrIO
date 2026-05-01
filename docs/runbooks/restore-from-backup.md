# Restore Ledgr.io from Postgres Backup

## Recovery Expectations

| Metric | Value |
|--------|-------|
| **RPO** (max data loss) | ~24 hours (daily backup cadence) |
| **RTO** (restore time) | ~15–30 minutes on a local machine |

If the last backup is more than 24 hours old, data created after the backup is lost. Accept this before starting.

---

## Prerequisites

- Docker and docker compose installed and working
- Access to a backup file (`ledgrio-<timestamp>.sql.gz`)
- Working directory: repo root (where `docker-compose.yml` lives)

---

## Procedure

### Step 0: Retrieve backup file (if local copy unavailable)

If the local machine failed (disk loss, stolen laptop), retrieve the latest backup from off-site storage first:

```bash
# Example: Backblaze B2 via rclone
rclone copy b2:ledgrio-backups/ledgrio-<timestamp>.sql.gz ./restore/

# Example: AWS S3
aws s3 cp s3://your-bucket/ledgrio-<timestamp>.sql.gz ./restore/
```

Verify integrity before continuing:

```bash
gunzip -t ./restore/ledgrio-<timestamp>.sql.gz && echo "OK"
```

If this fails, try the previous day's backup.

---

### Step 1: Stop the entire stack

```bash
docker compose down
```

---

### Step 1.5: Safety dump of current data (if any)

**Skip only if the current database is confirmed empty or corrupted.**

If there is any chance the current DB has data newer than the backup (e.g., partial restore scenario), dump it first:

```bash
docker compose up -d postgres
until docker compose exec postgres pg_isready -U ledgrio -d ledgrio; do sleep 1; done
docker compose exec postgres pg_dump -U ledgrio ledgrio | gzip > ./backups/ledgrio-pre-restore-$(date +%Y%m%dT%H%M%S).sql.gz
docker compose down
```

This is your rollback if the restore makes things worse.

---

### Step 2: Wipe the postgres data volume

```bash
docker volume rm ledgrio_pgdata
```

If the volume name is different: `docker volume ls | grep ledgrio`

---

### Step 3: Start only the postgres service

```bash
docker compose up -d postgres
```

---

### Step 4: Wait for postgres to be ready

```bash
until docker compose exec postgres pg_isready -U ledgrio -d ledgrio; do sleep 1; done
```

---

### Step 5: Restore the dump

```bash
gunzip -c /path/to/ledgrio-<timestamp>.sql.gz | \
  docker compose exec -T postgres psql -U ledgrio ledgrio
```

Watch for errors in the output. `ERROR:` lines indicate a problem. A few `NOTICE:` lines are normal.

---

### Step 6: Start the remaining services

```bash
docker compose up -d
```

---

### Step 7: Smoke test

```bash
curl -s http://localhost:8000/api/v1/health/ | python3 -m json.tool
```

Expected: `"database": "ok"` and `"redis": "ok"`.

Login with a known account and verify recent transactions are present. If data is missing, check backup timestamp vs expected data date.

---

## Drill Log

| Date | Operator | Backup file used | Result | Notes |
|------|----------|-----------------|--------|-------|
| _not yet executed_ | — | — | — | Run once before going to production |

**An untested backup is not a backup.** Record every drill here. Schedule quarterly drills once production data exists.

# PART 20: BACKUP, RESTORE AND DISASTER RECOVERY

## 20.1 The Two Backup Families

| | Logical Backup | Physical Backup |
|---|---|---|
| **What** | SQL statements / plain objects | Raw cluster files + WAL |
| **Tools** | `pg_dump`, `pg_dumpall`, `pg_restore` | `pg_basebackup`, `rsync` |
| **Granularity** | Per database / object | Per cluster |
| **Speed** | Slower (reads through the engine) | Fast (file copy + WAL streaming) |
| **PITR?** | No (point-in-time = last dump) | **Yes** (WAL replay to any moment) |
| **Restore target version** | Any (SQL text) | Same major version |
| **Use case** | Small DBs, migrations, upgrades, portability | Production DR, replication, PITR |

**Rule of thumb:** production PostgreSQL = physical base backup + continuous WAL archiving. Logical dumps are your *portability* tool, not your DR tool.

## 20.2 Logical Backups

```bash
# Plain SQL (single file, restore with psql)
pg_dump -U postgres -F p shopdb > shopdb_plain.sql
psql -U postgres -d shopdb_restore -f shopdb_plain.sql

# Custom format (compressed, split into archives, selective restore)
pg_dump -U postgres -Fc shopdb > shopdb.dump

# Restore a single table only
pg_restore -U postgres -d shopdb --table=orders shopdb.dump

# All databases + global objects (roles, tablespaces)
pg_dumpall -U postgres > cluster_dump.sql

# Parallel custom dump (big databases)
pg_dump -U postgres -Fc -j 4 shopdb > shopdb_par.dump
```

**Practical notes:**
- `pg_dump` is consistent: it runs in a single snapshot transaction, so you can dump a *live* database.
- Custom format (`.dump`/`.dmp`) is the default choice: compressed, resumable, selective.
- For very large tables, dump with `--format=c` and `--compress=9`.
- **`pg_dump` cannot back up template0/1 or `pg_` catalogs meaningfully** — use `pg_dumpall` for cluster-level objects.

## 20.3 Physical Backups (pg_basebackup)

```bash
# Server side: enable WAL archiving + replication in postgresql.conf
wal_level = replica
archive_mode = on
archive_command = 'test ! -f /var/lib/pg_archive/%f && cp %p /var/lib/pg_archive/%f'

# Client side:
pg_basebackup -h db.example.com -U replicator -D /backup/base -X -P -v
```

- **`-X`/`-c fast|spread`** copies/streams WAL since the backup started — needed for PITR.
- **Replication user** needs `REPLICATION` attribute: `CREATE ROLE replicator REPLICATION LOGIN;`
- `pg_basebackup` connects as a *replication* connection; it is not a SQL client.

## 20.4 WAL Archiving and PITR

**The two-phase restore:**

1. **Base backup** — consistent file snapshot (`pg_basebackup` or a cold `rsync`).
2. **WAL replay** — replay archived WAL segments up to the chosen target.

```bash
# After copying base backup to a fresh cluster directory:
# 1. Tell PostgreSQL to enter recovery:
touch /var/lib/postgresql/17/main/standby.signal     # or postgresql.auto.conf:

# postgresql.conf / postgresql.auto.conf
restore_command = 'cp /var/lib/pg_archive/%f %p'
recovery_target_timeline = 'latest'
# For PITR:
recovery_target_time = '2026-11-05 22:31:00+00'
# or: recovery_target_xid / recovery_target_lsn / recovery_target_lsn (any LSN marker)
```

PostgreSQL replays WAL until it hits `recovery_target_*`, then starts up. **`recovery_target_action`** = `pause` (default, inspect then `SELECT pg_wal_replay_pause(); ... pg_promote()`) or `shutdown`.

**Incremental backup concept:** PostgreSQL has no built-in *incremental file* backup (no "backup only files changed since last backup"). The practical equivalents:
- **`pg_basebackup` + WAL** — the standard "full + continuous" scheme (incremental in effect).
- **Third-party tools** (e.g., `pgBackRest`) implement *actual* incremental file backups by copying only changed blocks between successive full backups.

## 20.5 Replication Slots and WAL Retention

- Without a slot, a long-dead standby loses WAL and must restart from a fresh base backup.
- With a slot, the primary **retains WAL** until the consumer confirms it.
- **Danger:** a paused/broken standby with a retained slot accumulates WAL and **fills the data disk**. Monitor:

```sql
SELECT slot_name, slot_type, active, active_pid,
       pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn) AS pending_wal_bytes,
       pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) AS pending
FROM pg_replication_slots;
```

## 20.6 Backup Verification and Restore Testing

**A backup you have not restored is not a backup.**

1. **Checksum test:** `pg_basebackup` can be verified by `sha256sum` (or `pg_checksums`).
2. **Restore drill (quarterly):**
   - Restore base backup to a scratch instance.
   - Replay WAL to "now" and compare `pg_stat_database` transaction counts or checksum a sample table.
   - Automate: `pg_restore --if-exists` + a `md5` of a reference table vs. prod (read-only snapshot).
3. **RPO/RTO definitions:**
   - **RPO** (Recovery Point Objective): maximum acceptable data loss (e.g., 5 min with 5-min WAL archiving + async standby).
   - **RTO** (Recovery Time Objective): maximum acceptable downtime (e.g., 15 min to fail over).
   - `synchronous_commit`/sync standby: RPO → near 0, RTO → minutes.

## 20.7 High Availability and DR Planning

- **HA:** Primary + synchronous/async standby + automatic failover (`Patroni` for HA orchestration, `RDS Multi-AZ` on AWS).
- **DR:** A *second region* standby (read-replica with `standby.signal` in the remote region), plus encrypted offsite backups (S3/Glacier).
- **Split-brain:** two primaries accepting writes = corruption risk. Use **one writer**, and for two-writer setups a quorum/consensus layer (Raft) — see Part 21.
- **Runbooks:** document exact commands, test them, and keep a "recovery rehearsal" in CI.

## 20.8 Complete Workflow — From Backup to Recovery

```text
1.  Schedule nightly pg_basebackup (or pgBackRest full).
2.  Continuously archive WAL every 64MB (archive_command).
3.  Ship archives to S3 (encrypted, versioned).
4.  RPO = archive interval + standby lag.
5.  On incident:
    a. Stop the failed instance.
    b. Spin up a fresh instance (same major version).
    c. Restore latest base backup + set recovery.conf / postgresql.auto.conf.
    d. Set recovery_target_time (or 'latest') + recovery_target_action = 'promote'.
    e. Start the instance → it replays WAL to the target → promotes to primary.
    f. Verify: pg_isready, pg_stat_database.xact_commit sanity, application smoke test.
6.  Post-incident: restore the *old* primary from a fresh base backup as a standby.
```

## 20.9 Interview Questions

- **Q:** `pg_dump` vs `pg_basebackup`? **A:** logical (portable, PITR not possible) vs physical (fast, PITR-capable, version-locked).
- **Q:** How does PITR work? **A:** base backup + continuous WAL archiving; on restore, replay WAL up to a target timestamp/LSN/xid.
- **Q:** What's RPO/RTO? **A:** max data loss / max downtime. Tune with WAL archiving interval + standby type (sync ⇒ RPO≈0).
- **Q:** How do replication slots affect WAL? **A:** they pin WAL until the slot confirms; a broken slot fills the disk.

# PART 30: DATABASE MONITORING AND PRODUCTION TROUBLESHOOTING

## 30.1 The Monitoring Stack (at a glance)

| Layer | Tool | What it tells you |
|---|---|---|
| OS / host | `top`, `vmstat`, `iostat`, `df` | CPU, memory pressure, I/O saturation, disk full |
| Cluster | `pg_stat_database` | Per-DB traffic, transactions, cache hit ratio |
| Tables | `pg_stat_user_tables` | Seq scans, tuples inserted/updated/deleted, last vacuum |
| Indexes | `pg_stat_user_indexes` | Index usage, read tuples, bloat indicators |
| I/O | `pg_statio_user_tables` / `pg_statio_user_indexes` | Buffer hits/reads per relation |
| Sessions | `pg_stat_activity` | Every connection, state, current query, start time |
| Locks | `pg_locks` | Held vs. requested lock modes |
| Replication | `pg_stat_replication`, `pg_replication_slots` | Standby lag, slot WAL retention |
| Background | `pg_stat_bgwriter` | Checkpoint and background-writer buffer writes |
| Config | `pg_settings` | Every GUC and its current value |
| Objects | `pg_class`, `pg_attribute`, `pg_constraint`, `pg_roles`, `pg_database`, `pg_tables`, `pg_indexes` | Structure and ownership |

> **Version note:** `pg_stat_activity` gained `backend_type` and `wait_event` in PostgreSQL 9.6. Per-relation I/O statistics live in `pg_statio_user_tables` / `pg_statio_user_indexes` (9.4+). WAL and I/O statistics views (`pg_stat_wal`, `pg_stat_io`) appeared in PostgreSQL 15.

## 30.2 Finding Long-Running Queries

```sql
SELECT pid, usename, application_name, state,
       now() - query_start AS duration,
       left(query, 120) AS query_snippet
FROM pg_stat_activity
WHERE state = 'active'
  AND query_start < now() - interval '2 minutes'
ORDER BY duration DESC;
```

## 30.3 Detecting Blocked Sessions

```sql
SELECT blocked_locks.pid AS blocked_pid,
       blocking_locks.pid AS blocking_pid,
       blocked_activity.usename AS blocked_user,
       blocking_activity.usename AS blocking_user,
       blocked_activity.query AS blocked_query,
       blocking_activity.query AS blocking_query
FROM pg_locks blocked_locks
JOIN pg_stat_activity blocked_activity
  ON blocked_activity.pid = blocked_locks.pid
JOIN pg_locks blocking_locks
  ON  blocking_locks.locktype = blocked_locks.locktype
  AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
  AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
  AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
  AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
  AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
  AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
  AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
  AND blocking_locks.pid <> blocked_locks.pid
  AND blocking_locks.granted = TRUE
WHERE blocked_locks.granted = FALSE;
```

## 30.4 Finding Deadlock Victims (After the Fact)

PostgreSQL aborts one victim of each deadlock; the server log contains the full
deadlock diagram. To see sessions that are *currently* waiting on locks:

```sql
SELECT l.pid, l.locktype, l.mode, l.granted, a.query
FROM pg_locks l
JOIN pg_stat_activity a ON a.pid = l.pid
WHERE NOT l.granted;
```

**Log keyword:** `ERROR: deadlock detected` in the server log, followed by a
two-line "Process N waits for X; Process M waits for Y" diagram.

## 30.5 Finding Unused Indexes

```sql
SELECT schemaname, tablename, indexname,
       pg_size_pretty(pg_relation_size(indexrelid)) AS size,
       idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC;
```

> **Caution:** `idx_scan` resets on restart; a brand-new index is not "unused" yet.

## 30.6 Finding Table Bloat Indicators

```sql
SELECT schemaname, relname, n_live_tup, n_dead_tup,
       CASE WHEN n_live_tup + n_dead_tup > 0
            THEN round(100.0 * n_dead_tup / (n_live_tup + n_dead_tup), 1)
            ELSE 0 END AS pct_dead,
       last_vacuum, last_autovacuum
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC
LIMIT 25;
```

For a precise figure, install `pgstattuple` and call
`pgstatinfo('table')` / `pgstatindex('index')`.

## 30.7 Checking Replication Lag

```sql
-- On the PRIMARY:
SELECT client_addr, state, sent_lsn, write_lsn, flush_lsn, replay_lsn,
       pg_wal_lsn_diff(sent_lsn, replay_lsn) AS lag_bytes
FROM pg_stat_replication;

-- On the STANDBY:
SELECT pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn(),
       pg_wal_lsn_diff(pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn());
```

**Slot safety:** a dead standby with a *retained* slot stops the WAL from
being recycled and eventually fills the disk:

```sql
SELECT slot_name, active, active_pid,
       pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn) AS retained_wal_bytes
FROM pg_replication_slots
WHERE restart_lsn IS NOT NULL;
```

## 30.8 Checking Connection Usage

```sql
SELECT count(*) AS total,
       count(*) FILTER (WHERE state = 'active') AS active,
       count(*) FILTER (WHERE state = 'idle') AS idle,
       count(*) FILTER (WHERE state = 'idle in transaction') AS idle_in_tx
FROM pg_stat_activity;

SELECT current_setting('max_connections')::int AS max_connections;
```

## 30.9 Checking Database / Table Size

```sql
-- Databases
SELECT datname, pg_size_pretty(pg_database_size(datname)) FROM pg_database;

-- Tables, indexes, total (per schema)
SELECT schemaname, relname,
       pg_size_pretty(pg_relation_size(c.oid))        AS table_size,
       pg_size_pretty(pg_indexes_size(c.oid))         AS index_size,
       pg_size_pretty(pg_total_relation_size(c.oid))  AS total
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'r' AND n.nspname NOT IN ('pg_catalog','information_schema')
ORDER BY pg_total_relation_size(c.oid) DESC LIMIT 25;
```

## 30.10 Finding Sequential Scans and Cache Hit Ratios

```sql
-- Tables scanned sequentially more than they are indexed
SELECT schemaname, relname, seq_scan, idx_scan,
       seq_tup_read, n_live_tup,
       CASE WHEN n_live_tup > 0 THEN seq_scan::numeric / greatest(idx_scan, 1) END
FROM pg_stat_user_tables
WHERE seq_scan > 0 AND n_live_tup > 10000
ORDER BY seq_tup_read DESC;

-- Cache hit ratio per database
SELECT datname,
       round(100.0 * sum(heap_blks_hit) /
             nullif(sum(heap_blks_hit) + sum(heap_blks_read), 0), 2) AS cache_hit_pct
FROM pg_stat_database
GROUP BY datname;
```

Healthy: > 99%. Sustained < 95% = raise `shared_buffers` or check the
working-set size.

## 30.11 Diagnosing Slow Queries — a 6-Step Procedure

1. **Reproduce:** get the exact SQL (with parameters) from
   `pg_stat_statements` (worst `mean_exec_time`) or the application log.
2. **Explain:** `EXPLAIN (ANALYZE, BUFFERS)` — look for high-actual-cost
   nodes, large `rows` overestimates, and disk `Buffers: read` misses.
3. **Stats:** check `pg_stat_user_tables.last_analyze` age; run `ANALYZE`
   on the hot tables.
4. **Locks:** are queries *waiting*? `pg_locks` + `pg_stat_activity`.
5. **Plan hints:** if the plan is wrong, look for a missing/misordered
   index, or collation/cast mismatches on a join predicate.
6. **Measure the fix:** re-run `EXPLAIN (ANALYZE)` and compare *actual*
   times; verify with `pg_stat_statements` that `total_exec_time` falls.
   Never claim a speedup without this measurement.

## 30.12 Version-Specific Monitoring Differences

| Feature | Version note |
|---|---|
| `pg_stat_statements` | PG 9.4+ (extension + `shared_preload_libraries`) |
| `pg_stat_activity` `wait_event` | 9.6+ |
| Extended statistics (dependencies) | 9.6+ |
| Parallel workers in `pg_stat_activity` | 9.6+ (`backend_type`) |
| `pg_stat_io` (I/O statistics) | 15+ |
| `pg_stat_wal` (WAL statistics) | 15+ |
| Logical decoding statistics views | 15+ |
| `pg_stat_archiver` | 14+ |

When upgrading, re-check which view replaced what (some 15+ views split
previously combined statistics); the release notes list them explicitly.

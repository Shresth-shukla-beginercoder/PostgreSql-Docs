# PART 19: POSTGRESQL ADMINISTRATION AND DBA COMMANDS

## 19.1 psql Meta-Commands

| Meta | Purpose |
|---|---|
| `\l` | List databases |
| `\c dbname user host` | Connect to a database |
| `\dt` | List tables |
| `\d <table>` | Describe table structure |
| `\du` | List roles |
| `\dn` | List schemas |
| `\df` | List functions |
| `\di` | List indexes |
| `\dv` | List views |
| `\dx` | List extensions |
| `\timing` | Show per-statement execution time |
| `\conninfo` | Show current connection details |
| `\password` | Change password (client-side) |
| `\copy` | Client-side CSV/TSV import/export |

**Interview trap:** "Is `\dt` SQL?" — No. It is a *psql* meta-command. It does not run on a JDBC connection.

## 19.2 Shell Utilities

| Utility | Purpose |
|---|---|
| `pg_dump` | Logical backup of a database (plain SQL or custom format) |
| `pg_restore` | Restore from a `pg_dump` custom-format archive |
| `pg_dumpall` | Dump all databases + global objects (roles, tablespaces) |
| `pg_basebackup` | Physical base backup (for PITR/replication, Part 20) |
| `pg_isready` | TCP liveness probe |
| `createdb` / `dropdb` | Create/drop a database (wraps `CREATE DATABASE`) |
| `createuser` / `dropuser` | Create/drop a role |
| `vacuumdb` | Vacuum all databases |
| `reindexdb` | Rebuild all indexes in a database |
| `clusterdb` | Physically reorder a table by index |
| `pg_ctl` | Start/stop/restart the server (DBA tool) |
| `pg_upgrade` | Binary upgrade between major versions |
| `initdb` | Initialize a new cluster |

**Version policy:** `pg_basebackup` 12+ supports `--no-slot`; `pg_dump` 10+ supports JSON output; `pg_upgrade` requires a *matching* build of the target major version.

## 19.3 PostgreSQL Configuration Files

| File | Purpose |
|---|---|
| `postgresql.conf` | Main configuration file (server parameters) |
| `pg_hba.conf` | Host-based authentication configuration |
| `pg_ident.conf` | User name mapping configuration |
| `postgresql.auto.conf` | Auto-generated configuration (ALTER SYSTEM) |

## 19.4 Connections and Connection Limits

```sql
-- Set max connections in postgresql.conf
max_connections = 100

-- Show current connections
SELECT * FROM pg_stat_activity;
```

## 19.5 Shared Buffers

```sql
-- Set shared buffers in postgresql.conf
shared_buffers = 4GB
```

## 19.6 Work Memory

```sql
-- Set work memory in postgresql.conf
work_mem = 16MB
```

## 19.7 Maintenance Work Memory

```sql
-- Set maintenance work memory in postgresql.conf
maintenance_work_mem = 512MB
```

## 19.8 WAL Configuration

```sql
-- Set WAL settings in postgresql.conf
wal_level = replica
max_wal_size = 1GB
min_wal_size = 80MB
```

## 19.9 Checkpoints

```sql
-- Set checkpoint settings in postgresql.conf
checkpoint_timeout = 5min
checkpoint_completion_target = 0.9
```

## 19.10 Autovacuum Configuration

```sql
-- Set autovacuum settings in postgresql.conf
autovacuum = on
autovacuum_vacuum_scale_factor = 0.2
autovacuum_analyze_scale_factor = 0.1
autovacuum_vacuum_cost_delay = 20ms
autovacuum_vacuum_cost_limit = -1
```

## 19.11 Logging

```sql
-- Set logging settings in postgresql.conf
logging_collector = on
log_directory = 'pg_log'
log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
log_statement = 'all'
log_connections = on
log_disconnections = on
```

## 19.12 Memory Management

```sql
-- Set memory settings in postgresql.conf
shared_buffers = 4GB
work_mem = 16MB
maintenance_work_mem = 512MB
effective_cache_size = 12GB
```

## 19.13 Disk Management

```sql
-- Set disk settings in postgresql.conf
random_page_cost = 1.1
seq_page_cost = 1.0
```

## 19.14 Practical Examples

### 1. Basic Server Configuration

```ini
# postgresql.conf
listen_addresses = '*'
port = 5432
max_connections = 100
shared_buffers = 4GB
work_mem = 16MB
maintenance_work_mem = 512MB
effective_cache_size = 12GB
random_page_cost = 1.1
seq_page_cost = 1.0
wal_level = replica
max_wal_size = 1GB
min_wal_size = 80MB
checkpoint_timeout = 5min
checkpoint_completion_target = 0.9
logging_collector = on
log_directory = 'pg_log'
log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
log_statement = 'all'
log_connections = on
log_disconnections = on
autovacuum = on
autovacuum_vacuum_scale_factor = 0.2
autovacuum_analyze_scale_factor = 0.1
autovacuum_vacuum_cost_delay = 20ms
autovacuum_vacuum_cost_limit = -1
```

### 2. pg_hba.conf Configuration

```
# TYPE  DATABASE        USER            ADDRESS                 METHOD
local   all             all                                     peer
host    all             all             127.0.0.1/32            scram-sha-256
host    all             all             ::1/128                 scram-sha-256
hostssl all             all             0.0.0.0/0              scram-sha-256
```

### 3. pg_ident.conf Configuration

```
# MAPNAME       SYSTEM-USERNAME         PG-USERNAME
app_user_map   app_user                app_user
dba_map        dba_user                dba_user
```

### 4. Monitoring Connections

```sql
-- Show current connections
SELECT * FROM pg_stat_activity;

-- Show active queries
SELECT pid, now() - query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active' AND query NOT LIKE '%pg_stat_activity%'
ORDER BY duration DESC;
```

### 5. Vacuum and Analyze

```sql
-- Vacuum a table
VACUUM users;

-- Vacuum and analyze a table
VACUUM ANALYZE users;

-- Vacuum all databases
vacuumdb --all --username=postgres
```

### 6. Reindex a Database

```sql
-- Reindex a database
reindexdb --all --username=postgres
```

### 7. Cluster a Table

```sql
-- Cluster a table by an index
clusterdb --username=postgres mydb users users_pkey
```

### 8. Start/Stop/Restart the Server

```bash
# Start the server
pg_ctl start -D /path/to/data/directory

# Stop the server
pg_ctl stop -D /path/to/data/directory

# Restart the server
pg_ctl restart -D /path/to/data/directory
```

### 9. Upgrade PostgreSQL

```bash
# Upgrade PostgreSQL
pg_upgrade --old-bindir=/path/to/old/bin --new-bindir=/path/to/new/bin --old-datadir=/path/to/old/data --new-datadir=/path/to/new/data
```

### 10. Initialize a New Cluster

```bash
# Initialize a new cluster
initdb -D /path/to/data/directory
```

## 19.15 Common Mistakes

1. **Not setting `shared_buffers` appropriately** → poor performance.
2. **Not setting `work_mem` appropriately** → poor performance for complex queries.
3. **Not setting `maintenance_work_mem` appropriately** → poor performance for maintenance operations.
4. **Not setting `effective_cache_size` appropriately** → poor performance for large queries.
5. **Not setting `random_page_cost` appropriately** → poor performance for index scans.
6. **Not setting `seq_page_cost` appropriately** → poor performance for sequential scans.
7. **Not setting `wal_level` appropriately** → poor performance for replication.
8. **Not setting `max_wal_size` appropriately** → poor performance for write-heavy workloads.
9. **Not setting `min_wal_size` appropriately** → poor performance for write-heavy workloads.
10. **Not setting `checkpoint_timeout` appropriately** → poor performance for write-heavy workloads.
11. **Not setting `checkpoint_completion_target` appropriately** → poor performance for write-heavy workloads.
12. **Not setting `logging_collector` appropriately** → poor performance for logging.
13. **Not setting `log_directory` appropriately** → poor performance for logging.
14. **Not setting `log_filename` appropriately** → poor performance for logging.
15. **Not setting `log_statement` appropriately** → poor performance for logging.
16. **Not setting `log_connections` appropriately** → poor performance for logging.
17. **Not setting `log_disconnections` appropriately** → poor performance for logging.
18. **Not setting `autovacuum` appropriately** → poor performance for autovacuum.
19. **Not setting `autovacuum_vacuum_scale_factor` appropriately** → poor performance for autovacuum.
20. **Not setting `autovacuum_analyze_scale_factor` appropriately** → poor performance for autovacuum.
21. **Not setting `autovacuum_vacuum_cost_delay` appropriately** → poor performance for autovacuum.
22. **Not setting `autovacuum_vacuum_cost_limit` appropriately** → poor performance for autovacuum.

## 19.16 Interview-Style Quick Reference

| Question | Answer |
|---|---|
| What is `postgresql.conf`? | The main configuration file for PostgreSQL server parameters |
| What is `pg_hba.conf`? | The host-based authentication configuration file |
| What is `pg_ident.conf`? | The user name mapping configuration file |
| What is `postgresql.auto.conf`? | The auto-generated configuration file for ALTER SYSTEM commands |
| What is `max_connections`? | The maximum number of concurrent connections to the database |
| What is `shared_buffers`? | The amount of memory the database server uses for shared memory buffers |
| What is `work_mem`? | The amount of memory to be used by internal sort operations and hash tables before writing to temporary disk files |
| What is `maintenance_work_mem`? | The amount of memory to be used by maintenance operations, such as VACUUM, CREATE INDEX, and ALTER TABLE ADD FOREIGN KEY |
| What is `effective_cache_size`? | The amount of memory the database server assumes is available for caching data |
| What is `random_page_cost`? | The estimated execution cost of a non-sequentially fetched disk page |
| What is `seq_page_cost`? | The estimated execution cost of a sequentially fetched disk page |
| What is `wal_level`? | The level of information written to the WAL |
| What is `max_wal_size`? | The maximum size to let the WAL grow |
| What is `min_wal_size`? | The minimum size to shrink the WAL to |
| What is `checkpoint_timeout`? | The maximum time between automatic WAL checkpoints |
| What is `checkpoint_completion_target`? | The target percentage of time spent on checkpointing |
| What is `logging_collector`? | The logging collector process |
| What is `log_directory`? | The directory where log files are written |
| What is `log_filename`? | The file name pattern for log files |
| What is `log_statement`? | The type of statements to log |
| What is `log_connections`? | Whether to log successful connections |
| What is `log_disconnections`? | Whether to log disconnections |
| What is `autovacuum`? | The autovacuum daemon |
| What is `autovacuum_vacuum_scale_factor`? | The fraction of table size to add to autovacuum_vacuum_threshold |
| What is `autovacuum_analyze_scale_factor`? | The fraction of table size to add to autovacuum_analyze_threshold |
| What is `autovacuum_vacuum_cost_delay`? | The cost delay value to use in the autovacuum daemon |
| What is `autovacuum_vacuum_cost_limit`? | The cost limit value to use in the autovacuum daemon |

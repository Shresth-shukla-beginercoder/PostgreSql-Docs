# PART 29: ADVANCED AND ULTRA-ADVANCED POSTGRESQL

## 29.1 What This Part Covers

This part dives into **how PostgreSQL works under the hood** — the mechanics that power MVCC, transactions, the planner, and the storage layer. Understanding these internals helps you:
- Diagnose production mysteries (bloat, unexplained slow queries, lock contention).
- Write better SQL (knowing when the planner can push predicates, fold constants, or parallelize).
- Configure PostgreSQL for your workload (shared_buffers, work_mem, checkpoint tuning).

**Audience:** DBAs, performance engineers, and developers who've outgrown the "just add an index" phase.

## 29.2 MVCC Internals (Multi-Version Concurrency Control)

**Core idea:** PostgreSQL never overwrites a row. An UPDATE creates a *new version* with a new `xmax` (the transaction ID that created it) and marks the old version as obsolete (`xmax` = updating transaction).

### Row Headers (tuple header)
Every row (tuple) has:
- **`xmin`:** transaction ID that created this version.
- **`xmax`:** transaction ID that deleted/updated this version (0 = still live).
- **`ctid`:** physical location (page, offset); changes on UPDATE.
- **Visibility flags:** `HEAP_XMIN_COMMITTED`, `HEAP_XMAX_INVALID`, etc.

```sql
-- Show the system columns (normally hidden):
SELECT xmin, xmax, ctid, * FROM orders LIMIT 5;
```

**Visibility rule:** a transaction sees a row if:
1. `xmin` is committed and `xmin < current_snapshot`.
2. `xmax` is 0 OR `xmax` is uncommitted/aborted OR `xmax > current_snapshot`.

This is why two concurrent transactions can see different versions of the same row.

### Dead Tuples and VACUUM

An UPDATE leaves the old version *dead* but still on disk. `VACUUM` reclaims the space:
1. Scans the table for dead tuples (`xmax` is committed and all active transactions are past it).
2. Marks the space as reusable (no immediate shrink; `VACUUM FULL` rewrites the table).
3. Updates the *visibility map* (VM) so the planner knows which pages are all-visible (enables index-only scans).
4. Freezes old `xmin` to prevent wraparound (every 200M transactions, PostgreSQL must freeze old rows or risk data corruption).

**Autovacuum** does this automatically when `n_dead_tup` exceeds a threshold.

```sql
-- Force a manual vacuum + analyze:
VACUUM ANALYZE orders;

-- See dead-tuple stats:
SELECT schemaname, relname, n_live_tup, n_dead_tup, last_autovacuum
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC;
```

### Transaction ID Wraparound

`xmin` is a 32-bit counter; after 2^32 transactions, it wraps. PostgreSQL *freezes* old rows (sets `xmin` to a special "frozen" value) to prevent them from suddenly appearing "in the future." **If you disable autovacuum on a busy table, wraparound protection eventually forces an emergency VACUUM, blocking writes.**

Monitor:

```sql
SELECT datname, age(datfrozenxid) AS xid_age,
       2^31 - age(datfrozenxid) AS txns_until_wraparound
FROM pg_database
ORDER BY age(datfrozenxid) DESC;
```

When `age(datfrozenxid)` approaches 200M, PostgreSQL warns; at 2B, it refuses new transactions.

## 29.3 WAL (Write-Ahead Log) Internals

**Principle:** before modifying a data page in `shared_buffers`, PostgreSQL writes a *log record* (WAL) describing the change. On crash, the WAL is replayed to recover.

### WAL Segments
- 16 MB files (by default) named like `000000010000000000000042`.
- Sequential writes (append-only); much faster than random data-page writes.
- `wal_level = replica` logs enough for physical replication; `logical` adds row-change records.

### Checkpoints
- Periodically, PostgreSQL writes all dirty pages from `shared_buffers` to disk (a *checkpoint*).
- WAL before the checkpoint can be recycled (or archived for PITR).
- `checkpoint_timeout` (default 5 min) and `max_wal_size` (default 1 GB) control frequency.
- A **checkpoint storm** (too frequent) causes I/O spikes; too infrequent means longer crash recovery.

```sql
-- Force a checkpoint (usually unnecessary):
CHECKPOINT;

-- See checkpoint stats:
SELECT * FROM pg_stat_bgwriter;
```

### Full-Page Writes (FPW)
After a checkpoint, the first modification to a page writes the *entire page* to WAL (to guard against torn-page writes on crash). This inflates WAL size but is necessary for crash safety.

## 29.4 The Query Planner and Optimizer

**Three phases:**
1. **Parse** → abstract syntax tree (AST).
2. **Rewrite** → apply rules (views, RLS).
3. **Plan** → choose join order, access methods (seq scan vs index), and parallelism.

### Planner Statistics (`pg_statistic`)
- `ANALYZE` collects histograms, most-common-values (MCVs), correlation, null fraction.
- The planner estimates *selectivity* (fraction of rows a predicate keeps) and *cost* (I/O + CPU).
- Stale stats → bad estimates → slow plans.

```sql
-- Check when a table was last analyzed:
SELECT schemaname, relname, last_analyze, last_autoanalyze
FROM pg_stat_user_tables
WHERE relname = 'orders';

-- Force fresh stats:
ANALYZE orders;
```

### Cost Model
Each plan node has a *cost* (startup + total):
- **Seq Scan cost** = `seq_page_cost` × pages + `cpu_tuple_cost` × rows.
- **Index Scan cost** = `random_page_cost` × index_pages + seek_overhead.
- **Join cost** depends on the algorithm (Nested Loop, Hash, Merge).

**Tuning GUCs:**
- `random_page_cost = 1.1` (SSD; default 4.0 is for spinning disks).
- `effective_cache_size` = available OS cache (affects index-vs-seq decision).
- `work_mem` = per-operation sort/hash buffer (raise for big joins/sorts).

### Join Reordering (GEQO)
For queries with 12+ tables, the planner uses a *genetic algorithm* (GEQO) instead of exhaustive search. It's fast but may miss the optimal join order.

### Parallel Query (9.6+)
- The planner spawns *background workers* for seq scans, joins, and aggregates.
- `max_parallel_workers_per_gather = 2` (default); raise on many-core machines.
- Parallel plans appear as `Gather` nodes in `EXPLAIN`.

```sql
-- Check parallel settings:
SHOW max_parallel_workers_per_gather;
SHOW max_worker_processes;

-- Force parallel plan (testing):
SET max_parallel_workers_per_gather = 4;
```

## 29.5 Storage — TOAST, Heap, and Page Layout

### Page Structure (8 KB by default)
Each table/index is a sequence of *pages*:
- **Page header** (24 bytes): LSN, checksum, free space pointer.
- **Item pointers** (line pointer array): offsets to tuples.
- **Tuples** (rows): headers + data.
- **Special space** (for indexes).

**Free space map (FSM):** tracks which pages have room for new tuples (speeds INSERTs).

### TOAST (The Oversized-Attribute Storage Technique)
- Columns > ~2 KB are compressed and/or moved to a separate TOAST table.
- `EXTENDED` (default): compress + out-of-line if still big.
- `MAIN`: compress only (never out-of-line).
- `EXTERNAL`: never compress (use for already-compressed data like images).

```sql
-- Check a column's storage strategy:
SELECT attname, attstorage
FROM pg_attribute
WHERE attrelid = 'orders'::regclass AND attname = 'large_json_column';

-- Change it:
ALTER TABLE orders ALTER COLUMN large_json_column SET STORAGE EXTERNAL;
```

## 29.6 Index Internals (B-tree deep dive)

### B-tree Structure
- **Root → internal nodes → leaf nodes** (3-4 levels for millions of rows).
- Each leaf page is a *doubly-linked list* (enables sorted scans).
- Index tuples: `(key, ctid pointer to heap)`.

**Index-only scan:** if all `SELECT` columns are in the index *and* the visibility map says the heap page is all-visible, PostgreSQL reads only the index.

### Index Bloat
Frequent updates create dead index entries. `REINDEX` rebuilds the index, reclaiming space. Use `REINDEX CONCURRENTLY` (PG12+) to avoid blocking writes.

```sql
-- Check index size:
SELECT indexrelname, pg_size_pretty(pg_relation_size(indexrelid))
FROM pg_stat_user_indexes
WHERE relname = 'orders';

-- Rebuild (blocks writes unless CONCURRENTLY):
REINDEX INDEX CONCURRENTLY orders_user_id_idx;
```

## 29.7 JIT Compilation (PostgreSQL 11+)

**Just-In-Time compilation** of SQL expressions via LLVM. Enabled when a query is expensive enough (`jit_above_cost`).

```sql
SHOW jit;  -- on or off
SHOW jit_above_cost;  -- default 100000 (cost units)

-- See JIT in action:
EXPLAIN (ANALYZE, BUFFERS) SELECT ... FROM large_table WHERE expensive_function(...);
-- Look for "JIT: Functions: 3" in the output.
```

**Trade-off:** JIT adds compilation overhead (~10-50ms); it pays off only on long-running queries (>100ms). For OLTP (sub-10ms queries), JIT is usually a net loss.

## 29.8 Lock Internals

PostgreSQL uses **lightweight locks** (spinlocks/LWLocks for internal structures) and **heavyweight locks** (for tables/rows, visible in `pg_locks`).

### Lock Modes (table-level)
- **ACCESS SHARE** (SELECT) — least restrictive.
- **ROW SHARE** (SELECT FOR UPDATE).
- **ROW EXCLUSIVE** (INSERT/UPDATE/DELETE).
- **SHARE UPDATE EXCLUSIVE** (VACUUM, ANALYZE, CREATE INDEX CONCURRENTLY).
- **SHARE** (CREATE INDEX without CONCURRENTLY).
- **EXCLUSIVE** (REFRESH MATERIALIZED VIEW CONCURRENTLY).
- **ACCESS EXCLUSIVE** (DROP, TRUNCATE, ALTER TABLE) — blocks everything.

**Lock queue:** when a lock is held, conflicting requests *queue* (FIFO). A single `ACCESS EXCLUSIVE` request blocks all subsequent readers, even if the lock is currently shared (to prevent writer starvation).

### Advisory Locks
Application-level locks (not tied to rows):

```sql
-- Block until lock is available:
SELECT pg_advisory_lock(12345);

-- Try-lock (returns immediately):
SELECT pg_try_advisory_lock(12345);  -- TRUE if acquired

-- Release:
SELECT pg_advisory_unlock(12345);
```

Use case: distributed job queue (each worker locks a job ID).

## 29.9 Autovacuum Tuning

**Three triggers:**
1. **Transaction-wraparound prevention** (`autovacuum_freeze_max_age`).
2. **Dead-tuple threshold** (`autovacuum_vacuum_threshold + autovacuum_vacuum_scale_factor × n_live_tup`).
3. **Analyze trigger** (similar, for stats freshness).

**Per-table tuning:**

```sql
-- Speed up autovacuum on a hot table:
ALTER TABLE orders SET (autovacuum_vacuum_scale_factor = 0.05);  -- default 0.2

-- Delay autovacuum on a cold archive table:
ALTER TABLE old_logs SET (autovacuum_enabled = false);  -- DANGER: wraparound risk
```

**Global tuning (postgresql.conf):**

```ini
autovacuum_max_workers = 3          # Parallel vacuums (default 3)
autovacuum_naptime = 10s            # How often the launcher checks (default 1min)
autovacuum_vacuum_cost_delay = 2ms  # Throttle to avoid I/O storms (default 2ms)
```

## 29.10 Extension Internals (pgxs and Hooks)

PostgreSQL extensions use **hooks** (function pointers) to customize behavior:
- **`planner_hook`**: intercept the planner (used by `pg_hint_plan`).
- **`executor_start_hook`**: pre-query execution (used by `pg_stat_statements`).
- **`ProcessUtility_hook`**: intercept DDL.

**Building an extension:**

```bash
# Makefile (uses PGXS):
EXTENSION = my_extension
DATA = my_extension--1.0.sql
PG_CONFIG = pg_config
PGXS := $(shell $(PG_CONFIG) --pgxs)
include $(PGXS)

# Build and install:
make
sudo make install

# Load:
CREATE EXTENSION my_extension;
```

## 29.11 Monitoring Query Progress (pg_stat_progress_*)

PostgreSQL 13+ exposes real-time progress for long operations:

```sql
-- VACUUM progress:
SELECT relid::regclass, phase, heap_blks_total, heap_blks_scanned, heap_blks_vacuumed
FROM pg_stat_progress_vacuum;

-- CREATE INDEX progress:
SELECT relid::regclass, phase, blocks_total, blocks_done
FROM pg_stat_progress_create_index;

-- ANALYZE progress:
SELECT relid::regclass, phase, sample_blks_total, sample_blks_scanned
FROM pg_stat_progress_analyze;
```

## 29.12 Advanced GUC (postgresql.conf) Tuning

| GUC | Default | Tuning |
|---|---|---|
| **shared_buffers** | 128 MB | 25% of RAM (but diminishing returns past 8-16 GB; OS cache is faster) |
| **work_mem** | 4 MB | Raise for complex sorts/joins (per operation, not per query!) |
| **maintenance_work_mem** | 64 MB | Raise to 1-2 GB for faster VACUUM/CREATE INDEX |
| **effective_cache_size** | 4 GB | Set to 50-75% of total RAM (hint to planner) |
| **random_page_cost** | 4.0 | 1.1 for SSD, 1.0 for all-in-memory |
| **checkpoint_timeout** | 5 min | Raise to 15-30 min for write-heavy workloads (reduces checkpoint storms) |
| **max_wal_size** | 1 GB | Raise to 2-4 GB if WAL fills between checkpoints |
| **wal_buffers** | auto (3% of shared_buffers) | Usually fine; raise if `pg_stat_bgwriter.buffers_backend_fsync` is high |
| **synchronous_commit** | on | Set to `off` for faster writes (at risk of losing last ~N ms on crash) |

**Reload config:**

```bash
# Non-restart changes:
pg_ctl reload

# Restart-required changes (shared_buffers, max_connections):
pg_ctl restart
```

## 29.13 Logical Decoding and CDC (Change Data Capture)

Logical decoding converts the WAL into a stream of row-level before/after images, powering CDC pipelines (Debezium, Flink CDC, wal2json consumers).

```bash
# Create a logical slot:
SELECT pg_create_logical_replication_slot('cdc_slot', 'wal2json');

# Tail the changes:
SELECT * FROM pg_logical_output_slot('cdc_slot', 0, 'wal2json');
```

**Tools:** `pgoutput` (built-in protocol, used by native logical replication), `wal2json` (JSON output), `pg_logical` (table-level). **Danger:** a dead consumer leaves its slot retaining WAL → disk fills up (see Part 20 §20.5).

## 29.14 Custom Operators and Composite Types

```sql
-- Composite type:
CREATE TYPE money AS (amount numeric, currency char(3));

-- Custom operator (<->  = "distance" example):
CREATE FUNCTION l2_dist(a int, b int) RETURNS int AS
  'SELECT abs($1 - $2)' LANGUAGE SQL;
CREATE OPERATOR <-> (
  leftarg = int, rightarg = int,
  procedure = l2_dist, commutator = <->
);

-- Now usable in expressions and as an index operator class (with GiST support).
```

## 29.15 Interview Questions (Advanced)

- **Q:** How does MVCC work? **A:** Each row has `xmin`/`xmax`; transactions see versions based on snapshot; old versions are dead tuples cleaned by VACUUM.
- **Q:** What is transaction wraparound? **A:** `xmin` is 32-bit; after ~2B transactions, old rows appear "in the future" unless frozen by VACUUM — autovacuum exists mainly to prevent this.
- **Q:** What is WAL? **A:** Write-ahead log; changes are logged to WAL before data pages are modified (crash recovery + replication).
- **Q:** What is a checkpoint? **A:** Flush all dirty buffers to disk; WAL before it can be recycled.
- **Q:** What is TOAST? **A:** Compression + out-of-line storage for large columns (> ~2 KB); storage modes MAIN/EXTERNAL/EXTENDED/PLAIN.
- **Q:** What is an index-only scan? **A:** Reading only the index (no heap access) when all columns are in the index and the visibility map confirms all-visible.
- **Q:** What is JIT? **A:** Just-in-time compilation of SQL expressions via LLVM (PG11+); speeds up CPU-heavy queries, adds compilation overhead.
- **Q:** What is the planner's cost model? **A:** Estimated I/O + CPU cost; driven by `seq_page_cost`, `random_page_cost`, `cpu_tuple_cost`, and `pg_statistic`.
- **Q:** What is GEQO? **A:** Genetic Query Optimizer; used for 12+ table joins (faster than exhaustive search, may miss optimal plan).
- **Q:** What is an advisory lock? **A:** Application-level lock (not tied to rows); useful for distributed coordination.
- **Q:** How does logical decoding power CDC? **A:** A logical replication slot + output plugin (wal2json/pgoutput) turns WAL into before/after row images consumed by Debezium or Flink.

## 29.16 Further Reading

- **Official PostgreSQL Internals Documentation:** https://www.postgresql.org/docs/17/internals.html
- **"The Internals of PostgreSQL"** by Hironobu SUZUKI (online book): http://www.interdb.jp/pg/
- **Source code:** `src/backend/` (executor, optimizer, storage) — readable C.
- **pg_stat_statements + EXPLAIN (ANALYZE, BUFFERS)** — your primary profiling tools.

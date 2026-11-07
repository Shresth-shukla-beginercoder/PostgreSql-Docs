# PART 27: SQL INTERVIEW PREPARATION — ALL LEVELS

> **How to use this part.** Questions are grouped by level (Junior → Mid → Senior → Architect) and by topic. Each answer is the *interview-grade* response — concise, but complete enough to earn full marks. Aim to answer each in under 90 seconds, then go deeper if asked to.

---

## 27.1 Junior-Level Questions

### Fundamentals
1. **What is a database? An RDBMS?** A database is an organized collection of data; an RDBMS stores it in tables related by keys and speaks SQL (e.g., PostgreSQL, MySQL).
2. **What is a primary key?** A column (or set) that uniquely identifies each row, is NOT NULL, and is immutable in practice. PostgreSQL allows only one per table.
3. **Primary Key vs Unique Key?** PK = UNIQUE + NOT NULL, one per table. UNIQUE allows multiple columns, and (in SQL standard) can contain NULLs — in practice prefer NOT NULL + UNIQUE.
4. **What is a foreign key?** A column referencing the PK of another table; enforces referential integrity; supports `ON DELETE/UPDATE` actions (CASCADE, SET NULL, RESTRICT, NO ACTION).
5. **What is normalization?** Organizing tables to eliminate redundancy and update anomalies. 1NF: atomic values; 2NF: no partial dependencies on composite keys; 3NF: no transitive dependencies; BCNF: every determinant is a candidate key.
6. **When do you *denormalize*?** To remove expensive joins on read-heavy hot paths (e.g., storing `customer_name` on `orders`). Accept stale data or trigger-maintained copies.
7. **DELETE vs TRUNCATE vs DROP?** DELETE removes matching rows (DML, log-based, can have WHERE, can rollback per-row cost). TRUNCATE empties the whole table (fast, ACCESS EXCLUSIVE lock, DDL-ish, RESET IDENTITY). DROP deletes the table definition.
8. **What is NULL?** The absence of a value. `NULL = NULL` is NULL (not TRUE); `COUNT(col)` ignores NULLs, `COUNT(*)` does not; `NOT IN` subquery containing NULL returns no rows.
9. **Differences: WHERE vs HAVING?** WHERE filters rows *before* aggregation; HAVING filters *groups* after GROUP BY.
10. **Differences: UNION vs UNION ALL?** UNION removes duplicates (sorts/compares); UNION ALL keeps all (faster). Use ALL unless distinctness is required.
11. **What is a view?** A stored query. PostgreSQL views are lazily expanded; MATERIALIZED VIEW stores results in a table and must be REFRESHed.
12. **What is a stored procedure vs function in PostgreSQL?** Functions RETURN values (PL/pgSQL, SQL, C, Rust); procedures (PG11+) are `CALL`ed, manage transactions (`COMMIT`/`ROLLBACK` inside), and return no value.
13. **What are DDL, DML, DCL, TCL?** DDL: CREATE/ALTER/DROP. DML: INSERT/UPDATE/DELETE/MERGE. DCL: GRANT/REVOKE. TCL: BEGIN/COMMIT/ROLLBACK/SAVEPOINT.
14. **What is a sequence?** A counter object: `nextval('s')`; SERIAL and IDENTITY use sequences under the hood.
15. **What is an index? What does it cost?** A data structure (B-tree by default) that speeds reads but slows INSERT/UPDATE/DELETE and uses disk; a query only benefits if its shape matches the index.

### Querying
16. **Explain the logical order of SELECT.** `FROM` → `JOIN` → `WHERE` → `GROUP BY` → `HAVING` → `SELECT` → `DISTINCT` → `ORDER BY` → `LIMIT`/`OFFSET`. (Aliases in WHERE are not visible; window functions run after SELECT.)
17. **How do you find the 2nd highest salary?** `ORDER BY salary DESC LIMIT 1 OFFSET 1`, or `DENSE_RANK() OVER (ORDER BY salary DESC)` filtering rank = 2.
18. **What is a self-join?** Joining a table to itself (with two aliases) — e.g., employee↔manager in one table.
19. **How do you delete duplicate rows, keeping one?** `DELETE FROM t WHERE ctid IN (SELECT ctid FROM (SELECT ctid, ROW_NUMBER() OVER (PARTITION BY dup_col ORDER BY id) r FROM t) x WHERE r > 1);`
20. **INNER, LEFT, RIGHT, FULL JOIN?** INNER: matches on both. LEFT: all left rows, NULLs when no match. RIGHT: mirror. FULL: all rows from both. PostgreSQL also has CROSS JOIN (Cartesian) and LATERAL (right side can reference left).
21. **How does `DISTINCT` work?** Computes distinct values over the whole row (or expressions); typically a Hash or Sort; costly over wide rows — consider `GROUP BY` or unique indexes.
22. **What is a correlated subquery?** A subquery that references columns of the outer query; re-evaluated per outer row — often rewritten as a JOIN or window function.
23. **What is a CTE? When does it help?** `WITH name AS (...)`. Improves readability, enables recursion; the planner MAY inline it (PG12+) or materialize it (`MATERIALIZED` hint forces a snapshot).
24. **How do you check if a subquery returns any rows?** `WHERE EXISTS (SELECT 1 FROM ...)` — short-circuits, usually faster than `IN (SELECT ...)`, and NULL-safe (unlike `IN` with NULLs).
25. **`LIMIT` / `OFFSET`? What about deep paging?** `LIMIT n OFFSET m` scans m+n rows — O(offset) cost. Better: **keyset pagination** `WHERE id > last_seen ORDER BY id LIMIT n`.

### Data Types
26. **TEXT vs VARCHAR(n)?** In PostgreSQL they are the same type in performance/storage; VARCHAR(n) adds a length check. Use TEXT.
27. **JSON vs JSONB?** JSON keeps the original text (order, duplicates); JSONB stores a binary, indexed, key-deduplicated format — faster queries, GIN-indexable. Use JSONB for querying.
28. **TIMESTAMP vs TIMESTAMPTZ?** TIMESTAMP has no zone (naive). TIMESTAMPTZ stores an instant in UTC and renders in the session's `TimeZone`; compare instants with TIMESTAMPTZ, never string-compare timestamps.
29. **NUMERIC vs REAL/DOUBLE?** NUMERIC is exact (arbitrary precision) — use for money. REAL/DOUBLE are approximate (faster, 4/8 bytes).
30. **How do you store an enum?** `CREATE TYPE mood AS ENUM (...)` (fast, constrained, hard to extend) or a lookup table (flexible) or CHECK constraint (lightweight).

---

## 27.2 Mid-Level Questions

### Join Mastery
31. **When would the planner choose Nested Loop, Hash, or Merge join?** Small inner side or correlated access → Nested Loop; both sides large and in-memory → Hash; both sides sorted (or streaming external) → Merge. Check via `EXPLAIN`.
32. **What is a LATERAL join and a real use case?** Each outer row runs the right subquery: "top-3 products per category": `FROM categories c, LATERAL (SELECT * FROM products WHERE category = c.id ORDER BY price LIMIT 3) p;`
33. **Anti-join pattern?** `LEFT JOIN ... ON ... WHERE right.key IS NULL` (or `NOT EXISTS`). "All users without orders."
34. **Diverging FROM / JOIN?** `FROM a, b` = cross join; prefer explicit `JOIN` with `ON` to avoid accidental Cartesian products.
35. **How do you find rows present in A but not B?** `EXCEPT`, `NOT EXISTS`, or anti-join `LEFT JOIN ... IS NULL`.

### Aggregates and Windows
36. **ROW_NUMBER vs RANK vs DENSE_RANK?** ROW_NUMBER: unique 1,2,3 (ties broken arbitrarily). RANK: ties share rank, gaps after (1,2,2,4). DENSE_RANK: ties share, no gaps (1,2,2,3).
37. **LAG / LEAD?** Peek at the previous/next row in the partition; specify offset and default for missing neighbor.
38. **What is a window frame? Why does it matter?** The set of rows the aggregate sees: `ROWS 1 PRECEDING AND 1 FOLLOWING` = 3-row sliding window; `RANGE` = value-based; default `RANGE UNBOUNDED PRECEDING` causes ties to aggregate together — a classic surprise.
39. **Can you use window functions in HAVING?** No — windows compute after GROUP BY/HAVING. Use the window in an outer query or CTE.
40. **Moving average pattern?** `AVG(value) OVER (ORDER BY day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)`.
41. **Year-over-year growth?** Self-join on `date - 365` (or `LAG(value, 12)` on a monthly pivot), compute `cur / prev - 1`.

### Constraints and Integrity
42. **CHECK constraints: what can they reference?** The row's columns only (not other rows, not subqueries). Use triggers for cross-row rules.
43. **How do you enforce "one active subscription per user"?** Partial unique index: `CREATE UNIQUE INDEX ON subs (user_id) WHERE status = 'active';`
44. **EXCLUDE constraint?** PostgreSQL-only: `EXCLUDE USING gist(range_col)` — prevents overlapping ranges (e.g., booking slots).
45. **What happens with `ON DELETE CASCADE` and multiple FK paths?** PostgreSQL blocks table definitions where a row can be reached by two different FK paths (ambiguity of cascade).
46. **How do you audit who changed a row?** `row_to_json` history tables + triggers, or `pgaudit`, or temporal tables with `valid_from/valid_to`.

### Performance (Mid)
47. **When is a B-tree index *not* useful?** Low-cardinality columns (boolean, country), leading-wildcard `LIKE '%abc'`, expressions that don't match the indexed column, queries scanning most of the table (seq scan wins).
48. **Composite index order rule?** Equality columns first, then range/sort column: `WHERE status = 'open' ORDER BY created_at` → `(status, created_at)`.
49. **What is an index-only scan? What's required?** Reading only the index (no heap) when all SELECT columns are in the index (or `INCLUDE`d) and the visibility map shows the page all-visible; the index must be INCLUDE/covering for the needed columns.
50. **What does EXPLAIN output tell you?** `cost` = estimate, `actual time/rows` (with ANALYZE) = reality; compare estimated vs actual rows; look for Seq Scans on huge tables, high row overestimates, and nested-loop blowups.
51. **What is the N+1 query problem?** One query per row in an application loop (e.g., orders, then a price query per order). Fix: fetch in one batched query, or `CROSS JOIN LATERAL` if per-row is truly needed.
52. **When is a materialized view the right answer?** Expensive read-only aggregate reports that tolerate minutes of staleness; refresh with `REFRESH MATERIALIZED VIEW CONCURRENTLY` (needs UNIQUE index).
53. **What is query jitter / plan instability?** The planner's estimates shift as data/statistics change, flipping plans. Mitigate with `plan_cache_mode = force_generic_plan` for prepared statements or `pg_hint_plan`.
54. **How do prepared statements help?** The server plans once, reuses plans and parameter types; avoids repeated parse/plan cost and SQL-injection risk.
55. **What is `work_mem` and why does it matter?** Per-operation buffer for sort/hash; exceeded → disk temp files → dramatic slowdown. Raise (with caution: it's per operator × operators) or narrow queries.

### Transactions
56. **Explain ACID with PostgreSQL specifics.** Atomicity: WAL-logged, all-or-nothing. Consistency: constraints enforced at commit. Isolation: default READ COMMITTED (snapshot per statement). Durability: WAL `fsync` before commit returns (unless `synchronous_commit = off`).
57. **READ COMMITTED pitfall?** **Non-repeatable reads / phantom reads**: each statement gets a fresh snapshot, so the same SELECT twice can differ mid-transaction. Use REPEATABLE READ or SERIALIZABLE if needed.
58. **What does SERIALIZABLE isolation do in PostgreSQL?** Uses predicate locking (SSI): reads are tracked; on commit, a dependency conflict aborts one transaction with `ERROR: could not serialize access due to concurrent update`. Retry the transaction.
59. **What is a savepoint and when use it?** `SAVEPOINT sp; ... ROLLBACK TO sp;` — partial rollback; classic use: upsert loops where one bad row shouldn't kill the batch.
60. **When should a transaction be long?** Almost never. Long txns pin old row versions (bloat), hold locks, and hold snapshots that delay VACUUM. Keep them short; split work.

---

## 27.3 Senior-Level Questions

### Concurrency and Locking
61. **Explain the table lock modes and compatibility.** ACCESS SHARE (SELECT) ↔ everything except ACCESS EXCLUSIVE; ROW EXCLUSIVE (writes) is compatible with ACCESS/ROW SHARE; ACCESS EXCLUSIVE (ALTER/DROP/TRUNCATE) is incompatible with all. See `pg_locks`.
62. **What is `SELECT ... FOR UPDATE`? Variants?** Locks rows for the transaction. `FOR NO KEY UPDATE` (allows key updates), `FOR SHARE` (read-locks against writers except DELETE), `NOWAIT` (error instead of wait), `SKIP LOCKED` (queue-workers pattern: take the next un-locked job).
63. **Deadlock vs lock convoy?** Deadlock: A holds X waits Y; B holds Y waits X — PostgreSQL detects, aborts one with the full diagram in the log. Convoy: a single slow txn holding a hot row serializes everyone; fix by shortening transactions or batching.
64. **How do you prevent hot-row update contention?** Aggregate counters in an app or a batching queue; use `UPDATE ... WHERE` on sharded sub-tables; or update less frequently (`UPDATE ... ` with deltas merged periodically).
65. **What is `pg_advisory_lock` and a use case?** An application-level named lock: `pg_try_advisory_lock(key)` — single-flight job execution, one-at-a-time maintenance across app replicas.
66. **MVCC: explain xmin/xmax and visibility.** Each tuple stores the xid that created it (`xmin`) and the xid that last modified/deleted it (`xmax`). A snapshot at xid N sees a tuple if `xmin ≤ N` and committed, and (`xmax = 0` or `xmax > N`).
67. **What is VACUUM actually doing? Why autovacuum?** Scans for dead tuples, marks space reusable, updates visibility maps (enabling index-only scans), and freezes old xids (wraparound). Autovacuum runs on `n_dead_tup` thresholds; disabling it on hot tables → bloat + eventual wraparound emergency.
68. **What is transaction ID wraparound?** xids are 32-bit; approaching 2 billion, PostgreSQL freezes old rows and *eventually blocks writes* until VACUUM catches up. Monitor with `age(datfrozenxid)` in `pg_database`.
69. **What is bloat? How to detect it?** Dead tuples + dead index entries growing a relation beyond its live size. Detect: `n_dead_tup` in `pg_stat_user_tables`, `pgstattuple` (`pgstatinfo`), or compare `pg_relation_size` to expected. Fix: autovacuum tuning, `VACUUM` / `VACUUM FULL` (rewrites, blocks writes).
70. **HOT updates? When do they matter?** Heap-Only Tuple updates that keep the B-tree unchanged when the update doesn't touch indexed columns — cheaper writes and index updates. Keep HOT chains short with autovacuum.

### WAL and Durability
71. **Explain the WAL write path.** Modify shared buffers → log WAL record → `fsync` WAL (durable point) → dirty page flushed at checkpoint. `synchronous_commit` levels: `on` (default, fsync), `local` (fsync in same cluster; PG15+), `remote_apply`, `off` (fastest; last ~ms can be lost on crash).
72. **What is a checkpoint? What tuning?** Periodic "flush all dirty buffers + mark WAL recyclable." Raise `checkpoint_timeout`/`max_wal_size` to spread I/O; avoid checkpoint storms.
73. **What is PITR and its prerequisites?** Point-in-Time Recovery: restore base backup + replay archived WAL to `recovery_target_time/xid/lsn`. Prerequisites: continuous `archive_command` (never failing), a base backup taken after the last good state, and a tested restore procedure.
74. **Logical vs physical replication — deep differences?** Physical: WAL byte stream, full-cluster, same-major-version, DDL follows. Logical: row images decoded from WAL, selective tables, cross-version, DDL must be managed on both sides.
75. **Synchronous replication: cost and configuration?** `synchronous_standby_names` + `synchronous_commit` — every commit waits for standby's WAL ack (zero data loss). Cost: commit latency = network RTT; quorum `FIRST n (...)` for N-of-M.
76. **What are replication slots? Their failure mode?** Slots pin WAL so a standby/consumer can't miss it. Failure mode: an inactive slot retains WAL forever → **data disk fills** → monitor `pg_replication_slots.restart_lsn` distance.

### Performance Engineering
77. **You're given a 10x-slow query. Walk me through it.** (1) `EXPLAIN (ANALYZE, BUFFERS)` — actual vs estimated rows, where the time goes; (2) missing/misordered index? stats stale (`ANALYZE`)?; (3) rewrite (N+1, deep OFFSET, function-in-WHERE, `NOT IN` with NULLs); (4) GUC/plan (work_mem, random_page_cost on SSD, `pg_hint_plan` as last resort); (5) re-measure.
78. **`NOT IN` vs `NOT EXISTS`? Why?** `NOT IN (subquery)` with any NULL in the subquery yields NULL (no rows). `NOT EXISTS` is NULL-safe and usually optimizes to an anti-join.
79. **`COUNT(*)` on 100M rows? How to make it fast?** Exact count is a full scan (or index scan on the smallest index). Acceptable: `pg_class.reltuples` (from ANALYZE, approximate) or `pg_stat_user_tables.n_live_tup`.
80. **What are extended statistics?** `CREATE STATISTICS s ON a, b FROM t` captures multi-column correlations the single-column histograms miss; helps join-order decisions. (PG11+.)
81. **When does a CTE cost you?** In PG < 12 CTEs were always materialized; PG12+ inlines them by default unless `MATERIALIZED`. A `MATERIALIZED` CTE that feeds multiple consumers saves recomputation; a `NOT MATERIALIZED` one saves the snapshot.
82. **How does parallel query work? Limits?** Max `max_parallel_workers_per_gather` workers scan/join in parallel under a `Gather` node; only some operations parallelize; small workloads add overhead.
83. **What is partitioning and when?** Declaring a table as `PARTITION BY RANGE/LIST/HASH` with child tables; prunes irrelevant partitions in queries. When: > ~50–100 GB per logical table, time-series (range by month), multi-tenant (list). Partitions do *not* speed up random writes to one hot partition.
84. **What is table bloat's impact on seq scans and indexes?** Reads + dead tuples; wasted I/O; visibility-map gaps block index-only scans; autovacuum must keep up. `VACUUM FULL` rewrites (blocking); `pg_repack` (extension) does it online.
85. **How do you cap a runaway query?** `statement_timeout`, `lock_timeout`, `idle_in_transaction_session_timeout`, or `pg_terminate_backend(pid)`. Also pgbouncer for connection limits.

### Security
86. **How does pg_hba.conf work?** Source-IP → user → database → auth-method matrix (scram-sha-256, md5, peer, cert). First matching rule wins. Use scram-sha-256 for passwords.
87. **What is Row-Level Security and a pattern?** `ALTER TABLE t ENABLE RLS; CREATE POLICY p ON t USING (tenant_id = current_setting('app.tenant')::uuid);` — each session sets `app.tenant`; the DB enforces per-row isolation. **Danger:** bypassable by `superuser`/`table owner` (unless `FORCE RLS`).
88. **How do you prevent SQL injection?** Parameterized queries only (PDO/psycopg with `%s`); never string-concat user input; least-privilege DB users; `pglast`/WAF as defense-in-depth, not primary defense.
89. **What are prepared statements' security benefits?** The query plan is fixed at prepare; user input is data, never code — injection surface collapses.
90. **Database user design for an app?** Two roles: `app_reader` (SELECT only) and `app_writer` (INSERT/UPDATE/DELETE, no DDL); DDL only via a CI pipeline role. `GRANT` column-level where needed.

### Operations
91. **Design a backup strategy for production.** Nightly `pg_basebackup` + continuous WAL archiving to object storage (S3, encrypted, versioned); test restore quarterly; RPO = archive lag + standby lag; RTO = failover drill time.
92. **Primary fails at 3 AM. Walk me through failover.** Promote the most-current standby (`pg_ctl promote` / `pg_promote()`), point the app at it (DNS/RDS endpoint), verify (queries, replication catch-up); then rebuild the dead primary as a *standby of the new primary* (never re-promote it) to avoid split-brain.
93. **What is a read replica's staleness risk and mitigation?** Asynchronous lag → read-your-writes violations. Mitigate: route post-write reads to primary, or `synchronous_commit = remote_apply` (read after apply), or check `pg_last_wal_replay_lsn()` before serving.
94. **Monitoring: the five dashboards that matter.** (1) WAL/replication lag + slot retention; (2) cache hit ratio + seq scans; (3) long-running + blocking sessions; (4) connection usage vs max; (5) disk growth + dead-tuple growth per table.
95. **What is a maintenance window for a zero-downtime deploy?** DB schema deploy in two phases: (a) backward-compatible additive change (add nullable column, index CONCURRENTLY); (b) switch app write; (c) cleanup (drop old columns) after all app versions are past the old path.

---

## 27.4 Architect-Level Questions

96. **Design a schema for e-commerce orders with 100M+ rows.** Partition `orders` by range (month); keep order lines in `order_items` (partitioned by the same key, FK via `FOREIGN KEY` with `NO ACTION` caveat on PG17); hot indexes (status, customer+date); archive > 18 months to cold storage or partition-drop.
97. **Multi-tenant SaaS: row-level tenant vs separate DB per tenant.** RLS: shared infra, strong isolation via policies, single codebase, but noisy neighbors and harder per-tenant backup; separate DBs: clean isolation/backup/deletion, per-tenant scale, higher ops cost (connection pools, migrations). RLS up to ~10^3–10^4 active tenants; sharding (Citus) or per-tenant DBs beyond.
98. **You have 50 billion event rows and need p99 latency queries. Design it.** Time-partitioned range partitions; BRIN or B-tree on `(ts)`; keep hot 30 days online, archive older to object storage or a columnar store; pre-aggregate daily rollups (materialized views / dbt); never full-scan 50B rows — design the query so it lands in one partition.
99. **How would you move from PostgreSQL 16 to 17 with zero data loss?** `pg_upgrade` (binary, fast) or logical replication from 16→17 (downtime = switch window only; DDL must be applied on both). Plan: parallel-run, verify row counts, cutover.
100. **Design a global multi-region write workload.** PostgreSQL is single-writer; multi-region writes needs consensus (CockroachDB/Yugabyte) or per-region writers + eventual consistency (async replication, conflict resolution); or Citus/multi-primary patterns with app-level routing. Choose CP (quorum) vs AP (availability) per feature.
101. **What is a data-warehouse-vs-OLTP split and why?** OLTP: small fast transactions, lots of indexes/locks, normalized; warehouse: large analytical scans, columnar (Greenplum/Redshift/Athena), pre-aggregated. Move with logical replication or CDC (Debezium) — keep the OLTP DB unburdened by BI scans.
102. **Explain CAP for a database engineer.** Consistency, Availability, Partition Tolerance: on a network partition, a *distributed* system must choose C or A. Single-node PostgreSQL is "CA" (partition = unavailable); synchronous replication = CP; async replicas = AP reads. Choose the isolation your business tolerates.
103. **Design a failover with RPO ≈ 0.** Two synchronous standbys in different AZs/regions + `synchronous_commit = on` + automatic promotion (Patroni/RDS Multi-AZ/Orb); quorum commit so one standby is enough; measure RTO with quarterly drills, target < 60 s.
104. **How do you cap disk growth on a write-heavy system?** TTL partition drops (auto-drop > N months), compression (pg_zstd / TOAST on large cols), archive to object storage, `autovacuum` tuned to keep dead tuples low, monitoring on growth-rate alerts.
105. **What is zero-downtime schema migration, step by step?** (1) Expand: add column/index (non-blocking; `CREATE INDEX CONCURRENTLY`), dual-write both fields; (2) Migrate: backfill historical data; (3) Contract: switch reads to new field; (4) Cleanup: drop old column. Never do it in one deploy.

---

## 27.5 PostgreSQL-Specific Deep Questions

106. **`TEXT` vs `VARCHAR`?** Same type under the hood; `VARCHAR(n)` just adds a check. Use `TEXT`.
107. **`JSON` vs `JSONB`?** JSONB is binary, dedupes keys, indexable (GIN), faster to query; JSON preserves text/order. Default to JSONB.
108. **How does `pg_dump` guarantee consistency on a live DB?** It opens a single transaction with `REPEATABLE READ` and takes a consistent snapshot — no locks beyond READ COMMITTED needed.
109. **`pg_basebackup` vs `pg_dump`?** Physical (binary + WAL, PITR-capable, version-locked) vs logical (portable, per-object, no PITR).
110. **What is `CTID` and how do you use it?** Physical row location (block, offset) — system column; used by `DELETE`-duplicate patterns and VACUUM internals.
111. **How do generated columns / table functions work?** `GENERATED ALWAYS AS (expr) STORED` — computed at write, queryable; `TABLE(...)` syntax for function-returns-table.
112. **What is the `REINDEX CONCURRENTLY` caveat (PG12+)?** Rebuilds without blocking writes; creates a temp index and swaps; leaves the old index if it fails (clean up orphans); cannot run on a partitioned table's children simultaneously in all versions.
113. **`pg_stat_statements` — how to use it?** `shared_preload_libraries` + `CREATE EXTENSION`; top-N by `total_exec_time`, `calls` vs mean; `reset()` to baseline; per-DB stats for multi-tenant.
114. **What is `pg_hint_plan` and when?** A GUC-injection mechanism to override planner choices when you know better (last-resort; usually better to fix the index/stats).
115. **Explain the `shared_buffers` sizing intuition.** 25–40% of RAM for dedicated DB servers, diminishing returns past 8–16 GB (OS page cache matters more); don't starve OS or other processes.
116. **`VACUUM` vs `VACUUM FULL` vs `pg_repack`?** VACUUM: marks dead, cheap, online. VACUUM FULL: rewrites, blocks writes. `pg_repack`: online rewrite (extension) — for huge bloat.
117. **What is the `visibility map` and why does it matter?** Bitmap of pages whose tuples are all-visible; lets the planner do index-only scans without touching the heap. Updated by VACUUM.
118. **How does `SERIAL` differ from `IDENTITY`?** SERIAL = sequence + `DEFAULT` (legacy); IDENTITY = `GENERATED ALWAYS/BEFORE` (standard, PG10+). Prefer IDENTITY.
119. **What are `pgcrypto`, `pg_trgm`, `hstore`?** Extensions: crypto functions, trigram similarity (fuzzy `LIKE` + GIN), key-value semi-structured data.
120. **How does PostgreSQL handle `CREATE DATABASE` speed?** Each DB is a separate directory (template copy); use *schemas* within one DB for most multi-project needs; databases are for isolated resource/permission boundaries.

---

## 27.6 Scenario-Based (System Design)

121. **"Your INSERT is 10x slower than it was. What do you check?"** Blocking locks (`pg_locks`), dead tuples/autovacuum, a long-running `VACUUM`, disk full, a hot row, synchronous standby delay, or a DDL in progress (`pg_stat_activity`).
122. **"The Monday 9 AM report makes the whole system slow."** Move to a replica (or a dedicated read-only), or pre-aggregate (materialized view refreshed overnight), or add a resource cap (`statement_timeout`, `max_worker` isolation), or `ALTER TABLE ... SET (autovacuum_naptime)`.
123. **"Two regions must serve writes. How?"** Per-region primary + async replication + a conflict-resolution layer (vector clocks / last-writer-wins), or a global consensus DB (CockroachDB) if you need one logical dataset.
124. **"A table is 4 TB and queries are slow."** Partition it (range by time), prune partitions in queries, archive old partitions, use BRIN on time-ordered cols, and verify the working set fits in shared_buffers.
125. **"How do you back up a 1 TB DB with a 5-minute RPO?"** Continuous WAL archiving (every 16 MB segment) + nightly base backup + S3 offload; test restore; monitor `pg_stat_archiver` for gaps.

---

## 27.7 Answers Review — Common Traps

| Trap | Why it bites |
|---|---|
| `NOT IN (subquery)` with NULLs | Returns no rows; use `NOT EXISTS`. |
| `AVG` over a *window* with default frame | Ties aggregate together; use `ROWS` frame. |
| `VARCHAR(n)` for unbounded text | Adds a check; use `TEXT`. |
| `CREATE INDEX` on a hot table (no CONCURRENTLY) | Blocks writes (SHARE lock). |
| Long `idle in transaction` | Pins snapshots, blocks VACUUM, grows bloat. |
| `SELECT *` in production code | Wide rows, missing columns in joins, no index-only scan. |
| `COUNT(*)` on a huge table | Full scan; use `pg_class.reltuples` for approximate. |
| `JOIN` on `TIMESTAMP` (naive) instead of `TIMESTAMPTZ` | Timezone bugs; store instants. |
| `TRUNCATE` inside a transaction and `COMMIT` | TRUNCATE is not row-logged; it's transactional but DDL-ish; be aware of lock level. |
| Forgetting `FOR UPDATE` on a read-then-write txn | Lost updates; use row locks. |

---

## 27.8 The 10 "Must-Nail" Answers (quick drill)

1. **MVCC** — every row has `xmin`/`xmax`; readers never block writers; VACUUM reclaims.
2. **EXPLAIN ANALYZE** — read actual vs estimated rows; fix the top-cost node.
3. **Composite index order** — equality cols, then range/sort.
4. **Partitioning** — range/list; prune irrelevant partitions; not a silver bullet for hot writes.
5. **ACID under PG** — Durability via WAL `fsync`; Isolation default READ COMMITTED.
6. **RLS** — per-row tenancy via policies; `FORCE RLS` to stop owner bypass.
7. **PITR** — base backup + continuous WAL archive + `recovery_target_*`.
8. **Synchronous vs async replication** — RPO≈0 vs fast; `synchronous_standby_names`.
9. **Bloat detection** — `n_dead_tup`, `pgstattuple`; autovacuum tuning.
10. **Failover** — promote most-current standby, re-point app, rebuild dead primary as a standby.

---

## 27.9 Practice: Ask Yourself

- *Explain `pg_wal_lsn_diff(sent_lsn, replay_lsn)` and what "large" means for your SLO.*
- *Write the `NOT EXISTS` anti-join for "users who never ordered."*
- *Design a composite index for `WHERE region = ? AND created_at > ? ORDER BY priority DESC LIMIT 50`.*
- *What's wrong with this query? `SELECT * FROM orders WHERE LEFT(user, 1) = 'a'`* (function on column kills index).
- *What does `synchronous_commit = off` buy and cost?*

# PART 12: QUERY PERFORMANCE AND OPTIMIZATION

## 12.1 The Query Lifecycle

```
SQL text → Parser → Analyzer → Rewriter → Planner → Executor → Result
```

- **Parser:** syntax check, builds a parse tree.
- **Analyzer:** semantic check (tables/columns exist), builds a query tree.
- **Rewriter:** applies rules (views → subqueries, CTEs).
- **Planner:** generates candidate plans, estimates costs, picks the cheapest.
- **Executor:** runs the chosen plan, returns rows.

**EXPLAIN shows the planner's choice; EXPLAIN ANALYZE shows actual execution.**

## 12.2 EXPLAIN and EXPLAIN ANALYZE

### Basic EXPLAIN

```sql
EXPLAIN SELECT * FROM orders WHERE customer_id = 42;
```

Output:
```
Index Scan using idx_orders_customer on orders  (cost=0.42..8.44 rows=1 width=64)
  Index Cond: (customer_id = 42)
```

- **`cost=0.42..8.44`:** startup cost .. total cost (arbitrary units, not milliseconds).
- **`rows=1`:** estimated row count.
- **`width=64`:** average row size in bytes.

### EXPLAIN ANALYZE (runs the query)

```sql
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM orders WHERE customer_id = 42;
```

Output:
```
Index Scan using idx_orders_customer on orders  (cost=0.42..8.44 rows=1 width=64)
                                                (actual time=0.034..0.035 rows=1 loops=1)
  Index Cond: (customer_id = 42)
  Buffers: shared hit=4
Planning Time: 0.123 ms
Execution Time: 0.078 ms
```

- **`actual time`:** real milliseconds (startup..total).
- **`rows=1`:** actual row count.
- **`loops=1`:** number of times this node ran.
- **`Buffers`:** cache hits/misses (shared = shared_buffers; read = disk).

### EXPLAIN Options

```sql
EXPLAIN (ANALYZE, BUFFERS, VERBOSE, FORMAT JSON) SELECT ...;
```

- **`ANALYZE`:** run the query, show actual times.
- **`BUFFERS`:** I/O stats (cache hits/misses).
- **`VERBOSE`:** output list, filter predicates.
- **`COSTS OFF`:** hide cost estimates (for regression tests).
- **`FORMAT JSON/YAML/XML`:** machine-readable.

## 12.3 Understanding Query Plans

### Node Types

| Node | What it does | Cost shape |
|---|---|---|
| **Seq Scan** | Read the whole table | O(n) |
| **Index Scan** | B-tree lookup + heap fetch per row | O(log n + matches) |
| **Index Only Scan** | B-tree lookup, no heap fetch | O(log n + matches) |
| **Bitmap Heap Scan** | Build a bitmap of matching pages, then scan those pages | O(matches) with less random I/O |
| **Nested Loop** | For each outer row, lookup inner (often index scan) | O(outer × inner-lookup) |
| **Hash Join** | Build hash of inner, probe with outer | O(inner + outer) |
| **Merge Join** | Both sides sorted, merge | O(n + m) |
| **Sort** | Quicksort (or external if too large) | O(n log n) |
| **Aggregate** | GROUP BY | O(n) after sort/hash |
| **Hash Aggregate** | Hash-based GROUP BY | O(n) |
| **Limit** | Stop after N rows | O(N) |
| **Materialize** | Store intermediate result | O(n) |
| **CTE Scan** | Read from a CTE | O(n) |

### Reading a Plan (Top-Down)

```
Nested Loop  (cost=0.85..24.92 rows=5 width=128)
  ->  Index Scan using idx_customers_id on customers  (cost=0.42..8.44 rows=1 width=64)
        Index Cond: (customer_id = 42)
  ->  Index Scan using idx_orders_customer on orders  (cost=0.43..16.45 rows=5 width=64)
        Index Cond: (customer_id = customers.customer_id)
```

**Execution order:** *bottom-up* (inner scans run first, outer loops over them).

## 12.4 Cost Estimation

PostgreSQL estimates cost using:
- **`seq_page_cost`** (default 1.0): cost to read one page sequentially.
- **`random_page_cost`** (default 4.0): cost to read one page randomly (SSD: lower to ~1.1).
- **`cpu_tuple_cost`** (default 0.01): cost to process one row.
- **`cpu_operator_cost`** (default 0.0025): cost to evaluate one operator.

**Why random_page_cost matters:** if it's too high (4.0 on SSD), the planner prefers seq scans over index scans. Tune it:

```sql
ALTER DATABASE mydb SET random_page_cost = 1.1;
```

## 12.5 Sequential Scan vs Index Scan

**Seq Scan wins when:**
- Table is small (< a few thousand rows).
- Query matches > 5–10% of rows (index lookup + heap fetch costs exceed seq scan).
- No suitable index exists.

**Index Scan wins when:**
- Table is large and query is selective (< 5% of rows).
- Index covers the query (index-only scan).

**Bitmap Heap Scan (hybrid):** when many rows match but scattered across pages, PostgreSQL builds a bitmap of matching TIDs, sorts them, and scans pages in order (less random I/O than index scan).

## 12.6 Join Algorithms

### Nested Loop

```
for each row r in outer:
  for each row s in inner where s.key = r.key:
    emit (r, s)
```

**When it wins:** small outer, indexable inner, `LIMIT` on outer.

### Hash Join

```
1. Build hash table of inner on join key
2. Probe hash table with each outer row
```

**When it wins:** medium-to-large both sides, equi-join, no index.

### Merge Join

```
1. Sort both sides on join key
2. Merge in one pass
```

**When it wins:** both sides already sorted (index scans), large result set.

## 12.7 Statistics and ANALYZE

**PostgreSQL maintains statistics** on each column in `pg_statistic` (queried via `pg_stats`):
- **`n_distinct`:** estimated # of distinct values.
- **`most_common_vals`, `most_common_freqs`:** top values and their frequencies.
- **`histogram_bounds`:** value distribution (for range queries).

**Run `ANALYZE` to update:**

```sql
ANALYZE users;
ANALYZE;   -- all tables
```

**Auto-analyze:** enabled by default (`autovacuum_analyze_threshold`, `autovacuum_analyze_scale_factor`).

**Stale statistics → bad plans:**

```sql
-- Check last analyze time
SELECT schemaname, tablename, last_analyze, last_autoanalyze
FROM pg_stat_user_tables;
```

## 12.8 VACUUM and Autovacuum

**VACUUM** reclaims space from dead tuples (MVCC garbage):

```sql
VACUUM users;
VACUUM ANALYZE users;   -- vacuum + refresh stats
VACUUM FULL users;      -- rewrites the table (ACCESS EXCLUSIVE lock)
```

- **`VACUUM`:** marks dead tuples as reusable, updates visibility map.
- **`VACUUM FULL`:** rewrites the entire table, reclaiming disk space (slow, blocking).
- **Autovacuum:** runs in the background (default ON).

**Tuning autovacuum:**

```sql
ALTER TABLE hot_table SET (autovacuum_vacuum_scale_factor = 0.05);
-- Vacuum when 5% of rows change (default 20%)
```

## 12.9 pg_stat_statements

**The #1 performance tool:** tracks all queries run on the cluster.

```sql
CREATE EXTENSION pg_stat_statements;
-- Add to postgresql.conf: shared_preload_libraries = 'pg_stat_statements'
-- Restart PostgreSQL

SELECT query, calls, total_exec_time, mean_exec_time, stddev_exec_time, rows
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 20;
```

- **`calls`:** how many times the query ran.
- **`total_exec_time`:** cumulative time.
- **`mean_exec_time`:** average time per call.

**Use to find:**
- Slowest queries (high `mean_exec_time`).
- Highest total time (high `total_exec_time`).
- N+1 queries (high `calls`, low `mean_exec_time`).

## 12.10 Slow Query Optimization — 10 Case Studies

### Case 1: Missing Index

**Query:**
```sql
SELECT * FROM orders WHERE customer_id = 42;
```

**Plan:**
```
Seq Scan on orders  (cost=0.00..1500.00 rows=5 width=64)
  Filter: (customer_id = 42)
```

**Diagnosis:** No index on `customer_id` → full table scan.

**Fix:**
```sql
CREATE INDEX idx_orders_customer ON orders (customer_id);
```

**Result:** Index Scan, 100× faster.

---

### Case 2: Wrong Index Column Order

**Query:**
```sql
SELECT * FROM orders WHERE status = 'PAID' AND placed_at > '2026-01-01' ORDER BY placed_at DESC;
```

**Index:**
```sql
CREATE INDEX idx_orders_placed_status ON orders (placed_at, status);
```

**Plan:** Index scan, but inefficient (must scan all `placed_at > '2026-01-01'` rows, then filter `status`).

**Fix:** Swap column order (equality first, range second):
```sql
DROP INDEX idx_orders_placed_status;
CREATE INDEX idx_orders_status_placed ON orders (status, placed_at DESC);
```

---

### Case 3: Function in WHERE (Not Indexable)

**Query:**
```sql
SELECT * FROM users WHERE lower(email) = 'alice@example.com';
```

**Plan:** Seq Scan (the index on `email` is not used because `lower(email)` is computed per row).

**Fix:** Expression index:
```sql
CREATE INDEX idx_users_email_lower ON users (lower(email));
```

---

### Case 4: Deep OFFSET

**Query:**
```sql
SELECT * FROM events ORDER BY created_at DESC LIMIT 10 OFFSET 1000000;
```

**Plan:** Sort, then skip 1M rows → O(offset).

**Fix:** Keyset pagination:
```sql
-- First page
SELECT * FROM events ORDER BY created_at DESC LIMIT 10;

-- Next page (after last `created_at` from previous result)
SELECT * FROM events WHERE created_at < '2026-01-01 12:00:00' ORDER BY created_at DESC LIMIT 10;
```

---

### Case 5: N+1 Query Problem

**Code (Node.js):**
```js
const users = await db.query('SELECT * FROM users LIMIT 100');
for (const user of users) {
  const orders = await db.query('SELECT * FROM orders WHERE user_id = ?', [user.id]);
  user.orders = orders;
}
```

**Diagnosis:** 1 query for users + 100 queries for orders = 101 queries.

**Fix:** Single JOIN:
```sql
SELECT u.*, json_agg(o.*) AS orders
FROM users u
LEFT JOIN orders o ON o.user_id = u.id
GROUP BY u.id
LIMIT 100;
```

---

### Case 6: Correlated Subquery

**Query:**
```sql
SELECT c.name,
       (SELECT count(*) FROM orders o WHERE o.customer_id = c.id) AS order_count
FROM customers c;
```

**Plan:** Nested loop (subquery runs per row).

**Fix:** Window function or JOIN:
```sql
SELECT c.name, count(o.id) AS order_count
FROM customers c LEFT JOIN orders o ON o.customer_id = c.id
GROUP BY c.name;
```

---

### Case 7: OR Across Columns (Not Indexable)

**Query:**
```sql
SELECT * FROM products WHERE name LIKE '%widget%' OR description LIKE '%widget%';
```

**Plan:** Seq Scan (no index can support OR across different columns).

**Fix 1:** Full-text search:
```sql
ALTER TABLE products ADD COLUMN fts tsvector
  GENERATED ALWAYS AS (to_tsvector('english', name || ' ' || description)) STORED;
CREATE INDEX idx_products_fts ON products USING gin (fts);

SELECT * FROM products WHERE fts @@ to_tsquery('widget');
```

**Fix 2:** UNION:
```sql
SELECT * FROM products WHERE name LIKE '%widget%'
UNION
SELECT * FROM products WHERE description LIKE '%widget%';
```

---

### Case 8: Sort Without Index

**Query:**
```sql
SELECT * FROM orders ORDER BY placed_at DESC LIMIT 10;
```

**Plan:**
```
Limit  (cost=1500.00..1501.00 rows=10)
  ->  Sort  (cost=1500.00..1600.00 rows=100000)
        Sort Key: placed_at DESC
        ->  Seq Scan on orders
```

**Fix:** Index on `placed_at DESC`:
```sql
CREATE INDEX idx_orders_placed_desc ON orders (placed_at DESC);
```

**Result:** Index Scan Backward, no sort.

---

### Case 9: Unused CTE

**Query:**
```sql
WITH heavy AS (SELECT * FROM big_table)
SELECT count(*) FROM heavy WHERE x = 1;
```

**Plan:** `heavy` is materialized (computed fully), then filtered.

**Fix:** Inline or use `NOT MATERIALIZED`:
```sql
WITH heavy AS NOT MATERIALIZED (SELECT * FROM big_table)
SELECT count(*) FROM heavy WHERE x = 1;
```

---

### Case 10: Type Mismatch

**Query:**
```sql
SELECT * FROM users WHERE user_id = '42';   -- user_id is INT
```

**Plan:** Seq Scan (implicit cast `user_id::text = '42'` defeats the index).

**Fix:** Cast the literal:
```sql
SELECT * FROM users WHERE user_id = 42;
```

---

## 12.11 Query Rewriting Patterns

| Anti-pattern | Better |
|---|---|
| `SELECT *` in app code | `SELECT col1, col2, ...` (fetch only needed columns) |
| `WHERE func(col) = x` | Expression index on `func(col)`, or rewrite predicate |
| `DISTINCT` on large result | `GROUP BY` (same effect, sometimes faster plan) |
| Multiple round-trips | Batch with `IN (...)` or `ANY(array)` |
| `OFFSET 1000000` | Keyset pagination |
| Correlated subquery | JOIN or window function |
| `OR` across columns | UNION or full-text search |
| `NOT IN (subquery)` with NULLs | `NOT EXISTS` |

## 12.12 Connection Pooling

**Problem:** Each PostgreSQL connection costs ~10 MB of memory + connection overhead.

**Solution:** Connection pooler (PgBouncer, pgpool-II, Odyssey).

**PgBouncer modes:**
- **Session pooling:** one connection per client session (safe default).
- **Transaction pooling:** connection returned after each transaction (higher reuse, breaks `SET` / temp tables).
- **Statement pooling:** connection returned after each statement (breaks transactions).

```ini
[databases]
mydb = host=localhost port=5432 dbname=mydb

[pgbouncer]
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 20
```

## 12.13 Prepared Statements

**Benefit:** Parse/plan once, execute many times.

```sql
PREPARE get_user (int) AS SELECT * FROM users WHERE user_id = $1;
EXECUTE get_user(42);
EXECUTE get_user(99);
DEALLOCATE get_user;
```

**In application code (Node.js):**
```js
await client.query('SELECT * FROM users WHERE user_id = $1', [42]);
// Automatically uses a prepared statement (in postgres driver)
```

**Caveat:** Prepared statements with *generic* plans can be slower than ad-hoc queries with *custom* plans (the planner uses parameter values for a custom plan). PostgreSQL switches to a generic plan after 5 executions (configurable via `plan_cache_mode`).

## 12.14 Performance Monitoring Queries

```sql
-- Long-running queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active' AND query NOT LIKE '%pg_stat_activity%'
ORDER BY duration DESC;

-- Cache hit ratio (should be > 99%)
SELECT sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) AS cache_hit_ratio
FROM pg_statio_user_tables;

-- Index usage
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan;

-- Table sizes
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

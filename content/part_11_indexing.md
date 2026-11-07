# PART 11: INDEXING — PROFESSIONAL AND ADVANCED LEVEL

## 11.1 What Is an Index?

An **index** is a separate data structure that maintains sorted references to table rows, enabling fast lookups without scanning the whole table.

**Key insight:** An index is a **trade-off**:
- **Faster reads** (queries can skip irrelevant rows).
- **Slower writes** (every INSERT/UPDATE/DELETE must also update all affected indexes).
- **Disk space** (indexes consume storage).

**When to index:** columns in `WHERE`, `JOIN ... ON`, `ORDER BY`, `GROUP BY`, and `DISTINCT` clauses that are selective (filter out many rows).

**When NOT to index:** very small tables (seq scan is faster), columns with low cardinality (e.g., boolean on a 50/50 split), or write-heavy tables where index maintenance cost exceeds query benefit.

## 11.2 Index Types in PostgreSQL

| Type | Structure | Best for | Notes |
|---|---|---|---|
| **B-tree** | Balanced tree | `=`, `<`, `>`, `BETWEEN`, `LIKE 'prefix%'`, `ORDER BY` | Default; 99% of indexes |
| **Hash** | Hash table | `=` only | Rarely better than B-tree since PG 10 |
| **GiST** | Generalized Search Tree | Geometric, full-text, ranges | PostGIS, `tsvector` |
| **SP-GiST** | Space-partitioned GiST | Non-balanced data (IP ranges, quad-trees) | |
| **GIN** | Generalized Inverted Index | JSONB, arrays, full-text | Multi-key lookups |
| **BRIN** | Block Range INdex | Very large, naturally sorted tables (time-series) | Tiny index size |

### B-tree (the workhorse)

```sql
CREATE INDEX idx_users_email ON users (email);
CREATE INDEX idx_orders_created ON orders (placed_at DESC);
CREATE INDEX idx_products_cat_price ON products (category_id, price_cents DESC);
```

- **Composite index order matters:** `(a, b)` supports queries on `a` or `(a, b)`, but **not** `b` alone.
- **Equality + range:** put equality columns first: `(status, created_at)` supports `WHERE status='x' AND created_at > t`.

### GIN (for JSONB, arrays, full-text)

```sql
CREATE INDEX idx_metadata ON events USING gin (metadata jsonb_path_ops);
CREATE INDEX idx_tags ON products USING gin (tags);   -- array
CREATE INDEX idx_fts ON articles USING gin (to_tsvector('english', body));
```

- **`jsonb_path_ops`** is smaller and faster than default `jsonb_ops`, but only supports `@>` (containment), not key existence (`?`).

### BRIN (for huge append-only tables)

```sql
CREATE INDEX idx_events_ts_brin ON events USING brin (ts);
-- Index is ~1000× smaller than a B-tree; only useful when data is naturally sorted
```

**When BRIN wins:** time-series logs, IoT sensor data, append-only fact tables where `ts` is monotonically increasing.

## 11.3 Composite (Multicolumn) Indexes

**Rule:** columns in the index are ordered left-to-right. A query can use the index as long as it *starts* with the leftmost column(s).

```sql
CREATE INDEX idx_orders_user_created ON orders (customer_id, placed_at DESC);

-- Uses the index:
WHERE customer_id = 42 AND placed_at > '2026-01-01'

-- Uses the index (only the first column):
WHERE customer_id = 42

-- Does NOT use the index:
WHERE placed_at > '2026-01-01'
```

**Interview question:** "I have an index on `(a, b, c)`. Does `WHERE b = x AND c = y` use it?" **No** — the index requires `a` to narrow the tree; `b` and `c` alone are not at the root.

## 11.4 Partial Indexes

An index on a **subset** of rows:

```sql
CREATE UNIQUE INDEX uq_active_users_email
  ON users (email)
  WHERE deleted_at IS NULL;
```

**Use cases:**
- "One live record per key" (soft-delete tables).
- Index only the hot partition (e.g., `WHERE status IN ('pending','active')`).
- Index outliers (e.g., `WHERE price > 100000`).

**Performance:** smaller index → faster scans, less bloat.

## 11.5 Expression Indexes

Index on a **computed** column:

```sql
CREATE INDEX idx_users_email_lower ON users (lower(email));
-- Now queries with WHERE lower(email) = 'alice@example.com' use the index
```

**When to use:** when you filter/sort on a function of a column (`UPPER`, `LOWER`, `date_trunc`, `jsonb ->> 'key'`).

**Volatility requirement:** the expression must be `IMMUTABLE` (Part 2).

## 11.6 Covering Indexes (INCLUDE)

```sql
CREATE INDEX idx_products_cat_price_covering
  ON products (category_id)
  INCLUDE (name, price_cents);
```

- **`INCLUDE`** adds columns to the *leaf* level of the index (not the tree structure).
- Enables **index-only scans** for queries that `SELECT` those columns.

**Example:**

```sql
SELECT name, price_cents FROM products WHERE category_id = 3;
-- Index-only scan on idx_products_cat_price_covering (no heap fetch)
```

**Trade-off:** larger index size.

## 11.7 Index-Only Scans

When the planner can answer a query *entirely from the index* (no heap lookups), it is an **index-only scan**.

**Requirements:**
1. The index covers all columns in the `SELECT` and `WHERE` (via `INCLUDE` or natural index columns).
2. The table's **visibility map** is up-to-date (`VACUUM` cleans dead tuples and marks pages all-visible).

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT user_id FROM orders WHERE customer_id = 42;
-- Look for: "Index Only Scan"
```

**Common blocker:** stale visibility map (run `VACUUM`).

## 11.8 Unique Indexes

```sql
CREATE UNIQUE INDEX uq_users_email ON users (email);
-- Equivalent to: ALTER TABLE users ADD CONSTRAINT ... UNIQUE (email)
```

- A `UNIQUE` constraint **is** a unique index under the hood.
- **Partial unique indexes** enforce uniqueness only on the filtered rows (Part 11.4).

## 11.9 Concurrent Index Creation

```sql
CREATE INDEX CONCURRENTLY idx_orders_user ON orders (customer_id);
```

- **No write-blocking:** readers and writers continue (two-pass algorithm).
- **Cannot run inside a transaction.**
- **Longer duration** than a regular `CREATE INDEX`.
- **Failure handling:** if it fails (crash, deadlock), leaves an `INVALID` index — must `DROP` it and retry.

**Production rule:** always use `CONCURRENTLY` on live tables.

## 11.10 Index Maintenance

### REINDEX

```sql
REINDEX INDEX idx_orders_user;
REINDEX TABLE orders;
REINDEX DATABASE dbname;   -- not CONCURRENTLY; blocks
REINDEX INDEX CONCURRENTLY idx_orders_user;  -- PG12+
```

**When:** index bloat (check `pg_stat_user_indexes`), corruption (rare).

### Index Bloat

**Cause:** dead tuples accumulate inside the index; `VACUUM` does not shrink the index files (it only marks space reusable).

**Detection:**

```sql
SELECT schemaname, tablename, indexname,
       pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
ORDER BY pg_relation_size(indexrelid) DESC;
```

**Fix:** `REINDEX CONCURRENTLY`.

### Unused Indexes

```sql
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC;
```

- **`idx_scan = 0`** means the index has never been used.
- **Drop it** (after confirming the workload is representative).

### Duplicate Indexes

Two indexes with the same leading column(s):

```sql
-- Bad: idx_a on (customer_id), idx_b on (customer_id, placed_at)
-- idx_a is redundant; queries on customer_id alone can use idx_b
```

**Fix:** drop the narrower index.

## 11.11 Fillfactor

**`fillfactor`** (B-tree only): percentage of a page to fill during index build.

```sql
CREATE INDEX idx_orders_user ON orders (customer_id) WITH (fillfactor = 85);
```

- Default: 90 (leave 10% free for updates).
- **High-update tables:** lower fillfactor (70–80) reduces page splits.
- **Read-only tables:** 100 (no wasted space).

## 11.12 Operator Classes and Collations

**Operator class** determines *how* values are compared:

```sql
CREATE INDEX idx_text ON t (col text_pattern_ops);
-- Supports LIKE 'prefix%' with non-C locale
```

**Collation mismatch:**

```sql
CREATE INDEX ON users (email);   -- default collation
SELECT * FROM users WHERE email = 'Alice' COLLATE "C";
-- Index is NOT used (collation differs)
```

**Fix:** match collations between the index and the query, or create an index with the required collation.

## 11.13 Selecting the Right Index: A Decision Tree

```
Is the table < 10k rows?
  └─ YES → No index needed (seq scan is fine)
  └─ NO  → Continue

Do you filter/join on this column?
  └─ NO  → No index
  └─ YES → Continue

Is the column in ORDER BY / GROUP BY?
  └─ YES → B-tree index
  └─ NO  → Continue

Is it JSONB / array / full-text?
  └─ YES → GIN
  └─ NO  → Continue

Is the table huge and append-only (time-series)?
  └─ YES → BRIN
  └─ NO  → B-tree (default)

Do you need index-only scans?
  └─ YES → Add INCLUDE columns

Is the predicate on a function?
  └─ YES → Expression index
  └─ NO  → Done
```

## 11.14 Five Production Index Examples

### 1. E-commerce orders by customer + date

```sql
CREATE INDEX idx_orders_customer_created
  ON orders (customer_id, placed_at DESC)
  INCLUDE (total_cents, status);

-- Supports:
-- WHERE customer_id = 42 ORDER BY placed_at DESC
-- WHERE customer_id = 42 AND placed_at > '...'
-- Index-only scan for SELECT total_cents, status
```

### 2. Partial index for active rows

```sql
CREATE UNIQUE INDEX uq_users_active_email
  ON users (email)
  WHERE deleted_at IS NULL;
-- Enforces one live user per email; deleted users are ignored
```

### 3. JSONB containment

```sql
CREATE INDEX idx_events_metadata
  ON events USING gin (metadata jsonb_path_ops);
-- Fast: WHERE metadata @> '{"user_id": 42}'
```

### 4. Full-text search

```sql
ALTER TABLE articles ADD COLUMN fts tsvector
  GENERATED ALWAYS AS (to_tsvector('english', title || ' ' || body)) STORED;
CREATE INDEX idx_articles_fts ON articles USING gin (fts);
-- Fast: WHERE fts @@ to_tsquery('postgres & performance')
```

### 5. Time-series (BRIN)

```sql
CREATE INDEX idx_logs_ts_brin ON logs USING brin (created_at) WITH (pages_per_range = 128);
-- Tiny index; only useful when created_at is monotonic
```

## 11.15 Index Monitoring (Production Checklist)

```sql
-- 1. Index sizes
SELECT schemaname, tablename, indexname,
       pg_size_pretty(pg_relation_size(indexrelid))
FROM pg_stat_user_indexes
ORDER BY pg_relation_size(indexrelid) DESC LIMIT 20;

-- 2. Unused indexes
SELECT * FROM pg_stat_user_indexes WHERE idx_scan = 0;

-- 3. Index bloat (estimate via pgstattuple extension)
CREATE EXTENSION IF NOT EXISTS pgstattuple;
SELECT * FROM pgstatindex('idx_orders_user');

-- 4. Missing indexes (queries with seq scans on large tables)
SELECT schemaname, tablename, seq_scan, seq_tup_read
FROM pg_stat_user_tables
WHERE seq_scan > 1000 AND seq_tup_read / seq_scan > 10000
ORDER BY seq_tup_read DESC;
```

## 11.16 Common Index Mistakes

1. **Indexing every column** → write slowdown, bloat.
2. **Wrong column order in composite index** → planner cannot use it.
3. **Forgetting `CONCURRENTLY`** → table locked during build.
4. **Expression index without matching query** → `WHERE upper(x)` but index on `lower(x)`.
5. **Partial index predicate mismatch** → query uses `WHERE status = 'x'` but index is `WHERE status IN ('y','z')`.
6. **No `VACUUM`** → visibility map stale, no index-only scans.
7. **Duplicate indexes** → wasted space and write overhead.

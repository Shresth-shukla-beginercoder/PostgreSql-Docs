# PART 2 (continued): DML, DQL, DCL AND TCL COMMANDS

## 2.19 INSERT / INSERT INTO

**Purpose:** Add one or many rows to a table.

### Syntax

```sql
INSERT INTO table_name
    [ ( column_name [, ...] ) ]
    [ source | DEFAULT VALUES ]
    [ ON CONFLICT [ conflict_target ] conflict_action ]
    [ RETURNING * | column_name [, ...] ];

-- source is one of:
--   SELECT ... | TABLE name | VALUES ( ... ), ( ... ), ...
```

### Keywords

| Keyword | Meaning |
|---|---|
| **column list** | Optional but **always recommended** — positions matter without it. |
| **`DEFAULT VALUES`** | Inserts one row with every value from `DEFAULT` expressions; no values given. |
| **`ON CONFLICT`** | PostgreSQL upsert (see 2.21). Without it, a constraint violation aborts the whole statement. |
| **`RETURNING`** | Returns the inserted rows (or expressions) to the client — the standard way to fetch a newly generated `id`. |

### Execution behavior

- Each inserted row gets a **new row version (tuple)** in the heap; the `xmax`/`xmin` fields are tracked for MVCC (Part 14).
- **Constraint checks** run at row level (immediately) or transaction level (deferred, if `DEFERRABLE INITIALLY DEFERRED`).
- The `INSERT` statement is **atomic per statement** unless inside an explicit transaction (Part 13).

### Practical examples

```sql
-- 1. Simple positional insert
INSERT INTO users (id, email, full_name, created_at)
VALUES (1, 'alice@example.com', 'Alice', now());

-- 2. Bulk insert from a query
INSERT INTO orders_summary (day, orders, revenue)
SELECT date_trunc('day', placed_at), count(*), sum(total_cents)
FROM orders
WHERE placed_at >= now() - interval '30 days'
GROUP BY 1;

-- 3. Insert with RETURNING (get the generated key)
INSERT INTO products (name, price_cents)
VALUES ('Widget', 999)
RETURNING product_id, name;

-- 4. Multi-row VALUES
INSERT INTO tags (label)
VALUES ('PostgreSQL'), ('Docker'), ('Kubernetes'), ('Rust');

-- 5. Table defaults
INSERT INTO audit_log DEFAULT VALUES;   -- uses only column DEFAULTs
```

### Common mistakes

- **Column count/order mismatch** (the classic `INSERT INTO t VALUES (...)` where a new column was added to the table). Always write the column list.
- **`DEFAULT` vs omitting the column** — same effect for the single column, but DEFAULT applies to the *whole row* (all columns default).
- **`INSERT ... SELECT` with type mismatches:** e.g., `date` column from a `text` source — cast explicitly (`::date`).

## 2.20 UPDATE / DELETE

**Purpose:** Modify or remove matching rows.

### Syntax

```sql
UPDATE table_name
   SET column_name = expression [, ...]
 [ FROM from_items ]
 [ WHERE condition | WHERE CURRENT OF cursor_name ]
 [ RETURNING * | column_name [, ...] ];

DELETE FROM table_name
 [ USING from_item [AS name] [, ...] ]
 [ WHERE condition | WHERE CURRENT OF cursor_name ]
 [ RETURNING * | column_name [, ...] ];
```

### The `FROM` clause in UPDATE (PostgreSQL-specific)

**This is a favorite interview question** — most people don't know `UPDATE` can have a `FROM` clause:

```sql
-- Update prices from a reference table
UPDATE products p
   SET price_cents = pr.new_price
  FROM price_revisions pr
 WHERE p.product_id = pr.product_id
   AND pr.effective_at <= now();
```

- The `FROM` rows are joined against the target rows *row-by-row*; if multiple `FROM` rows match a target row, the target is updated multiple times (last one wins, or errors if ambiguous). Use `DISTINCT ON` or a CTE when you need a single source of truth.

### Execution behavior

- **`UPDATE`/`DELETE` write new tuple versions** (MVCC: old versions are marked *dead*, not physically removed — `VACUUM` reclaims them later, Part 14/12).
- **Index maintenance:** every UPDATE to an indexed column re-inserts into the index (two writes). For high-throughput tables, this is the reason to be careful with many single-column indexes.
- **Locks:** row-level `FOR UPDATE` (shared if READ COMMITTED); table-level lock if the table is concurrently being altered.

### Practical examples

```sql
-- 1. Simple
UPDATE users SET last_login_at = now() WHERE user_id = 42;

-- 2. Multi-row with JOIN
UPDATE orders o
   SET status = 'shipped'
  FROM shipments s
 WHERE o.order_id = s.order_id AND s.shipped_at IS NOT NULL;

-- 3. Bulk with RETURNING (see affected rows)
UPDATE products
   SET price_cents = price_cents + 150
 WHERE category_id = 3
RETURNING product_id, name, price_cents;

-- 4. Delete with a join (PostgreSQL FROM clause)
DELETE FROM audit_log a
  USING old_logs o
 WHERE a.log_id = o.id AND o.before < now() - interval '90 days';

-- 5. Delete where a column is NULL-safe
DELETE FROM temp_jobs WHERE lease_expires_at < now() RETURNING id;
```

### Common mistakes

- **`UPDATE t SET col = 0;`** (no `WHERE`) — updates *every row* in the table. A `pg_stat` "0 rows modified" warning is your safety net.
- **`UPDATE` with `FROM` producing multiple matches:** the target row is updated more than once. Use a CTE with `DISTINCT ON`.
- **`DELETE ... RETURNING` with no `WHERE`** — deletes the entire table.

## 2.21 UPSERT — `INSERT ... ON CONFLICT`

**Purpose:** Insert a row; if a constraint violation occurs (e.g., a UNIQUE or PK duplicate), take an alternative action — **update** the existing row instead. This is PostgreSQL's native upsert; no separate command is needed.

### Syntax

```sql
INSERT INTO table_name (cols...)
VALUES (...)
ON CONFLICT [ conflict_target ] [ DO UPDATE SET col = expr | DO NOTHING ];

-- conflict_target:
--   ( unique_col, ...)       -- the columns of a UNIQUE/PK constraint
--   ON CONSTRAINT constr_name -- a specific constraint
--   ( expression, ... )      -- a partial-index predicate
--   ARBITRARY               -- catch-all
--   WHERE predicate           -- applies to DO UPDATE
```

### Examples

```sql
-- 1. Classic upsert: replace if exists
INSERT INTO users (user_id, name, score)
VALUES (1, 'Alice', 100)
ON CONFLICT (user_id)
DO UPDATE SET name = EXCLUDED.name, score = EXCLUDED.score;

-- 2. Conditional upsert (only update when the new value is higher)
INSERT INTO leader_scores (user_id, best)
VALUES (7, 42)
ON CONFLICT (user_id)
DO UPDATE SET best = GREATEST(leader_scores.best, EXCLUDED.best);

-- 3. INSERT ... ON CONFLICT DO NOTHING (ignore duplicates)
INSERT INTO dedup_log (event_id, payload)
VALUES ('abc123', '{"a":1}')
ON CONFLICT (event_id) DO NOTHING;

-- 4. Upsert into a partial index
CREATE UNIQUE INDEX uq_active_email ON users (email) WHERE active = true;
INSERT INTO users (email, active)
VALUES ('bob@example.com', true)
ON CONFLICT (email) WHERE active
DO UPDATE SET last_seen = now();
```

- **`EXCLUDED`** is a pseudo-table holding the *would-have-been* values of the conflicting row.
- **Performance:** `DO UPDATE` acquires a stronger lock (`FOR KEY SHARE`) on the target row — fine for low-conflict, terrible if you are upserting the *same* row from many connections concurrently. For high-throughput, consider `ON CONFLICT DO NOTHING` + separate `UPDATE`, or application-level dedup.

## 2.22 RETURNING

**Purpose:** Return the rows affected by an `INSERT`, `UPDATE`, `DELETE`, or `TRUNCATE` — exactly what the operation produced. This is the *only* standard way to get back a generated key from PostgreSQL.

```sql
INSERT INTO products (name, price_cents)
VALUES ('Gadget', 4999)
RETURNING product_id, name, price_cents;

UPDATE products SET price_cents = 5499 WHERE product_id = 10
RETURNING price_cents, (price_cents - 4999) AS delta;

DELETE FROM temp_cache WHERE expired RETURNING cache_key, expires_at;
```

- **`RETURNING` changes the lock semantics:** an `UPDATE ... RETURNING` takes the same row locks as a plain UPDATE but *holds them until the transaction commits* — beware in long transactions.
- **With `pgBouncer` / connection pooling:** `RETURNING` forces the result back to the client — do not use it for fire-and-forget audit rows on hot paths.

## 2.23 SELECT — the DQL workhorse

(Deep `SELECT` clause breakdown: Parts 3–7. Here, command-level features.)

### Syntax

```sql
SELECT [ ALL | DISTINCT [ ON ( expr_list ) ] ]
       select_list | * | {table_name}.*
  FROM from_item [AS alias] [, ...]      -- or JOIN (Part 4)
 [ WHERE condition ]
 [ GROUP BY grouping_element [, ... ] ]
 [ HAVING condition ]
 [ WINDOW window_definition [, ... ] ]
 [ TABLESAMPLE method (args) ]
 [ ORDER BY expression [ASC|DESC] [NULLS {FIRST|LAST}] [, ...] ]
 [ LIMIT count | OFFSET count |
   FETCH {FIRST|NEXT} count {ROW|ROWS} ONLY |
   OFFSET count ]
 [ FOR { UPDATE | SHARE | NO KEY UPDATE | KEY SHARE } [ OF table ] ... ]
```

### The `FROM` clause: `TABLE`, `VALUES`, subqueries, and `LATERAL`

```sql
TABLE orders;                         -- ≡ SELECT * FROM orders
VALUES (1, 'a'), (2, 'b');          -- literal table
SELECT (selects from a subquery);   -- inline view
```

- **`TABLE`** is a SQL standard shorthand (also supported by `TABLE` in `INSERT`, `DELETE`, `UPDATE` sources).
- **`VALUES`** can also be a *row generator*: `SELECT * FROM (VALUES (1),(2),(3)) v(n) WHERE v.n IN (1,3)`.

### Execution behavior

- **Planning:** parser → analyzer → rewriter (CTE inlining) → planner (generates candidate plans) → cost model picks the plan → executor runs it (Part 12/29).
- **`ORDER BY` without `WHERE`/`GROUP BY`** on a large table is a **Sort** node — an expensive operation on millions of rows.
- **`LIMIT`** without `ORDER BY` returns *arbitrary* rows (no guarantee which).

## 2.24 DISTINCT / DISTINCT ON

**`DISTINCT`:** removes duplicate rows from the result set.

- **Performance:** requires a *Sort* (or hash) of all result rows — O(n log n). On a large table, prefer `GROUP BY` or a *filter predicate* if the goal is deduplication.
- **`DISTINCT ON (col)`:** PostgreSQL extension — keeps *one row per distinct value of `col`*, chosen by the `ORDER BY` order:

```sql
-- Latest event per user
SELECT DISTINCT ON (user_id) user_id, event_type, ts
FROM events
ORDER BY user_id, ts DESC;
```

> **Note:** `DISTINCT ON` is not standard SQL. For portability, use a CTE + window function (`ROW_NUMBER()`).

## 2.25 WHERE, ORDER BY, GROUP BY, HAVING

(Full keyword-by-keyword treatment: Part 3.)

- **`WHERE`:** filters *rows before* aggregation. HAVING filters *after*.
- **`GROUP BY`:** aggregates per distinct combination. `ORDER BY` aliases allowed (PostgreSQL extension).
- **`HAVING`:** filters on aggregates (`count(*) > 5`).
- **`ORDER BY`:** applies *after* `DISTINCT`/`LIMIT` in the result. Without it, results are *unordered* — never rely on implicit order.

## 2.26 LIMIT / OFFSET / FETCH

**Standard SQL (`FETCH`)** vs **PostgreSQL (`LIMIT`/`OFFSET`)**:

```sql
-- PostgreSQL / non-standard
SELECT * FROM products ORDER BY price DESC LIMIT 10 OFFSET 20;

-- Standard SQL
SELECT * FROM products ORDER BY price DESC
OFFSET 20 ROWS
FETCH NEXT 10 ROWS ONLY;
```

- **`FETCH FIRST ... ROWS ONLY`** is the SQL standard way; `LIMIT/OFFSET` is the PostgreSQL syntax.
- **`LIMIT -1`** = no limit (PostgreSQL).
- **`OFFSET` vs keyset pagination** (Part 12): deep `OFFSET` (`OFFSET 1000000`) is O(offset); keyset (WHERE id > last_seen) is O(1) per page.

## 2.27 FOR UPDATE / FOR SHARE / FOR NO KEY UPDATE / FOR KEY SHARE

**Row-level locking at the SELECT level** (used inside transactions):

```sql
SELECT * FROM products WHERE product_id = 42 FOR UPDATE;
SELECT * FROM products WHERE product_id = 42 FOR SHARE;
SELECT * FROM products WHERE product_id = 42 FOR NO KEY UPDATE;
SELECT * FROM products WHERE product_id = 42 FOR KEY SHARE;
SELECT * FROM jobs WHERE status='pending' FOR UPDATE SKIP LOCKED LIMIT 5;
```

| Mode | What it locks | Use case |
|---|---|---|
| **`FOR UPDATE`** | Full exclusive lock on the row | Reading to modify; blocks other writers |
| **`FOR NO KEY UPDATE`** | Exclusive lock, but *only if a key column would change* | Update without blocking key-based joins |
| **`FOR SHARE`** | Shared lock; blocks other `FOR UPDATE` but not readers | Read-mostly transaction needing write intent |
| **`FOR KEY SHARE`** | Shared lock on key only; lightest | Rare; blocks only FK updates |
| **`SKIP LOCKED`** | Skip rows that are already locked (non-blocking) | Job queue workers (Part 14) |
| **`NOWAIT`** | Fail immediately instead of blocking | Short-circuit contention detection |

- **`FOR UPDATE` + `ORDER BY` on the same column:** locks *in that order* (affects deadlock probability with concurrent transactions).

## 2.28 TABLESAMPLE

**Purpose:** Grab a random sample of rows for testing/debugging without reading the whole table.

```sql
SELECT * FROM orders TABLESAMPLE BERNOULLI (1.0);     -- 1% sample
SELECT * FROM orders TABLESAMPLE SYSTEM (100);        -- 100 random pages
```

- **`BERNOULLI (p)`:** keep each row with probability p.
- **`SYSTEM (n)`:** take n random pages (faster on huge tables; less random).
- **Extensions:** `ZABBERST` (non-Bernoulli, PostgreSQL 14) for exact-sized samples.

## 2.29 GRANT / REVOKE

**Purpose:** Manage privileges (Part 18 full security model).

```sql
GRANT { SELECT | INSERT | UPDATE | DELETE | TRUNCATE | REFERENCES | TRIGGER }
    [ , ... ]
    ON { [ TABLES ] table_name |
         SCHEMA schema_name |
         SEQUENCE seq_name |
         ALL TABLES IN SCHEMA schema_name }
    TO { role_name | PUBLIC } [ WITH GRANT OPTION ];

REVOKE [ GRANT OPTION FOR ] privileges
    ON object
    FROM { role_name | PUBLIC } [ CASCADE ];

ALTER DEFAULT PRIVILEGES [ FOR ROLE role ] IN SCHEMA schema
    GRANT SELECT ON TABLES TO reports_role;
```

- **`ALTER DEFAULT PRIVILEGES`:** sets permissions on *future* objects in a schema — the key to a least-privilege strategy (Part 18).
- **`GRANT`/`REVOKE` are transactional** (roll back on `ROLLBACK`).

## 2.30 SET ROLE / SET SESSION AUTHORIZATION

```sql
SET ROLE app_api;                 -- switch to a role the user is IN ROLE
RESET ROLE;
SET SESSION AUTHORIZATION app_admin;  -- superuser-only, "act as"
```

- **`SET ROLE`:** changes the *current role* for privilege checks in the current transaction.
- **`SET SESSION AUTHORIZATION`:** a superuser-only "impersonation" — use with extreme caution (audit implications).

## 2.31 BEGIN / COMMIT / ROLLBACK / SAVEPOINT

(Full transaction semantics: Part 13. Command reference here.)

```sql
BEGIN [ WORK ] [ TRANSACTION transaction_mode [, ...] ];
-- or
START TRANSACTION [ WITH ... ];

COMMIT [ WORK ] [ TO transaction_name ];
ROLLBACK [ WORK ] [ TO SAVEPOINT savepoint_name ];
ROLLBACK [ WORK ] [ TO SAVEPOINT savepoint_name ];

SAVEPOINT savepoint_name;
RELEASE SAVEPOINT savepoint_name;   -- optional; savepoints are auto-released at commit

SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;   -- affects only the *next* transaction
SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY;
```

### Transaction modes

| Mode | Keyword | Meaning |
|---|---|---|
| **Isolation** | `READ UNCOMMITTED` (mapped to `READ COMMITTED`) / `READ COMMITTED` / `REPEATABLE READ` / `SERIALIZABLE` | What a transaction can *see* |
| **Access** | `READ ONLY` / `READ WRITE` | Can the tx write? |
| **Deferrable** | `DEFERRABLE` | Allow the planner to take a deferred fast path (rarely useful) |

### Practical example (banking transfer)

```sql
BEGIN;
UPDATE accounts SET balance = balance - 500 WHERE user_id = 1;
UPDATE accounts SET balance = balance + 500 WHERE user_id = 2;
-- If both succeed:
COMMIT;
-- If either fails:
ROLLBACK;
```

- **`PREPARE TRANSACTION 'txn_abc123'`:** two-phase commit — commit after phase 1 (prepare) is logged to WAL, then commit in phase 2 (Part 13, 21).
- **`SET TRANSACTION READ ONLY`:** a fast path for read-only reports — no WAL writes.

## 2.32 psql meta-commands (not SQL)

`psql` has **client-side** commands that start with `\` — **they are not SQL** and do not work over JDBC, ODBC, or application drivers.

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

## 2.33 Shell utilities (not SQL)

These are **programs** (executed from the shell/PowerShell), not statements inside a SQL client:

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

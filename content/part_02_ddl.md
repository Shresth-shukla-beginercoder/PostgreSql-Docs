# PART 2: COMPLETE POSTGRESQL COMMAND REFERENCE — DDL COMMANDS

> This part covers PostgreSQL's **DDL (Data Definition Language)** commands. Each command gets: purpose, syntax, keyword breakdown, execution behavior, when to use / when NOT to use, two practical examples, a project example, common mistakes, and interview angles.
>
> **Version policy note:** All commands below are valid in PostgreSQL 17. Features added in PostgreSQL 15–17 are flagged. `CREATE PROCEDURE` and `MERGE` were added in PostgreSQL 14; `pg_dump`/`pg_basebackup` cover versions 12+; `ALTER DEFAULT PRIVILEGES` works on 11+ for schema-level grants.

## 2.1 CREATE DATABASE

**Purpose:** Create a new database within a PostgreSQL *cluster* (an instance).

### Syntax

```sql
CREATE DATABASE database_name
    [ WITH ] [ ENCODING 'encoding' ]
             [ LOCALE_PROVIDER { builtin | icu } ]
             [ LOCALE 'locale' ]            -- ICU
             [ COLLATE 'collation' ]        -- built-in
             [ CTYPE 'ctype' ]              -- built-in
             [ TEMPLATE template ]
             [ ACCESS METHOD 'method' ]
             [ TABLESPACE tablespace_name ]
             [ CONNECTION LIMIT connlimit ]
             [ IS_SUPERUSER { TRUE | FALSE } ]   -- added in PostgreSQL 13
```

### Keywords

| Keyword | What it does |
|---|---|
| `ENCODING` | Character set of the database (default: server's `server_encoding`). `UTF8` is overwhelmingly the right choice. |
| `TEMPLATE` | Create a copy of another database. Must not be read/written during the copy, and it fixes the encoding — you cannot freely mix template and encoding. |
| `LOCALE` / `COLLATE` / `CTYPE` | Collation rules (ordering, case sensitivity of comparisons). ICU locale provider (PostgreSQL 16) enables arbitrary ICU locales including non-Latin scripts. |
| `TABLESPACE` | Where the physical files of this database's objects live. |
| `CONNECTION LIMIT` | Maximum concurrent connections to this database. |
| `IS_SUPERUSER` | Shortcut for `ALTER DATABASE ... SET SCHEMAS`/role membership to grant/revoke the implicit superuser-like ability. |

### Execution behavior

- Not transactional: `CREATE DATABASE` cannot be run inside a transaction block (psql refuses; the server will error).
- Creates a physical *directory* (base/<db-oid>) and copies the template (default `template1`).
- The issuing user must be a **superuser** or hold the `CREATEDB` privilege (and `pg_database_owner` for template1/0 operations).
- New databases start with the `public` schema (in 15+, the default `public` schema is read-only for non-superusers; the database owner gets a grant to create in it, plus `pg_database_owner` can grant to others).

### Practical examples

```sql
-- Basic: create a dev database
CREATE DATABASE shopdb
  ENCODING 'UTF8'
  LOCALE 'en_US.UTF-8'
  TEMPLATE template0;     -- template0: empty, no custom data

-- Limit connections for a noisier dev DB
CREATE DATABASE analytics
  CONNECTION LIMIT 50
  TABLESPACE fastdisk;
```

### Common mistakes

- `CREATE DATABASE` inside a transaction (`BEGIN; CREATE DATABASE x; COMMIT;` fails).
- `DROP DATABASE` while other sessions are connected to it → `cannot drop database ... because other users are connected`. Use `ALTER DATABASE ... RENAME` + kill sessions, or the `DROP DATABASE ... WITH (FORCE)` (PostgreSQL 13+).
- Forgetting `TEMPLATE template0` when you need a pristine database — `template1` may carry objects/extensions from your environment.

### Interview angle

"Can you run DDL inside a transaction?" — Most DDL yes, `CREATE/DROP DATABASE` no. "How are two databases in one cluster isolated?" — They cannot join across each other; use `postgres_fdw` (Part 29) to reach across.

## 2.2 CREATE SCHEMA

**Purpose:** Create a namespace (schema) inside a database.

### Syntax

```sql
CREATE SCHEMA [ IF NOT EXISTS ] schema_name [ AUTHORIZATION role_name ]
CREATE SCHEMA schema_name
    CREATE TABLE t1 (a int), CREATE TABLE t2 (b int), ...   -- schema body
```

### Execution behavior

- A schema is a **namespace**, not a physical boundary: one user can own objects in many schemas; a connection can access any schema it has privileges on.
- The `search_path` (a per-database or per-role GUC) determines which schema objects are found *unqualified*.
- `ALTER SCHEMA` / `DROP SCHEMA` and `RENAME` change the name or move objects; `DROP SCHEMA ... CASCADE` removes all objects inside it.

### Practical examples

```sql
-- Dev/prod naming and audit separation
CREATE SCHEMA billing AUTHORIZATION finance_role;
CREATE SCHEMA audit;
CREATE SCHEMA legacy;

-- Add a default privilege so future tables are readable by a report role
ALTER DEFAULT PRIVILEGES IN SCHEMA billing
  GRANT SELECT ON TABLES TO report_role;
```

### When NOT to use

- Do **not** create a schema per microservice on a single database just for "isolation" unless combined with **Row-Level Security** or per-schema privileges; schemas give you no real multi-tenant isolation. RLS + per-tenant policies (Part 18) is the correct pattern.

## 2.3 CREATE TABLE

The most-used DDL command in the book.

### Syntax (complete, PostgreSQL 17)

```sql
CREATE TABLE [ IF NOT EXISTS ] [ schema_name. ] table_name (
    column_def [, ...]
    , table_constraint [, ...]
    , [ LIKE source_table [like_option ...] ]
)
[ TABLESPACE tablespace_name ]
[ PARTITION BY { RANGE | LIST | HASH } ( partition_column ) ]   -- Part 17
[ WITH ( storage_parameter = value, ... ) ]
[ USING method ]          -- access method, e.g. USING heap (default)

-- column_def
    column_name data_type [ COLLATE collation ] [ column_constraint [ ... ] ]

-- column_constraint
    [ CONSTRAINT name ] {
        PRIMARY KEY | UNIQUE [ USING method ] |
        CHECK ( expression ) |
        NOT NULL |
        DEFAULT default_expr |
        GENERATED { ALWAYS | BY DEFAULT } AS ( expression ) { VIRTUAL | STORED }  -- PG17
        | DEFERRABLE | NOT DEFERRABLE | INITIALLY DEFERRED | INITIALLY IMMEDIATE
        | REFERENCES table_name [ ( column_name ) ] [ MATCH FULL|PARTIAL|SIMPLE ]
          [ ON DELETE action ] [ ON UPDATE action ]
          [ DEFERRABLE | NOT DEFERRABLE | INITIALLY DEFERRED | INITIALLY IMMEDIATE ]
        | LIKE source_column [ VARYING ] [ { OPTIONS | CHARACTER VARYING } ]
    }

-- table_constraint
    [ CONSTRAINT name ] {
        PRIMARY KEY ( column_name [, ... ] ) |
        UNIQUE [ USING method ] ( column_name [, ... ] ) |
        CHECK ( expression ) |
        EXCLUDE USING access_method ( op [ ( op_parameter ) ] [ NULLS { DISTINCT | EQUAL } ] WITHIN PARTITION { YES | NO } [, ... ])
        | FOREIGN KEY ( column_name [, ... ] ) REFERENCES table_name [ ( column_name [, ... ] ) ]
          [ MATCH FULL | MATCH PARTIAL | MATCH SIMPLE ]
          [ ON DELETE action ] [ ON UPDATE action ]
          [ DEFERRABLE | NOT DEFERRABLE | INITIALLY DEFERRED | INITIALLY IMMEDIATE ]
    }

-- ON DELETE / ON UPDATE actions
    CASCADE | RESTRICT | SET NULL [ col ] | SET DEFAULT | NO ACTION
```

Key **table storage parameters** (`WITH (...)`) you'll actually use:

| Parameter | Meaning |
|---|---|
| `fillfactor` | Max % page fullness for a table or an index (B-tree). Leaving 10–15% for updates avoids chain rewrites. |
| `autovacuum` | Toggle or parameters for autovacuum on this table (overrides `ALTER TABLE ... SET autovacuum_enabled`). |
| `toast_tuple_target` | Threshold for TOAST-ing row overflow (Part 29). |
| `o_ids` / `oid` | Obsolete; OIDs no longer on by default (8.3+). |

### Generated columns (PostgreSQL 12+, virtual in PG15–17; STORED in PG17)

```sql
CREATE TABLE products (
    price_cents    int NOT NULL,
    currency       char(3) NOT NULL DEFAULT 'USD',
    price_display  text GENERATED ALWAYS AS (price_cents || ' ' || currency) STORED
);
```

### Practical examples

```sql
-- A clean orders table with identity, constraints, and a generated column
CREATE TABLE orders (
    order_id      bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id   int NOT NULL,
    placed_at     timestamptz NOT NULL DEFAULT now(),
    status        text NOT NULL CHECK (status IN ('PENDING','SHIPPED','DELIVERED','CANCELLED')),
    total_cents   int NOT NULL GENERATED ALWAYS AS (subtotal_cents + tax_cents) STORED,
    subtotal_cents int NOT NULL,
    tax_cents     int NOT NULL DEFAULT 0
);
```

### When NOT to use `CREATE TABLE AS` vs `CREATE TABLE ... (cols)`

`CREATE TABLE AS SELECT` (CTAS) copies **data and structure** but **not** constraints, indexes, or generated columns. When you need structure-only, use `CREATE TABLE ... AS SELECT ... WITH NO DATA`.

### Common mistakes

- **`VARCHAR(255)` by reflex:** use `TEXT` for free text (Part 8: `VARCHAR` with no limit ≡ `TEXT`; both store without length difference).
- **`SERIAL` vs `IDENTITY`:** `SERIAL` creates a separate sequence (not an actual column); `GENERATED ... AS IDENTITY` is standard SQL (PostgreSQL 10+), more portable, and preferred in new code (Part 8, 9).
- **`DEFAULT` on a `GENERATED ... AS IDENTITY` column** — not allowed.
- **`UNIQUE` without a `NULL`-aware index:** by standard SQL, `NULL ≠ NULL` so two `NULL`s are allowed in a `UNIQUE` column. If you need a "one live record per key" semantic, use a `partial unique index` (Part 11) on `WHERE deleted_at IS NULL` pattern.

## 2.4 CREATE VIEW

**Purpose:** A stored query. A **virtual** table: no data of its own, re-executed on every use.

### Syntax

```sql
CREATE [ OR REPLACE ] VIEW view_name
    [( column_name [, ...] )]
    AS SELECT statement
    [ WITH [ CASCADED | LOCAL ] CHECK OPTION [ CONSTRAINT constraint_name ] ]
    [ WITH [ NOT ] READABLE ]

CREATE [ OR REPLACE ] [ TEMPORARY | TEMP ] VIEW ...  -- session-scoped
```

- **`WITH CHECK OPTION`** forces INSERT/UPDATE through the view to keep rows valid in the view.
- **`READABLE`** restricts the view to the listed columns in *selective* privilege grants.
- **`OR REPLACE`** rewrites the view definition without recreating it (keeps dependent objects and privileges).

### Execution behavior

- Views are **rewritten into the outer query** by the planner; a query using the view is planned as if the view's SELECT were inlined.
- **Materialized differently from `MATERIALIZED VIEW`:** a plain `VIEW` always shows *current* data; a `MATERIALIZED VIEW` shows a *frozen copy* until `REFRESH` (Part 2 covers `REFRESH MATERIALIZED VIEW`).
- **Recursive CTEs and `LATERAL`** can appear in views.
- **Upserts through a view:** if the view is *simple* (one table, no aggregation, no DISTINCT, no GROUP BY, no window functions), INSERT/UPDATE/DELETE pass through automatically.

### Practical examples

```sql
-- Simple filter
CREATE VIEW v_active_users AS
SELECT user_id, email, created_at
FROM users
WHERE deleted_at IS NULL AND status = 'active';

-- Aggregation (not updatable — correct usage: reporting only)
CREATE VIEW v_revenue_by_month AS
SELECT date_trunc('month', placed_at) AS month, sum(total_cents) AS revenue
FROM orders GROUP BY 1;

-- Upsertable view
CREATE VIEW v_high_value_orders AS
SELECT * FROM orders WHERE total_cents > 50000;
-- Now: UPDATE v_high_value_orders SET status='CANCELLED' WHERE ...;   (works — simple view)
```

### When NOT to use a plain view

- Heavy aggregation used repeatedly → use a **materialized view** with periodic `REFRESH` (or a real table refreshed by a pipeline).
- A query that must be stable across data changes in a transaction → use **CTEs or materialized views** (a plain view replays on every reference).

## 2.5 CREATE MATERIALIZED VIEW

**Purpose:** A *frozen* result of a query, stored on disk. Query is computed at creation/refresh, not on read.

### Syntax

```sql
CREATE [ OR REPLACE ] MATERIALIZED VIEW mv_name
    [( column_name [, ...] )]
    AS SELECT statement
    [ WITH DATA | WITHOUT DATA ]           -- WITH DATA computes at creation
    [ TABLESPACE tablespace_name ]
    [ WITH ( storage_parameter = value, ... ) ]

REFRESH [ CONCURRENTLY ] MATERIALIZED VIEW mv_name [ WHERE condition ]
DROP MATERIALIZED VIEW [ IF EXISTS ] mv_name [ CASCADE ]
TRUNCATE TABLE mv_name
```

**`REFRESH CONCURRENTLY`** (requires a UNIQUE index on the materialized view) applies changes without blocking readers — like a parallel UPDATE of the materialized view.

### Practical example (analytics pipeline)

```sql
CREATE MATERIALIZED VIEW mv_daily_sales AS
SELECT date_trunc('day', placed_at) AS day,
       category_id,
       count(*) AS orders,
       sum(total_cents) AS revenue
FROM orders JOIN products USING (product_id)
GROUP BY 1, 2
WITH DATA;

CREATE UNIQUE INDEX ON mv_daily_sales (day, category_id);   -- enables CONCURRENTLY

-- Nightly refresh without stopping reads:
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_sales;
```

### When NOT to use

- Data that must reflect the *current* table state — that's a plain `VIEW`.
- If you need transactional visibility (MVCC) inside a transaction — use a CTE/subquery; materialized views are "as of the refresh," not "as of the transaction."

## 2.6 CREATE INDEX / CREATE UNIQUE INDEX / CREATE INDEX CONCURRENTLY

(Full index theory: Part 11. This section covers the commands.)

### Syntax

```sql
CREATE [ UNIQUE ] INDEX [ IF NOT EXISTS ] index_name
    ON [ ONLY ] table_name [ USING method ]
    ( column_name [ COLLATE collation ] [ opclass ] [ ASC | DESC ] [ NULLS { FIRST | LAST } ] [, ...] )
    [ INCLUDE ( include_column [, ... ] ) ]           -- covering index, PG11+
    [ WITH ( storage_parameter = value, ... ) ]
    [ TABLESPACE tablespace_name ]
    [ WHERE predicate ]                                 -- partial index

-- For concurrent building without blocking:
CREATE INDEX CONCURRENTLY [ IF NOT EXISTS ] idx_name
    ON table_name USING method (column) ...;
-- Must be run OUTSIDE a transaction block.

DROP INDEX [ IF EXISTS ] index_name [, ...]
REINDEX [ ( CONCURRENTLY | VERBOSE ) ] [ INDEX | TABLE ] index_name | table_name;
```

- **`CONCURRENTLY`** builds a shadow index and merges it, so readers/writers are not blocked. It takes **two passes** and fails atomically on error. Cannot run inside a transaction.
- **`INCLUDE`** adds columns to the index *without* making them part of the tree — enables **index-only scans** for queries that select those columns but don't filter on them (Part 11, 12).
- **`USING method`:** `btree` (default), `hash`, `gin`, `gist`, `spgist`, `brin`, `pgvector`? no — `btree` is default; other methods come from extensions (Part 24).

### Practical examples

```sql
-- Composite index matching a WHERE + JOIN pattern
CREATE INDEX idx_orders_customer_created
  ON orders (customer_id, created_at DESC);

-- Covering index: avoid a heap fetch for report columns
CREATE INDEX idx_products_hot
  ON products (category_id)
  INCLUDE (name, price_cents, tax_rate);

-- Partial index: only where deleted_at IS NULL
CREATE UNIQUE INDEX uq_users_active_email
  ON users (email)
  WHERE deleted_at IS NULL;

-- Concurrent build in production
CREATE INDEX CONCURRENTLY idx_events_user_ts ON events (user_id, ts);
```

### Common mistakes

- **Creating duplicate indexes** (`idx_orders_customer` and `idx_orders_customer_ts` on the same column). Check `pg_stat_user_indexes` (Part 30).
- **Including columns you don't need** in the covering index — bloat.
- **`CONCURRENTLY` inside a transaction** → error: "CREATE INDEX CONCURRENTLY cannot run inside a transaction block."
- **Indexing a column with a `COLLATE` that doesn't match the index's collation** — the planner can't use the index for string comparisons.

## 2.7 CREATE SEQUENCE

**Purpose:** An autonomous counter object. Backs `SERIAL`/`BIGSERIAL` columns and `GENERATED ... AS IDENTITY`.

### Syntax

```sql
CREATE SEQUENCE [ IF NOT EXISTS ] sequence_name
    [ AS data_type ]                      -- default BIGINT
    [ INCREMENT [ BY ] n ]                -- step
    [ MINVALUE n | NO MIN ]
    [ MAXVALUE n | NO MAX ]
    [ START [ WITH ] n ]
    [ CACHE n ]                           -- pre-allocated batch
    [ [ NO ] CYCLE ]

ALTER SEQUENCE seq_name SET INCREMENT BY 2;
DROP SEQUENCE [ IF EXISTS ] seq_name;
SELECT nextval('seq'), lastval('seq'), setval('seq', 1000);
```

### Behavior

- **Cache:** pre-generates `CACHE` values in a shared memory block; speeds up allocation but leaves "gaps" after a crash. `NO CYCLE` + cache can jump when the server crashes (non-contiguity is the trade-off).
- **`nextval`** is atomic and safe under concurrency (even across parallel workers) — one of the few truly "distributed" operations.
- **Identity columns** use the same mechanism: `int` generated as identity → `nextval` on the hidden sequence.

### Practical example

```sql
-- Ticket numbers that never repeat across restarts
CREATE SEQUENCE ticket_id_seq
  AS BIGINT START 100000 INCREMENT BY 1
  NO MINVALUE NO MAXVALUE CYCLE;

SELECT nextval('ticket_id_seq');   -- 100000
```

## 2.8 CREATE TYPE

**Purpose:** Define composite types and ENUMs.

### Syntax

```sql
CREATE TYPE type_name AS ( column_name data_type [, ...] );   -- composite
CREATE TYPE type_name AS ENUM ( 'val1', 'val2', ... );        -- enum

CREATE TYPE complex AS COMPLEX ( real_value double precision,
                                 imag_value double precision );
CREATE TYPE intarray AS ( data int[], length int );

ALTER TYPE type_name ADD VALUE 'new_value';
ALTER TYPE type_name RENAME VALUE 'old' TO 'new';
DROP TYPE [ IF EXISTS ] type_name [ CASCADE ];
```

- **ENUM:** stored as a 4-byte OID internally. New values in *existing* ENUMs require `ALTER TYPE ... ADD VALUE`, which is **not allowed inside a transaction** and can block writers on tables using it.
- **Composite:** can be used as a column type (`col complex_type NOT NULL`), a function return type, or as a *type cast* `ROW(1,2)::intpair`.

### When NOT to use ENUM

- Frequent value additions or removals → use `CHECK` constraint on `TEXT`, or a *lookup table* for referential integrity.
- If the "type" is really a *dimension* (status, category), a lookup table + `FK` is more flexible than an ENUM.

## 2.9 CREATE DOMAIN

**Purpose:** A named data type with its own constraints — a "type + rules" bundle.

```sql
CREATE DOMAIN phone AS char(11)
  CHECK (VALUE ~ '^[0-9]{11}$');

CREATE DOMAIN email_addr AS text
  CHECK (value LIKE '%_@_%');

CREATE DOMAIN us_state AS char(2)
  CHECK (value IN ('CA','TX','NY','...'));
```

Domains can reference other domains; `ALTER DOMAIN ... ADD CONSTRAINT`.

## 2.10 CREATE FUNCTION

The most powerful (and most-misused) command in the DDL section. Full procedural coverage is in Part 15; this section is about *declaring* functions.

### Syntax

```sql
CREATE [ OR REPLACE ] FUNCTION function_name ( [ argument_name ] arg_type [, ...] )
    RETURNS return_type
    | RETURNS TABLE ( col1 type1, col2 type2 )
    | RETURNS SEQUENCE type
    { LANGUAGE plpgsql | LANGUAGE sql | LANGUAGE c | ... }
    AS $$ ... body ... $$
    [ WINDOW { [ window_name, ... ] } WINDOW { [ window_name, ... ] } ]
    [ CALLED ON NULL INPUT | RETURNS NULL ON NULL INPUT | STRICT ]
    [ VOLATILE | STABLE | IMMUTABLE ]
    [ [ NOT ] LEAKPROOF ]
    [ COST cost ]
    [ ROWS result_rows ]
    [ SET configuration_parameter = value ]
    [ AS 'library', 'symbol' ]    -- C language
```

### Volatility categories (interview favorite)

| Category | Meaning | Example |
|---|---|---|
| `VOLATILE` | Output can change on each call, even with the same arguments (may use randomness, external state) | `now()`, `random()`, functions that read tables |
| `STABLE` | Same input → same output within one statement, but may vary across statements | `now()` (within a transaction is fixed), `currval()`, user-defined that only reads |
| `IMMUTABLE` | Output is a pure function of arguments | `abs(x)`, `length(s)`, user-defined without external state |

**Why it matters:** `IMMUTABLE` functions can be **indexed** (expression indexes on them are stable), folded at plan time, and used in partitioned-index predicates. `VOLATILE` functions defeat any such optimization.

### Practical examples

```sql
-- Immutable: safe to index on
CREATE FUNCTION is_vip(score int) RETURNS boolean
  LANGUAGE sql IMMUTABLE AS
  $$ SELECT score >= 90 $$;
CREATE INDEX ON customers (is_vip(score));   -- planner can evaluate at plan time

-- Volatile: re-evaluated every row
CREATE FUNCTION last_sync() RETURNS timestamptz
  LANGUAGE sql VOLATILE AS $$ SELECT max(updated_at) FROM sync_log $$;

-- Aggregate / set-returning
CREATE FUNCTION top_products_by_cat(cat_id int)
RETURNS TABLE ( product_id int, units int )
LANGUAGE sql STABLE AS
$$ SELECT product_id, count(*) FROM orders JOIN order_items USING (product_id)
   WHERE category_id = cat_id GROUP BY 1 ORDER BY 2 DESC LIMIT 5 $$;

SELECT * FROM top_products_by_cat(42);
```

**`SECURITY DEFINER` vs `SECURITY INVOKER`:**

- `INVOKER` (default): function runs with the *caller's* privileges.
- `DEFINER`: runs with the *owner's* privileges — needed for cross-tenant or elevated-privilege logic (Part 18 security). **Never** grant `DEFINER` on a function that touches `pg_class`/system catalogs unless you audit it.

## 2.11 CREATE PROCEDURE (PostgreSQL 14+)

A stored *procedure* — called with `CALL proc(...)` rather than `SELECT func(...)`. Differences from functions:

- Cannot be used *in a query* (no `SELECT proc()`; only `CALL proc()`).
- Can contain `SAVEPOINT`, `COMMIT`/`ROLLBACK`? **No** — inside a procedure, `SAVEPOINT` is allowed but `COMMIT`/`ROLLBACK` are **not** (they must be issued outside the procedure body itself; the statement `COMMIT` inside the proc is not supported).
- **`PLPGSQL`** supports `EXECUTE ... ;` and the `CALL`/`SAVEPOINT` keywords.
- `PROCEDURE` vs `FUNCTION` in an interview: a *procedure* is a unit of work that *must* be called from a client or a trigger; a *function* is a value-producing unit.

## 2.12 CREATE TRIGGER

(Full trigger semantics: Part 15. Here, command syntax.)

```sql
CREATE [ OR REPLACE ] TRIGGER trigger_name
    { BEFORE | AFTER | INSTEAD OF } { event [, ...] }
    ON table_name                          -- or VIEW for INSTEAD OF
    [ FOR { EACH ROW | EACH STATEMENT } ]
    [ WHEN ( condition ) ]
    [ FROM transition_table_name ]        -- PG13+, transition tables for AFTER triggers
    [ REFERENCING OLD TABLE AS n ]
    EXECUTE FUNCTION function_name [ ( args ) ];

ALTER TRIGGER trig_name DISABLE;   -- or ENABLE
DROP TRIGGER [ IF EXISTS ] trig_name ON table_name;
```

- **BEFORE ROW triggers:** *can* modify the new row (`NEW` can be assigned).
- **AFTER triggers:** run after the statement; cannot modify rows.
- **INSTEAD OF:** view-only; replaces INSERT/UPDATE/DELETE on the view with the trigger's logic.

## 2.13 CREATE ROLE / CREATE USER

**Purpose:** Create a *role* (PostgreSQL's term for an account). `CREATE USER` is shorthand for `CREATE ROLE ... LOGIN`.

```sql
CREATE ROLE role_name
    [ SUPERUSER | NOSUPERUSER ]
    [ CREATEDB | NOCREATEDB ]
    [ CREATEROLE | NOCREATEROLE ]
    [ INROLE | INGROUP role_name ]
    [ LOGIN | NOLOGIN ]
    [ REPLICATION | NOREPLICATION ]
    [ CONNECTION LIMIT connlimit ]
    [ VALID UNTIL 'date' ]
    [ PASSWORD 'scram_sha_256_password' ]   -- stored as SCRAM by default (PG10+)

CREATE USER app_user WITH LOGIN PASSWORD '...';   -- = CREATE ROLE ... LOGIN
```

- **`ROLE`** = any role. **`USER`** = a role with `LOGIN` (an account that can connect).
- **Inheritance:** by default, `CREATE ROLE` inherits from parent roles — if you `GRANT role_a TO role_b`, role_b gets role_a's privileges without an `explicit`. Use `NOINHERIT` to decouple: `CREATE ROLE x NOINHERIT` + explicit `GRANT x TO me; SET ROLE x;`.

### Practical example

```sql
-- Least-privilege app role
CREATE ROLE app_api LOGIN PASSWORD 'change_me';
GRANT USAGE ON SCHEMA public TO app_api;
GRANT SELECT, INSERT, UPDATE ON TABLE users, orders TO app_api;
GRANT USAGE ON SEQUENCE orders_order_id_seq TO app_api;

-- Read-only reporting role
CREATE ROLE reports NOLOGIN;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO reports;
```

## 2.14 CREATE EXTENSION

**Purpose:** Install a compiled library + catalog entries that add features (PostGIS, pgvector, pg_trgm, `pg_stat_statements`, etc.).

```sql
CREATE EXTENSION [ IF NOT EXISTS ] extension_name
    [ WITH ( option = value, ... ) ]
    [ SCHEMA schema_name ]
    [ CASCADE ]
```

- **Requires:** the user to be a **superuser** (or a role with `CREATE ANY` on the extension) and the server to have the extension files installed (compiled `.so` in `pglib`/`share`).
- **`pg_stat_statements`** must be installed *and* enabled in `postgresql.conf` (`shared_preload_libraries`) before it can work.

## 2.15 ALTER DATABASE / ALTER SCHEMA / ALTER INDEX / ALTER ROLE

```sql
ALTER DATABASE db_name
    RENAME TO new_name
  | SET configuration_parameter { TO value | FROM RESET }
  | RESET configuration_parameter
  | SET SCHEMA search_path_schema AS search_path
  | OWNER TO new_owner
  | SET CONNECTION LIMIT connlimit
  | WITH TEMPLATE ...

ALTER SCHEMA schema_name RENAME TO new_schema_name;
ALTER SCHEMA schema_name OWNER TO new_role;

ALTER INDEX idx_name
    RENAME TO new_name
  | SET TABLESPACE tablespace_name
  | SET ( fillfactor = value );

ALTER ROLE role_name
    [ RENAME TO new_role ]
    [ WITH { SUPERUSER | NOSUPERUSER } [ CREATEROLE | NOCREATEROLE ] ... ]
    [ SET configuration_parameter = value ]
    [ IN ROLE role_name ]
    [ IN GROUP group_role ]
```

- **`ALTER DATABASE ... SET`** sets a per-database GUC that applies to all new sessions on that DB — useful for pinning a database to `timezone` or `search_path`.
- **`ALTER SCHEMA RENAME`** rewrites all object names referencing it (catalog surgery).

## 2.16 DROP DATABASE / DROP TABLE / DROP VIEW / DROP INDEX / DROP SCHEMA

```sql
DROP DATABASE [ IF EXISTS ] database_name [ WITH ( FORCE ) ];   -- FORCE: PG13+
DROP TABLE [ IF EXISTS ] table_name [, ...] [ CASCADE ];
DROP VIEW [ IF EXISTS ] view_name [, ...] [ CASCADE ];
DROP INDEX [ IF EXISTS ] index_name [, ...];
DROP SCHEMA [ IF EXISTS ] schema_name [ CASCADE ];
DROP SEQUENCE [ IF EXISTS ] seq_name;
DROP TYPE [ IF EXISTS ] type_name;
DROP DOMAIN [ IF EXISTS ] domain_name;
DROP FUNCTION [ IF EXISTS ] func_name( arg_types );     -- arg types required!
DROP PROCEDURE [ IF EXISTS ] proc_name( arg_types );
DROP TRIGGER [ IF EXISTS ] trig_name ON table_name;
DROP ROLE [ IF EXISTS ] role_name;
DROP USER [ IF EXISTS ] user_name;
DROP EXTENSION [ IF EXISTS ] ext_name [ CASCADE ];
DROP POLICY policy_name ON table_name;

TRUNCATE [ TABLE ] table_name [ RESTART IDENTITY | CONTINUE IDENTITY ] [ CASCADE ];
```

- **`CASCADE`** means "drop everything that *depends* on this object" — **dangerous**: `DROP TABLE ... CASCADE` will remove views, materialized views, and indexes on that table.
- **`TRUNCATE` vs `DELETE`:** TRUNCATE resets sequences and is O(1) vs O(rows). **Locking:** TRUNCATE takes an ACCESS EXCLUSIVE lock (like DROP). DELETE takes row-level locks.
- **`DROP FUNCTION` requires argument types:** `DROP FUNCTION my_func();` → "multiple functions match". You must write `DROP FUNCTION my_func(int);`.

## 2.17 COMMENT ON

**Purpose:** Attach human-readable comments to any database object — they persist, show up in `\d` output, and are the DBA's best tool for documentation.

```sql
COMMENT ON DATABASE db_name = 'E-commerce production';
COMMENT ON SCHEMA public = 'Main application schema';
COMMENT ON TABLE orders = 'Customer orders. Partitioned by created_at monthly (2024+).';
COMMENT ON COLUMN orders.status = 'PENDING | SHIPPED | DELIVERED | CANCELLED. Never use lowercase.';
COMMENT ON INDEX idx_orders_customer_created = 'Covering index for orders-by-customer reports.';
COMMENT ON FUNCTION top_products_by_cat(int) = 'Returns the top 5 products in a category.';
COMMENT ON TRIGGER trg_audit_orders ON orders = 'Writes to audit_log on UPDATE.';
COMMENT ON TYPE order_status = 'Values: PENDING, SHIPPED, DELIVERED, CANCELLED.';
COMMENT ON DOMAIN email_addr = 'Email addresses, enforced with a CHECK.';
COMMENT ON EXTENSION pgvector = 'Adds vector type and distance operators for AI workloads.';
```

- **`SHOW` in psql:** `\d+ orders` displays the comment next to the object.
- **No syntax validation:** comments are free text; the *statement* is just `COMMENT ON ... = '...'`.

## 2.18 DESTRUCTIVE-WARNING — Commands that can destroy data

| Command | Destructive | Mitigation |
|---|---|---|
| `TRUNCATE TABLE` | Yes (all rows) | Run inside a transaction; use `ROLLBACK` to confirm. |
| `DROP TABLE/INDEX/VIEW SCHEMA ... CASCADE` | Yes (and dependents) | Review with `\dd`/`\di`/`pg_depend` before running. |
| `ALTER TABLE ... DROP COLUMN` | Yes (data) | `ALTER TABLE ... RENAME COLUMN` instead if you might need it back. |
| `DROP DATABASE` | Yes | `pg_dump` first; confirm no active sessions (or use `WITH (FORCE)` and kill). |
| `REINDEX DATABASE ...` | No, but expensive | Run off-peak; use `CONCURRENTLY` for individual indexes. |
| `VACUUM FREEZE` | No (maintenance) | Fine off-peak. |

> **Professional practice:** In production, any DDL that changes *data* or *removes* objects should (a) run inside a transaction when possible, (b) have a *tested rollback script* ready, and (c) be communicated to the team (especially `DROP ... CASCADE` and `TRUNCATE`).

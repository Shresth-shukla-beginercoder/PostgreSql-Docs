# PART 31: COMPLETE KEYWORD GLOSSARY

Alphabetical glossary of SQL and PostgreSQL terminology used throughout this
handbook. Each entry states: definition, syntax where applicable, example,
related concepts, and its classification — **STD** (standard SQL),
**PG** (PostgreSQL-specific), **CLIENT** (psql meta-command), or **SHELL**
(external utility).

| Term | Class | Definition |
|---|---|---|
| **ACCESS EXCLUSIVE** | STD | Strongest table lock mode; blocks all other locks. Taken by `DROP`, `TRUNCATE`, `ALTER TABLE`. |
| **ACID** | STD | Atomicity, Consistency, Isolation, Durability — transaction guarantees. |
| **ALTER TABLE** | STD | Change a table's structure: add/drop/modify columns, add constraints, rename. |
| **AND** | STD | Boolean operator; both sides must be TRUE. Three-valued logic with NULL. |
| **ANY** | STD | `x = ANY (list)` is true if x equals any list element. Also `SOME` (synonym). |
| **ARRAY** | PG | Native multi-value type: `int[]`, `text[]`; supports `unnest`, `array_agg`, GIN indexing. |
| **AS** | STD | Introduces a table/column alias. |
| **AT TIME ZONE** | STD | Converts `timestamptz` to another zone (or `timestamp` to `timestamptz`). |
| **AUTHORIZATION** | STD | Grants object ownership to a role. |
| **BERNOULLI / SYSTEM (TABLESAMPLE)** | STD/PG | Sampling methods: row-probability vs. page-random. |
| **BETWEEN** | STD | Inclusive range test: `x BETWEEN a AND b`. |
| **BIGSERIAL / SMALLSERIAL** | PG | Legacy auto-numbering sequences; prefer `IDENTITY`. |
| **BIGINT / INTEGER / SMALLINT** | STD | Fixed-width integers (8/4/2 bytes). |
| **BOUNCE / CHECKPOINT** | STD | Forced write of all modified buffers to disk. |
| **CASCADE (constraint option)** | STD | Delete/update parent also deletes/updates children. Also `DROP ... CASCADE` removes dependents. |
| **CHAR / VARCHAR / TEXT** | STD/PG | Character types; in PostgreSQL `TEXT` and unbounded `VARCHAR` are equivalent. |
| **CHECK** | STD | Boolean predicate constraint on rows. |
| **CHECKPOINT** | STD | WAL flush boundary guaranteeing on-disk consistency. |
| **COLLATE / COLLATION** | STD | Rules for string comparison; "C" is byte order. |
| **COMMIT / ROLLBACK / BEGIN** | STD | Transaction control. |
| **CONCAT / CONCAT_WS** | PG | String concatenation; `CONCAT` ignores NULLs, `CONCAT_WS` takes a separator. |
| **CONCURRENTLY (CREATE INDEX)** | PG | Build an index without blocking the table. |
| **CONSTRAINT** | STD | Named rule (PK, FK, UNIQUE, CHECK, EXCLUDE) enforcing integrity. |
| **CROSS JOIN** | STD | Cartesian product; no `ON` predicate. |
| **CTE (Common Table Expression)** | STD | `WITH name AS (SELECT ...)` named subquery; `RECURSIVE` self-reference. |
| **CYCLE / NO CYCLE** | PG | Sequence wrap behavior. |
| **DATE / TIME / TIMESTAMP / TIMESTAMPTZ / INTERVAL** | STD | Temporal types; `timestamptz` stores instant (UTC), renders locally. |
| **DEFERRABLE / INITIALLY DEFERRED / INITIALLY IMMEDIATE** | STD | When a constraint is enforced: per-statement vs. at commit. |
| **DEFAULT (value)** | STD | Value used when a column is not supplied. |
| **DELETE** | STD | Remove matching rows; MVCC + log-based. |
| **DENSE_RANK** | STD | Ranking with gaps closed on ties (1,2,2,3). |
| **DOMAIN** | PG | Named base type + constraints (`CREATE DOMAIN`). |
| **DROP TABLE / VIEW / INDEX / SCHEMA / FUNCTION / ROLE / EXTENSION / DATABASE** | STD | Remove objects; `CASCADE` removes dependents. |
| **ELSE / END / THEN / WHEN / CASE** | STD | Conditional expression and PL/pgSQL control flow. |
| **EXCLUDE** | PG | Exclusion constraint preventing overlapping ranges (uses GiST). |
| **EXCLUDE CURRENT ROW** | PG | Window frame exclusion option. |
| **EXISTS** | STD | Subquery predicate: at least one row returned. |
| **EXPLAIN [ANALYZE] [BUFFERS] [VERBOSE]** | STD/PG | Show the query plan; `ANALYZE` actually runs the query and reports real timings. |
| **FETCH FIRST n ROWS ONLY** | STD | Standard limit syntax (`LIMIT`/`OFFSET` is the PG equivalent). |
| **FILTER (WHERE ...)** | STD | Conditional aggregate: `count(*) FILTER (WHERE x)`. |
| **FIRST_VALUE / LAST_VALUE / NTH_VALUE** | STD | Window functions; `LAST_VALUE` requires the whole-partition frame to be meaningful. |
| **FOR UPDATE / FOR SHARE / FOR NO KEY UPDATE / FOR KEY SHARE** | STD | Row-lock modes on `SELECT`. `NOWAIT`/`SKIP LOCKED` (PG) control blocking. |
| **FOREIGN KEY / REFERENCES** | STD | Referential integrity between tables. |
| **FORMAT (...)** | PG | printf-style string formatter (`format('%s', x)`). |
| **FULL OUTER JOIN** | STD | Rows from both sides; NULLs where unmatched. |
| **GENERATED ALWAYS AS IDENTITY** | STD | Standard auto-numbering column (PG10+). |
| **GIN / GiST / Hash / B-tree / BRIN / SP-GiST** | PG | Index access methods: inverted, tree, hash, B-tree, block-range, space-partitioned. |
| **GROUP BY / HAVING** | STD | Aggregate groups / filter groups. |
| **IDENTITY** | STD | See `GENERATED ... AS IDENTITY`. |
| **ILIKE** | PG | Case-insensitive `LIKE`. |
| **INCLUDE (index option)** | PG | Covering-index columns (leaf-only, enabling index-only scans). |
| **INDEX ONLY SCAN** | PG | Plan node reading only the index (needs up-to-date visibility map). |
| **IN / NOT IN** | STD | List membership; `NOT IN` is NULL-poisoned. |
| **INNER JOIN / LEFT JOIN / RIGHT JOIN** | STD | Overlap / left-preserved / right-preserved joins. |
| **INSTEAD OF TRIGGER** | PG | View trigger that substitutes the operation. |
| **INTERSECT / EXCEPT / UNION / UNION ALL** | STD | Set operations. |
| **IS DISTINCT FROM** | STD | NULL-safe inequality (total order, returns TRUE on NULL vs value). |
| **IS NULL / IS NOT NULL** | STD | NULL tests. |
| **JOIN** | STD | Row-linking operation; algorithms: Nested Loop, Hash, Merge. |
| **JSON / JSONB** | STD/PG | Text-preserved JSON / binary, indexable JSON. |
| **KEYSET PAGINATION** | — | `WHERE pk > last_seen ORDER BY pk LIMIT n` — constant-depth pagination. |
| **LATERAL** | PG | `FROM` subquery referencing preceding items. |
| **LEAD / LAG** | STD | Window functions reading neighboring rows. |
| **LIKE** | STD | Pattern match with `%`, `_`. |
| **LIMIT / OFFSET** | PG | Row-limiting syntax (standard: `FETCH`/`OFFSET ... ROWS`). |
| **LOCK TABLE / NOWAIT / SKIP LOCKED** | STD/PG | Explicit table locking; non-blocking variants are PG. |
| **MATERIALIZED VIEW / REFRESH [CONCURRENTLY]** | PG | Stored query result; `CONCURRENTLY` needs a UNIQUE index. |
| **MERGE** | STD (PG15+) | Conditional insert/update/delete in one statement. |
| **MODE() WITHIN GROUP** | STD | Ordered-set aggregate: most frequent value. |
| **MULTIRANGE** | PG (14+) | Set of non-overlapping ranges. |
| **MVCC** | — | Multi-version concurrency control: row versions `xmin`/`xmax`. |
| **NATURAL JOIN** | STD | Join on all same-named columns (not supported as a keyword in PostgreSQL). |
| **NTH_VALUE / NTILE / RANK / ROW_NUMBER / DENSE_RANK** | STD | Window ranking/offset functions. |
| **NULL / NULLS FIRST / NULLS LAST** | STD | Missing-value token and its ordering. |
| **NUMERIC / DECIMAL** | STD | Exact arbitrary-precision numbers; use for money. |
| **ON (join clause)** | STD | Join predicate; `ON DELETE/UPDATE` referential actions. |
| **OR / NOT** | STD | Boolean operators; `AND` binds tighter. |
| **OVER / PARTITION BY / WINDOW** | STD | Window function syntax; named windows are PG extension. |
| **PERCENTILE_CONT / PERCENTILE_DISC** | STD | Ordered-set quantile aggregates. |
| **pg_* catalogs / views** | PG | `pg_class`, `pg_attribute`, `pg_constraint`, `pg_stat_activity`, `pg_locks`, `pg_stat_statements`, `pg_replication_slots`, … |
| **PRIMARY KEY** | STD | UNIQUE + NOT NULL; one per table. |
| **PROCEDURE / CALL** | STD (PG14+) | Stored procedure invoked with `CALL`. |
| **psql** | CLIENT | Interactive SQL client; `\` meta-commands are client-side, not SQL. |
| **RANGE / ROWS / GROUPS (frame)** | STD/PG | Window frame units; `GROUPS` is PG17+. |
| **RANK / DENSE_RANK** | STD | Ranking with/without gap-closing. |
| **RECURSIVE CTE** | STD | Self-referencing CTE. |
| **REFERENCES / ON DELETE / ON UPDATE** | STD | FK target + referential actions (CASCADE/RESTRICT/SET NULL/SET DEFAULT/NO ACTION). |
| **REGEXP_REPLACE / regexp_like / `~`** | PG | Regular-expression operators. |
| **REINDEX [CONCURRENTLY]** | PG | Rebuild an index, online if `CONCURRENTLY` (PG12+). |
| **RETURNING** | PG | `INSERT`/`UPDATE`/`DELETE`/`TRUNCATE` return the affected rows. |
| **REVOKE / GRANT / USAGE / SELECT ... TO ROLE** | STD | Privilege management. |
| **ROLLBACK TO SAVEPOINT / RELEASE SAVEPOINT** | STD | Nested rollback within a transaction. |
| **SERIAL** | PG | Legacy auto-numbering (sequence + DEFAULT); superseded by IDENTITY. |
| **SERIALIZABLE (isolation)** | STD | Strict serializable execution; PostgreSQL detects conflicts and aborts. |
| **SHARE / SHARE UPDATE EXCLUSIVE / EXCLUSIVE** | STD | Table lock modes. |
| **TABLE (shorthand)** | STD | `TABLE t` ≡ `SELECT * FROM t`. |
| **TIMESTAMPTZ** | PG | Timestamp with time zone (instant). |
| **TOAST** | PG | Compression + chunking of large row values. |
| **TRUNCATE [RESTART IDENTITY] [CASCADE]** | STD/PG | Fast table-empty; ACCESS EXCLUSIVE lock; DDL-like. |
| **UNIQUE (partial)** | PG | `UNIQUE (col) WHERE pred` — uniqueness on a subset of rows. |
| **USING (join clause)** | STD | Implicit-equality join on named columns. |
| **VALUES** | STD | Inline row-set: `VALUES (1,'a'), (2,'b')`. |
| **VACUUM [ANALYZE] [FULL] / autovacuum** | PG | Reclaim dead-tuple space; `FULL` rewrites the table. |
| **VARCHAR / CHAR** | STD | Character types (see TEXT equivalence in PG). |
| **VOLATILE / STABLE / IMMUTABLE** | PG | Function volatility; affects indexability and plan folding. |
| **WITH (CTE) / MATERIALIZED / NOT MATERIALIZED** | STD/PG | Named subquery; materialization hint is PG13+. |
| **WINDOW (named)** | PG | `WINDOW w AS (...)` reused by multiple `OVER w`. |
| **WITHIN GROUP** | STD | Ordered-set aggregate syntax (`PERCENTILE_CONT ... WITHIN GROUP (ORDER BY x)`). |

## 31.1 psql Meta-Commands (CLIENT) — Quick Table

| Command | Purpose |
|---|---|
| `\l`, `\c db`, `\dt`, `\d <obj>`, `\du`, `\dn`, `\df`, `\di`, `\dv`, `\dx` | Object listings / connect / describe |
| `\copy` | Client-side CSV/TSV import-export |
| `\timing`, `\conninfo`, `\password` | Diagnostics / session utilities |

## 31.2 Shell Utilities (SHELL) — Quick Table

| Command | Purpose |
|---|---|
| `pg_dump`, `pg_dumpall`, `pg_restore` | Logical backup / restore |
| `pg_basebackup` | Physical base backup |
| `pg_isready` | Liveness probe |
| `createdb`, `dropdb`, `createuser`, `dropuser` | Quick object management |
| `vacuumdb`, `reindexdb`, `clusterdb` | Maintenance across a database |
| `pg_ctl` | Server lifecycle |
| `pg_upgrade` | Major-version binary upgrade |
| `initdb` | Cluster initialization |

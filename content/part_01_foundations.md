# PART 1: COMPLETE SQL FOUNDATION

> **Version policy:** This handbook uses **PostgreSQL 17** as the primary reference (the latest stable major release at the time of writing). Where behavior differs across PostgreSQL versions, the relevant version is called out explicitly. PostgreSQL implements most of the **SQL:2016** standard (with some SQL:2011 and SQL:2023 features), plus many PostgreSQL-specific extensions. Every standard-vs-PostgreSQL-specific distinction that matters is flagged throughout the book.

## 1.1 What Is a Database?

A **database** is an organized, structured collection of data that is stored persistently, can be queried, and can be modified over time — usually for the purpose of supporting an application or an organization's operations.

The key idea that separates a database from a plain file (a spreadsheet, a JSON file, a text log) is that a database is **managed by a system that guarantees properties**:

- **Persistence:** Data survives the application (and often the machine) that created it.
- **Structured access:** Data is retrieved with a formal query language (SQL) rather than hardcoded parsing logic.
- **Integrity:** Constraints (unique keys, check rules, foreign keys) keep the data in valid states.
- **Concurrency:** Many users can read and write at the same time without corrupting the data.
- **Reliability:** Crash recovery and backup facilities mean committed data is not lost.

Think of it this way: a database is not the *data*. A database is the **data plus the rules, the access mechanisms, and the reliability guarantees** that live around it.

### When is a database the right tool?

- Data must outlive a single run of a program.
- Multiple users or services read/write the same records.
- You need consistency (e.g., money must not be duplicated or vanish).
- The data has relationships (an order belongs to a customer; a patient has many visits).

### When it might *not* be the right tool

- Ephemeral data (caches, session state) — a key-value store such as Redis is better.
- Massive unstructured media — object storage is better.
- If you only ever read the data once — a file is simpler.

**Interview relevance:** "When would you choose a database over a file?" — The expected answer names concurrency, integrity, query flexibility, persistence, and scale.

## 1.2 What Is a DBMS?

A **Database Management System (DBMS)** is the software that manages a database. It is the program that receives your queries, enforces the rules, and protects the data files. PostgreSQL, MySQL, Oracle, and SQL Server are all DBMSs.

A DBMS provides:

1. **Data definition** — create and modify the schema (structure).
2. **Data manipulation** — insert, update, delete rows.
3. **Query processing** — parse, plan, and execute queries.
4. **Transaction management** — group operations into all-or-nothing units (ACID).
5. **Concurrency control** — keep simultaneous transactions correct.
6. **Recovery** — restore consistency after a crash.
7. **Security and authorization** — control who can do what.
8. **Backup/restore utilities** — copies of the data for disaster recovery.

The **DBMS** is the program; the **database** is the organized data it manages. A DBMS typically manages one or more databases.

## 1.3 What Is an RDBMS?

A **Relational Database Management System (RDBMS)** is a DBMS that stores data in **tables** (relations) organized by **rows** (records) and **columns** (fields), and manages those tables using the relational model:

- Tables are related through shared key columns (foreign keys).
- Data is described by a formal model (E. F. Codd's relational model) with proven properties.
- Queries use **SQL**, a declarative language: you state *what* you want, not *how* to get it.

**PostgreSQL is an RDBMS.** It goes further than a minimal RDBMS: it supports JSON, arrays, full-text search, custom types, procedural language, and replication, which is why it is often called a "relational" database that also handles many non-relational workloads.

Common RDBMS products: PostgreSQL, MySQL/MariaDB, Oracle, Microsoft SQL Server, SQLite.

## 1.4 What Is SQL?

**SQL** (Structured Query Language — it is pronounced "sequel") is the standard language for communicating with relational databases. It was introduced in the 1970s (originally "SEQUEL" at IBM) and standardized by ISO/IEC and ANSI.

SQL is **declarative**: for queries, you describe the result you want, and the **query planner** decides how to produce it efficiently. This is one of the most important differences between SQL and imperative programming.

SQL is split into command categories (covered fully below):

| Category | Full Name | Purpose | Examples |
|---|---|---|---|
| **DDL** | Data Definition Language | Define/modify schema objects | `CREATE TABLE`, `ALTER TABLE`, `DROP INDEX` |
| **DML** | Data Manipulation Language | Modify table data | `INSERT`, `UPDATE`, `DELETE`, `MERGE` |
| **DQL** | Data Query Language | Retrieve data | `SELECT` (and its clauses) |
| **DCL** | Data Control Language | Control access | `GRANT`, `REVOKE` |
| **TCL** | Transaction Control Language | Manage transactions | `COMMIT`, `ROLLBACK`, `SAVEPOINT` |

Note: the DQL/DML/DCL split is a pedagogical convention. The SQL standard itself groups things differently; some languages (like classic Oracle) historically bundled parts of these. In PostgreSQL, `SELECT` is the only DQL command; everything else falls under DDL, DML, DCL, or TCL.

## 1.5 What Is PostgreSQL?

**PostgreSQL** (often "Postgres") is a free, open-source (PostgreSQL License), object-relational database system developed by a global community (the PostgreSQL Global Development Group). It is:

- **Extensible:** custom types, operators, functions, and extensions (PostGIS, pgvector, TimescaleDB, …).
- **Standards-compliant:** the most complete implementation of the SQL standard among open-source databases.
- **ACID-strict:** fully transactional with true SERIALIZABLE isolation.
- **MVCC-based:** readers never block writers and vice versa (see Part 14).
- **Production-hardened:** streaming and logical replication, partitioning, parallel query, JIT compilation.

You interact with PostgreSQL through:
- **SQL statements** (DDL/DML/DCL/TCL)
- **psql meta-commands** (`\dt`, `\l`) — a *client tool* feature, **not SQL**
- **Shell utilities** (`pg_dump`, `pg_basebackup`) — external programs
- **Libraries/drivers** from application code (psycopg2, libpq, pgx, node-postgres, …)

> **IMPORTANT NOTE:** `psql` meta-commands (lines starting with backslash) and shell utilities are *not* portable SQL. Only SQL statements are. This distinction is a favorite interview trap — Part 19 covers it in depth.

## 1.6 PostgreSQL vs MySQL vs SQLite vs Oracle vs SQL Server

All five are relational databases. The table below summarizes their practical differences (the full landscape — including NoSQL, analytical, and graph engines — is covered in Part 23).

| Feature | PostgreSQL | MySQL / MariaDB | SQLite | Oracle | SQL Server |
|---|---|---|---|---|---|
| License | PostgreSQL (permissive, free) | GPL (MariaDB), mixed (Oracle MySQL) | Public domain | Commercial | Commercial |
| License model | MIT-style open source | Open source | Free | Enterprise (very expensive) | Enterprise |
| Standards compliance | Excellent | Good (dialect differences) | Good | Excellent | Good (T-SQL extensions) |
| Isolation levels | 4, incl. true SERIALIZABLE | 4, incl. SERIALIZABLE | 4, but default is deferred | 4, incl. SERIALIZABLE | 5 (incl. SNAPSHOT, READ UNCOMMITTED default) |
| JSON | JSON + JSONB (binary, indexable) | JSON (binary, indexable since 8.0) | JSON (1.x) | BINARY/XML JSON, BLOB-based | NJSON |
| Arrays | Native ARRAY type | No native arrays | Native arrays | Yes | No |
| Full-text search | Built-in | Built-in (basic) | FTS5 module | PowerText etc. | Full-text engine |
| Geography (GIS) | PostGIS (de facto standard) | GIS extension | SpatiaLite | Spatial | SQL Spatial |
| Vector search (AI) | pgvector | MySQL 9 HeatWave | Not really | Oracle AI | Vector type in recent versions |
| Partitioning | Declarative (range/list/hash, multi-level) | Declarative (MySQL 8) | Limited (table-split strategies) | Mature (IOT/HTP) | Declarative |
| Row-Level Security | Native | Community (MariaDB) | N/A | Native | Native |
| Logical replication | Native (10+) | Native (8.0+) | N/A | Golden Gate / Native | Native |
| Embedded / file-based | No (server) | No | **Yes** — single file | No | No |
| Typical use | Web backends, multi-model OLTP+analytics | Web backends (LAMP), huge OLTP | Mobile / IoT / local apps, testing | Large enterprises (banking, ERP) | .NET shops, Microsoft ecosystem |

**Rule of thumb for choosing:**

- Need a **file-based embedded** database in an app (mobile, desktop, appliance)? → **SQLite**.
- Need the **most capable general-purpose relational DB for free**, with exotic features (GIS, vectors, JSONB, arrays)? → **PostgreSQL**.
- Already deep in the **MySQL/MariaDB ecosystem** or need the largest shared hosting footprint? → **MySQL/MariaDB**.
- Enterprise with **budget and DBA teams**, legacy ETL/OLAP (Exadata, Data Guard)? → **Oracle**.
- **Microsoft / .NET** stack, SSIS/SSAS/Reporting Services ecosystem? → **SQL Server**.

> **Common mistake:** answering "PostgreSQL or MySQL?" with "PostgreSQL is better" as a blanket statement. The correct answer is workload- and ecosystem-dependent; the interviewer wants to hear *trade-offs*, not a slogan.

## 1.7 Terminology: Database, Schema, Table, Row, Column, Record, Field

These terms get mixed up constantly in job interviews. Here is the precise PostgreSQL usage:

| Term | Meaning in PostgreSQL |
|---|---|
| **Database** | A named collection of schemas with its own catalogs and permissions. A cluster can hold many databases. |
| **Schema** | A namespace within a database that groups tables, views, functions, types. Default schema: `public`. (Note: in MySQL the word "schema" is an alias for "database" — a porting trap.) |
| **Table** | A relation: named, persistent collection of rows. |
| **Row** | One tuple (record) in a table. |
| **Column** | One attribute (field) of a table, with a type and constraints. |
| **Record / Tuple** | Synonyms for row in standard SQL and the PostgreSQL docs. "Record" is also a specific keyword (for composite types; see Part 8). |
| **Field** | A colloquial synonym for a column. Not a keyword in SQL. |

Example layout:

```
Cluster (one running PostgreSQL instance, e.g. on one machine)
 └── Database: "shopdb"
      └── Schema: "public"
           ├── Table: "users"  (rows: one user each; columns: id, email, …)
           ├── Table: "orders"
           └── View:  "active_users"
      └── Schema: "billing"
           └── Table: "invoices"
```

**Interview trap:** "What is the difference between a database and a schema?" — A database is a hard boundary: objects, permissions, and connections are separated per database; a query cannot see across databases (with `postgres_fdw` exceptions, Part 29). A schema is a soft namespace: objects from different schemas are freely visible and joinable, controlled by `search_path`.

## 1.8 SQL Statement Structure

Most SQL statements follow a recognizable skeleton. The `SELECT` statement, the workhorse of SQL:

```sql
WITH cte_name AS ( SELECT ... )            -- [optional] Common Table Expressions
SELECT [DISTINCT] column_list              -- what to return
FROM table_list_with_joins                 -- where from
[WHERE filter_conditions]                  -- row-level filter
[GROUP BY grouping_columns]                -- aggregate groups
[HAVING group_filters]                      -- filter groups
[WINDOW named_window AS (...) ...]         -- [optional] named windows
[ORDER BY ordering_spec]                   -- sort order
[FETCH FIRST n ROWS ONLY / LIMIT n]        -- row limit
```

Important observations:

- The **keyword order in source text** (SELECT → FROM → WHERE → GROUP BY → …) is fixed, but the **execution order** is not the same (see 1.9).
- Semicolons (`;`) terminate statements in psql and in JDBC/ADO.NET batch execution. Some clients allow multiple statements separated by semicolons.
- SQL is **case-insensitive for keywords and identifiers**: `SELECT` = `select`. Unquoted identifiers are folded to **lowercase**; double-quoted identifiers preserve case (and become case-sensitive).
  - `select Name from Users` looks fine but implicitly means `select "name" from "users"` — a classic source of "column does not exist" errors.
  - `select "Name" from "Users"` refers to literally case-preserved names created with double quotes.
- Single quotes `'` delimit **string literals**. Double quotes `"` delimit **identifiers**. Backticks are *not* SQL.

## 1.9 SQL Syntax vs Execution Order

The planner executes a query in a very different order than you write it. Understanding this explains "why does this error happen?" more than any other topic in the book:

```
Written order:            Actual evaluation order:
1. SELECT                  1. FROM (tables joined, CTEs, subqueries resolved)
2. FROM                    2. WHERE, ON, HAVING (row filtering)
3. WHERE                   3. GROUP BY (grouping)
4. GROUP BY                4. Aggregate functions and expressions
5. HAVING                  5. DISTINCT
6. SELECT (list)           6. SELECT list (computed columns)
7. DISTINCT                7. ORDER BY (uses computed aliases)
8. ORDER BY                8. LIMIT / OFFSET / FETCH
```

Consequences that catch people in interviews:

1. **You cannot reference a SELECT alias in WHERE** (aliases don't exist yet):

   ```sql
   -- WRONG: "no column named total"
   SELECT price * qty AS total FROM orders WHERE total > 100;

   -- RIGHT: repeat the expression, or wrap in a subquery/CTE
   SELECT * FROM (SELECT price * qty AS total FROM orders) o WHERE total > 100;
   ```

2. **You cannot reference a SELECT alias in GROUP BY** in standard SQL (PostgreSQL *does* allow aliasing in GROUP BY/ORDER BY as a convenience — a **PostgreSQL extension**, not standard, so don't write it in portable code).

3. **WHERE runs before SELECT**, so filtering on computed columns needs a subquery, a `LATERAL` expression, or HAVING/GROUP BY if the computed value depends on aggregates.

## 1.10 SQL Command Classification (the five families)

### DDL — Data Definition Language

Defines the **structure** of the database. Most DDL is transactional in PostgreSQL (CREATE TABLE, DROP TABLE, ALTER TABLE all run inside a transaction and roll back if the transaction fails).

| Command | Purpose |
|---|---|
| `CREATE TABLE` / `CREATE SCHEMA` / `CREATE DATABASE` / `CREATE VIEW` / `CREATE MATERIALIZED VIEW` / `CREATE INDEX` / `CREATE SEQUENCE` / `CREATE TYPE` / `CREATE DOMAIN` / `CREATE FUNCTION` / `CREATE PROCEDURE` / `CREATE TRIGGER` / `CREATE ROLE` / `CREATE USER` / `CREATE EXTENSION` | Create objects |
| `ALTER ...` (TABLE, COLUMN, INDEX, ROLE, DATABASE, SCHEMA, FUNCTION) | Modify object structure/properties |
| `DROP ...` / `TRUNCATE` | Remove objects or their data |
| `COMMENT ON` | Attach human-readable comments to objects |

> **Note:** `TRUNCATE` is historically classed as DML because it acts on *data*, not structure — but in PostgreSQL it actually **rewrites** the table (removes all rows, resets identity columns) and takes a stronger lock (ACCESS EXCLUSIVE) than `DELETE`. Its `CONTINUE IDENTITY`/`RESTART IDENTITY` options and locking behavior are covered in Part 2.

> **DESTRUCTIVE-WARNING:** `DROP` and `TRUNCATE` are high-impact operations. In production, use `DROP TABLE IF EXISTS` with care, run against a staging database first, and wrap in a transaction where possible to confirm intent.

### DML — Data Manipulation Language

Modifies **row data** inside existing tables.

| Command | Purpose |
|---|---|
| `INSERT` | Add one or many rows |
| `UPDATE` | Modify matching rows |
| `DELETE` | Remove matching rows |
| `MERGE` | SQL:2015 upsert-style conditional merge (added in PostgreSQL 15) |
| `INSERT ... ON CONFLICT` | PostgreSQL upsert (Part 2) — functionally a MERGE for single-table |

DML statements are **transactional** — always run them inside an explicit `BEGIN; ... COMMIT;` block when you care about atomicity (in psql, autocommit is ON by default, so each statement is its own transaction unless you BEGIN).

### DQL — Data Query Language

Retrieves data. In PostgreSQL, effectively one command plus its clauses:

| Command | Purpose |
|---|---|
| `SELECT` | Retrieve and shape rows (JOINs, GROUP BY, windows, CTEs — Parts 4, 5, 7) |
| `TABLE` / `VALUES` | Shorthand selects (`TABLE orders` ≡ `SELECT * FROM orders`; `VALUES` builds inline row sets) |
| `SHOW` / `SET` | PostgreSQL-specific session settings (not standard SQL) |

### DCL — Data Control Language

Controls **who can do what**.

| Command | Purpose |
|---|---|
| `GRANT` | Give privileges (to users, roles, PUBLIC) |
| `REVOKE` | Remove privileges |
| `ALTER DEFAULT PRIVILEGES` | Privileges applied to *future* objects in a schema |
| `SET ROLE` / `SET SESSION AUTHORIZATION` | Switch/act as a role for the session |

(For the full privilege model — roles, inheritance, row-level security, `pg_hba.conf` — see Part 18.)

### TCL — Transaction Control Language

Controls the **life of a transaction**.

| Command | Purpose |
|---|---|
| `BEGIN` / `START TRANSACTION` | Open a transaction |
| `COMMIT` | Make changes permanent |
| `ROLLBACK` | Undo changes |
| `SAVEPOINT` / `RELEASE SAVEPOINT` / `ROLLBACK TO SAVEPOINT` | Nested rollback points |
| `SET TRANSACTION` | Set isolation level / read-only on the current transaction |
| `PREPARE TRANSACTION` | Two-phase commit (Part 13) |
| `ABORT` | psql/postgres synonym for ROLLBACK |

### Common mistakes with classification

- **"Is TRUNCATE DDL or DML?"** — Pedagogically DML (it affects data); technically it acquires an ACCESS EXCLUSIVE lock and is like a DELETE without WHERE.
- **"Is VIEW DDL or DQL?"** — `CREATE VIEW` is DDL. *Using* a view in `SELECT` is DQL.
- **"Is GRANT transactional?"** — DCL changes are transactional in PostgreSQL (can be rolled back).

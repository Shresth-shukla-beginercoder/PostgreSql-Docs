# PART 8: DATA TYPES — COMPLETE REFERENCE

> PostgreSQL type system: **120+ built-in types**. Below: the ones you will use in production, with storage, range, and performance notes.

## 8.1 Numeric Types

| Type | Range / Size | Storage | Notes |
|---|---|---|---|
| `SMALLINT` | −32 768 – 32 767 | 2 bytes | |
| `INTEGER` / `INT` | −2 147 483 648 – 2 147 483 647 | 4 bytes | Default integer |
| `BIGINT` | ±9.2 × 10¹⁸ | 8 bytes | Use for IDs that may exceed 2¹³¹ |
| `NUMERIC(p,s)` / `DECIMAL` | Exact, arbitrary precision | 8+ bytes | `p`=digits, `s`=scale; **money type** |
| `REAL` | ±3.4 × 10³⁸ (7 digits) | 4 bytes | IEEE 754 |
| `DOUBLE PRECISION` | ±1.8 × 10³⁰⁸ (15–17 digits) | 8 bytes | Faster than NUMERIC |

**`NUMERIC` vs `DOUBLE PRECISION`:**
- **Exact** arithmetic (money, accounting) → `NUMERIC`.
- **Approximate** scientific/measurement → `DOUBLE PRECISION` (but be warned: `0.1 + 0.2 ≠ 0.3` in binary FP).
- `ROUND/CEIL/FLOOR` on `DOUBLE PRECISION` can produce `0.30000000000000004` artifacts; `NUMERIC` avoids them.

### IDENTITY vs SERIAL

```sql
-- Modern (PostgreSQL 10+), standard SQL
CREATE TABLE users (user_id int GENERATED ALWAYS AS IDENTITY PRIMARY KEY);

-- Legacy (still works, but not portable)
CREATE TABLE users (user_id serial PRIMARY KEY);
```

- **`IDENTITY`:** the default value is *part of the column definition*; `ALTER COLUMN ... SET GENERATED` can be changed; more portable (SQL standard).
- **`SERIAL`:** creates a separate `BIGINT` sequence + `DEFAULT nextval('seq')`; the sequence is a *separate object* (must be owned/dropped together).

## 8.2 String Types

| Type | Max Length | Notes |
|---|---|---|
| `CHAR(n)` / `CHARACTER(n)` | Fixed width, padded | **Rarely used**; `VARCHAR(n)` is better |
| `VARCHAR(n)` / `CHARACTER VARYING(n)` | Up to `n` chars | `n` is a *check constraint* (not a storage width) |
| `TEXT` | ~1 GB | **Default for free text** |

**`TEXT` vs `VARCHAR`:** In PostgreSQL, **there is no performance difference** — both store inline (or in TOAST when large). `VARCHAR(255)` only adds a check. *Use `TEXT`* unless you need a non-PostgreSQL portability or a *hard* length cap.

**`BYTEA`:** binary data (files, protobuf, images). Use `BYTEA` over `BLOB` (which is not in PostgreSQL).

## 8.3 Boolean and Logical

- **`BOOLEAN` / `BOOL`:** `TRUE`/`FALSE`/`NULL` (three-valued logic, Part 3). **Not a substitute for a `CHECK` on integers.**

## 8.4 Temporal Types

| Type | Timezone | Example |
|---|---|---|
| `DATE` | No | `2026-11-06` |
| `TIME` / `TIME WITH TIME ZONE` | ± | `14:03:02+05` |
| `TIMESTAMP` / `TIMESTAMP WITH TIME ZONE` (timestamptz) | No / Yes | `2026-11-06 14:03:02+05` |
| `INTERVAL` | No | `3 days 4 hours` |

**`TIMESTAMP` vs `TIMESTAMPTZ`:**
- `TIMESTAMP` is a *wall-clock* value (no timezone stored).
- `TIMESTAMPTZ` is *instant* (stored as UTC, rendered in the session's `timezone`).
- **Production rule:** store `timestamptz` for *event times*; `date`/`timestamp` only for *local* reporting.

```sql
SELECT now(), now() AT TIME ZONE 'Asia/Kolkata';
SELECT '2026-11-06 14:00'::timestamp;           -- 14:00 *local*
SELECT '2026-11-06 14:00+05'::timestamptz;      -- 09:00 UTC
```

## 8.5 UUID

- **`UUID`:** 16-byte universally unique ID (v1–v8). `gen_random_uuid()` (PostgreSQL 13+) generates v4.
- **Storage:** 16 bytes; **index size:** large — a B-tree on a UUID is ~2× the size of an `int` B-tree.
- **Use when:** distributed IDs are needed (multi-region, no central sequence); *do not* use as the primary key of a hot OLTP table for high insert rates (B-tree insert performance degrades vs. `bigserial`).

## 8.6 JSON / JSONB

| Feature | `JSON` | `JSONB` |
|---|---|---|
| Storage | Text (as given) | Binary (normalized) |
| Preserves key order | Yes | No |
| Duplicate keys | Kept | Collapsed |
| White space / comments | Kept | Stripped |
| Indexable | No | Yes (GIN) |
| Query speed | Slower | Faster |
| Size | Smaller | Larger (~30% bloat) |

**Rule:** store *arbitrary/flexible* data as **`JSONB`**; use `JSON` only when you need *the exact original text* (legal/audit documents).

## 8.7 Arrays

- **`ARRAY` / typed arrays (`int[]`, `text[]`):** a fixed-length, ordered list of one type.
- **Storage:** varlena; can be TOASTed.
- **Operations:** `array_agg`, `unnest`, `any(array)`, `array_contains(arr, val)` (from `PG14`).
- **Indexing:** `GIN` on arrays supports `CONTAINS`/`OVERLAPS`.
- **Use when:** a small, fixed set of values (tags, addresses) — *not* for large relational data.

## 8.8 Enums, Ranges, and Multi-Range

- **`ENUM`:** an ordered list of named values. Stored as a 4-byte OID. **Limitations:** `ALTER TYPE ADD VALUE` is not transactional, and cannot be used in partition keys.
- **`RANGE`:** `[a,b)`, `(a,b]`, etc. Types: `int4range`, `int8range`, `numrange`, `tsrange`, `tstzrange`, `daterange`.
- **`MULTIRANGE`:** a set of non-overlapping ranges (PostgreSQL 14+).

```sql
SELECT int4range(1,10) && int4range(5,15);   -- overlap → true
```

## 8.9 Money, XML, Network, Bit Strings

- **`MONEY`:** currency-aware (locale). *Not recommended* — use `NUMERIC` + a `currency` column instead.
- **`XML`:** well-formed XML with XPath support.
- **`INET` / `CIDR`:** IP addresses / network blocks. `INET` = single address or network with explicit mask; `CIDR` = network address (mask rounded).
- **`MACADDR` / `MACADDR8`:** hardware addresses.
- **`BIT(n)` / `VARBIT`:** fixed / variable bit strings.

## 8.10 Full-Text and Vectors

- **`TSVECTOR` / `TSQUERY`:** full-text search (Part 11/24).
- **`VECTOR`** (via `pgvector` extension): high-dimensional embeddings.

## 8.11 Composite Types and Domain Types

- **Composite** (`CREATE TYPE ... AS (...)`): named struct; used in `INSERT ... VALUES ROW(1,2)`, in `RETURNS TABLE` for SRFs, and as a *row-type* cast.
- **Domain** (`CREATE DOMAIN ... AS base CHECK(...)`): a base type + default constraints + NOT NULL. **Domain is the best tool for *reusable validated types*:**

```sql
CREATE DOMAIN us_phone AS char(10)
  CHECK (VALUE ~ '^[0-9]{10}$');
CREATE DOMAIN email_addr AS text
  CHECK (VALUE LIKE '%_@_%') NOT NULL;
```

## 8.12 Key Comparisons (interview-ready)

| Comparison | Verdict |
|---|---|
| `TEXT` vs `VARCHAR` | Same storage; use `TEXT` |
| `TIMESTAMP` vs `TIMESTAMPTZ` | `TIMESTAMPTZ` for event times; `TIMESTAMP` for local |
| `JSON` vs `JSONB` | `JSONB` (indexable, faster); `JSON` only for text preservation |
| `SERIAL` vs `IDENTITY` | `IDENTITY` (standard, more control) |
| `INTEGER` vs `BIGINT` | `BIGINT` for anything that could grow beyond 2³¹ |
| `NUMERIC` vs `DOUBLE PRECISION` | `NUMERIC` for money; `DOUBLE` for floats |
| `CHAR(n)` vs `VARCHAR(n)` | `VARCHAR` (no padding) |
| `ENUM` vs `CHECK` | `CHECK` on `TEXT` is more flexible (value additions) |

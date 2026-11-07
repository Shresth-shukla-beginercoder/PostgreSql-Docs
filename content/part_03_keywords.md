# PART 3: EVERY SQL KEYWORD, CLAUSE AND OPERATOR

> This part dissects individual building blocks rather than complete statements. Every keyword gets: plain-language definition, role in SQL, syntax, how it changes behavior, two examples, common mistakes, and relationships to neighboring keywords.

## 3.1 Logical Operators

### AND / OR / NOT

- **`AND`:** both sides true.
- **`OR`:** at least one side true.
- **`NOT`:** inverts a boolean.

PostgreSQL's three-valued logic: `TRUE`, `FALSE`, `UNKNOWN` (NULL involved).

| A | B | A AND B |
|---|---|---|
| TRUE | TRUE | TRUE |
| TRUE | FALSE | FALSE |
| TRUE | NULL | NULL |
| FALSE | NULL | FALSE |
| NULL | NULL | NULL |

| A | B | A OR B |
|---|---|---|
| FALSE | FALSE | FALSE |
| FALSE | NULL | NULL |
| TRUE | NULL | TRUE |

**De Morgan's law** (used to simplify and to flip negated predicates):
`NOT (A AND B) ≡ (NOT A) OR (NOT B)` and `NOT (A OR B) ≡ (NOT A) AND (NOT B)`.

Examples:

```sql
-- AND with NULL semantics: an open order with a possibly-missing discount
SELECT * FROM orders
WHERE status = 'open' AND discount_pct IS NOT NULL;

-- NOT: invert a predicate
SELECT * FROM products WHERE NOT (discontinued);

-- Parentheses matter: AND binds tighter than OR
SELECT * FROM users
WHERE region = 'EU' AND (country = 'DE' OR country = 'FR');
```

**Common mistake:** `WHERE a = 1 OR a = 2 AND b = 3` is read as `a = 1 OR (a = 2 AND b = 3)` — almost certainly not what you meant. Always parenthesize mixed AND/OR.

## 3.2 Comparison Operators

### =, <>, !=, <, >, <=, >=

PostgreSQL supports `<>` and `!=` (both "not equals"). Ordering operators only work when the type has an ordering (no `int[] < int[]`). `NULL = anything` → `UNKNOWN` (never TRUE/FALSE), so `WHERE col = NULL` matches *nothing*; use `IS NULL` instead.

```sql
SELECT * FROM orders WHERE total_cents >= 10000;
SELECT count(*) FROM users WHERE last_login_at > now() - interval '30 days';
```

### BETWEEN

**Inclusive** on both ends.

```sql
SELECT * FROM events WHERE ts BETWEEN '2025-01-01' AND '2025-03-31'::timestamp;
-- Note: BETWEEN on timestamptz truncates at '2025-03-31 00:00:00', so the day of 03-31 is missed. Prefer:
WHERE ts >= '2025-01-01' AND ts < '2025-04-01';
```

**Common mistake:** the `BETWEEN` on dates ends at the *start* of the boundary day.

### IN / NOT IN

`col IN (a, b, c)` ≡ `col = a OR col = b OR col = c`. `NOT IN` becomes *UNKNOWN* (no rows) if any list element is NULL — a very common bug:

```sql
-- Bug: list contains NULL → NOT IN returns no rows at all
SELECT * FROM users WHERE dept_id NOT IN (SELECT dept_id FROM depts WHERE active);

-- Fix
SELECT * FROM users u WHERE NOT EXISTS (
  SELECT 1 FROM depts d WHERE d.dept_id = u.dept_id AND d.active
);
```

### LIKE / ILIKE

Pattern matching with wildcards: `%` (any string) and `_` (any single char). `ILIKE` is case-insensitive (PostgreSQL). Use `ESCAPE` to escape the wildcards themselves:

```sql
SELECT name FROM products WHERE name LIKE 'Widget%' AND name NOT LIKE 'Widget%Pro';
SELECT * FROM users WHERE email ILIKE '%@company.io';
SELECT * FROM files WHERE filename LIKE '%%' ESCAPE '!' ESCAPE '%!'; -- escaped percent
```

**Performance:** `LIKE '%prefix'` (leading wildcard) cannot use a B-tree; use `pg_trgm` (Part 24) for fast substring searches.

### SIMILAR TO

PostgreSQL/Oracle pattern language using regex-like classes:

```sql
SELECT * FROM codes WHERE code SIMILAR TO '[A-Z]{3}-[0-9]{2}';
```

### IS NULL / IS NOT NULL

Only correct way to test for NULL (never `= NULL`):

```sql
SELECT count(*) FROM orders WHERE shipping_address IS NULL;
SELECT * FROM users WHERE deleted_at IS NOT NULL;
```

### IS DISTINCT FROM

A NULL-safe equality: `a IS DISTINCT FROM b` is true when they differ *or* when one is NULL.

```sql
-- Find users whose email changed to NULL or a different value
SELECT * FROM users u
WHERE u.email IS DISTINCT FROM default_email.email;
```

## 3.3 Arithmetic Operators

`+`, `-`, `*`, `/`, `%` (modulo). Division of integers truncates: `7/2 = 3`. Use `::numeric` to get fractions.

```sql
SELECT 7/2;                 -- 3
SELECT 7::numeric/2;        -- 3.5
SELECT 10 % 3;              -- 1
SELECT GREATEST(1,2,3);    -- 3
```

## 3.4 String, Type, and JSON Operators

| Operator | Meaning | Example |
|---|---|---|
| `||` | Concatenation | `'a' \|\| 'b'` → `ab`; also array concatenation |
| `::` | Type cast | `now()::date` → `2026-11-06` |
| `->` | JSON/JSONB: field as JSON | `'{"a":1}'::jsonb -> 'a'` → `1` |
| `->>` | JSON/JSONB: field as TEXT | `'{"a":1}'::jsonb ->> 'a'` → `'1'` |
| `#>` | JSON path (array of keys) | `'{"a":{"b":1}}'::jsonb #> '{a,b}'` → `1` |
| `#>>` | JSON path as TEXT | `'{"a":{"b":1}}'::jsonb #>> '{a,b}'` → `'1'` |
| `@>` | Containment (does left contain right?) | `'{"a":1,"b":2}'::jsonb @> '{"a":1}'` → `true` |
| `<@` | Contained by | `'{"a":1}'::jsonb <@ '{"a":1,"b":2}'::jsonb` → `true` |
| `?` | Key exists (JSONB) | `'{"a":1}'::jsonb ? 'a'` → `true` |
| `?|` | Any key in list | `'{"a":1}'::jsonb ?\| array['a','b']` |
| `?&` | All keys in list | `'{"a":1,"b":2}'::jsonb ?& array['a','b']` |

**Performance:** `@>` is the JSONB workhorse for "has field X with value Y" — it is indexable with GIN (Part 11). `->>` in a `WHERE` is *not* indexable without an expression index or a GIN operator-class match.

## 3.5 AS

Gives an alias to a table or expression.

```sql
SELECT o.order_id, c.full_name AS customer_name
FROM orders o JOIN customers c ON c.user_id = o.customer_id;

-- AS on a computed column
SELECT price * qty AS total FROM products;
```

- **Aliases in `ORDER BY`:** PostgreSQL allows aliasing in `ORDER BY` (e.g., `ORDER BY total`); standard SQL does not.
- **Aliases in `WHERE`:** not allowed (WHERE runs before the SELECT-list aliases exist).

## 3.6 CASE / WHEN / THEN / ELSE / END

The SQL "if-else":

```sql
SELECT status,
  CASE
    WHEN status = 'PENDING' THEN 'Pending'
    WHEN status = 'SHIPPED' THEN 'In transit'
    ELSE 'Done'
  END AS status_label
FROM orders;

-- Expression form
SELECT CASE WHEN score >= 90 THEN 'A' WHEN score >= 80 THEN 'B' ELSE 'C' END
FROM students;
```

- **`CASE` is nullable** (returns `NULL` if no branch matches and no `ELSE`).
- **Rows vs statements:** `CASE` appears in `SELECT` lists, `WHERE`, `GROUP BY`, and even `INSERT ... VALUES`.

## 3.7 COALESCE / NULLIF

- **`COALESCE(a, b, c)`:** first non-NULL. Indexable as an expression in some plans; short-circuits.
- **`NULLIF(a, b)`:** returns NULL if a = b, else a.

```sql
SELECT COALESCE(phone, email, 'no-contact') AS contact FROM users;
SELECT user_id, NULLIF(name, '') AS name FROM users;   -- treat '' as NULL
```

## 3.8 CAST / ::

`CAST(x AS type)` and the PostgreSQL shortcut `x::type`.

```sql
SELECT '123'::int;          -- 123
SELECT now()::date;         -- 2026-11-06
SELECT '{"a":1}'::jsonb;    -- {"a": 1}
```

**Common mistake:** casting `text` to `int` fails on `'12.5'` (`invalid input syntax for type integer`); cast to `numeric` instead.

## 3.9 EXISTS / ANY / ALL / SOME

- **`EXISTS (subquery)`:** true if the subquery returns *at least one row*.
- **`NOT EXISTS`:** true if zero rows.
- **`col IN (subquery)` vs `EXISTS`:** often equivalent in cost after a good plan; `NOT EXISTS` is usually faster/safer than `NOT IN` (NULL-safe).

```sql
-- Which customers have at least one order?
SELECT c.* FROM customers c
WHERE EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.customer_id);

-- ANY / ALL
SELECT * FROM scores WHERE score > ALL (SELECT avg FROM class_averages);
SELECT * FROM scores WHERE score = ANY (SELECT passing_score FROM settings);
-- SOME is a synonym for ANY.
```

## 3.10 FILTER and WITHIN GROUP

- **`FILTER (WHERE ...)`:** conditional aggregate (PostgreSQL/standard):

```sql
SELECT count(*) FILTER (WHERE status='PAID') AS paid,
       sum(amount) FILTER (WHERE status='PAID') AS paid_total
FROM orders;
```

- **`WITHIN GROUP`:** ordered-set aggregates — `PERCENTILE_CONT`, `MODE`, ordered aggregates:

```sql
SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_cents) AS median
FROM orders;
SELECT MODE() WITHIN GROUP (ORDER BY status) FROM orders;
```

## 3.11 Window Clauses: OVER / PARTITION BY / ROWS / RANGE / GROUPS / EXCLUDE

(Full treatment: Part 7.)

- **`OVER (...)`:** window function scope.
- **`PARTITION BY`:** partitioning column(s).
- **`ORDER BY` inside `OVER`:** ordering within the partition.
- **Frame:** `ROWS BETWEEN ... AND ...`, `RANGE BETWEEN`, `GROUPS BETWEEN`.
- **`EXCLUDE`:** `EXCLUDE CURRENT ROW` (for self-aggregate patterns).

```sql
SELECT order_id,
       sum(total_cents) OVER (PARTITION BY customer_id ORDER BY placed_at
                              ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_total
FROM orders;
```

## 3.12 RECURSIVE

Marks a CTE as self-referencing:

```sql
WITH RECURSIVE tree AS (
  SELECT id, name, parent_id FROM departments WHERE parent_id IS NULL
  UNION ALL
  SELECT d.id, d.name || '/' || t.name, d.parent_id
  FROM departments d JOIN tree t ON t.id = d.parent_id
)
SELECT * FROM tree;
```

## 3.13 MATERIALIZED / NOT MATERIALIZED (CTE options)

```sql
WITH x AS MATERIALIZED ( SELECT ... )    -- compute once, store
WITH x AS NOT MATERIALIZED ( SELECT ... ) -- inline into outer query
```

In PostgreSQL, **non-recursive CTEs are inlined by default** unless the planner proves it cheaper; `MATERIALIZED` forces materialization, `NOT MATERIALIZED` forces inlining.

## 3.14 LATERAL

Allows a subquery in `FROM` to reference preceding `FROM` items:

```sql
-- Top 3 most recent orders per customer
SELECT c.name, o.*
FROM customers c
CROSS JOIN LATERAL (
  SELECT order_id, total_cents FROM orders WHERE customer_id = c.user_id
  ORDER BY placed_at DESC LIMIT 3
) o;
```

Without `LATERAL`, `WHERE customer_id = c.user_id` would be illegal.

## 3.15 UNION / UNION ALL / INTERSECT / EXCEPT

- **`UNION`** removes duplicates (expensive — a Sort).
- **`UNION ALL`** preserves duplicates (fast).
- **`INTERSECT`** keeps rows present in both.
- **`EXCEPT`** keeps rows in the first but not the second.

All require matching column counts and compatible types; `ORDER BY` applies to the whole set.

## 3.16 FETCH FIRST / NULLS FIRST / NULLS LAST

- **`FETCH FIRST n ROWS ONLY`:** standard limit (equivalent to `LIMIT n`).
- **`NULLS FIRST` / `NULLS LAST`:** order of NULLs in `ORDER BY` (default: `NULLS LAST` for ASC, `NULLS FIRST` for DESC).

## 3.17 COLLATE

Specifies a collation for string comparisons:

```sql
SELECT name FROM products WHERE name > 'apple' COLLATE "C";
ALTER TABLE t ALTER COLUMN name SET COLLATE "en_US.UTF-8";
```

- **"C"** = byte-order (fast, case-sensitive, locale-agnostic).
- Use the **same collation** for a column and its index, or the planner cannot use the index for comparisons.

## 3.18 USING / NATURAL

- **`JOIN ... USING (col)`:** joins on `col` (implicit equality), producing a single column named `col` (not `t1.col`, `t2.col`).
- **`JOIN ... ON (a = b AND c = d)`:** explicit predicate.
- **`NATURAL JOIN`:** auto-joins on *all columns of the same name* — **dangerous** (surprise joins; non-ANSI; not supported by PostgreSQL as a separate keyword — `USING` with all shared cols is the equivalent).

> **PostgreSQL does not have a `NATURAL` keyword**; it is the `USING` clause that handles the implicit-equality case.

## 3.19 TABLE / VALUES / DEFAULT / CHECK

Already covered in 2.23 and Part 9. `TABLE name` is shorthand for `SELECT * FROM name`; `VALUES` builds inline row sets; `DEFAULT` sets a column default; `CHECK` is a predicate constraint (Part 9).

## 3.20 Constraint Keywords

(Full treatment: Part 9.)

- **`PRIMARY KEY`, `FOREIGN KEY`, `UNIQUE`, `NOT NULL`, `CHECK`, `DEFAULT`** — declarative integrity.
- **`ON DELETE CASCADE | RESTRICT | SET NULL | SET DEFAULT`** and **`ON UPDATE ...`** — referential actions.
- **`DEFERRABLE | INITIALLY DEFERRED | INITIALLY IMMEDIATE`** — when a constraint is checked.
- **`REFERENCES`** — the FK target.
- **`EXCLUSION`** (PostgreSQL) — prevents overlapping interval/range constraints.

## 3.21 DIFFERENCES BETWEEN SIMILAR-LOOKING KEYWORDS (interview favorites)

| Pairs | Difference |
|---|---|
| `IN` vs `EXISTS` | `IN` can be NULL-poisoned; `EXISTS` is NULL-safe |
| `JOIN` vs `CROSS JOIN` | `JOIN` has a predicate; `CROSS JOIN` is a Cartesian product |
| `LIKE` vs `~` | `LIKE` uses `%_`; `~` uses regex |
| `=` vs `IS DISTINCT FROM` | `=` with NULL → UNKNOWN; `IS DISTINCT FROM` is total |
| `LIMIT` vs `FETCH FIRST` | Syntax only; `LIMIT` is PostgreSQL |
| `SERIAL` vs `GENERATED ... AS IDENTITY` | `SERIAL` is a separate sequence object; `IDENTITY` is standard SQL |
| `JSON` vs `JSONB` | `JSON` preserves text; `JSONB` is binary, indexable, dedupes keys |
| `TIMESTAMP` vs `TIMESTAMPTZ` | `TIMESTAMP` is wall-clock; `TIMESTAMPTZ` is UTC + timezone |
| `VARCHAR(n)` vs `TEXT` | In PostgreSQL: identical storage; `TEXT` is the portable default |
| `TRUNCATE` vs `DELETE` | `TRUNCATE` is O(1) + resets sequences; `DELETE` is row-by-row + MVCC |
| `FOR UPDATE` vs `FOR SHARE` | Exclusive vs shared row lock |
| `GROUP BY` vs `DISTINCT` | Group + aggregate vs deduplicate rows |
| `WHERE` vs `HAVING` | Row-level vs group-level filter |
| `HAVING` vs `ORDER BY` | Filter groups vs sort results |
| `COALESCE` vs `CASE WHEN` | `COALESCE` = first non-NULL; `CASE` is general branching |

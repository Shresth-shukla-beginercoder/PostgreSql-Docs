# PART 4: ALL TYPES OF JOINS — EXTRAORDINARY DETAIL

> Two sample tables are used throughout.
>
> **Employees** (`e`): `emp_id, name, dept_id`
> ```
> 1, Alice, 10
> 2, Bob,   20
> 3, Carol, 10
> 4, Dan,   30
> 5, Eve,   NULL
> ```
>
> **Departments** (`d`): `dept_id, dept_name`
> ```
> 10, Engineering
> 20, Sales
> 30, HR
> 40, Marketing
> ```

## 4.1 INNER JOIN

**Concept:** Keep only rows where the join condition is true on *both* sides. Rows with no match on either side disappear.

```sql
SELECT e.name, d.dept_name
FROM employees e
INNER JOIN departments d ON e.dept_id = d.dept_id;
```

**Output:**

| name | dept_name |
|---|---|
| Alice | Engineering |
| Bob | Sales |
| Carol | Engineering |
| Dan | HR |

Eve (dept_id NULL) and Marketing (no employees) are dropped.

**Unmatched record behavior:** silently discarded — the classic source of "I lost rows" in reporting.

## 4.2 LEFT JOIN (and RIGHT, FULL OUTER)

**LEFT JOIN:** keep *all* left rows; fill right side with NULLs when there is no match.

```sql
SELECT e.name, d.dept_name
FROM employees e
LEFT JOIN departments d ON e.dept_id = d.dept_id;
```

**Output:**

| name | dept_name |
|---|---|
| Alice | Engineering |
| Bob | Sales |
| Carol | Engineering |
| Dan | HR |
| Eve | **NULL** |

Marketing still does not appear (it is on the *right* side).

**RIGHT JOIN** is the mirror: keep all right rows; left side NULL when no match.

```sql
SELECT e.name, d.dept_name
FROM employees e
RIGHT JOIN departments d ON e.dept_id = d.dept_id;
```

**Output:**

| name | dept_name |
|---|---|
| Alice | Engineering |
| Bob | Sales |
| Carol | Engineering |
| Dan | HR |
| **NULL** | Marketing |

**FULL OUTER JOIN:** keep every row from *both* tables; NULLs on the unmatched side.

```sql
SELECT e.name, d.dept_name
FROM employees e
FULL OUTER JOIN departments d ON e.dept_id = d.dept_id;
```

**Output:**

| name | dept_name |
|---|---|
| Alice | Engineering |
| Bob | Sales |
| Carol | Engineering |
| Dan | HR |
| Eve | NULL |
| NULL | Marketing |

> **NULL behavior note:** unmatched rows have `NULL` in *all* the joined columns — not only the join key. Check `WHERE d.dept_name IS NULL` when hunting unmatched right-side records.

## 4.3 CROSS JOIN

**Concept:** Cartesian product — every left row × every right row. No `ON` clause.

```sql
SELECT e.name, d.dept_name
FROM employees e
CROSS JOIN departments d;
```

Output: 5 employees × 4 departments = 20 rows (each employee paired with every department).

**Use cases:** generating combinations (report matrix, benchmark pairs, time slots × items), and — when there is a correlated filter — a *degenerate* cross join via `LATERAL` (Part 4.8).

**When NOT to use:** if you accidentally write `FROM a, b` without a `WHERE`, you get an implicit CROSS JOIN. On million-row tables, that is a multi-billion-row explosion.

## 4.4 SELF JOIN

**Concept:** Join a table to itself, using different aliases.

```sql
-- Find pairs of employees in the same department
SELECT e1.name AS emp1, e2.name AS emp2, e1.dept_id
FROM employees e1
JOIN employees e2 ON e1.dept_id = e2.dept_id AND e1.emp_id < e2.emp_id;
```

**Practical use:** hierarchical (parent/child) relationships — "who reports to whom," product/category lookups, version diffing.

## 4.5 NATURAL JOIN (and `USING`)

PostgreSQL does **not** implement the `NATURAL` keyword. The equivalent is `JOIN ... USING`:

```sql
-- USING: one implicit-equality column
SELECT e.name, d.dept_name
FROM employees e JOIN departments d USING (dept_id);

-- ON: explicit multi-column predicate
SELECT e.name, d.dept_name
FROM employees e JOIN departments d ON e.dept_id = d.dept_id;
```

**`USING` vs `ON`:**
- `USING` produces a single result column named `dept_id` (no `e.`/`d.` prefix).
- `ON` lets you write multi-column and inequality predicates, plus filters inside the `ON` itself.
- **Rule of thumb:** use `ON` for anything more than a single equality; `USING` only for clean 1:1 equality joins.

## 4.6 LATERAL JOIN

**Concept:** A subquery in `FROM` may reference *earlier* `FROM` items only when the subquery is marked `LATERAL`.

```sql
-- Top 2 most recent orders per customer
SELECT c.user_id, c.name, o.order_id, o.total_cents
FROM customers c
CROSS JOIN LATERAL (
  SELECT order_id, total_cents
  FROM orders
  WHERE customer_id = c.user_id
  ORDER BY placed_at DESC
  LIMIT 2
) o
ORDER BY c.user_id, o.placed_at DESC;
```

**Practical uses:**
- "Top-N per group" (the pattern above) — an alternative to window functions.
- Function calls per row: `SELECT * FROM users u, LATERAL get_top_events(u.user_id)` (Part 15).
- Correlated aggregation (Part 5).

**Performance:** the LATERAL subquery can run *once per outer row* — a nested loop; use when the outer row set is small.

## 4.7 Multi-Table Joins (3+ Tables, Composite Keys)

### Joining three or more tables

```sql
-- Order line items: order → item → product → supplier
SELECT o.order_id, oi.qty, p.name AS product_name, s.supplier_name
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
JOIN products p     ON p.product_id = oi.product_id
JOIN suppliers s    ON s.supplier_id = p.supplier_id;
```

**Order matters to the planner, not to the result** (for inner joins): PostgreSQL is free to pick any join order; for LEFT/RIGHT/FULL joins the tree shape is honored, so put the "keep-all" table on the left.

### Composite keys

```sql
-- A fact table keyed on (store_id, product_id, month)
SELECT m.month, m.region, m.qty
FROM monthly_sales m
JOIN regions r
  ON m.region_id = r.region_id AND m.year = r.fiscal_year
 WHERE m.year = 2025;
```

The **join predicate** must reference *all* key columns — a partial match silently broadens the result set.

### Joining on different column types

`CAST` on one side (not both) — PostgreSQL resolves operator ambiguity:

```sql
SELECT * FROM users u JOIN orders o ON o.customer_id = u.user_id::int;
```

## 4.8 JOIN vs Subquery vs EXISTS

Three equivalent shapes:

```sql
-- JOIN (eager)
SELECT c.name, count(o.order_id)
FROM customers c LEFT JOIN orders o ON o.customer_id = c.user_id
GROUP BY c.name;

-- Correlated subquery (evaluated per row)
SELECT c.name,
       (SELECT count(*) FROM orders o WHERE o.customer_id = c.user_id) AS n
FROM customers c;

-- EXISTS (boolean test)
SELECT c.name FROM customers c
WHERE EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.user_id);
```

**Costs:** the planner often turns a correlated subquery into a Hash/Nested-Loop join (or vice-versa) — the *choice of syntax* is less important than *which plan wins* (Part 12). `EXISTS` short-circuits; `JOIN` materializes.

**JOIN vs UNION:** `UNION` merges *result sets* from independent queries (vertical), `JOIN` links *columns* from related tables (horizontal). A `UNION` of two `SELECT`s that share a `WHERE` is the classic anti-pattern for OR-across-tables queries.

## 4.9 Why Do Joins Produce Duplicate Rows?

**Answer:** when the right side has *multiple* matching rows per left row, the left row is duplicated. Example: one customer → five orders → a `JOIN` to orders returns five copies of that customer row.

**Fix patterns:**
- Deduplicate with `DISTINCT` (expensive) or `GROUP BY`.
- Restrict the join (e.g., `WHERE o.status = 'PAID'`).
- Use `EXISTS` when you only need a boolean.

## 4.10 Troubleshooting Incorrect Join Results

Checklist (production debugging):

1. **Count sanity:** `SELECT count(*) FROM a; SELECT count(*) FROM a JOIN b ...;` — if the joined count is *much* larger than `a`, you are multiplying (one-to-many without aggregation).
2. **Check NULLs in the join key:** `NULL = NULL` is `UNKNOWN`, so NULL-keyed rows never match in `INNER`/`LEFT` joins. Use `IS NOT DISTINCT FROM` if you need NULL-matching.
3. **Type mismatch:** `text = int` is a silent cast in some cases; verify with `\dt` or `information_schema.columns`.
4. **Collation/locale:** two "equal" strings that differ in collation.
5. **Wrong direction:** `LEFT JOIN` where you wanted `RIGHT` (or vice versa).
6. **Missing predicate in `ON`:** a `LEFT JOIN` with `ON 1=1` is a `CROSS JOIN`.

## 4.11 Join Algorithms: Nested Loop, Hash, Merge

(Full planner cost model: Parts 11–12.)

| Algorithm | When it wins | Cost shape |
|---|---|---|
| **Nested Loop** | Small inner side; LATERAL; `LIMIT`; indexable inner table | O(outer × inner-lookups) |
| **Hash** | Medium-to-large both sides; equi-join | Build: O(inner); probe: O(outer) |
| **Merge** | Both sides *already sorted* on the join key (e.g., index-only scans) | O(n+m) |

**How to force / inspect:**

```sql
EXPLAIN (ANALYZE, BUFFERS) SELECT ... ;
SET enable_hashjoin = off;        -- diagnostic only, never in production
SET enable_nestloop = off;       -- see the planner's *non-forced* preference
```

**Practical example:** a 10-million-row `events` table joined to a 1000-row `users` table:
- Planner chooses **Hash** (small side → hash, probe large side) or **Nested Loop with index** on `events.user_id`.
- `EXPLAIN` shows either a `Hash Join` (one build + probe) or `Nested Loop → Index Scan on events_user_idx`.

## 4.12 Three Practical Examples per Join Type

### INNER

```sql
-- 1. Order count per product
SELECT p.name, count(o.order_id) AS orders
FROM products p INNER JOIN orders o ON o.product_id = p.product_id
GROUP BY p.name ORDER BY orders DESC;

-- 2. Shipment + payment consistency check
SELECT o.order_id FROM orders o
INNER JOIN shipments s ON s.order_id = o.order_id
INNER JOIN payments  p ON p.order_id = o.order_id
WHERE o.status = 'shipped' AND s.tracking IS NULL;

-- 3. Average order value per region
SELECT r.region_name, avg(o.total_cents)
FROM regions r
JOIN customers c ON c.region_id = r.region_id
JOIN orders o    ON o.customer_id = c.user_id
GROUP BY r.region_name;
```

### LEFT

```sql
-- 1. Customers without orders
SELECT c.user_id, c.email
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.user_id
WHERE o.order_id IS NULL;

-- 2. Department headcount (including empty departments)
SELECT d.dept_name, count(e.emp_id) AS headcount
FROM departments d LEFT JOIN employees e ON e.dept_id = d.dept_id
GROUP BY d.dept_name;

-- 3. Last login per user (users with no sessions still listed)
SELECT u.user_id, s.last_seen
FROM users u
LEFT JOIN sessions s ON s.user_id = u.user_id;
```

### FULL OUTER

```sql
-- 1. All customers, all products — find "missing" purchase pairs
SELECT c.email, p.name
FROM customers c FULL OUTER JOIN purchases pu
  ON pu.customer_id = c.user_id AND pu.product_id = p.product_id
...

-- 2. Reconciliation: orders vs payments (both sides may miss rows)
SELECT o.order_id AS oid, p.payment_id AS pid
FROM orders o FULL OUTER JOIN payments p ON p.order_id = o.order_id
WHERE o.order_id IS NULL OR p.payment_id IS NULL;

-- 3. Symmetric difference of tags
SELECT t.tag FROM tags t FULL OUTER JOIN legacy_tags l USING(tag)
WHERE t.id IS NULL OR l.id IS NULL;
```

## 4.13 Join Diagrams (mental model)

```
INNER            LEFT               FULL OUTER
┌────┐           ┌────┐            ┌────┐
│ A  │           │ A  │            │ A  │
└─┬──┘           └─┬──┘            └─┬──┘
  │  B               │  B               │  B
┌─┴──┐             ┌─┴──┐            ┌─┴──┐
│ B  │              │ B  │            │ B  │
└────┘              └────┘            └────┘
match = overlap     match = A fully   match = A∪B union
```

**Diagram for a 4-table join (plan shape):**

```
orders ──order_items ──products ──suppliers
  │         │            │
 (1)───(2)───(3)───(4)
```

The planner may reorder `(3)` before `(2)` if `products` is far smaller — **join order is a cost decision, not a syntactic one**.

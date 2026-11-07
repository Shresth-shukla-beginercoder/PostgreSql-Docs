# PART 5: SUBQUERIES AND ADVANCED QUERYING

## 5.1 The Five Flavors of Subqueries

| Flavor | Position | Example |
|---|---|---|
| **Scalar** | In `SELECT` list (single value expected) | `SELECT (SELECT max(score) FROM scores)` |
| **Single-row** | In `WHERE` (returns exactly one row or 0) | `WHERE id = (SELECT id FROM x LIMIT 1)` |
| **Multiple-row** | `IN`/`ANY`/`ALL` list | `WHERE dept IN (SELECT ...)` |
| **Correlated** | References an outer row | `WHERE o.cust_id = c.cust_id` inside `c`'s loop |
| **Non-correlated** | No outer reference | `WHERE id IN (SELECT id FROM blacklist)` |

### Practical examples (increasing difficulty)

```sql
-- 1. Scalar: average order value in the SELECT list
SELECT c.email, c.orders_n,
       (SELECT avg(o.total_cents) FROM orders o WHERE o.customer_id = c.user_id) AS avg_order
FROM customers c;

-- 2. Single-row: the company's oldest employee
SELECT * FROM employees
WHERE hire_date = (SELECT min(hire_date) FROM employees);

-- 3. Multiple-row: in-stock products
SELECT p.name FROM products p
WHERE p.product_id IN (SELECT product_id FROM stock WHERE qty > 0);

-- 4. Correlated: employees above their department average
SELECT e.name, e.salary, d.dept_name
FROM employees e JOIN departments d ON d.dept_id = e.dept_id
WHERE e.salary > (SELECT avg(e2.salary) FROM employees e2
                  WHERE e2.dept_id = d.dept_id);

-- 5. Nested: second-highest salary per department (window function alternative in Part 7)
SELECT dept_id, max(salary) AS second
FROM (
  SELECT dept_id, salary,
         rank() OVER (PARTITION BY dept_id ORDER BY salary DESC) AS r
  FROM employees
) t WHERE r = 2
GROUP BY dept_id;
```

## 5.2 EXISTS and NOT EXISTS

**`EXISTS`** tests for *presence* of any matching row — it short-circuits (stops at first match).

```sql
-- Customers who have placed at least one order
SELECT c.* FROM customers c
WHERE EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.user_id);

-- Orders with no shipment
SELECT o.order_id FROM orders o
WHERE NOT EXISTS (SELECT 1 FROM shipments s WHERE s.order_id = o.order_id);
```

**Why prefer `EXISTS` over `IN` (with a subquery)?**
- `IN` can be NULL-poisoned (see Part 3); `NOT IN` + NULLs returns zero rows.
- `EXISTS` is typically *faster* when the inner side is large (stop at first match vs. materialize the whole set).
- Modern PostgreSQL *often* plans `IN (subquery)` as a semi-join, so `EXISTS` and `IN` produce similar plans — but `NOT EXISTS` is still the safer default.

## 5.3 ANY and ALL

```sql
-- Score above every employee in the same department
SELECT e.* FROM employees e
WHERE e.salary > ALL (SELECT e2.salary FROM employees e2 WHERE e2.dept_id = e.dept_id);

-- Any active tag
SELECT p.* FROM products p
WHERE p.tag = ANY (SELECT tag FROM active_tags);
```

**Semantics:** `> ALL` = greater than the *maximum*; `< ANY` = less than the *minimum*.

## 5.4 Subquery Placement

### Inside SELECT (scalar or set-returning)

```sql
SELECT u.name,
       (SELECT count(*) FROM orders o WHERE o.customer_id = u.user_id) AS orders
FROM users u;
```

### Inside FROM (derived tables)

```sql
-- Aggregate before joining
SELECT c.name, d.total
FROM customers c
JOIN (
  SELECT customer_id, sum(total_cents) AS total
  FROM orders GROUP BY customer_id
) d ON d.customer_id = c.user_id;
```

### Inside WHERE (correlated)

```sql
-- The "correlated aggregate" pattern
SELECT c.user_id, c.name
FROM customers c
WHERE (SELECT count(*) FROM orders o WHERE o.customer_id = c.user_id) > 3;
```

## 5.5 Common Table Expressions (CTEs)

**Purpose:** a *named* subquery at the top of the statement. In PostgreSQL, **non-recursive CTEs are inlined by default** (treated as subqueries).

### Multiple CTEs

```sql
WITH base AS (
  SELECT order_id, total_cents FROM orders WHERE placed_at >= now() - interval '30 days'
),
by_region AS (
  SELECT r.region_name, sum(b.total_cents) AS revenue
  FROM base b
  JOIN orders o ON o.order_id = b.order_id
  JOIN customers c ON c.user_id = o.customer_id
  JOIN regions r ON r.region_id = c.region_id
  GROUP BY r.region_name
)
SELECT * FROM by_region ORDER BY revenue DESC;
```

### Recursive CTEs

```sql
-- Flattening a hierarchy (org chart)
WITH RECURSIVE org AS (
  SELECT emp_id, manager_id, name, 1 AS lvl
  FROM employees WHERE manager_id IS NULL
  UNION ALL
  SELECT e.emp_id, e.manager_id, e.name, org.lvl + 1
  FROM employees e JOIN org ON e.manager_id = org.emp_id
)
SELECT * FROM org ORDER BY lvl, name;
```

**Termination:** recursive CTEs require an acyclic graph, a `LIMIT` on `lvl`, or a `WHILE` in `UNION`. Add `SELECT 1 AS lvl` and check `count(lvl)` to guard against runaway recursion.

### Materialized vs Non-Materialized CTEs

```sql
-- Force materialization (compute once, store result)
WITH heavy AS MATERIALIZED (
  SELECT * FROM big_expensive_join
)
SELECT * FROM heavy WHERE x;
SELECT * FROM heavy WHERE y;   -- both read the stored copy

-- Force inlining
WITH light AS NOT MATERIALIZED (SELECT * FROM t WHERE a = 1)
SELECT * FROM light;
```

**When `MATERIALIZED`:** heavy subquery used 2+ times, or you want to *freeze* intermediate results (audit / debugging).

## 5.6 LATERAL

(See Part 4.6 for the join form; the `SELECT`-form: `SELECT * FROM t, LATERAL (SELECT ...) f`.)

**Top-N-per-group (the classic):**

```sql
-- 3 most recent orders per customer
SELECT c.name, o.*
FROM customers c
CROSS JOIN LATERAL (
  SELECT order_id, placed_at, total_cents FROM orders
  WHERE customer_id = c.user_id
  ORDER BY placed_at DESC LIMIT 3
) o
ORDER BY c.name, o.placed_at DESC;
```

## 5.7 Set Operations with ORDER BY and LIMIT

```sql
SELECT tag FROM tag_a
UNION
SELECT tag FROM tag_b
ORDER BY tag
LIMIT 10;
```

- **`ORDER BY` / `LIMIT`** apply to the *entire* set result (standard SQL).
- `UNION` removes duplicates (Sort); `UNION ALL` keeps them (fast).
- `INTERSECT` and `EXCEPT` likewise support `ORDER BY` + `LIMIT` at the end.

## 5.8 Execution Concepts (what the planner does)

- **Correlated subquery → Nested Loop:** each outer row triggers the inner query. If the inner is indexable, a *per-outer-row* index scan.
- **`IN (subquery)` → Semi-Join (Hash or Merge):** the planner materializes the inner set, hashes it, probes with outer rows.
- **`NOT EXISTS` → Anti-Semi-Join:** like `IN`, but the probe stops at the first match.
- **`EXISTS` short-circuits:** planner can stop at first matching inner row.
- **CTE inlining:** `WITH x AS (SELECT ...) SELECT * FROM x` may be *rewritten* to a subquery — the `MATERIALIZED` keyword pins it.

**Practical benchmarking:**

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT c.name, o.total_cents FROM customers c
CROSS JOIN LATERAL (
  SELECT total_cents FROM orders WHERE customer_id = c.user_id
  ORDER BY placed_at DESC LIMIT 1
) o;
-- Look for: Nested Loop (LATERAL) with an Index Scan on orders_user_created_idx
```

## 5.9 Difficulty Ladder (interview-style)

**Easy:** list of customers who have ordered (one `EXISTS`).
**Medium:** customers whose *most recent* order is > 90 days old (`LATERAL` + `LIMIT 1`, or window function + `DISTINCT ON`).
**Hard:** second-most-recent order per customer (window `ROW_NUMBER` + `QUALIFY` is not available; use a CTE + `WHERE rn=2`).

```sql
-- Second-most-recent order per customer
SELECT customer_id, placed_at FROM (
  SELECT customer_id, placed_at,
         row_number() OVER (PARTITION BY customer_id ORDER BY placed_at DESC) AS rn
  FROM orders
) t WHERE rn = 2;
```

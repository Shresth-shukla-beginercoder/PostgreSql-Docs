# PART 7: WINDOW FUNCTIONS — ADVANCED LEVEL

## 7.1 The Core Idea

A **window function** computes a value over a *set* of rows (the **window/partition**) **while preserving the row** (unlike `GROUP BY`, which collapses rows).

**Syntax skeleton:**

```sql
SELECT col,
       window_function(col)
       OVER (
         [ PARTITION BY pcols ]
         [ ORDER BY ocols [ ASC|DESC ] ]
         [ frame_clause ]
       ) AS wf
FROM table;
```

- **`PARTITION BY`** — splits the table into independent groups.
- **`ORDER BY` inside `OVER`** — row order *within* each partition (required for row-number functions).
- **Frame clause** — *which rows of the partition* the aggregate sees (Part 7.3).

**Named windows** (PostgreSQL extension):

```sql
SELECT col, row_number() OVER w
FROM t
WINDOW w AS (PARTITION BY cat ORDER BY ts);
```

## 7.2 The Function Families

### Ranking

| Function | Ties behavior |
|---|---|
| `ROW_NUMBER()` | Unique per partition (ties broken arbitrarily by `ORDER BY`) |
| `RANK()` | Ties share rank, next rank is skipped (1,2,2,4) |
| `DENSE_RANK()` | Ties share rank, next rank is not skipped (1,2,2,3) |
| `NTILE(n)` | Divide into `n` buckets |

```sql
-- 1. Top 3 salespeople
SELECT user_id, sales, RANK() OVER (ORDER BY sales DESC) AS r
FROM sales WHERE RANK() OVER (ORDER BY sales DESC) <= 3;

-- 2. Second-highest price per category
SELECT * FROM (
  SELECT p.*, DENSE_RANK() OVER (PARTITION BY category_id ORDER BY price DESC) AS r
  FROM products p
) t WHERE r = 2;
```

**`LAST_VALUE` gotcha:** by default the frame is `RANGE UNBOUNDED PRECEDING TO CURRENT ROW`, so `LAST_VALUE` returns the *current* row — to get the true last, use `ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING`.

### Offset

| Function | Meaning |
|---|---|
| `LAG(col, n)` | Value `n` rows *before* the current |
| `LEAD(col, n)` | Value `n` rows *after* the current |
| `FIRST_VALUE(col)` | First row of the partition |
| `LAST_VALUE(col)` | Last row (mind the frame!) |
| `NTH_VALUE(col, n)` | Nth row |

```sql
-- Month-over-month revenue
SELECT month, revenue,
       revenue - LAG(revenue, 1) OVER (ORDER BY month) AS delta,
       ROUND(100.0 * revenue / LAG(revenue,1) OVER (ORDER BY month), 2) AS mom_pct
FROM monthly_revenue;

-- Year-over-year
SELECT month, revenue,
       revenue / LAG(revenue, 12) OVER (ORDER BY month) AS yoy_ratio
FROM monthly_revenue;
```

### Running Aggregates

`SUM/AVG/COUNT/MIN/MAX OVER (...)` — with a frame.

```sql
-- Running total
SELECT ts, amount,
       SUM(amount) OVER (ORDER BY ts
                         ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running
FROM ledger;
```

### Three Practical Analytics Patterns

**Percentage contribution:**

```sql
SELECT category_id, revenue,
       revenue * 100.0 / SUM(revenue) OVER () AS pct_of_total
FROM category_revenue;
```

**Cumulative distribution:**

```sql
SELECT ts, user_id,
       PERCENT_RANK() OVER (ORDER BY ts) AS pctile
FROM sessions;
```

**Gaps-and-islands (consecutive logins):**

```sql
WITH islands AS (
  SELECT user_id, login_ts,
         DENSE_RANK() OVER (PARTITION BY user_id ORDER BY login_ts)
         - ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY login_ts) AS grp
  FROM logins
)
SELECT user_id, min(login_ts) AS start, max(login_ts) AS end, count(*) AS n
FROM islands
GROUP BY user_id, grp;
```

## 7.3 Frame Clauses — The Subtlety That Gets Interviews Wrong

**The default frame depends on the presence of `ORDER BY`:**

| If `OVER(...)` contains... | Default frame |
|---|---|
| `ORDER BY` | `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` |
| `PARTITION BY` only (no ORDER BY) | `RANGE BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING` (whole partition) |
| No `PARTITION BY`, no `ORDER BY` | Whole result set |

**Frame units:**

| Unit | Compares |
|---|---|
| **`ROWS`** | Physical rows (peers at the same offset) |
| **`RANGE`** | Logical values (peers = tied values) |
| **`GROUPS`** | (PostgreSQL 17) groups of rows via `GROUPS n PRECEDING` |

```sql
-- SUM over the whole partition (not a running sum!)
SELECT emp, dept, salary,
       SUM(salary) OVER (PARTITION BY dept) AS dept_total
FROM employees;

-- Running sum (RANGE up to current row)
SELECT emp, salary,
       SUM(salary) OVER (PARTITION BY dept ORDER BY salary
                         RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running
FROM employees;
```

**Common mistake:** `LAST_VALUE(x) OVER (PARTITION BY p ORDER BY t)` returns *the current row's x*, not the partition's last x. Fix: add `ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING`.

## 7.4 Window Functions vs GROUP BY vs Correlated Subqueries

| Need | Best tool |
|---|---|
| Collapse to one row per group | `GROUP BY` |
| Preserve rows + add group stats | Window function |
| "Top-N per group" | Window `ROW_NUMBER()` + CTE, or `LATERAL` + `LIMIT` |
| Comparing each row to a group aggregate | Window (`AVG OVER`), *not* a correlated subquery per row |

## 7.5 Complex Interview Questions

**Q: Return the second-largest value per category, without `LIMIT` per group.**

```sql
SELECT * FROM (
  SELECT category_id, price, DENSE_RANK() OVER (PARTITION BY category_id ORDER BY price DESC) AS r
  FROM products
) t WHERE r = 2;
```

**Q: Detect a gap of > 2 days in a per-user event stream.**

```sql
WITH gaps AS (
  SELECT user_id, ts,
         ts - LAG(ts) OVER (PARTITION BY user_id ORDER BY ts) AS gap
  FROM events
)
SELECT * FROM gaps WHERE gap > interval '2 days';
```

**Q: Running distinct-count (expensive — note the O(n·m)).**

```sql
SELECT ts, COUNT(DISTINCT user_id) OVER (ORDER BY ts
                                         ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
FROM events;
```

**Performance note:** `COUNT(DISTINCT ...) OVER` is *not* supported on all backends; in PostgreSQL it works but is expensive. Use a *materialized* approach (refresh a table) for large data.

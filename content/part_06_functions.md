# PART 6: AGGREGATE, STRING, DATE, AND NUMERIC FUNCTIONS

> PostgreSQL has **hundreds** of built-in functions. This part covers the most-used in each family, plus *how to discover* the rest. For a single function: purpose, syntax, parameters, return type, NULL behavior, two examples, practical application, performance notes.

## 6.1 How to Discover Available Functions

```sql
-- Search system catalogs
SELECT proname, pg_get_functiondef(oid)
FROM pg_proc
WHERE proname ILIKE '%round%'
ORDER BY proname;

-- Or simply
SELECT * FROM pg_available_extensions;   -- Part 30
\df round        -- psql meta: list functions
```

## 6.2 Aggregate Functions

| Function | Purpose | Notes |
|---|---|---|
| `COUNT(expr)` / `COUNT(*)` / `COUNT(DISTINCT x)` | Number of rows / distinct values | `COUNT(*)` counts rows (fast); `COUNT(col)` skips NULLs |
| `SUM(x)` | Sum of numeric `x` | NULLs ignored; all-NULL group → NULL |
| `AVG(x)` | Mean | NULLs ignored |
| `MIN(x)` / `MAX(x)` | Extremes | Works on dates, strings, arrays |
| `STRING_AGG(x, sep)` | Concatenate with separator | `STRING_AGG(name, ', ' ORDER BY name)` |
| `ARRAY_AGG(x)` | Collect into an ARRAY | `ARRAY_AGG(name ORDER BY name)` |
| `JSON_AGG(x)` / `JSONB_AGG(x)` | Aggregate to a JSON array/object | `jsonb_agg(row_to_jsonb(r))` |
| `BOOL_AND(x)` / `BOOL_OR(x)` / `EVERY(x)` | All true / any true / all true | `EVERY` ≡ `BOOL_AND` |
| `MODE() WITHIN GROUP (ORDER BY x)` | Most-frequent value | Ordered-set aggregate |
| `PERCENTILE_CONT(q) WITHIN GROUP (ORDER BY x)` | Interpolated quantile | Median = 0.5 |
| `PERCENTILE_DISC(q) WITHIN GROUP (ORDER BY x)` | Discrete quantile | |
| `STDDEV(x)` / `VARIANCE(x)` | Spread | `STDDEV_POP`/`STDDEV_SAMP` |

### Examples

```sql
-- Revenue by month with a median
SELECT date_trunc('month', placed_at) AS m,
       count(*) AS orders,
       sum(total_cents) AS revenue,
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_cents) AS median_order
FROM orders
GROUP BY 1
ORDER BY m;

-- Distinct product count with a string of names
SELECT category_id,
       count(DISTINCT product_id) AS products,
       STRING_AGG(DISTINCT name, ', ' ORDER BY name) AS names
FROM products
GROUP BY category_id;
```

**NULL behavior:** all aggregates (except `COUNT(*)`) *ignore* NULLs. `SUM(NULL)` on an all-NULL group → `NULL`.

**Performance:** `COUNT(DISTINCT)` on a large column forces a full sort/hash — for huge tables use a `GROUP BY` + `COUNT(*)` two-step, or `approx_count_distinct` (hypopg extension, Part 24).

## 6.3 String Functions

| Function | Example | Notes |
|---|---|---|
| `LENGTH(s)` / `CHAR_LENGTH(s)` | `length('héllo')` → 5 | `LENGTH` counts characters |
| `LOWER` / `UPPER` / `INITCAP` | `initcap('john smith')` → 'John Smith' | Locale-dependent |
| `TRIM(s)` / `LTRIM` / `RTRIM` | `trim('  ab ')` → `ab` | |
| `CONCAT(a,b,c)` / `CONCAT_WS(sep,a,b,c)` | `concat_ws(' - ', 'a','b')` → `a - b` | `CONCAT` skips NULLs (unlike `\|\|`) |
| `SUBSTRING(s FROM p FOR n)` | `substring('abc' from 2 for 2)` → `bc` | |
| `LEFT(s, n)` / `RIGHT(s, n)` | `left('hello',3)` → `hel` | |
| `REPLACE(s, from, to)` | `replace('a-b-c','-','/')` → `a/b/c` | |
| `POSITION(sub IN s)` | `position('@' in email)` | |
| `SPLIT_PART(s, sep, n)` | `split_part('a,b,c',',',2)` → `b` | |
| `STRING_TO_ARRAY(s, sep)` | `string_to_array('a,b,c',',')` → `{a,b,c}` | |
| `ARRAY_TO_STRING(arr, sep)` | `array_to_string(ARRAY[1,2],',')` → `1,2` | |
| `REGEXP_REPLACE(s, pat, rep)` | `regexp_replace('a1b2','[0-9]','#')` → `a#b#` | |
| `REGEXP_MATCHES(s, pat)` | `regexp_like('abc','^[a-z]+$')` → `true` | |
| `FORMAT(fmt, args)` | `format('%s-%s','a',2)` → `a-2` | |

**Performance:** `LENGTH`, `UPPER`, etc. on an *expression* (e.g., `UPPER(email)`) are **not indexable** — wrap in an expression index (`CREATE INDEX ON t ((upper(email)))`).

## 6.4 Date and Time Functions

| Function | Example | Notes |
|---|---|---|
| `NOW()` / `CURRENT_TIMESTAMP` | `2026-11-06 14:03:02.456+05` | Identical; a *transaction* timestamp (fixed within a tx) |
| `CURRENT_DATE` / `CURRENT_TIME` / `LOCALTIME` / `LOCALTIMESTAMP` | | |
| `AGE(a, b)` | `age('1990-01-01')` → interval | |
| `EXTRACT(unit FROM ts)` | `extract('hour' from now())` | |
| `DATE_PART(unit, ts)` | `date_part('day', now())` | Same as EXTRACT |
| `DATE_TRUNC(unit, ts)` | `date_trunc('month', now())` | |
| `INTERVAL 'n unit'` | `interval '3 days'` | |
| `MAKE_DATE(y,m,d)` / `MAKE_TIMESTAMP(...)` | | |
| `TO_DATE(s, fmt)` | `to_date('06-11-2026','DD-MM-YYYY')` | Dangerous: use ISO format |
| `TO_TIMESTAMP(s, fmt)` | | |
| `AT TIME ZONE` | `now() AT TIME ZONE 'Asia/Kolkata'` | |
| `TO_CHAR(ts, fmt)` | `to_char(now(), 'YYYY-MM-DD HH24:MI:SS')` | |

**NULL behavior:** `EXTRACT`/`DATE_TRUNC` on NULL → NULL.

**Performance:** `WHERE created_at >= date_trunc('month', now())` is *sargable* (indexable); `WHERE to_char(created_at,'YYYY-MM') = '2026-11'` is *not* (a function on the column). **Always compare against a range, not a formatted string.**

## 6.5 Numeric Functions

| Function | Example |
|---|---|
| `ROUND(x)` / `CEIL(x)` / `FLOOR(x)` / `TRUNC(x)` | `round(3.456, 2)` → `3.46` |
| `ABS(x)` | `abs(-42)` → 42 |
| `POWER(x,y)` / `SQRT(x)` | `sqrt(144)` → 12 |
| `MOD(a,b)` | `mod(10,3)` → 1 |
| `RANDOM()` | 0.0–1.0 |
| `GREATEST(a,b,...)` / `LEAST(a,b,...)` | `greatest(1,2,3)` → 3 |

**Note:** `CEILING`/`FLOOR` are SQL aliases; `CEIL`/`FLOOR` are the PostgreSQL names.

## 6.6 Conditional and Conversion Functions

| Function | Purpose |
|---|---|
| `COALESCE(a,b,...)` | First non-NULL |
| `NULLIF(a,b)` | NULL when a=b |
| `GREATEST` / `LEAST` | Max / min of a list |
| `CAST(x AS type)` / `x::type` | Type conversion |
| `TO_CHAR` / `TO_NUMBER` | Format / parse |
| `TO_JSON` / `TO_JSONB` | Row → JSON |
| `JSON_BUILD_OBJECT` / `JSONB_BUILD_OBJECT` | key-value → JSON |

```sql
-- Combine a row into a JSON object (for API-friendly reporting)
SELECT JSONB_BUILD_OBJECT(
  'id', user_id, 'email', email, 'vip', (score >= 90)
) FROM users;

-- Parse a numeric string
SELECT to_number('1,234.56', '999G999D99');
```

**Performance:** `TO_JSONB(row)` is moderately expensive; do not call it per row on millions.

## 6.7 Function Categories (quick map)

- **Math:** abs, ceil, floor, round, power, sqrt, mod, random, trunc, gcd, lgamma
- **String:** length, lower, upper, initcap, trim, concat, substring, left, right, replace, position, split_part, string_to_array, array_to_string, regexp_replace, regexp_like, format
- **Datetime:** now, age, extract, date_part, date_trunc, make_date, to_date, to_timestamp, to_char
- **Aggregate:** count, sum, avg, min, max, string_agg, array_agg, json_agg, jsonb_agg, bool_and, bool_or, every, mode, percentile_cont, percentile_disc, stddev, variance
- **Conditional/Conversion:** coalesce, nullif, greatest, least, cast, to_char, to_number, to_json, to_jsonb, json_build_object, jsonb_build_object

## 6.8 Common Function Mistakes

1. **`= NULL` instead of `IS NULL`** (comparisons never match NULL).
2. **`COALESCE` with a volatile argument** (e.g., `coalesce(now(), ...)` — the "default" is itself volatile).
3. **`TO_DATE` with locale-ambiguous formats** (`DD/MM/YYYY` vs `MM/DD/YYYY`).
4. **Aggregating the wrong column** (`SUM(a.col)` vs `SUM(b.col)` in a join).
5. **Assuming `RANDOM()` is stable across runs** (it is not; use `seed` in tests).

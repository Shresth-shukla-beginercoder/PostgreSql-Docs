# PART 28: SQL PRACTICE PROBLEMS

> **Setup.** Run against a PostgreSQL 17 instance. Sample datasets are listed per section; create them with the `SETUP` blocks. Solutions appear in **bold** in the answer key at the end of each section. Try the problem for 5 minutes before peeking.

**Progressive difficulty:** Section 1–4 (junior) → 5–8 (mid) → 9–12 (senior) → 13–15 (expert).

---

## 28.1 Basic Filtering

```sql
-- SETUP
CREATE TABLE employees (id int PRIMARY KEY, name text, department text, salary numeric, hired date);
INSERT INTO employees VALUES
 (1,'Alice','Engineering',95000,'2019-03-01'),
 (2,'Bob','Sales',60000,'2020-01-15'),
 (3,'Carol','Engineering',120000,'2017-08-22'),
 (4,'Dan','Sales',70000,'2021-05-10'),
 (5,'Eve','Marketing',65000,'2022-02-01');
```

1. Select all employees in the 'Engineering' department.
2. Select employees whose salary is between 50000 and 100000 (inclusive).
3. Find employees whose names start with 'A' (case-insensitive).
4. List employees hired after January 1, 2020, ordered by hire date.
5. Find employees whose name contains the letter 'l'.
6. Return all columns for salary above the company average.
7. Find employees in departments with more than 2 people (requires aggregation).
8. List employees NOT in Sales.
9. Find employees with salaries in (50000, 95000, 120000) using `IN`.
10. Return rows where department is 'Engineering' OR salary > 100000.

**Answers:**

> 1. `SELECT * FROM employees WHERE department = 'Engineering';`
> 2. `SELECT * FROM employees WHERE salary BETWEEN 50000 AND 100000;`
> 3. `SELECT * FROM employees WHERE name ILIKE 'A%';`
> 4. `SELECT * FROM employees WHERE hired > '2020-01-01' ORDER BY hired;`
> 5. `SELECT * FROM employees WHERE name ILIKE '%l%';`
> 6. `SELECT * FROM employees WHERE salary > (SELECT AVG(salary) FROM employees);`
> 7. `SELECT e.* FROM employees e JOIN (SELECT department FROM employees GROUP BY department HAVING count(*) > 2) d USING (department) WHERE e.department = d.department;`
> 8. `SELECT * FROM employees WHERE department <> 'Sales';`
> 9. `SELECT * FROM employees WHERE salary IN (50000, 95000, 120000);`
> 10. `SELECT * FROM employees WHERE department = 'Engineering' OR salary > 100000;`

---

## 28.2 Aggregations

```sql
-- SETUP (reuse employees)
```

11. Average salary per department.
12. Number of employees per department, only departments with more than 1.
13. Total salary spent per department, ordered by total descending.
14. Min, max, and range (max-min) of salary per department.
15. Overall average of department averages (i.e., AVG of AVG(salary) per dept).
16. Departments where the top-earner makes at least double the bottom-earner.
17. Count of distinct departments.
18. Average salary, rounded to 2 decimals, per department.
19. The department with the highest average salary (single row).
20. Number of employees hired in each calendar year.

**Answers:**

> 11. `SELECT department, AVG(salary) FROM employees GROUP BY department;`
> 12. `SELECT department, count(*) FROM employees GROUP BY department HAVING count(*) > 1;`
> 13. `SELECT department, SUM(salary) FROM employees GROUP BY department ORDER BY SUM(salary) DESC;`
> 14. `SELECT department, MIN(salary), MAX(salary), MAX(salary)-MIN(salary) AS range FROM employees GROUP BY department;`
> 15. `SELECT AVG(avg_s) FROM (SELECT AVG(salary) avg_s FROM employees GROUP BY department) t;`
> 16. `SELECT department FROM employees GROUP BY department HAVING MAX(salary) >= 2*MIN(salary);`
> 17. `SELECT count(DISTINCT department) FROM employees;`
> 18. `SELECT department, ROUND(AVG(salary),2) FROM employees GROUP BY department;`
> 19. `SELECT department, AVG(salary) FROM employees GROUP BY department ORDER BY AVG(salary) DESC LIMIT 1;`
> 20. `SELECT extract(year FROM hired) yr, count(*) FROM employees GROUP BY 1;`

---

## 28.3 Joins

```sql
-- SETUP
CREATE TABLE users (id int PRIMARY KEY, name text, email text);
CREATE TABLE orders (id int PRIMARY KEY, user_id int REFERENCES users(id), amount numeric, placed_at timestamptz);
INSERT INTO users VALUES (1,'Alice','a@x.com'),(2,'Bob','b@x.com'),(3,'Carol','c@x.com'),(4,'Dan',NULL);
INSERT INTO orders VALUES (10,1,120,now()),(11,1,40,now()),(12,2,300,now()),(13,3,20,now());
```

21. List all orders with the user's name.
22. Find users who have never placed an order.
23. Top 5 users by total amount spent.
24. Users with more than 2 orders.
25. The largest single order, with user name.
26. Left join users↔orders showing order count (0 for none).
27. Orders for users whose email is NULL.
28. Full outer join of users/orders — show unmatched rows from both sides.
29. Self-join: find pairs of users who share the same first name letter (distinct pairs, a.id < b.id).
30. Count total orders and total amount in one row (conditional aggregates).

**Answers:**

> 21. `SELECT o.id, o.amount, u.name FROM orders o JOIN users u ON u.id = o.user_id;`
> 22. `SELECT u.name FROM users u LEFT JOIN orders o ON o.user_id = u.id WHERE o.id IS NULL;`
> 23. `SELECT u.name, SUM(o.amount) total FROM users u JOIN orders o ON o.user_id=u.id GROUP BY u.name ORDER BY total DESC LIMIT 5;`
> 24. `SELECT u.name, count(*) FROM users u JOIN orders o ON o.user_id=u.id GROUP BY u.name HAVING count(*)>2;`
> 25. `SELECT u.name, o.amount FROM orders o JOIN users u USING(user_id) ORDER BY o.amount DESC LIMIT 1;`
> 26. `SELECT u.name, count(o.id) FROM users u LEFT JOIN orders o ON o.user_id=u.id GROUP BY u.name;`
> 27. `SELECT o.* FROM orders o JOIN users u USING(user_id) WHERE u.email IS NULL;`
> 28. `SELECT u.name, o.id FROM users u FULL JOIN orders o ON o.user_id=u.id WHERE u.id IS NULL OR o.user_id IS NULL;`
> 29. `SELECT a.name a1, b.name a2 FROM users a JOIN users b ON left(a.name,1)=left(b.name,1) AND a.id < b.id;`
> 30. `SELECT count(*) orders, SUM(amount) FROM orders;`

---

## 28.4 String and Date Functions

31. Reverse each employee's name.
32. First word of each name.
33. Days between hire date and today, per employee.
34. Employees hired in the same month+day but different years.
35. Format `hired` as 'YYYY-MM'.
36. Convert '2024-11-06' to today's weekday name.
37. Add 3 months to each hire date (watch out for month-end overflow).
38. Trim spaces and uppercase each department.
39. Find email domains (part after '@') and count users per domain.
40. Replace 'Engineering' with 'Eng' in department values (view).

**Answers:**

> 31. `SELECT name, reverse(name) FROM employees;`
> 32. `SELECT name, split_part(name, ' ', 1) FROM employees;`
> 33. `SELECT name, now()::date - hired FROM employees;`
> 34. `SELECT e1.name, e2.name FROM employees e1, employees e2 WHERE e1.id<e2.id AND to_char(hired,'MM-DD')=to_char(e2.hired,'MM-DD');`
> 35. `SELECT to_char(hired,'YYYY-MM') FROM employees;`
> 36. `SELECT to_char('2024-11-06'::date, 'Day');`
> 37. `SELECT hired + interval '3 months' FROM employees;`
> 38. `SELECT upper(trim(department)) FROM employees;`
> 39. `SELECT split_part(email,'@',2) dom, count(*) FROM users WHERE email IS NOT NULL GROUP BY 1;`
> 40. `SELECT replace(department,'Engineering','Eng') FROM employees;`

---

## 28.5 Window Functions

```sql
-- SETUP
CREATE TABLE sales (id int PRIMARY KEY, region text, day date, amount numeric);
INSERT INTO sales VALUES
 (1,'EU','2024-01-01',100),(2,'EU','2024-01-02',150),(3,'EU','2024-01-03',200),
 (4,'US','2024-01-01',50),(5,'US','2024-01-02',300),(6,'US','2024-01-03',250);
```

41. Rank each region's daily sales by amount (RANK).
42. Row number per region, day 1, 2, 3.
43. 3-day running total of sales per region.
44. Difference in amount vs the previous day within the same region (LAG).
45. 7-day moving average per region (ROWS frame, 3 days).
46. Top 2 regions per day by amount.
47. Percent of daily total that each region contributed on a given day.
48. NTILE(2) across all sales ordered by amount.
49. The region with the biggest day-over-day drop.
50. For each region, first and last day of sales (FIRST_VALUE/LAST_VALUE with full frame).

**Answers:**

> 41. `SELECT region, day, amount, RANK() OVER (PARTITION BY region ORDER BY amount DESC) FROM sales;`
> 42. `SELECT region, day, ROW_NUMBER() OVER (PARTITION BY region ORDER BY day) FROM sales;`
> 43. `SELECT region, day, SUM(amount) OVER (PARTITION BY region ORDER BY day ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) FROM sales;`
> 44. `SELECT region, day, amount - LAG(amount,1) OVER (PARTITION BY region ORDER BY day) delta FROM sales;`
> 45. `SELECT region, day, AVG(amount) OVER (PARTITION BY region ORDER BY day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) FROM sales;`
> 46. `SELECT * FROM (SELECT day, region, amount, ROW_NUMBER() OVER (PARTITION BY day ORDER BY amount DESC) rn FROM sales) t WHERE rn<=2;`
> 47. `SELECT s.*, 100.0*amount/SUM(amount) OVER (PARTITION BY day) pct FROM sales s;`
> 48. `SELECT region, amount, NTILE(2) OVER (ORDER BY amount DESC) FROM sales;`
> 49. `SELECT region, day, delta FROM (SELECT region, day, amount-LAG(amount) OVER (PARTITION BY region ORDER BY day) delta FROM sales) t WHERE delta IS NOT NULL ORDER BY delta ASC LIMIT 1;`
> 50. `SELECT region, FIRST_VALUE(day) OVER w, LAST_VALUE(day) OVER w FROM sales WINDOW w AS (PARTITION BY region ORDER BY day ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING);`

---

## 28.6 CTEs and Subqueries

51. Compute month-over-month revenue change using a CTE.
52. Find the top 3 spenders per region without `LIMIT` in a subquery (use `DENSE_RANK`).
53. Recursively list an org hierarchy (employees.manager_id).
54. Identify employees earning above *their department's* average using a correlated subquery.
55. Same as 54 but with a window function (`AVG() OVER (PARTITION BY ...)`).
56. For each region, find the single best day (amount max) — use `QUALIFY`-style filter with `RANK` (or CTE).
57. Generate a report: for each region, total and share of overall total.
58. `UNION` two report columns into one "metrics" table.
59. Use `EXISTS` to find regions with at least one sale above 200.
60. Use `NOT EXISTS` to find regions with no sales in a given month.

**Answers:**

> 51. `WITH m AS (SELECT to_char(day,'YYYY-MM') mon, SUM(amount) rev FROM sales GROUP BY 1) SELECT mon, rev, LAG(rev) OVER (ORDER BY mon) prev, rev - LAG(rev) OVER (ORDER BY mon) delta FROM m;`
> 52. `SELECT * FROM (SELECT region, user, sum, DENSE_RANK() OVER (PARTITION BY region ORDER BY sum DESC) rn FROM (SELECT region, user, SUM(amount) sum FROM orders GROUP BY region, user) t) x WHERE rn<=3;`
> 53. `WITH RECURSIVE tree(id, manager, depth) AS (SELECT id, manager_id, 0 FROM employees WHERE manager_id IS NULL UNION ALL SELECT e.id, e.manager_id, t.depth+1 FROM employees e JOIN tree t ON e.manager_id=t.id) SELECT * FROM tree;`
> 54. `SELECT name FROM employees e WHERE salary > (SELECT AVG(salary) FROM employees WHERE department=e.department);`
> 55. `SELECT name, salary FROM (SELECT *, AVG(salary) OVER (PARTITION BY department) d_avg FROM employees) t WHERE salary > d_avg;`
> 56. `SELECT * FROM (SELECT day, region, amount, RANK() OVER (PARTITION BY region ORDER BY amount DESC) rn FROM sales) t WHERE rn=1;`
> 57. `WITH t AS (SELECT region, SUM(amount) s FROM sales GROUP BY region) SELECT region, s, 100.0*s/(SELECT SUM(s) FROM t) share FROM t;`
> 58. `SELECT 'total' metric, region, SUM(amount) v FROM sales GROUP BY region UNION ALL SELECT 'avg', region, AVG(amount) FROM sales GROUP BY region;`
> 59. `SELECT DISTINCT region FROM sales WHERE amount>200;  -- or EXISTS form`
> 60. `SELECT DISTINCT r.region FROM regions r WHERE NOT EXISTS (SELECT 1 FROM sales s WHERE s.region=r.region AND to_char(s.day,'YYYY-MM')='2024-01');`

---

## 28.7 Advanced Data Types (JSONB, Arrays, Ranges)

```sql
-- SETUP
CREATE TABLE events (id int PRIMARY KEY, metadata jsonb, tags text[], day date);
INSERT INTO events VALUES
 (1,'{"source":"web","city":"NYC"}','{error,critical}','2024-01-01'),
 (2,'{"source":"mobile","city":"LA"}','{info}','2024-01-02'),
 (3,'{"source":"web","city":"SF"}','{error}','2024-01-03');
```

61. Filter events where metadata.source = 'web'.
62. Count events per source (jsonb key value).
63. Find events whose tags contain both 'error' and 'critical'.
64. Get all tags across all events (unnest, distinct).
65. Create a GIN index on metadata and tags.
66. Create a `tsrange` of active hours and test overlap with a booking.
67. Use `jsonb_array_elements` to flatten an array of jsonb objects.
68. Generate 30 days of dates from a start date.
69. Build a jsonb object from row columns using `jsonb_build_object`.
70. Find the largest array length in `tags`.

**Answers:**

> 61. `SELECT * FROM events WHERE metadata->>'source'='web';`
> 62. `SELECT metadata->>'source' src, count(*) FROM events GROUP BY 1;`
> 63. `SELECT * FROM events WHERE tags @> ARRAY['error','critical'];`
> 64. `SELECT DISTINCT unnest(tags) FROM events;`
> 65. `CREATE INDEX ON events USING gin(metadata); CREATE INDEX ON events USING gin(tags);`
> 66. `SELECT tsrange('09:00','17:00') && tsrange('16:00','22:00');`
> 67. `SELECT e.* FROM events, jsonb_array_elements(metadata->'items') e;`
> 68. `SELECT generate_series('2024-01-01'::date,'2024-01-30','1 day')::date;`
> 69. `SELECT jsonb_build_object('id',id,'src',metadata->>'source') FROM events;`
> 70. `SELECT max(array_length(tags,1)) FROM events;`

---

## 28.8 DDL, Constraints, and Schemas

71. Create a `money` domain: numeric(10,2) CHECK (money > 0).
72. Create a table `invoices` using the domain and a generated `total` column.
73. Add a CHECK constraint `email ~ '.*@.*\..*'` to `users`.
74. Create a partial unique index: one active subscription per user.
75. Create an `EXCLUDE` constraint for non-overlapping booking ranges.
76. Alter `users`: add `phone`, make it NOT NULL with a default.
77. Create a view `top_users` and a materialized version with a UNIQUE index for CONCURRENTLY refresh.
78. Create a sequence and use it as a `DEFAULT`.
79. Create a composite type `point` and store it in a table.
80. Drop the objects you created, verifying dependent objects first (`pg_depend`).

**Answers:**

> 71. `CREATE DOMAIN money AS numeric(10,2) CONSTRAINT positive CHECK (VALUE > 0);`
> 72. `CREATE TABLE invoices (id int PRIMARY KEY, subtotal money, tax money, total money GENERATED ALWAYS AS (subtotal + tax) STORED);`
> 73. `ALTER TABLE users ADD CONSTRAINT email_format CHECK (email ~ '.*@.*\..*');`
> 74. `CREATE UNIQUE INDEX one_active ON subs(user_id) WHERE status='active';`
> 75. `ALTER TABLE bookings ADD CONSTRAINT no_overlap EXCLUDE USING gist (user_id WITH =, slot WITH &&);`
> 76. `ALTER TABLE users ADD COLUMN phone text NOT NULL DEFAULT '';`
> 77. `CREATE MATERIALIZED VIEW top_users AS SELECT * FROM (SELECT u.*, SUM(o.amount) s FROM users u JOIN orders o USING(user_id) GROUP BY u.id ORDER BY s DESC LIMIT 100) t; CREATE UNIQUE INDEX ON top_users(id); REFRESH MATERIALIZED VIEW CONCURRENTLY top_users;`
> 78. `CREATE SEQUENCE inv_seq; ALTER TABLE invoices ALTER id SET DEFAULT nextval('inv_seq');`
> 79. `CREATE TYPE point AS (x double precision, y double precision); CREATE TABLE pts (p point);`
> 80. `SELECT dependent FROM pg_depend WHERE refobjid = 'invoices'::regclass;` (then drop in order)

---

## 28.9 Transactions, Locks, and Concurrency

81. Write a transaction that moves $100 between two accounts atomically.
82. Use `SAVEPOINT` to isolate a failing row in a batch insert.
83. Simulate a deadlock on two sessions (A/B cross-lock).
84. `SELECT ... FOR UPDATE` on a row in session 1; try to update in session 2. Observe.
85. `SKIP LOCKED` job-queue pattern: dequeue the next unlocked job.
86. Use `pg_advisory_lock` to enforce single-flight execution.
87. Demonstrate READ COMMITTED non-repeatable read (two SELECTs in one txn with a concurrent UPDATE).
88. Demonstrate a SERIALIZABLE conflict and retry.
89. Use `idempotent` upsert: `INSERT ... ON CONFLICT DO UPDATE`.
90. `TRUNCATE ... RESTART IDENTITY CASCADE` on a test table.

**Answers:**

> 81. `BEGIN; UPDATE accounts SET bal=bal-100 WHERE id=1; UPDATE accounts SET bal=bal+100 WHERE id=2; COMMIT;`
> 82. `BEGIN; SAVEPOINT sp; INSERT ...; ROLLBACK TO sp; COMMIT;`
> 83. Session A: `LOCK t IN EXCLUSIVE MODE;` Session B: `LOCK t2 IN EXCLUSIVE MODE;` then cross-lock and observe the deadlock log.
> 84. Session 1: `SELECT * FROM accounts WHERE id=1 FOR UPDATE;` Session 2: `UPDATE accounts SET bal=0 WHERE id=1;` (blocks until commit).
> 85. `SELECT * FROM jobs WHERE status='pending' ORDER BY priority LIMIT 1 FOR UPDATE SKIP LOCKED;`
> 86. `SELECT pg_try_advisory_lock(42);` (TRUE = acquired)
> 87. Begin txn; `SELECT bal FROM accounts WHERE id=1;` (in another session `UPDATE ... COMMIT;`) then `SELECT bal ...;` (differs)
> 88. `SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;` two overlapping txns → `ERROR: could not serialize access due to concurrent update`.
> 89. `INSERT INTO users(email, name) VALUES($1,$2) ON CONFLICT(email) DO UPDATE SET name=EXCLUDED.name;`
> 90. `TRUNCATE logs RESTART IDENTITY CASCADE;`

---

## 28.10 Indexing and Performance

91. Create a composite index for `WHERE status='open' ORDER BY created_at`.
92. Create a partial index for `WHERE active = true`.
93. Create an expression index for `upper(email)` and use it in a query.
94. Build a GIN index on a jsonb column and query it.
95. Create a BRIN index on a time-ordered log table.
96. Use `CREATE INDEX CONCURRENTLY` on a live table.
97. Force an index-only scan with a `INCLUDE` column.
98. `EXPLAIN (ANALYZE, BUFFERS)` a slow query; interpret the top-cost node.
99. Use `pg_stat_statements` to find the top 5 slowest queries.
100. Rewrite a `NOT IN (subquery)` as `NOT EXISTS`.
101. Replace deep `OFFSET` pagination with keyset pagination.
102. Find and drop an unused index (check `pg_stat_user_indexes.idx_scan`).
103. `REINDEX` a bloated index.
104. Analyze a table and compare plan estimates before/after.
105. Cap a runaway query with `statement_timeout`.

**Answers:**

> 91. `CREATE INDEX ON tickets(status, created_at);`
> 92. `CREATE INDEX ON subs(user_id) WHERE active;`
> 93. `CREATE INDEX ON users(upper(email));` then `SELECT * FROM users WHERE upper(email)='A@X.COM';`
> 94. `CREATE INDEX ON events USING gin(metadata);` then `WHERE metadata @> '{"source":"web"}';`
> 95. `CREATE INDEX ON logs USING brin(ts);`
> 96. `CREATE INDEX CONCURRENTLY ON big_tbl(col);`
> 97. `CREATE INDEX ON orders(status, created_at) INCLUDE (user_id, amount);` then `EXPLAIN ANALYZE SELECT user_id, amount FROM orders WHERE status='open' AND created_at > now()-interval '1 day';`
> 98. Run the command; read `actual time` and `Buffers` on each node.
> 99. `SELECT query, calls, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 5;`
> 100. `SELECT * FROM users WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.user_id=users.id);`
> 101. `SELECT * FROM orders WHERE id > :last_seen ORDER BY id LIMIT 20;`
> 102. `SELECT indexname FROM pg_stat_user_indexes WHERE idx_scan=0;` then `DROP INDEX ...;`
> 103. `REINDEX INDEX CONCURRENTLY idx_name;`
> 104. `ANALYZE big_table;` then `EXPLAIN ANALYZE SELECT ...;`
> 105. `SET statement_timeout='10s';`

---

## 28.11 Partitions and Schemas

106. Create a range-partitioned table by month (auto-attach new months).
107. Insert 100K rows and query one month (verify partition pruning in `EXPLAIN`).
108. List-partition by region; insert rows into the right partition.
109. Drop a cold partition (instant cleanup).
110. Create a schema `analytics` and move aggregates there.
111. Use a `search_path` to qualify objects.
112. Grant read-only access to the `analytics` schema to a reporting role.
113. Create a foreign-key across two partitioned tables (child references parent).
114. Attach a partition to an existing table.
115. Detach a partition for migration.

**Answers:**

> 106. `CREATE TABLE logs(ts timestamptz) PARTITION BY RANGE(ts); CREATE TABLE logs_2024_01 PARTITION OF logs FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');`
> 107. `EXPLAIN SELECT * FROM logs WHERE ts >= '2024-01-01' AND ts < '2024-02-01';` (shows `logs_2024_01` only)
> 108. `CREATE TABLE events(region text) PARTITION BY LIST(region); CREATE TABLE events_eu PARTITION OF events FOR IN ('EU');`
> 109. `DROP TABLE logs_2020_01;`
> 110. `CREATE SCHEMA analytics; CREATE VIEW analytics.daily AS ...;`
> 111. `SET search_path = analytics, public;`
> 112. `GRANT USAGE ON SCHEMA analytics TO reporter; GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO reporter;`
> 113. `ALTER TABLE order_items ADD FOREIGN KEY (order_id) REFERENCES orders(id);` (both partitioned; PG17 supports)
> 114. `ALTER TABLE logs ATTACH PARTITION logs_2024_02;`
> 115. `ALTER TABLE logs DETACH PARTITION logs_2024_01;`

---

## 28.12 Security and Roles

116. Create a least-privilege role `app_reader` (SELECT on specific tables).
117. Create a role with `LOGIN` and `PASSWORD` (scram-sha-256).
118. Revoke a privilege you granted earlier.
119. Create a default privilege for future tables in a schema.
120. Enable RLS on a tenant table and set a policy per tenant.
121. Use `FORCE RLS` to stop the table owner bypassing policies.
122. Set a session variable `app.tenant` and use it in an RLS policy.
123. Grant `USAGE` on a sequence to a role.
124. Create a role that can only `INSERT` (no SELECT).
125. Verify a role's effective privileges with `has_table_privilege`.

**Answers:**

> 116. `CREATE ROLE app_reader NOLOGIN; GRANT SELECT ON orders, users TO app_reader;`
> 117. `CREATE ROLE deployer LOGIN PASSWORD '...' ENCRYPTED PASSWORD '...';` (PG17 uses scram by default)
> 118. `REVOKE SELECT ON orders FROM app_reader;`
> 119. `ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO reporter;`
> 120. `ALTER TABLE tenants ENABLE ROW LEVEL SECURITY; CREATE POLICY tenant_iso ON tenants USING (tenant_id = current_setting('app.tenant')::uuid);`
> 121. `ALTER TABLE tenants FORCE ROW LEVEL SECURITY;`
> 122. `SET app.tenant='...'; SELECT * FROM tenants;`
> 123. `GRANT USAGE ON SEQUENCE inv_seq TO app_writer;`
> 124. `CREATE ROLE inserter NOLOGIN; GRANT INSERT ON logs TO inserter;`
> 125. `SELECT has_table_privilege('app_reader','orders','SELECT');`

---

## 28.13 Backup, Replication, and DR

126. Take a logical dump of a database in custom format.
127. Restore a single table from that dump.
128. Take a physical base backup with `pg_basebackup`.
129. Configure WAL archiving (`archive_command`) and verify with `pg_stat_archiver`.
130. Simulate PITR: set `restore_command` + `recovery_target_time`.
131. Create a physical replication slot and monitor retention.
132. Create a logical publication/subscription for a single table.
133. Promote a standby (simulated) and verify.
134. Check replication lag from both sides.
135. Drop an inactive replication slot safely.

**Answers:**

> 126. `pg_dump -Fc shopdb > shop.dump`
> 127. `pg_restore -d shop --table=orders shop.dump`
> 128. `pg_basebackup -h db -U replicator -D /backup -X -P`
> 129. `archive_mode=on; archive_command='test ! -f /var/lib/pg_archive/%f && cp %p /var/lib/pg_archive/%f'` then `SELECT * FROM pg_stat_archiver;`
> 130. Set `restore_command`, `recovery_target_time='2026-11-05 22:31:00+00'`, start cluster → replays to target.
> 131. `SELECT pg_create_physical_replication_slot('s1');` monitor `pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)`.
> 132. `CREATE PUBLICATION p FOR TABLE t; CREATE SUBSCRIPTION s CONNECTION '...' PUBLICATION p;`
> 133. `SELECT pg_promote();`
> 134. Primary: `SELECT pg_wal_lsn_diff(sent_lsn, replay_lsn) FROM pg_stat_replication;` Standby: `SELECT pg_wal_lsn_diff(pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn());`
> 135. `SELECT pg_drop_replication_slot('s1');` (after confirming inactive)

---

## 28.14 PL/pgSQL and Functions

136. Write a PL/pgSQL function that returns the top-N orders per user.
137. Write a function with `OUT` parameters.
138. Create a function that returns a table (e.g., a series of dates).
139. Write a `BEFORE INSERT` trigger to fill `created_at` with `now()`.
140. Write a `TRIGGER` that updates a parent counter on child insert.
141. Use a `FOREIGN KEY` with a `CHECK` constraint to enforce referential actions.
142. Write a stored procedure (`CREATE PROCEDURE`) that commits a batch.
143. Use a `CASE` expression to categorize a score.
144. Use `jsonb_agg` to build a nested structure in a query.
145. Write a recursive CTE that walks a tree of categories.

**Answers:**

> 136. `CREATE FUNCTION top_n_orders(uid int, n int) RETURNS SETOF orders AS $$ SELECT * FROM orders WHERE user_id=uid ORDER BY placed_at DESC LIMIT n; $$ LANGUAGE SQL;`
> 137. `CREATE FUNCTION f(x int, OUT y int, OUT z int) AS $$ SELECT x, x*2; $$ LANGUAGE SQL;`
> 138. `CREATE FUNCTION dates(s date) RETURNS TABLE(d date) AS $$ SELECT generate_series(s, s+interval'29 days'::date, '1 day'); $$ LANGUAGE SQL;`
> 139. `CREATE FUNCTION set_ts() TRIGGER BEFORE INSERT ON t FOR EACH ROW AS $$ NEW.created_at := now(); RETURN NEW; $$ LANGUAGE plpgsql;`
> 140. `CREATE FUNCTION inc_parent() TRIGGER AFTER INSERT ON child FOR EACH ROW AS $$ UPDATE parent SET count=count+1 WHERE id=NEW.parent_id; $$ LANGUAGE plpgsql;`
> 141. `ALTER TABLE child ADD FOREIGN KEY (parent_id) REFERENCES parent(id) ON DELETE CASCADE;`
> 142. `CREATE PROCEDURE batch() LANGUAGE plpgsql AS $$ BEGIN ... COMMIT; END; $$`
> 143. `SELECT CASE WHEN s>=90 THEN 'A' WHEN s>=80 THEN 'B' ELSE 'C' END;`
> 144. `SELECT jsonb_agg(jsonb_build_object('id',id,'name',name)) FROM t;`
> 145. `WITH RECURSIVE cat AS (SELECT * FROM c WHERE parent IS NULL UNION ALL SELECT c.* FROM c JOIN cat ON c.parent=cat.id) SELECT * FROM cat;`

---

## 28.15 Expert: Multi-Table and Real-World

146. Design a schema for a many-to-many "tags on posts" with a junction table.
147. Write a query: for each post, the count of its tags.
148. Find posts that have ALL of a given list of tags (using a CTE or array overlap).
149. Design a "leaderboard" that updates a score every 10 minutes with a materialized view.
150. Implement "read-your-writes" on a read replica by checking `pg_last_wal_replay_lsn()`.
151. Design a CDC pipeline: logical slot + a consumer that updates a search index.
152. Write a query that finds "users who ordered in every month of 2024" (using `COUNT DISTINCT month`).
153. Implement "exactly-once" semantics for a job queue with `SKIP LOCKED` + a unique key.
154. Design a schema that supports both OLTP (hot) and analytics (cold) without slowing the OLTP.
155. Write a function that given a date, returns the last N weeks with their totals.

**Answers:**

> 146. `CREATE TABLE post_tags(post_id int, tag_id int, PRIMARY KEY(post_id, tag_id));`
> 147. `SELECT p.id, count(pt.tag_id) tags FROM posts p LEFT JOIN post_tags pt USING(post_id) GROUP BY p.id;`
> 148. `WITH wanted AS (SELECT unnest(ARRAY['a','b','c']) tag) SELECT post_id FROM post_tags WHERE tag IN (SELECT tag FROM wanted) GROUP BY post_id HAVING count(DISTINCT tag)=(SELECT count(*) FROM wanted);`
> 149. `CREATE MATERIALIZED VIEW lb AS SELECT user, SUM(score) FROM scores GROUP BY user ORDER BY 2 DESC; REFRESH MATERIALIZED VIEW lb;` (scheduled)
> 150. `SELECT pg_last_wal_replay_lsn() >= :commit_lsn;` (route to primary if false)
> 151. `SELECT pg_create_logical_replication_slot('cdc','wal2json');` Debezium consumes it → updates Elasticsearch.
> 152. `SELECT user, count(DISTINCT extract(month FROM placed_at)) months FROM orders WHERE placed_at::date BETWEEN '2024-01-01' AND '2024-12-31' GROUP BY user HAVING count(DISTINCT extract(month FROM placed_at))=12;`
> 153. `SELECT id FROM jobs WHERE status='pending' ORDER BY priority LIMIT 1 FOR UPDATE SKIP LOCKED;` then `UPDATE jobs SET status='processing', worker=:id WHERE id=:job_id AND status='pending';`
> 154. Partition hot table by time; archive cold to a columnar warehouse via logical replication; OLTP queries always hit one partition.
> 155. `CREATE FUNCTION week_totals(s date, n int) RETURNS TABLE(week date, total numeric) AS $$ SELECT generate_series(date_trunc('week',s-n*interval'7 days'), s, '7 days') w FROM generate_series(1,n) i, (SELECT SUM(amount) total FROM sales WHERE day>=s-n*interval'7 days') t GROUP BY 1; $$ LANGUAGE SQL;`

---

## 28.16 How to Use These Problems in Interviews

- **Warm-up:** pick 3–5 from sections 1–4 to demonstrate fluency.
- **Mid:** sections 5–8 (windows, CTEs, jsonb) for a mid-level SQL role.
- **Senior/Architect:** sections 9–15 (concurrency, performance, partitioning, DR, PL/pgSQL).
- **Always:** time-box each problem; write the query, then `EXPLAIN` it, then explain the *cost* (what it does, when it's wrong, how to verify).

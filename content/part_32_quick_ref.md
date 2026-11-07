# PART 32: SQL QUICK REFERENCE

## 1. Basic SQL Cheat Sheet

```sql
-- Create a table
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert
INSERT INTO users (email) VALUES ('alice@example.com');

-- Update
UPDATE users SET email = 'bob@example.com' WHERE id = 1;

-- Delete
DELETE FROM users WHERE id = 2;

-- Select
SELECT * FROM users WHERE created_at > '2023-01-01';
```

## 2. DDL Cheat Sheet

```sql
-- DDL Commands
CREATE DATABASE mydb;
CREATE SCHEMA myschema;
CREATE TABLE mytable (id INT PRIMARY KEY, name TEXT NOT NULL);
CREATE VIEW myview AS SELECT * FROM mytable;
CREATE INDEX myindex ON mytable (name);
ALTER TABLE mytable ADD COLUMN age INT;
ALTER TABLE mytable DROP COLUMN age;
DROP TABLE mytable;
DROP INDEX myindex;
TRUNCATE TABLE mytable;
COMMENT ON TABLE mytable IS 'My table';
```

## 3. DML Cheat Sheet

```sql
-- DML Commands
INSERT INTO mytable (id, name) VALUES (1, 'Alice');
UPDATE mytable SET name = 'Bob' WHERE id = 1;
DELETE FROM mytable WHERE id = 1;
SELECT * FROM mytable WHERE name = 'Alice';
```

## 4. JOIN Cheat Sheet

```sql
-- JOIN Types
SELECT * FROM t1 INNER JOIN t2 ON t1.id = t2.id;  -- Matching rows only
SELECT * FROM t1 LEFT JOIN t2 ON t1.id = t2.id;   -- All t1 + matching t2
SELECT * FROM t1 RIGHT JOIN t2 ON t1.id = t2.id;  -- All t2 + matching t1
SELECT * FROM t1 FULL OUTER JOIN t2 ON t1.id = t2.id;  -- All rows from both
SELECT * FROM t1 CROSS JOIN t2;  -- Cartesian product
SELECT * FROM t1 LATERAL JOIN t2 ON t2.id = t1.id;  -- Lateral join
```

## 5. Aggregate Function Cheat Sheet

```sql
-- Aggregation
SELECT COUNT(*), SUM(amount), AVG(amount), MAX(amount), MIN(amount) FROM orders;
SELECT status, COUNT(*) FROM orders GROUP BY status HAVING COUNT(*) > 10;
SELECT * FROM (
  SELECT user_id, name, email,
         ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at DESC) AS rn
  FROM users
) t WHERE rn = 1;  -- Deduplicate by user_id
```

## 6. Window Function Cheat Sheet

```sql
-- Window Functions
SELECT name, dept_id,
  ROW_NUMBER() OVER (PARTITION BY dept_id ORDER BY salary DESC) AS rn,
  RANK() OVER (PARTITION BY dept_id ORDER BY salary DESC) AS rank,
  DENSE_RANK() OVER (PARTITION BY dept_id ORDER BY salary DESC) AS d_rank,
  LAG(salary, 1) OVER (PARTITION BY dept_id ORDER BY salary DESC) AS prev_salary,
  LEAD(salary, 1) OVER (PARTITION BY dept_id ORDER BY salary DESC) AS next_salary,
  SUM(salary) OVER (PARTITION BY dept_id) AS dept_total,
  AVG(salary) OVER (PARTITION BY dept_id) AS dept_avg,
  NTILE(4) OVER (PARTITION BY dept_id ORDER BY salary DESC) AS quartile,
  FIRST_VALUE(name) OVER (PARTITION BY dept_id ORDER BY salary DESC) AS top_earner,
  LAST_VALUE(name) OVER (PARTITION BY dept_id ORDER BY salary DESC) AS low_earner,
  NTH_VALUE(name, 2) OVER (PARTITION BY dept_id ORDER BY salary DESC) AS second_earner
FROM employees;
```

## 7. Date/Time Cheat Sheet

```sql
-- Date/Time Functions
SELECT now(), CURRENT_DATE, CURRENT_TIME, CURRENT_TIMESTAMP;
SELECT '2023-01-15'::date + INTERVAL '1 day' AS next_day;
SELECT now() AT TIME ZONE 'America/New_York' AS ny_time;
SELECT date_part('year', now()) AS year,
       date_part('month', now()) AS month,
       date_part('day', now()) AS day;
SELECT DATE_TRUNC('month', now()) AS start_of_month;
SELECT AGE('1990-01-15', now()) AS age;
SELECT make_date(2023, 1, 15) AS my_date;
SELECT to_timestamp('2023-01-15 10:00:00', 'YYYY-MM-DD HH24:MI:SS') AS ts;
```

## 8. JSONB Cheat Sheet

```sql
-- JSONB Operators
SELECT '{"a": 1, "b": 2}'::jsonb -> 'a' AS a;
SELECT '{"a": 1, "b": 2}'::jsonb ->> 'a' AS a;
SELECT '{"a": 1, "b": 2}'::jsonb ? 'a' AS has_a;
SELECT '{"a": 1, "b": 2}'::jsonb @> '{"a": 1}' AS contains_a;
SELECT '{"a": 1, "b": 2}'::jsonb <@ '{"a": 1}' AS contained_by;
SELECT jsonb_build_object('a', 1, 'b', 2) AS obj;
SELECT jsonb_array_elements('[1, 2, 3]'::jsonb) AS arr;
SELECT jsonb_object_keys('{"a": 1, "b": 2}'::jsonb) AS keys;
SELECT jsonb_set('{"a": 1}'::jsonb, '{a}', '2') AS set_a;
```

## 9. Indexing Cheat Sheet

```sql
-- Indexing
CREATE INDEX idx_mytable_name ON mytable (name);
CREATE UNIQUE INDEX idx_mytable_email ON mytable (email);
CREATE INDEX idx_mytable_composite ON mytable (name, age);
CREATE INDEX idx_mytable_partial ON mytable (name) WHERE active = true;
CREATE INDEX idx_mytable_expr ON mytable (lower(name));
CREATE INDEX idx_mytable_covering ON mytable (name) INCLUDE (age);
CREATE INDEX CONCURRENTLY idx_mytable_jsonb ON mytable (metadata jsonb_ops);
DROP INDEX idx_mytable_name;
REINDEX INDEX idx_mytable_name;
REINDEX TABLE mytable;
REINDEX DATABASE mydb;
```

## 10. Transaction Cheat Sheet

```sql
-- Transactions
BEGIN;
-- do some work
COMMIT;

BEGIN;
-- do some work
ROLLBACK;

BEGIN;
SAVEPOINT my_savepoint;
-- do some work
ROLLBACK TO SAVEPOINT my_savepoint;
COMMIT;

-- Isolation levels
BEGIN ISOLATION LEVEL SERIALIZABLE;
SELECT * FROM mytable;
COMMIT;

-- Locking
SELECT * FROM mytable WHERE id = 1 FOR UPDATE;
SELECT * FROM mytable WHERE id = 1 FOR SHARE;
SELECT * FROM mytable WHERE id = 1 FOR NO KEY UPDATE;
SELECT * FROM mytable WHERE id = 1 FOR KEY SHARE;
```

## 11. Administration Cheat Sheet

```sql
-- psql Meta-commands
\l  -- List databases
\c dbname  -- Connect to database
\dt  -- List tables
\d tablename  -- Describe table
\du  -- List roles
\dn  -- List schemas
\df  -- List functions
\di  -- List indexes
\dv  -- List views
\dx  -- List extensions
\timing  -- Toggle query timing
\conninfo  -- Show connection info
\password  -- Change password
\copy  -- Client-side copy

-- Shell Utilities
pg_dump -U user -d db -f backup.sql  -- Logical backup
pg_restore -U user -d db backup.sql  -- Restore
pg_dumpall -U user -f all_backup.sql  -- Backup all databases
pg_basebackup -U user -D /path/to/backup -Fp  -- Physical backup
pg_isready -U user -d db  -- Check if server is ready
createdb -U user db  -- Create database
dropdb -U user db  -- Drop database
createuser -U user newuser  -- Create user
dropuser -U user olduser  -- Drop user
vacuumdb -U user db  -- Vacuum database
reindexdb -U user db  -- Reindex database
clusterdb -U user db  -- Cluster database
pg_ctl start -D /path/to/data  -- Start server
pg_ctl stop -D /path/to/data  -- Stop server
pg_upgrade --old-bindir=... --new-bindir=...  -- Upgrade
initdb -D /path/to/data  -- Initialize cluster
```

## 12. Performance Optimization Cheat Sheet

```sql
-- EXPLAIN & EXPLAIN ANALYZE
EXPLAIN SELECT * FROM mytable WHERE id = 1;
EXPLAIN ANALYZE SELECT * FROM mytable WHERE id = 1;
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM mytable WHERE id = 1;
EXPLAIN (ANALYZE, BUFFERS, VERBOSE) SELECT * FROM mytable WHERE id = 1;

-- Query Planner
SELECT * FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 10;
SELECT query, calls, total_exec_time, mean_exec_time
FROM pg_stat_statements
ORDER BY total_exec_time DESC;

-- Statistics & Vacuum
ANALYZE mytable;
VACUUM mytable;
VACUUM ANALYZE mytable;
SELECT * FROM pg_stat_user_tables WHERE last_autovacuum IS NULL;

-- Slow Query Analysis
SELECT pid, now() - query_start AS duration, state, query
FROM pg_stat_activity
WHERE state = 'active' AND query NOT LIKE '%pg_stat_activity%'
ORDER BY duration DESC;
```

## 13. Backup & Restore Cheat Sheet

```sql
-- Logical Backups
pg_dump -U user -d db -f backup.sql  -- Plain SQL backup
pg_dump -U user -d db -Fc -f backup.dump  -- Custom format backup
pg_dumpall -U user -f all_backup.sql  -- Backup all databases

-- Physical Backups
pg_basebackup -U user -D /path/to/backup -Fp  -- Physical backup
pg_basebackup -U user -D /path/to/backup -Ft -z  -- Compressed backup

-- Restoration
pg_restore -U user -d db backup.dump  -- Restore from custom format
psql -U user -d db -f backup.sql  -- Restore from plain SQL

-- Point-in-Time Recovery (PITR)
-- 1. Configure WAL archiving
-- 2. Run pg_basebackup
-- 3. Restore base backup
-- 4. Restore WAL archives to play
```

## 14. AWS Database Cheat Sheet

```sql
-- RDS & Aurora
-- Connect to RDS
psql -h mydb.cluster-xyz.us-east-1.rds.amazonaws.com -U user -d db

-- Check Multi-AZ status
SELECT * FROM rds_instance WHERE instance_id = 'my-instance';

-- Check Read Replicas
SELECT * FROM rds_replica WHERE replica_instance_id = 'my-replica';

-- Check Performance Insights
SELECT * FROM performance_insights WHERE instance_id = 'my-instance';

-- Check RDS Proxy
SELECT * FROM rds_proxy WHERE proxy_name = 'my-proxy';
```

## 15. Most Important Interview Syntax Reference

```sql
-- Key SQL Syntax for Interviews

-- Window Functions
SELECT col,
  ROW_NUMBER() OVER (PARTITION BY pcol ORDER BY ocol) AS rn,
  RANK() OVER (PARTITION BY pcol ORDER BY ocol) AS rank,
  LAG(col, 1) OVER (PARTITION BY pcol ORDER BY ocol) AS lag,
  LEAD(col, 1) OVER (PARTITION BY pcol ORDER BY ocol) AS lead,
  SUM(col) OVER (PARTITION BY pcol ORDER BY ocol ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_sum
FROM table;

-- CTEs
WITH cte_name AS (
  SELECT * FROM table WHERE condition
)
SELECT * FROM cte_name;

-- Recursive CTE
WITH RECURSIVE cte_name AS (
  SELECT * FROM table WHERE condition
  UNION ALL
  SELECT * FROM table AS t
  JOIN cte_name AS c ON t.id = c.parent_id
)
SELECT * FROM cte_name;

-- Subqueries
SELECT * FROM table WHERE col IN (SELECT col2 FROM other_table);
SELECT * FROM table WHERE EXISTS (SELECT 1 FROM other_table WHERE other_table.id = table.id);

-- Joins
SELECT * FROM t1 INNER JOIN t2 ON t1.id = t2.id;
SELECT * FROM t1 LEFT JOIN t2 ON t1.id = t2.id;
SELECT * FROM t1 RIGHT JOIN t2 ON t1.id = t2.id;
SELECT * FROM t1 FULL OUTER JOIN t2 ON t1.id = t2.id;

-- Set Operations
SELECT col FROM t1 UNION SELECT col FROM t2;
SELECT col FROM t1 UNION ALL SELECT col FROM t2;
SELECT col FROM t1 INTERSECT SELECT col FROM t2;
SELECT col FROM t1 EXCEPT SELECT col FROM t2;

-- Aggregates
SELECT COUNT(*), SUM(col), AVG(col), MAX(col), MIN(col) FROM table;
SELECT col, COUNT(*) FROM table GROUP BY col HAVING COUNT(*) > 1;
```

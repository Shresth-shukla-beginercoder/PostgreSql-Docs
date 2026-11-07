# PART 14: LOCKING AND CONCURRENCY CONTROL

## 14.1 MVCC and Lock Modes

PostgreSQL uses **MVCC (Multi-Version Concurrency Control)**:
- Each row version has `xmin` (creating transaction) and `xmax` (deleting transaction).
- A row is visible if `xmin < current_tx_id < xmax`.

**Lock modes** (from lightest to strongest):

| Mode | Blocks | Purpose |
|---|---|---|
| **ACCESS SHARE** | No | Prevents DROP/CREATE on the table |
| **ROW SHARE** | No | Prevents `LOCK TABLE` in ROW EXCLUSIVE mode |
| **ROW EXCLUSIVE** | No | Prevents `LOCK TABLE` in ROW EXCLUSIVE or ACCESS EXCLUSIVE mode |
| **SHARE UPDATE EXCLUSIVE** | No | Prevents `LOCK TABLE` in SHARE UPDATE EXCLUSIVE, SHARE ROW EXCLUSIVE, EXCLUSIVE, or ACCESS EXCLUSIVE mode |
| **SHARE** | No | Prevents `LOCK TABLE` in SHARE ROW EXCLUSIVE, EXCLUSIVE, or ACCESS EXCLUSIVE mode |
| **SHARE ROW EXCLUSIVE** | No | Prevents `LOCK TABLE` in SHARE ROW EXCLUSIVE, EXCLUSIVE, or ACCESS EXCLUSIVE mode |
| **EXCLUSIVE** | No | Prevents `LOCK TABLE` in EXCLUSIVE or ACCESS EXCLUSIVE mode |
| **ACCESS EXCLUSIVE** | Yes | Prevents all other locks (heavyweight) |

## 14.2 Row-Level Locks

```sql
-- Exclusive lock on a row
SELECT * FROM accounts WHERE user_id = 1 FOR UPDATE;

-- Shared lock (prevents other writers but allows readers)
SELECT * FROM accounts WHERE user_id = 1 FOR SHARE;
```

**Locks are released at transaction end** (unless held by a `SAVEPOINT`).

## 14.3 Table-Level Locks

```sql
LOCK TABLE accounts IN ACCESS EXCLUSIVE MODE;
```

**Common table locks:**
- `ACCESS EXCLUSIVE`: blocks all other locks (e.g., `TRUNCATE`, `DROP TABLE`).
- `SHARE UPDATE EXCLUSIVE`: blocks `TRUNCATE`, `DROP TABLE`, `ALTER TABLE`.
- `SHARE ROW EXCLUSIVE`: blocks `TRUNCATE`, `DROP TABLE`.

## 14.4 Advisory Locks

```sql
-- Application-level locks (not tied to rows/tables)
SELECT pg_advisory_lock(42);   -- acquire
SELECT pg_try_advisory_lock(42); -- non-blocking
SELECT pg_advisory_unlock(42);
```

**Use cases:**
- Coordinate between application instances.
- Prevent duplicate background jobs.

## 14.5 FOR UPDATE / FOR SHARE / FOR NO KEY UPDATE / FOR KEY SHARE

```sql
-- Exclusive lock on matching rows
SELECT * FROM orders WHERE status = 'pending' FOR UPDATE;

-- Shared lock on matching rows
SELECT * FROM orders WHERE status = 'pending' FOR SHARE;

-- Exclusive lock only if a key column would change
UPDATE orders SET status = 'shipped' WHERE order_id = 123 FOR NO KEY UPDATE;

-- Shared lock on key only (lightest)
SELECT * FROM orders WHERE order_id = 123 FOR KEY SHARE;
```

**`FOR UPDATE` vs `FOR SHARE`:**
- `FOR UPDATE`: exclusive lock (blocks other writers).
- `FOR SHARE`: shared lock (allows other readers).

## 14.6 NOWAIT / SKIP LOCKED

```sql
-- Fail immediately if locked
SELECT * FROM jobs WHERE status = 'pending' FOR UPDATE NOWAIT LIMIT 1;

-- Skip locked rows
SELECT * FROM jobs WHERE status = 'pending' FOR UPDATE SKIP LOCKED LIMIT 5;
```

**Use cases:**
- `NOWAIT`: detect contention fast.
- `SKIP LOCKED`: job queue workers.

## 14.7 Deadlock Detection

PostgreSQL detects deadlocks and **automatically aborts one transaction** (error: `ERROR: deadlock detected`).

**Example:**

```sql
-- Tx 1
BEGIN;
UPDATE accounts SET balance = balance - 500 WHERE user_id = 1;
-- Waits for Tx 2's lock on user_id = 2
UPDATE accounts SET balance = balance + 500 WHERE user_id = 2;
COMMIT;

-- Tx 2 (runs concurrently)
BEGIN;
UPDATE accounts SET balance = balance - 300 WHERE user_id = 2;
-- Waits for Tx 1's lock on user_id = 1
UPDATE accounts SET balance = balance + 300 WHERE user_id = 1;
COMMIT;   -- Deadlock detected: aborts one tx
```

**Fix:** retry the aborted transaction.

## 14.8 Lock Escalation Misconceptions

**Myth:** PostgreSQL escalates row locks to table locks.

**Reality:** PostgreSQL does **not** escalate locks. A `FOR UPDATE` on 1000 rows holds 1000 row locks (not a table lock).

**Consequence:**
- Long-running transactions with many row locks can block other transactions.
- `VACUUM` cannot clean dead tuples if a transaction holds row locks.

## 14.9 Blocking Queries

```sql
-- Find blocking queries
SELECT blocked_locks.pid AS blocked_pid,
       blocking_locks.pid AS blocking_pid,
       blocked_activity.query AS blocked_statement,
       blocking_activity.query AS blocking_statement
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks
  ON blocking_locks.locktype = blocked_locks.locktype
  AND blocking_locks.DATABASE IS NOT DISTINCT FROM blocked_locks.DATABASE
  AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
  AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
  AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
  AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
  AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
  AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
  AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
  AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
  AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid;
```

## 14.10 Concurrent Writes

**Problem:** two transactions try to update the same row.

```sql
-- Tx 1
BEGIN;
UPDATE accounts SET balance = balance - 500 WHERE user_id = 1;
-- Waits for Tx 2's lock
COMMIT;

-- Tx 2 (runs concurrently)
BEGIN;
UPDATE accounts SET balance = balance + 300 WHERE user_id = 1;
-- Waits for Tx 1's lock
COMMIT;
```

**Fix:**
- Use `FOR UPDATE` to lock the row.
- Implement retry logic.

## 14.11 Optimistic vs Pessimistic Concurrency

| Approach | When to use |
|---|---|
| **Optimistic** | Read, check for conflicts, write (rare conflicts) |
| **Pessimistic** | Lock early (high contention) |

**PostgreSQL is pessimistic** (`FOR UPDATE`).

## 14.12 Job Queue Example

```sql
-- Worker process
BEGIN;
SELECT * FROM jobs WHERE status = 'pending'
  FOR UPDATE SKIP LOCKED LIMIT 1;
-- Process the job
UPDATE jobs SET status = 'completed' WHERE job_id = ...;
COMMIT;
```

**Key patterns:**
- `SKIP LOCKED`: skip already-locked rows.
- `LIMIT 1`: process one job at a time.
- Retry logic for conflicts.

## 14.13 Lock Monitoring Views

```sql
-- Active locks
SELECT locktype, relation::regclass, mode, transactionid, virtualtransaction, pid, granted
FROM pg_locks
WHERE NOT granted;

-- Blocking queries
SELECT blocked_locks.pid AS blocked_pid,
       blocking_locks.pid AS blocking_pid,
       blocked_activity.query AS blocked_statement,
       blocking_activity.query AS blocking_statement
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks
  ON blocking_locks.locktype = blocked_locks.locktype
  AND blocking_locks.DATABASE IS NOT DISTINCT FROM blocked_locks.DATABASE
  AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
  AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
  AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
  AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
  AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
  AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
  AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
  AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
  AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid;
```

## 14.14 Lock Troubleshooting Checklist

1. **Is the lock held by a long-running transaction?**
   ```sql
   SELECT pid, now() - query_start AS duration, query
   FROM pg_stat_activity
   WHERE state = 'active' AND query NOT LIKE '%pg_stat_activity%'
   ORDER BY duration DESC;
   ```

2. **Is the lock on a hot row?**
   ```sql
   SELECT locktype, relation::regclass, mode, transactionid, virtualtransaction, pid, granted
   FROM pg_locks
   WHERE relation = 'accounts'::regclass AND NOT granted;
   ```

3. **Is the lock a table lock?**
   ```sql
   SELECT locktype, relation::regclass, mode, transactionid, virtualtransaction, pid, granted
   FROM pg_locks
   WHERE locktype = 'relation' AND NOT granted;
   ```

4. **Is the lock a row lock?**
   ```sql
   SELECT locktype, relation::regclass, mode, transactionid, virtualtransaction, pid, granted
   FROM pg_locks
   WHERE locktype = 'tuple' AND NOT granted;
   ```

5. **Is the lock a deadlock victim?**
   ```sql
   SELECT pid, usename, application_name, client_addr, client_hostname, state, query
   FROM pg_stat_activity
   WHERE pid IN (SELECT pid FROM pg_locks WHERE NOT granted);
   ```

## 14.15 Interview-Style Quick Reference

| Question | Answer |
|---|---|
| What is MVCC? | Multi-Version Concurrency Control (row versions with xmin/xmax) |
| What is a dirty read? | Reading uncommitted data (not possible in PostgreSQL) |
| What is a non-repeatable read? | Same query returns different data (fixed by REPEATABLE READ) |
| What is a phantom read? | New rows appear in repeated queries (fixed by SERIALIZABLE) |
| What is a serialization failure? | Two transactions conflict at commit time (fixed by retry) |
| What is a lost update? | Two transactions read the same value and both update it (fixed by FOR UPDATE) |
| What is write skew? | Two transactions read the same state and write conflicting updates (fixed by SERIALIZABLE) |
| What is a deadlock? | Two transactions wait for each other's locks (PostgreSQL detects and aborts one) |
| What is a lock escalation? | PostgreSQL does not escalate locks (myth) |
| What is a blocking query? | A query waiting for a lock held by another transaction |
| What is a job queue? | A table of pending jobs processed by workers (SKIP LOCKED) |
| What is a lock mode? | A level of lock strength (ACCESS SHARE to ACCESS EXCLUSIVE) |
| What is a table lock? | A lock on the entire table (not row-level) |
| What is a row lock? | A lock on a specific row (FOR UPDATE) |
| What is an advisory lock? | An application-level lock (pg_advisory_lock) |
| What is a NOWAIT lock? | A lock that fails immediately if blocked |
| What is a SKIP LOCKED lock? | A lock that skips already-locked rows |

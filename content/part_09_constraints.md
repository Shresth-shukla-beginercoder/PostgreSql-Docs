# PART 9: CONSTRAINTS AND DATABASE INTEGRITY

## 9.1 The Six Core Constraints

| Constraint | What it enforces |
|---|---|
| **`PRIMARY KEY`** | NOT NULL + UNIQUE (on one or more columns) |
| **`FOREIGN KEY`** | Every value exists in the referenced PK/UNIQUE (or NULL, if allowed) |
| **`UNIQUE`** | No two rows share the same value (NULLs allowed multiple times by default) |
| **`NOT NULL`** | Column cannot be NULL |
| **`CHECK (expr)`** | Boolean expression must be TRUE (or NULL, i.e., not FALSE) |
| **`EXCLUDE`** | (PostgreSQL) No overlapping ranges/intervals |

### Practical examples

```sql
-- Real-world: users, orders, payments with integrity
CREATE TABLE users (
  user_id     int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  email       text NOT NULL UNIQUE,
  created_at  timestamptz NOT NULL DEFAULT now(),
  status      text NOT NULL CHECK (status IN ('active','frozen','deleted'))
);

CREATE TABLE orders (
  order_id     int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id      int NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
  total_cents  int NOT NULL CHECK (total_cents >= 0),
  status       text NOT NULL CHECK (status IN ('PENDING','PAID','SHIPPED','DELIVERED','CANCELLED')),
  placed_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE payments (
  payment_id   int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  order_id     int NOT NULL UNIQUE REFERENCES orders(order_id) ON DELETE RESTRICT,
  amount_cents int NOT NULL CHECK (amount_cents > 0),
  method       text NOT NULL,
  paid_at      timestamptz NOT NULL DEFAULT now()
);
```

## 9.2 ON DELETE / ON UPDATE Actions

| Action | Effect on child rows |
|---|---|
| `CASCADE` | Delete/update the referencing rows too |
| `RESTRICT` | Reject the parent operation if children exist (default) |
| `NO ACTION` | Check at end of statement (effectively RESTRICT unless deferred) |
| `SET NULL` | Set the FK column to NULL |
| `SET DEFAULT` | Set the FK column to its DEFAULT |

**Example (hospital domain):**

```sql
-- Deleting a doctor should NOT cascade to their patients
CREATE TABLE doctors ( doctor_id int PRIMARY KEY, name text );
CREATE TABLE patients (
  patient_id  int PRIMARY KEY,
  doctor_id   int REFERENCES doctors(doctor_id) ON DELETE RESTRICT
);

-- Deleting an appointment should remove its line items
CREATE TABLE appointments (
  appt_id int PRIMARY KEY,
  patient_id int REFERENCES patients(patient_id) ON DELETE CASCADE
);
CREATE TABLE appt_items (
  item_id int PRIMARY KEY,
  appt_id int REFERENCES appointments(appt_id) ON DELETE CASCADE
);
```

## 9.3 EXCLUSION Constraints

Prevents overlapping ranges:

```sql
-- A doctor cannot have two overlapping shifts
CREATE EXTENSION IF NOT EXISTS btree_gist;   -- required for int4/exclusion support

CREATE TABLE shifts (
  doctor_id int NOT NULL REFERENCES doctors,
  starts    timestamptz NOT NULL,
  ends      timestamptz NOT NULL,
  EXCLUDE USING gist (
    doctor_id WITH =,
    tsrange(starts, ends) WITH &&
  )
);
```

**Without `btree_gist`** (which provides a GIST operator class for `=` on ints), exclusion constraints only work on ranges/ints with appropriate support.

## 9.4 DEFERRABLE Constraints

- **`DEFERRABLE`:** the constraint is checked *at end of transaction* (not per row).
- **`INITIALLY DEFERRED`** (default for DEFERRABLE) vs **`INITIALLY IMMEDIATE`**.
- **`SET CONSTRAINTS ... DEFERRED/IMMEDIATE`:** change the timing mid-transaction.

```sql
-- Circular foreign key (account can reference another account as a guarantor)
CREATE TABLE accounts (
  acct_id int PRIMARY KEY,
  guarantor_id int REFERENCES accounts(acct_id)
             DEFERRABLE INITIALLY DEFERRED
);

BEGIN;
INSERT INTO accounts VALUES (1, 2);
INSERT INTO accounts VALUES (2, 1);
COMMIT;   -- succeeds: both rows exist at end of tx
```

## 9.5 Composite Constraints and Multi-Column Checks

```sql
-- A date range must make sense
CREATE TABLE reservations (
  res_id  int PRIMARY KEY,
  starts  date NOT NULL,
  ends    date NOT NULL,
  CHECK (ends >= starts)
);

-- Status/amount consistency
CHECK (status = 'PAID' OR amount_cents IS NULL)
```

## 9.6 Adding Constraints to Existing Tables

- **`ALTER TABLE t ADD CONSTRAINT c CHECK (...)`** validates all existing rows (can be slow; `NOT VALID` + `VALIDATE CONSTRAINT` splits it).

```sql
ALTER TABLE big_table ADD CONSTRAINT c CHECK (x > 0) NOT VALID;
ALTER TABLE big_table VALIDATE CONSTRAINT c;   -- online validation
```

## 9.7 Referential Integrity (the Big Picture)

- **`CASCADE`:** delete parent → delete children (e.g., a user's *all* sessions on delete).
- **`RESTRICT`:** cannot delete a parent while children reference it (safe default).
- **`SET NULL`:** the child's FK becomes NULL (requires `NULL` allowed).
- **`SET DEFAULT`:** the child's FK becomes the default value.

**When to use `ON DELETE CASCADE`:**
- **Yes:** transient/session data, cache, audit logs that must live as long as the parent.
- **No:** money, medical records, compliance data — use `RESTRICT` (or archive first).

## 9.8 Constraint Validation and Debugging

```sql
-- List all constraints on a table
SELECT conname, contype
FROM pg_constraint
WHERE conrelid = 'orders'::regclass;

-- Common contype codes
-- 'p' PRIMARY KEY, 'u' UNIQUE, 'f' FOREIGN KEY, 'c' CHECK, 'x' EXCLUSION, 't' TRIGGER

-- Find violations
SELECT count(*) FROM users WHERE email IS NULL;
```

**Common mistake:** a `UNIQUE` constraint with `NULL` values — by default, `NULL` is distinct from `NULL`, so two rows with `NULL` in a `UNIQUE` column are allowed. If you need "one non-deleted row per key," use a **partial unique index** (Part 11).

## 9.9 Real-World Example: Medicine Reminder App

```sql
CREATE TABLE patients (
  patient_id  int PRIMARY KEY,
  name        text NOT NULL,
  born_on     date NOT NULL,
  CHECK (born_on < now())
);

CREATE TABLE medications (
  med_id    int PRIMARY KEY,
  name      text NOT NULL UNIQUE,
  dosage_ml int NOT NULL CHECK (dosage_ml > 0)
);

CREATE TABLE doses (
  dose_id    int PRIMARY KEY,
  patient_id int NOT NULL REFERENCES patients ON DELETE CASCADE,
  med_id     int NOT NULL REFERENCES medications,
  taken_at   timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL,
  CHECK (expires_at > taken_at),
  -- A patient cannot have two active doses of the same med overlapping
  EXCLUDE USING gist (
    patient_id WITH =,
    med_id     WITH =,
    tsrange(taken_at, expires_at) WITH &&
  )
);
```

## 9.10 Interview-Style Quick Reference

| Question | Answer |
|---|---|
| Difference between UNIQUE and PRIMARY KEY? | PK = UNIQUE + NOT NULL; only one PK per table; many UNIQUEs. |
| Can you have a FOREIGN KEY on a NULL column? | Yes, unless NOT NULL is enforced. |
| What does `ON DELETE CASCADE` do? | Deletes child rows when the parent row is deleted. |
| How do you add a constraint online? | `ADD ... NOT VALID` + `VALIDATE CONSTRAINT` in two steps. |
| What is an exclusion constraint? | No overlapping values for the specified expression (uses GiST). |

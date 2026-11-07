# PART 10: DATABASE DESIGN AND NORMALIZATION

## 10.1 The Core Concepts

- **Entity:** a real-world thing (customer, order, product) — becomes a *table*.
- **Attribute:** a property (email, price) — becomes a *column*.
- **Relationship:** how entities relate — one-to-one, one-to-many, many-to-many.
- **Key:** a column (set) that uniquely identifies an entity.
- **Candidate key:** any minimal column set that uniquely identifies an entity.
- **Natural key:** a *meaningful* identifier (email, national ID).
- **Surrogate key:** an *artificial* identifier (`id`, `user_id`, `SERIAL`).

## 10.2 Relationships and Junction Tables

| Relationship | Implementation |
|---|---|
| One-to-one | One table holds the PK of the other (or a dedicated table with both as PK) |
| One-to-many | Many-side holds the FK to the one-side |
| Many-to-many | A **junction** (bridge) table with two FKs |

```sql
-- Many-to-many: users and roles
CREATE TABLE user_roles (
  user_id int REFERENCES users ON DELETE CASCADE,
  role_id int REFERENCES roles ON DELETE CASCADE,
  PRIMARY KEY (user_id, role_id)
);
```

## 10.3 Functional Dependencies and Normal Forms

- **Functional Dependency (FD):** `A → B` means knowing A determines B.
- **1NF:** no repeating groups / multi-valued attributes; all columns are atomic.
- **2NF:** 1NF + no *partial* dependencies (no non-key column depends on only *part* of a composite key).
- **3NF:** 2NF + no *transitive* dependencies (no non-key column depends on another non-key column).
- **BCNF:** every determinant is a candidate key (stronger than 3NF).
- **4NF:** no multi-valued *independent* attributes (each multi-valued fact has its own table).
- **5NF:** no *join dependencies* (a table cannot be losslessly decomposed into its projections).

**How to apply:**

1. Start in **1NF** (one table per entity, atomic columns).
2. Remove *partial* dependencies → **2NF**.
3. Remove *transitive* dependencies → **3NF**.
4. If a candidate key is not a superkey → **BCNF**.
5. Rarely: 4NF/5NF for multi-valued facts.

**Practical example: un-normalized orders table → 3NF**

```
Before (un-normalized):
  order_id, customer, customer_phone, product_list (comma-separated),
  city, city_zip

After (3NF):
  customers (customer_id PK, customer_phone)
  products  (product_id PK, name, category_id FK)
  orders    (order_id PK, customer_id FK, placed_at)
  order_items (order_id FK, product_id FK, qty, price_cents, PK(order_id, product_id))
  cities    (city_id PK, city_name, zip)
  customers... references cities (optional FK)
```

## 10.4 Denormalization (When and How)

**Why denormalize:**
- Read-heavy reporting (join cost).
- Caching slowly-changing data (e.g., a user's name in an audit table).
- Reducing N+1 joins on hot OLTP paths.

**How:**
- Add **redundant columns** (with triggers or application-level sync).
- Add **materialized views** that are refreshed periodically.
- Use **covering indexes** to make single-table reads fast.

**Rule:** never denormalize data that is *transactionally* critical (money, status) — keep the *canonical* source-of-truth in the normalized table.

## 10.5 Database Anomalies

| Anomaly | Description | How normalization fixes it |
|---|---|---|
| **Insert anomaly** | Cannot add a row unless related rows exist | Split the table (3NF) |
| **Update anomaly** | Must update many rows to stay consistent | Single-table 3NF |
| **Delete anomaly** | Deleting one row loses unrelated data | Separate the facts |

**Example (before 3NF):**

```
employees (emp_id, dept, mgr_id, mgr_name)
-- mgr_name is transitively dependent on mgr_id
-- If mgr_name changes, update *all* rows with that mgr_id
-- 3NF: move mgr_name into a managers table
```

## 10.6 Schema Evolution and Migrations

- **Forward migration:** create/modify objects in order.
- **Backward (down) migration:** revert the changes (for rollback).
- **Zero-downtime:**
  1. **Expand:** add new column (with default), write to both old and new.
  2. **Migrate:** back-fill data.
  3. **Contract:** drop the old column once all writers switch to the new.
- **Tooling:** `Flyway`, `Liquibase`, `Django migrations`, `Prisma migrate`, `golang-migrate` (Part 25).

**Never** rename a column in production without a migration that writes to both names in a dual-write phase.

## 10.7 Naming Conventions (industry standard)

| Item | Convention |
|---|---|
| Table | `snake_case` plural (`user_sessions`) |
| Column | `snake_case` (`created_at`) |
| Primary key | `<singular>_id` (`user_id`) |
| Foreign key | matches the referenced PK (`customer_id` → `customers.customer_id`) |
| Index | `idx_<table>_<col1>_<col2>` (`idx_orders_user_created`) |
| Constraint | `pk_<table>` / `uq_<table>_<cols>` / `fk_<table>_<cols>` |
| View | `v_<name>` |
| Materialized view | `mv_<name>` |

## 10.8 Eight Realistic Schema Designs

Each of these is implemented in Part 26 with full SQL, indexes, and constraints. Here is the *top-level* design for each:

### 1. E-commerce

```
users(id PK, email, created_at)
products(id PK, category_id FK, name, price_cents, stock_qty)
orders(id PK, user_id FK, status, total_cents, placed_at)
order_items(order_id FK, product_id FK, qty, price_cents)
payments(id PK, order_id FK UNIQUE, amount_cents, method, paid_at)
shipments(id PK, order_id FK, tracking, shipped_at)
reviews(id PK, user_id FK, product_id FK, rating, body, created_at)
categories(id PK, name, parent_id FK NULL)
```

### 2. Hospital Management

```
doctors(id PK, name, specialty, license_no)
patients(id PK, name, born_on, mrn UNIQUE)
appointments(id PK, patient_id FK, doctor_id FK, appt_at, status)
diagnoses(id PK, patient_id FK, doctor_id FK, dx_code, dx_desc, dx_at)
prescriptions(id PK, patient_id FK, doctor_id FK, med_id FK, dose, freq, start_date, end_date)
medications(id PK, name, strength, form)
labs(id PK, patient_id FK, test_name, result, performed_at)
```

### 3. Banking

```
accounts(id PK, user_id FK, balance_cents, currency, status, opened_at)
transactions(id PK, account_id FK, amount_cents, tx_type, counterparty, tx_at, ref_id UNIQUE)
transfers(id PK, src_acct FK, dst_acct FK, amount_cents, status, created_at, completed_at)
audit_log(id PK, entity, entity_id, action, actor, at, metadata jsonb)
```

### 4. Social Media

```
users(id PK, handle UNIQUE, display_name, bio, created_at)
follows(follower_id FK, followee_id FK, created_at, PK(follower_id, followee_id))
posts(id PK, user_id FK, body, media jsonb, created_at)
comments(id PK, post_id FK, user_id FK, body, created_at)
likes(id PK, post_id FK, user_id FK, created_at, PK(post_id, user_id))
```

### 5. Inventory Management

```
warehouses(id PK, name, location)
products(id PK, sku UNIQUE, name, cost_cents)
stock(warehouse_id FK, product_id FK, qty, updated_at, PK(warehouse_id, product_id))
movements(id PK, warehouse_id FK, product_id FK, direction, qty, ref, moved_at)
```

### 6. SaaS (Multi-tenant)

```
tenants(id PK, name, plan, status, created_at)
users(id PK, tenant_id FK, email, name, role, created_at)
workspaces(id PK, tenant_id FK, name)
resources(id PK, tenant_id FK, workspace_id FK, kind, jsonb data, created_at)
```

### 7. Authentication and Authorization

```
users(id PK, email UNIQUE, password_hash, created_at, last_login_at)
roles(id PK, name UNIQUE)
user_roles(user_id FK, role_id FK, PK(user_id, role_id))
permissions(id PK, code UNIQUE, description)
role_permissions(role_id FK, permission_id FK, PK(role_id, permission_id))
sessions(id PK, user_id FK, token_hash, expires_at, created_at)
```

### 8. Online Booking

```
users(id PK, email, phone)
venues(id PK, name, capacity)
services(id PK, venue_id FK, name, duration_min, price_cents)
bookings(id PK, user_id FK, service_id FK, starts_at, status, created_at)
```

**For each design:** Part 26 gives the **ER diagram** (ASCII), the **full `CREATE TABLE`** with constraints, **index choices**, and **3–5 representative queries**.

## 10.9 Schema Diagrams (ERD notation)

```
[users] 1 ────── N [orders] 1 ────── N [order_items] N ────── 1 [products]
  │ PK user_id                        FK order_id    FK product_id
  │
  │ N
  │
[follows] N ────── 1 [users]  (the followee)
```

**Conventions:**
- `1` and `N` on each side of a line.
- **Solid diamond** for *identifying* FK (parent PK = child PK), **hollow diamond** for *non-identifying* FK.
- **`[table]`** rectangle, **`(attr)`** rounded, **`<key>`** underlined.

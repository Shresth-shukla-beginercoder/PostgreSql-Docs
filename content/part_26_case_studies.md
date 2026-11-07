# PART 26: REAL-WORLD DATABASE ARCHITECTURE CASE STUDIES

## Case Study 1: E-commerce Order System
**Goal:** Handle high volume of orders, ensure stock integrity, and process payments reliably.

### Schema Design
- `products`: id, name, price, stock_quantity (with `CHECK stock_quantity >= 0`).
- `orders`: id, user_id, status (pending, paid, shipped), total_amount, created_at.
- `order_items`: id, order_id, product_id, quantity, unit_price.

### Critical Implementation: Atomic Purchase
```sql
BEGIN;
  -- 1. Check and Update Stock
  UPDATE products SET stock_quantity = stock_quantity - 1 
  WHERE id = 123 AND stock_quantity >= 1;
  
  -- 2. Create Order (only if step 1 affected a row)
  INSERT INTO orders (user_id, status) VALUES (456, 'pending') RETURNING id;
  
  -- 3. Create Order Item
  INSERT INTO order_items (order_id, product_id, quantity) VALUES (...);
COMMIT;
```

## Case Study 2: Hospital Management System
**Goal:** Patient records, doctor availability, and appointment scheduling.

### Key Constraints
- **Exclusion Constraint:** Prevent double-booking a doctor.
```sql
-- Using GiST index for range exclusion
CREATE TABLE appointments (
    id serial primary key,
    doctor_id int,
    appointment_time tstzrange,
    EXCLUDE USING gist (doctor_id WITH =, appointment_time WITH &&)
);
```

## Case Study 3: SaaS Multi-Tenant Database
**Goal:** Isolate data for different customer companies (tenants) in a single database.

### Implementation: Row-Level Security (RLS)
```sql
-- 1. Add tenant_id to all tables
ALTER TABLE users ADD COLUMN tenant_id uuid;

-- 2. Enable RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- 3. Create Policy
CREATE POLICY tenant_isolation_policy ON users
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```
**Application logic:** The backend sets the `app.current_tenant_id` at the start of every transaction.

## Case Study 4: High-Traffic Ride Booking
**Goal:** Fast location updates and driver matching.

### Strategies
- **PostGIS:** For finding drivers within X km of a user.
- **Unlogged Tables:** For transient data (like live GPS pings) that doesn't need to survive a crash, increasing write speed.
- **BRIN Indexes:** For huge log tables where data is naturally sorted by time.

## Case Study 5: Banking Transaction Ledger
**Goal:** Immutable record of every cent moved.

### Design
- **Append-only ledger:** Never `UPDATE` a balance. Only `INSERT` new credit/debit rows.
- **Materialized View:** For calculating the current balance of all accounts nightly.
- **Audit Logging:** Using `pgaudit` to track who accessed sensitive financial tables.

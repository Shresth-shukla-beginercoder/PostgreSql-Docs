# PART 15: STORED PROCEDURES, FUNCTIONS AND TRIGGERS

## 15.1 CREATE FUNCTION

```sql
CREATE [ OR REPLACE ] FUNCTION function_name ( [ argument_name ] arg_type [, ...] )
    RETURNS return_type
    | RETURNS TABLE ( col1 type1, col2 type2 )
    | RETURNS SEQUENCE type
    { LANGUAGE plpgsql | LANGUAGE sql | LANGUAGE c | ... }
    AS $$ ... body ... $$
    [ WINDOW { [ window_name, ... ] } WINDOW { [ window_name, ... ] } ]
    [ CALLED ON NULL INPUT | RETURNS NULL ON NULL INPUT | STRICT ]
    [ VOLATILE | STABLE | IMMUTABLE ]
    [ [ NOT ] LEAKPROOF ]
    [ COST cost ]
    [ ROWS result_rows ]
    [ SET configuration_parameter = value ]
    [ AS 'library', 'symbol' ]    -- C language
```

## 15.2 Volatility Categories

| Category | Meaning | Example |
|---|---|---|
| `VOLATILE` | Output can change on each call, even with the same arguments (may use randomness, external state) | `now()`, `random()`, functions that read tables |
| `STABLE` | Same input → same output within one statement, but may vary across statements | `now()` (within a transaction is fixed), `currval()`, user-defined that only reads |
| `IMMUTABLE` | Output is a pure function of arguments | `abs(x)`, `length(s)`, user-defined without external state |

**Why it matters:**
- `IMMUTABLE` functions can be **indexed** (expression indexes on them are stable), folded at plan time, and used in partitioned-index predicates.
- `VOLATILE` functions defeat any such optimization.

## 15.3 PL/pgSQL Basics

```sql
CREATE OR REPLACE FUNCTION calculate_discount(user_id int, order_total numeric)
RETURNS numeric LANGUAGE plpgsql AS $$
DECLARE
  discount_pct numeric;
  vip boolean;
BEGIN
  SELECT is_vip INTO vip FROM users WHERE user_id = calculate_discount.user_id;

  IF order_total > 1000 THEN
    discount_pct := 0.15;
  ELSIF vip THEN
    discount_pct := 0.10;
  ELSE
    discount_pct := 0.05;
  END IF;

  RETURN order_total * (1 - discount_pct);
END;
$$;
```

## 15.4 Control Structures

```sql
-- IF/ELSIF/ELSE/END IF
IF condition THEN
  statements;
ELSIF condition THEN
  statements;
ELSE
  statements;
END IF;

-- CASE
CASE variable
  WHEN value1 THEN statements;
  WHEN value2 THEN statements;
  ELSE statements;
END CASE;

-- LOOP
LOOP
  EXIT WHEN condition;
  statements;
END LOOP;

-- WHILE
WHILE condition LOOP
  statements;
END LOOP;

-- FOR
FOR counter IN 1..10 LOOP
  statements;
END LOOP;

-- FOREACH
FOREACH item IN ARRAY [1,2,3] LOOP
  statements;
END LOOP;
```

## 15.5 Exception Handling

```sql
BEGIN
  statements;
EXCEPTION
  WHEN unique_violation THEN
    RAISE NOTICE 'Duplicate key detected';
  WHEN others THEN
    RAISE EXCEPTION 'Unexpected error: %', SQLERRM;
END;
```

## 15.6 Dynamic SQL

```sql
CREATE OR REPLACE FUNCTION execute_query(query_text text)
RETURNS SETOF record LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY EXECUTE query_text;
END;
$$;

-- Safe dynamic SQL (parameterized)
CREATE OR REPLACE FUNCTION get_user_data(user_id int)
RETURNS SETOF users LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY EXECUTE format('SELECT * FROM users WHERE user_id = %s', user_id);
END;
$$;
```

**Warning:** dynamic SQL is a security risk if not properly parameterized.

## 15.7 SETOF record vs TABLE

```sql
CREATE OR REPLACE FUNCTION get_orders(user_id int)
RETURNS SETOF orders LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY SELECT * FROM orders WHERE customer_id = user_id;
END;
$$;

-- Equivalent to:
RETURNS TABLE (order_id int, customer_id int, total_cents numeric, ...)
```

## 15.8 SECURITY DEFINER vs SECURITY INVOKER

- **`INVOKER` (default):** function runs with the *caller's* privileges.
- **`DEFINER`:** runs with the *owner's* privileges — needed for cross-tenant or elevated-privilege logic (Part 18 security). **Never** grant `DEFINER` on a function that touches `pg_class`/system catalogs unless you audit it.

```sql
CREATE OR REPLACE FUNCTION get_all_users()
RETURNS SETOF users LANGUAGE sql SECURITY DEFINER AS $$
  SELECT * FROM users;
$$;
```

## 15.9 Trigger Functions

```sql
CREATE OR REPLACE FUNCTION audit_log()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  INSERT INTO audit_log (table_name, action, old_data, new_data, changed_at)
  VALUES (TG_TABLE_NAME, TG_OP, OLD, NEW, now());
  RETURN NULL;   -- AFTER triggers must return NULL
END;
$$;

CREATE TRIGGER trg_audit_orders
  AFTER INSERT OR UPDATE OR DELETE ON orders
  FOR EACH ROW EXECUTE FUNCTION audit_log();
```

## 15.10 BEFORE vs AFTER Triggers

| Type | When it runs | Can modify NEW | Can return NULL | Use case |
|---|---|---|---|---|
| **BEFORE** | Before the statement | Yes | No | Data validation, default values |
| **AFTER** | After the statement | No | Yes | Audit logging, notifications |

## 15.11 INSTEAD OF Triggers

```sql
CREATE OR REPLACE FUNCTION update_order_status()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  UPDATE orders SET status = NEW.status WHERE order_id = NEW.order_id;
  RETURN NULL;
END;
$$;

CREATE TRIGGER trg_update_order_status
  INSTEAD OF UPDATE ON v_order_status
  FOR EACH ROW EXECUTE FUNCTION update_order_status();
```

## 15.12 Transition Tables (PostgreSQL 13+)

```sql
CREATE OR REPLACE FUNCTION log_order_changes()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  INSERT INTO order_audit (order_id, old_status, new_status, changed_at)
  SELECT order_id, old.status, new.status, now()
  FROM old, new;
  RETURN NULL;
END;
$$;

CREATE TRIGGER trg_order_audit
  AFTER UPDATE OF status ON orders
  REFERENCING OLD TABLE AS old, NEW TABLE AS new
  FOR EACH STATEMENT EXECUTE FUNCTION log_order_changes();
```

## 15.13 Event Triggers

```sql
CREATE OR REPLACE FUNCTION log_table_ddl()
RETURNS event_trigger LANGUAGE plpgsql AS $$
BEGIN
  INSERT INTO ddl_audit (event, object_type, object_name, executed_by, executed_at)
  VALUES (TG_TAG, TG_EVENT, TG_NAME, current_user, now());
END;
$$;

CREATE EVENT TRIGGER trg_log_ddl
  ON ddl_command_end
  EXECUTE FUNCTION log_table_ddl();
```

## 15.14 Practical Examples

### 1. Data Validation Trigger

```sql
CREATE OR REPLACE FUNCTION validate_order()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.total_cents < 0 THEN
    RAISE EXCEPTION 'Order total cannot be negative';
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_order
  BEFORE INSERT OR UPDATE ON orders
  FOR EACH ROW EXECUTE FUNCTION validate_order();
```

### 2. Audit Log Trigger

```sql
CREATE OR REPLACE FUNCTION audit_orders()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    INSERT INTO order_audit (order_id, action, changed_at)
    VALUES (NEW.order_id, 'INSERT', now());
  ELSIF TG_OP = 'UPDATE' THEN
    INSERT INTO order_audit (order_id, action, changed_at)
    VALUES (NEW.order_id, 'UPDATE', now());
  ELSIF TG_OP = 'DELETE' THEN
    INSERT INTO order_audit (order_id, action, changed_at)
    VALUES (OLD.order_id, 'DELETE', now());
  END IF;
  RETURN NULL;
END;
$$;

CREATE TRIGGER trg_audit_orders
  AFTER INSERT OR UPDATE OR DELETE ON orders
  FOR EACH ROW EXECUTE FUNCTION audit_orders();
```

### 3. Row-Level Security (RLS) Trigger

```sql
CREATE OR REPLACE FUNCTION enforce_tenant_isolation()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.tenant_id != current_setting('app.current_tenant')::int THEN
    RAISE EXCEPTION 'Cannot modify data from another tenant';
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_tenant_isolation
  BEFORE INSERT OR UPDATE OR DELETE ON tenant_data
  FOR EACH ROW EXECUTE FUNCTION enforce_tenant_isolation();
```

### 4. Notification Trigger

```sql
CREATE OR REPLACE FUNCTION notify_order_update()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  PERFORM pg_notify('order_update', json_build_object(
    'order_id', NEW.order_id,
    'status', NEW.status
  )::text);
  RETURN NULL;
END;
$$;

CREATE TRIGGER trg_notify_order_update
  AFTER UPDATE OF status ON orders
  FOR EACH ROW EXECUTE FUNCTION notify_order_update();
```

### 5. Soft Delete Trigger

```sql
CREATE OR REPLACE FUNCTION soft_delete()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    UPDATE orders SET deleted_at = now() WHERE order_id = OLD.order_id;
    RETURN NULL;
  ELSE
    RETURN NEW;
  END IF;
END;
$$;

CREATE TRIGGER trg_soft_delete
  INSTEAD OF DELETE ON orders
  FOR EACH ROW EXECUTE FUNCTION soft_delete();
```

## 15.15 Common Mistakes

1. **`SECURITY DEFINER` on functions touching system catalogs** → security risk.
2. **`RETURN NEW` in an AFTER trigger** → AFTER triggers must return NULL.
3. **`BEFORE INSERT` trigger that modifies the wrong column** → infinite loop.
4. **`AFTER INSERT` trigger that tries to modify the row** → error (AFTER triggers cannot modify rows).
5. **`INSTEAD OF` trigger that doesn't handle all cases** → the view becomes read-only.
6. **Dynamic SQL without proper escaping** → SQL injection.
7. **`VOLATILE` function used in an indexable context** → planner cannot use the index.
8. **`STABLE` function that actually depends on external state** → incorrect plans.
9. **`IMMUTABLE` function that actually depends on arguments** → incorrect results.
10. **`BEFORE` trigger that doesn't return NEW** → the row is not inserted/updated.

## 15.16 Interview-Style Quick Reference

| Question | Answer |
|---|---|
| What is a stored procedure? | A stored procedure is a unit of work that must be called from a client or a trigger |
| What is a function? | A function is a value-producing unit |
| What is a trigger? | A trigger is a function that runs automatically in response to a database event |
| What is a volatility category? | VOLATILE, STABLE, or IMMUTABLE (how often the function's output changes) |
| What is SECURITY DEFINER? | A function that runs with the owner's privileges (use with caution) |
| What is SECURITY INVOKER? | A function that runs with the caller's privileges (default) |
| What is a BEFORE trigger? | A trigger that runs before the statement and can modify NEW |
| What is an AFTER trigger? | A trigger that runs after the statement and cannot modify rows |
| What is an INSTEAD OF trigger? | A trigger that replaces the operation on a view |
| What is a transition table? | A table that holds the old and new values of a row (PostgreSQL 13+) |
| What is an event trigger? | A trigger that runs in response to DDL events |
| What is a dynamic SQL? | SQL built at runtime (use with caution) |
| What is a SETOF record? | A function that returns a set of rows (dynamic columns) |
| What is a TABLE return type? | A function that returns a set of rows (fixed columns) |

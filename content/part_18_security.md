# PART 18: POSTGRESQL SECURITY

## 18.1 Users and Roles

```sql
CREATE ROLE app_user WITH LOGIN PASSWORD 'secure_password';
CREATE ROLE app_admin WITH LOGIN CREATEDB CREATEROLE;
```

- **`LOGIN`** = can connect to the database.
- **`CREATEDB`** = can create databases.
- **`CREATEROLE`** = can create roles.

## 18.2 Role Inheritance

```sql
CREATE ROLE developer;
CREATE ROLE senior_developer;
GRANT developer TO senior_developer;
```

- **`GRANT role TO role`** = inheritance.
- **`GRANT role TO user`** = membership.

## 18.3 Privileges

```sql
GRANT SELECT, INSERT, UPDATE ON TABLE users TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;
GRANT ALL PRIVILEGES ON DATABASE mydb TO app_admin;
```

- **`USAGE`** on schema = can access objects in the schema.
- **`ALL PRIVILEGES`** = all privileges on the object.

## 18.4 pg_hba.conf

```
# TYPE  DATABASE        USER            ADDRESS                 METHOD
local   all             all                                     peer
host    mydb            app_user        192.168.1.0/24          scram-sha-256
hostssl mydb            app_admin       all                     scram-sha-256
```

- **`peer`** = Unix socket authentication.
- **`scram-sha-256`** = password authentication.
- **`hostssl`** = SSL-encrypted connection.

## 18.5 Authentication Methods

| Method | Description |
|---|---|
| `peer` | Unix socket authentication |
| `md5` | MD5-encrypted password |
| `scram-sha-256` | SCRAM-SHA-256 password (recommended) |
| `cert` | Client certificate authentication |
| `gss` | GSSAPI authentication |
| `ldap` | LDAP authentication |
| `radius` | RADIUS authentication |
| `pam` | PAM authentication |

## 18.6 SQL Injection

**Problem:**

```sql
-- Unsafe: string concatenation
EXECUTE format('SELECT * FROM users WHERE email = ''%s''', user_input);
```

**Fix:**

```sql
-- Safe: parameterized query
EXECUTE 'SELECT * FROM users WHERE email = $1' USING user_input;
```

## 18.7 Least Privilege

```sql
-- Least-privilege app role
CREATE ROLE app_api LOGIN PASSWORD 'change_me';
GRANT USAGE ON SCHEMA public TO app_api;
GRANT SELECT, INSERT, UPDATE ON TABLE users, orders TO app_api;
GRANT USAGE ON SEQUENCE orders_order_id_seq TO app_api;
```

## 18.8 Audit Logging

```sql
-- Enable logging
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_connections = on;
ALTER SYSTEM SET log_disconnections = on;
```

## 18.9 Row-Level Security (RLS)

```sql
CREATE TABLE tenant_data (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  tenant_id int NOT NULL,
  data jsonb NOT NULL
);

ALTER TABLE tenant_data ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON tenant_data
  USING (tenant_id = current_setting('app.current_tenant')::int);
```

## 18.10 CREATE POLICY / ALTER POLICY / DROP POLICY

```sql
CREATE POLICY tenant_isolation_policy ON tenant_data
  USING (tenant_id = current_setting('app.current_tenant')::int);

ALTER POLICY tenant_isolation_policy ON tenant_data
  FOR ALL
  USING (tenant_id = current_setting('app.current_tenant')::int);

DROP POLICY tenant_isolation_policy ON tenant_data;
```

## 18.11 FORCE ROW LEVEL SECURITY

```sql
ALTER TABLE tenant_data FORCE ROW LEVEL SECURITY;
```

## 18.12 Practical Examples

### 1. Multi-Tenant Application

```sql
-- Create a table with tenant_id
CREATE TABLE tenant_data (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  tenant_id int NOT NULL,
  data jsonb NOT NULL
);

-- Enable RLS
ALTER TABLE tenant_data ENABLE ROW LEVEL SECURITY;

-- Create a policy to enforce tenant isolation
CREATE POLICY tenant_isolation_policy ON tenant_data
  USING (tenant_id = current_setting('app.current_tenant')::int);

-- Set the current tenant
SET app.current_tenant = '1';

-- Now queries are automatically filtered by tenant_id
SELECT * FROM tenant_data;   -- Only returns rows with tenant_id = 1
```

### 2. Read-Only Reporting Role

```sql
-- Create a read-only reporting role
CREATE ROLE reports NOLOGIN;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO reports;

-- Set up default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT ON TABLES TO reports;
```

### 3. Application User with Limited Privileges

```sql
-- Create an application user
CREATE ROLE app_user WITH LOGIN PASSWORD 'secure_password';

-- Grant usage on schema
GRANT USAGE ON SCHEMA public TO app_user;

-- Grant privileges on specific tables
GRANT SELECT, INSERT, UPDATE ON TABLE users, orders TO app_user;
GRANT USAGE ON SEQUENCE orders_order_id_seq TO app_user;
```

### 4. Admin User with Full Privileges

```sql
-- Create an admin user
CREATE ROLE app_admin WITH LOGIN CREATEDB CREATEROLE PASSWORD 'admin_password';

-- Grant all privileges on the database
GRANT ALL PRIVILEGES ON DATABASE mydb TO app_admin;
```

### 5. Secure Connection with SSL

```sql
-- Configure pg_hba.conf for SSL
# TYPE  DATABASE        USER            ADDRESS                 METHOD
hostssl mydb            app_user        192.168.1.0/24          scram-sha-256

-- Connect with SSL
psql "host=db.example.com dbname=mydb user=app_user sslmode=require"
```

## 18.13 Security Best Practices

1. **Use strong passwords** (SCRAM-SHA-256).
2. **Enforce SSL/TLS** for all connections.
3. **Use least privilege** (grant only necessary privileges).
4. **Enable audit logging** (log_statement, log_connections).
5. **Use Row-Level Security (RLS)** for multi-tenant applications.
6. **Regularly review and update privileges**.
7. **Use parameterized queries** to prevent SQL injection.
8. **Monitor for suspicious activity** (pg_stat_activity, pg_locks).
9. **Keep PostgreSQL updated** with the latest security patches.
10. **Backup and test your security configuration**.

## 18.14 Common Mistakes

1. **Using `md5` for password hashing** → use `scram-sha-256`.
2. **Granting `SUPERUSER` to application users** → security risk.
3. **Not using SSL for connections** → data can be intercepted.
4. **Granting `ALL PRIVILEGES` to application users** → security risk.
5. **Not enabling RLS for multi-tenant applications** → data leakage.
6. **Not reviewing and updating privileges** → outdated permissions.
7. **Using string concatenation for queries** → SQL injection.
8. **Not monitoring for suspicious activity** → security breaches.
9. **Not keeping PostgreSQL updated** → security vulnerabilities.
10. **Not backing up and testing security configuration** → security failures.

## 18.15 Interview-Style Quick Reference

| Question | Answer |
|---|---|
| What is a role in PostgreSQL? | A role is an entity that can own database objects and have database privileges |
| What is a user in PostgreSQL? | A user is a role with the LOGIN attribute |
| What is role inheritance? | Role inheritance is the ability of one role to use the privileges of another role |
| What is a privilege? | A privilege is the right to perform a specific action on a database object |
| What is pg_hba.conf? | pg_hba.conf is the PostgreSQL host-based authentication configuration file |
| What is SQL injection? | SQL injection is a code injection technique that exploits a security vulnerability |
| What is least privilege? | Least privilege is the principle of granting the minimum privileges necessary to perform a task |
| What is Row-Level Security (RLS)? | Row-Level Security (RLS) is a feature that allows you to control access to rows in a table |
| What is CREATE POLICY? | CREATE POLICY is a command that creates a new row security policy |
| What is ALTER POLICY? | ALTER POLICY is a command that changes the definition of a row security policy |
| What is DROP POLICY? | DROP POLICY is a command that removes a row security policy |
| What is FORCE ROW LEVEL SECURITY? | FORCE ROW LEVEL SECURITY is a command that enables row security for a table and prevents it from being disabled |

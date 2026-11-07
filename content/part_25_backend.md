# PART 25: BACKEND DEVELOPMENT AND DATABASE INTEGRATION

Connecting your application to PostgreSQL correctly is as important as the database design itself.

## 1. Connection Management

### 1.1 Connection Pooling
Creating a new connection for every request is expensive (handshake, process fork).
- **Client-Side Pooling:** Libraries like `pg-pool` (Node.js), `HikariCP` (Java), or `SQLAlchemy` (Python).
- **Server-Side Pooling:** **PgBouncer**. Acts as a buffer between the app and the DB. Essential for hundreds or thousands of app instances.

### 1.2 Environment Variables
**NEVER** hardcode credentials.
```bash
# Example .env file
DATABASE_URL=postgres://user:password@localhost:5432/dbname
```

## 2. Integration by Language

### 2.1 Node.js & Express (Modern pg)
Using the `pg` library.
```javascript
const { Pool } = require('pg');
const pool = new Pool();

// Always use parameterized queries to prevent SQL injection!
const getUser = async (id) => {
  const res = await pool.query('SELECT * FROM users WHERE id = $1', [id]);
  return res.rows[0];
};
```

### 2.2 Python (Psycopg2/Psycopg3)
```python
import psycopg
# Connection
with psycopg.connect("dbname=test user=postgres") as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
```

## 3. ORM vs Raw SQL
- **ORM (Object-Relational Mapping):** Prisma, Sequelize, TypeORM, SQLAlchemy, Django ORM.
  - **Pros:** Fast development, type safety, database abstraction.
  - **Cons:** Performance overhead, "Magic" queries can be slow, hard to write complex joins.
- **Raw SQL / Query Builders (Knex, Kysely):**
  - **Pros:** Full control, maximum performance, clear understanding of what's happening.
  - **Cons:** More boilerplate, risk of SQL injection if not careful.

## 4. Database Migrations
Migrations are version control for your schema.
- **Tools:** Liquibase, Flyway, Knex Migrations, Prisma Migrate.
- **Principle:** Every schema change is a code file (`20231106_add_status_to_users.sql`). This ensures all environments (Dev, Staging, Prod) are in sync.

## 5. Performance Best Practices for Backend
1. **N+1 Query Problem:** Avoid looping over results and firing a query for each item. Use `JOIN` or `IN (...)`.
2. **Select only what you need:** Use `SELECT id, name` instead of `SELECT *`.
3. **Indexes:** Ensure columns used in `WHERE`, `JOIN`, and `ORDER BY` are indexed.
4. **Transactions:** Group related writes in a transaction to ensure data integrity.
5. **Retry Logic:** Handle transient network errors or deadlocks with exponential backoff.

## 6. Integration Testing
Use a real database for integration tests.
- **Docker:** Spin up a PostgreSQL container for your CI/CD pipeline.
- **Test Cleanup:** Wrap tests in a transaction and roll back, or truncate tables between tests.

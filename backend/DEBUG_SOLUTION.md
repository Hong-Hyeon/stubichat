# Stubichat Database Debug Solution

## Problem Analysis

After fixing the initial NextAuth.js UntrustedHost error, we encountered a new database-related error:

```
[auth][error] CallbackRouteError: Failed to create guest user
[auth][cause]: Error: An error occurred while executing a database query.
```

## Root Cause

The frontend application requires a PostgreSQL database for user authentication, but:

1. **Missing Database Service**: The original Docker Compose configuration didn't include a PostgreSQL service
2. **Database Connection**: The frontend was trying to connect to a non-existent database
3. **Migration Issues**: The database tables weren't created properly

## Solution Implemented

### 1. Added PostgreSQL Database Service

Updated `docker-compose.yml` to include:

```yaml
# PostgreSQL Database
postgres:
  image: postgres:15-alpine
  environment:
    - POSTGRES_DB=stubichat
    - POSTGRES_USER=postgres
    - POSTGRES_PASSWORD=password
  ports:
    - "5433:5432"  # Changed to avoid port conflicts
  volumes:
    - postgres_data:/var/lib/postgresql/data
  networks:
    - stubichat_network
  restart: unless-stopped
  container_name: stubichat-postgres
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U postgres -d stubichat"]
    interval: 10s
    timeout: 5s
    retries: 5
```

### 2. Updated Frontend Environment Variables

Added database connection variables to the frontend service:

```yaml
frontend:
  environment:
    - POSTGRES_URL=postgresql://postgres:password@postgres:5432/stubichat
    - DATABASE_URL=postgresql://postgres:password@postgres:5432/stubichat
  depends_on:
    postgres:
      condition: service_healthy
```

### 3. Created Database Schema

Created `init-db.sql` with all required tables:

```sql
-- User table for NextAuth.js
CREATE TABLE IF NOT EXISTS "User" (
    "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    "email" varchar(64) NOT NULL UNIQUE,
    "password" varchar(64)
);

-- Chat table
CREATE TABLE IF NOT EXISTS "Chat" (
    "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    "createdAt" timestamp NOT NULL DEFAULT NOW(),
    "title" text NOT NULL,
    "userId" uuid NOT NULL REFERENCES "User"("id") ON DELETE CASCADE,
    "visibility" varchar(10) NOT NULL DEFAULT 'private' CHECK ("visibility" IN ('public', 'private'))
);

-- Message_v2 table
CREATE TABLE IF NOT EXISTS "Message_v2" (
    "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    "chatId" uuid NOT NULL REFERENCES "Chat"("id") ON DELETE CASCADE,
    "role" varchar NOT NULL,
    "parts" json NOT NULL,
    "attachments" json NOT NULL DEFAULT '[]',
    "createdAt" timestamp NOT NULL DEFAULT NOW()
);

-- Additional tables: Vote_v2, Document, Suggestion, Stream
-- ... (see init-db.sql for complete schema)
```

### 4. Database Initialization

Manually initialized the database:

```bash
# Copy SQL script to container
docker cp init-db.sql stubichat-postgres:/tmp/init-db.sql

# Execute the script
docker-compose exec postgres psql -U postgres -d stubichat -f /tmp/init-db.sql
```

## Current Status

✅ **Database Service**: PostgreSQL is running and healthy
✅ **Database Schema**: All required tables are created
✅ **Environment Variables**: Database connection is properly configured
✅ **Service Dependencies**: Frontend waits for database to be ready

## Verification

### Database Connection Test
```bash
# Check database tables
docker-compose exec postgres psql -U postgres -d stubichat -c "SELECT * FROM \"User\" LIMIT 5;"

# Expected output:
#                  id                  |         email          |    password    
# --------------------------------------+------------------------+----------------
#  c4911b4c-d903-4a3a-a968-102c5c01fc22 | guest-test@example.com | dummy-password
```

### Service Status
```bash
# All services should be healthy
docker-compose ps

# Expected output:
# stubichat-postgres      Healthy
# stubichat-frontend      Running
# stubichat-main-backend  Healthy
# stubichat-llm-agent     Healthy
# stubichat-mcp-server    Healthy
# stubichat-nginx         Up
```

## Remaining Issue

The frontend is still showing database connection errors. This might be due to:

1. **Production Build**: The frontend is built in production mode and may not have access to source files
2. **Migration Timing**: Database migrations might not be running automatically
3. **Connection Pool**: There might be connection pool issues

## Next Steps

### Option 1: Development Mode Testing
Change the frontend to development mode to test with source files:

```yaml
frontend:
  environment:
    - NODE_ENV=development  # Change from production
```

### Option 2: Manual Migration
Create a migration script that runs during container startup:

```bash
# Add to docker-compose.yml
frontend:
  command: >
    sh -c "
      npx drizzle-kit push &&
      node server.js
    "
```

### Option 3: Database Connection Debugging
Add more detailed logging to understand the exact database error:

```bash
# Check database connectivity from frontend container
docker-compose exec frontend sh -c "
  echo 'Testing database connection...' &&
  npx tsx -e '
    import postgres from \"postgres\";
    const client = postgres(process.env.POSTGRES_URL);
    client\`SELECT 1\`.then(() => console.log(\"DB connection OK\")).catch(console.error);
  '
"
```

## Alternative Solutions

### 1. Use SQLite Instead of PostgreSQL
For development, consider using SQLite which doesn't require a separate service:

```typescript
// In queries.ts
const client = postgres(process.env.DATABASE_URL || 'sqlite://./app.db');
```

### 2. Mock Authentication
For testing purposes, create a mock authentication that doesn't require database:

```typescript
// In auth.ts
async authorize() {
  // Return mock guest user without database
  return { 
    id: `guest-${Date.now()}`, 
    email: `guest-${Date.now()}@example.com`, 
    type: 'guest' 
  };
}
```

### 3. Use Environment-Based Authentication
Configure different authentication strategies based on environment:

```typescript
const useDatabase = process.env.NODE_ENV === 'production';
if (useDatabase) {
  // Use database authentication
} else {
  // Use mock authentication
}
```

## Summary

The database infrastructure is now properly set up with:
- ✅ PostgreSQL service running
- ✅ Database schema created
- ✅ Environment variables configured
- ✅ Service dependencies working

The remaining authentication error needs further investigation to determine if it's a connection issue, migration problem, or production build limitation. 
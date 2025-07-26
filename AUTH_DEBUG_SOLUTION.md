# Stubichat Authentication Debug Solution

## Problem Analysis

The error you're encountering is:
```
[auth][error] UntrustedHost: Host must be trusted. URL was: http://localhost:3000/api/auth/callback/guest?. Read more at https://errors.authjs.dev#untrustedhost
```

This is a NextAuth.js security feature that prevents authentication callbacks from untrusted hosts in production environments.

## Root Cause

1. **Production Environment**: The frontend is running with `NODE_ENV=production` in Docker
2. **Missing Configuration**: NextAuth.js requires explicit trusted host configuration in production
3. **Missing Environment Variables**: `NEXTAUTH_URL` and `NEXTAUTH_SECRET` are not properly configured

## Solution Steps

### 1. Create Frontend Environment File

Create a `.env` file in the `frontend/` directory:

```bash
# Backend API Configuration
NEXT_PUBLIC_BACKEND_API_URL=http://localhost:8000

# Authentication Configuration (REQUIRED for NextAuth.js)
NEXTAUTH_SECRET=your-secret-key-change-in-production
NEXTAUTH_URL=http://localhost:3000

# NextAuth.js Trusted Hosts (for production)
NEXTAUTH_TRUSTED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Database Configuration (if needed)
DATABASE_URL=postgresql://postgres:password@localhost:5432/stubichat

# OpenAI Configuration (if needed for direct frontend integration)
OPENAI_API_KEY=your-openai-api-key-here
```

### 2. Update Docker Compose Configuration

The `docker-compose.yml` has been updated to include the required environment variables:

```yaml
frontend:
  environment:
    - NODE_ENV=production
    - NEXT_PUBLIC_BACKEND_API_URL=http://localhost:8000
    - NEXTAUTH_SECRET=your-secret-key-change-in-production
    - NEXTAUTH_URL=http://localhost:3000
    - NEXTAUTH_TRUSTED_HOSTS=localhost,127.0.0.1,0.0.0.0
```

### 3. Update Auth Configuration

The `auth.ts` file has been updated to include `trustHost: true`:

```typescript
export const {
  handlers: { GET, POST },
  auth,
  signIn,
  signOut,
} = NextAuth({
  ...authConfig,
  trustHost: true, // Add trusted host configuration
  providers: [
    // ... existing providers
  ],
  // ... rest of configuration
});
```

### 4. Alternative Solutions

#### Option A: Development Mode (Quick Fix)
Change the frontend environment to development mode in `docker-compose.yml`:

```yaml
frontend:
  environment:
    - NODE_ENV=development  # Change from production to development
    - NEXT_PUBLIC_BACKEND_API_URL=http://localhost:8000
```

#### Option B: Custom Trusted Hosts Configuration
Add specific trusted hosts in the auth configuration:

```typescript
export const {
  handlers: { GET, POST },
  auth,
  signIn,
  signOut,
} = NextAuth({
  ...authConfig,
  trustHost: true,
  // Or specify exact hosts:
  // trustedHosts: ['localhost', '127.0.0.1', '0.0.0.0'],
  providers: [
    // ... existing providers
  ],
});
```

## Implementation Steps

### Step 1: Stop Current Services
```bash
cd stubichat/backend
docker-compose down
```

### Step 2: Create Environment File
```bash
cd ../frontend
cp env.example .env
# Edit .env file with the configuration above
```

### Step 3: Rebuild and Start Services
```bash
cd ../backend
docker-compose up -d --build
```

### Step 4: Verify Fix
```bash
# Check frontend logs
docker-compose logs -f frontend

# Access the application
# Open http://localhost:3000 in your browser
```

## Verification

After implementing the fix, you should see:

1. **No more UntrustedHost errors** in the frontend logs
2. **Successful guest authentication** when accessing the application
3. **Proper redirect flow** for authentication callbacks

## Additional Configuration

### For Production Deployment

When deploying to production, update the environment variables:

```bash
# Production environment variables
NEXTAUTH_URL=https://your-domain.com
NEXTAUTH_SECRET=your-production-secret-key
NEXTAUTH_TRUSTED_HOSTS=your-domain.com,www.your-domain.com
```

### Security Considerations

1. **Generate a strong secret**: Use a cryptographically secure random string for `NEXTAUTH_SECRET`
2. **Limit trusted hosts**: Only include domains you control
3. **Use HTTPS**: Always use HTTPS in production

## Troubleshooting

### If the error persists:

1. **Check environment variables**:
   ```bash
   docker-compose exec frontend env | grep NEXTAUTH
   ```

2. **Verify NextAuth configuration**:
   ```bash
   docker-compose logs frontend | grep -i auth
   ```

3. **Check network connectivity**:
   ```bash
   docker-compose exec frontend curl -f http://localhost:3000/api/auth/callback/guest
   ```

### Common Issues:

1. **Port conflicts**: Ensure port 3000 is available
2. **Docker networking**: Verify containers can communicate
3. **Environment file**: Ensure `.env` file is properly formatted

## Summary

The UntrustedHost error is a security feature of NextAuth.js that requires explicit configuration in production environments. By adding the proper environment variables and configuration, the authentication system will work correctly in both development and production environments. 
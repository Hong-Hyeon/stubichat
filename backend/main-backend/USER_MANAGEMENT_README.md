# User Management System - Stubichat Backend

This document describes the comprehensive user management system implemented for the Stubichat backend, following the Factory Pattern and best practices for authentication and authorization.

## 🏗️ Architecture Overview

The user management system is built using a layered architecture with the Factory Pattern:

```
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                      │
├─────────────────────────────────────────────────────────────┤
│                  Service Layer (Factory)                    │
├─────────────────────────────────────────────────────────────┤
│                Repository Layer (Factory)                   │
├─────────────────────────────────────────────────────────────┤
│                    Database Layer                           │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

1. **Models**: SQLAlchemy 2.x models with timezone support
2. **Repositories**: Data access layer with Factory Pattern
3. **Services**: Business logic layer with Factory Pattern
4. **API Endpoints**: RESTful endpoints with validation
5. **Migrations**: Alembic for database schema management

## 🔧 Technology Stack

- **Framework**: FastAPI with async support
- **ORM**: SQLAlchemy 2.x with async support
- **Database**: PostgreSQL with asyncpg
- **Authentication**: JWT (access + refresh tokens)
- **Password Hashing**: Argon2 (preferred over bcrypt)
- **Migrations**: Alembic
- **Validation**: Pydantic with custom validators
- **Rate Limiting**: SlowAPI
- **Timezone**: Asia/Seoul (KST) consistently

## 🚀 Quick Start

### 1. Environment Setup

Create a `.env` file in the backend directory:

```bash
# Database Configuration
DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/stubichat

# Security Configuration
SECRET_KEY=your-super-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Password Configuration
PASSWORD_MIN_LENGTH=8
PASSWORD_MAX_LENGTH=128

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Timezone
TIMEZONE=Asia/Seoul
```

### 2. Database Setup

Run the database migrations:

```bash
# Navigate to the backend directory
cd stubichat/backend/main-backend

# Run migrations
alembic upgrade head
```

### 3. Seed Test Data (Optional)

Create test users for development:

```bash
# Run the seed script
python app/scripts/seed_data.py
```

### 4. Start the Server

```bash
# Start the main backend
python -m app.main
```

The server will be available at `http://localhost:8000`

## 📚 API Endpoints

### Authentication Endpoints

| Method | Endpoint | Description | Rate Limited |
|--------|----------|-------------|--------------|
| POST | `/auth/register` | Register new user | ✅ |
| POST | `/auth/login` | User login | ✅ |
| POST | `/auth/logout` | User logout | ❌ |
| POST | `/auth/refresh` | Refresh access token | ❌ |
| GET | `/auth/me` | Get current user info | ❌ |

### Request/Response Examples

#### Register User

```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!",
    "name": "John Doe"
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "User registered successfully",
  "data": {
    "tokens": {
      "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
      "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
      "token_type": "bearer",
      "expires_in": 1800
    },
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "user@example.com",
      "name": "John Doe",
      "is_active": true,
      "is_verified": false,
      "last_login_at": "2024-01-01T12:00:00+09:00",
      "created_at": "2024-01-01T12:00:00+09:00",
      "updated_at": "2024-01-01T12:00:00+09:00"
    }
  }
}
```

#### Login User

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!"
  }'
```

#### Get Current User

```bash
curl -X GET "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## 🏭 Factory Pattern Implementation

### Repository Factory

The system uses a Factory Pattern for creating repository instances:

```python
# Get repository factory
repository_factory = get_repository_factory()

# Create specific repositories
user_repo = repository_factory.create_user_repository(session)
token_repo = repository_factory.create_refresh_token_repository(session)
```

### Service Factory

Authentication services are created through a factory:

```python
# Get auth service factory
auth_service_factory = get_auth_service_factory()

# Create auth service
auth_service = auth_service_factory.create_auth_service(session)
```

## 🔐 Security Features

### Password Security

- **Hashing**: Argon2 with optimized parameters
- **Validation**: Strong password requirements
  - Minimum 8 characters
  - Maximum 128 characters
  - At least one uppercase letter
  - At least one lowercase letter
  - At least one digit
  - At least one special character

### JWT Token Security

- **Access Tokens**: Short-lived (30 minutes)
- **Refresh Tokens**: Longer-lived (7 days)
- **Token Storage**: Refresh tokens stored as hashes
- **Token Revocation**: Support for token revocation
- **Token Validation**: Comprehensive validation with proper error handling

### Rate Limiting

- **Login/Register**: 100 requests per minute per IP
- **Configurable**: Rate limits can be adjusted via environment variables

## 🗄️ Database Schema

### Users Table

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    is_verified BOOLEAN DEFAULT FALSE NOT NULL,
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);
```

### Refresh Tokens Table

```sql
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    is_revoked BOOLEAN DEFAULT FALSE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);
```

## 🧪 Testing

### Unit Tests

Run unit tests for the authentication system:

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_auth_service.py

# Run with coverage
pytest --cov=app tests/
```

### Integration Tests

Test the complete authentication flow:

```bash
# Test API endpoints
pytest tests/test_auth_api.py

# Test database operations
pytest tests/test_repositories.py
```

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:password@postgres:5432/stubichat` | Database connection string |
| `SECRET_KEY` | `your-secret-key-change-in-production` | JWT signing key |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token expiration time |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token expiration time |
| `PASSWORD_MIN_LENGTH` | `8` | Minimum password length |
| `PASSWORD_MAX_LENGTH` | `128` | Maximum password length |
| `RATE_LIMIT_REQUESTS` | `100` | Rate limit requests per window |
| `RATE_LIMIT_WINDOW` | `60` | Rate limit window in seconds |
| `TIMEZONE` | `Asia/Seoul` | Application timezone |

## 🚀 Deployment

### Docker Deployment

The system is designed to work with Docker Compose:

```yaml
services:
  main-backend:
    build: .
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/stubichat
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      - postgres
```

### Production Considerations

1. **Secret Key**: Use a strong, randomly generated secret key
2. **Database**: Use connection pooling for production
3. **HTTPS**: Always use HTTPS in production
4. **Rate Limiting**: Adjust rate limits based on your needs
5. **Monitoring**: Add logging and monitoring for authentication events

## 🔄 Migration Management

### Creating New Migrations

```bash
# Generate a new migration
alembic revision --autogenerate -m "Add new feature"

# Apply migrations
alembic upgrade head

# Rollback migrations
alembic downgrade -1
```

### Migration Best Practices

1. Always test migrations on a copy of production data
2. Use descriptive migration names
3. Include both upgrade and downgrade operations
4. Test rollback scenarios

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection**: Ensure PostgreSQL is running and accessible
2. **Migration Errors**: Check if all dependencies are installed
3. **Token Issues**: Verify secret key configuration
4. **Rate Limiting**: Check rate limit configuration

### Debug Mode

Enable debug mode for detailed error messages:

```bash
export DEBUG=true
python -m app.main
```

## 📝 API Documentation

Once the server is running, you can access:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

## 🤝 Contributing

When contributing to the user management system:

1. Follow the existing Factory Pattern architecture
2. Add comprehensive tests for new features
3. Update documentation for API changes
4. Ensure proper error handling
5. Follow the established coding standards

## 📄 License

This user management system is part of the Stubichat project and follows the same licensing terms. 
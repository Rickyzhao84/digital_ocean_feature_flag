# Feature Flag Service

A production-ready REST API for managing and evaluating feature flags with contextual rules, intelligent caching, and role-based access control.

## Features

- **🎯 Contextual Evaluation**: Evaluate flags based on user context (attributes like region, tier, user_id)
- **⚡ Intelligent Caching**: TTL-based in-memory cache with automatic invalidation
- **🔀 Multiple Rule Types**:
  - `attribute_match`: Match context attributes with "eq" (equals) or "in" (contains) operators
  - `percentage_rollout`: Deterministic percentage-based rollout using SHA256 bucketing
- **🔐 JWT Authentication**: Secure API access with scope-based authorization
- **✅ Input Validation**: Comprehensive Pydantic-based validation for all inputs
- **📊 Comprehensive Testing**: 132+ unit, integration, and security tests
- **🚀 Production-Ready**: Error handling, logging, Docker support

## Quick Start

### Prerequisites
- Python 3.12+
- PostgreSQL 13+ (or SQLite for development)
- Docker (optional)

### Installation

#### Local Setup

1. **Clone and navigate to project**
   ```bash
   cd digital_ocean_feature_flag
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your settings (especially JWT_SECRET, DATABASE_URL)
   ```

5. **Initialize database**
   ```bash
   python -c "from app.db.session import init_db; init_db()"
   ```

6. **Run server**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

Server will be available at `http://localhost:8000`

## Quick Evaluation Example

```bash
# Create a flag
curl -X POST http://localhost:8000/flags \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "dark_mode",
    "default": false,
    "rules": [{
      "rule_type": "attribute_match",
      "parameters": {
        "attribute": "subscription_tier",
        "operator": "in",
        "values": ["premium"]
      },
      "on": true,
      "priority": 10
    }]
  }'

# Evaluate the flag
curl -X POST http://localhost:8000/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "flag": "dark_mode",
    "context": {
      "user_id": "user-123",
      "subscription_tier": "premium",
      "region": "us"
    }
  }'

# Response:
# {"flag": "dark_mode", "value": true, "reason": "rule:0"}
```

## Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture, request lifecycle, component descriptions
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Deployment guide, Docker setup, production configuration  
- **[RULES.md](RULES.md)** - Rule type specifications with detailed examples
- **[API Documentation](#api-documentation)** - Endpoint details below

## API Documentation

### Authentication

All write operations require JWT authentication:

```bash
curl -H "Authorization: Bearer $JWT_TOKEN" ...
```

Generate tokens:
```python
from app.core.security import create_access_token
admin_token = create_access_token(subject="admin", scopes=["admin"])
```

### Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/flags` | - | List all flags |
| POST | `/flags` | Admin | Create flag |
| GET | `/flags/{name}` | - | Get specific flag |
| PUT | `/flags/{name}` | Admin | Update flag |
| DELETE | `/flags/{name}` | Admin | Delete flag |
| POST | `/evaluate` | - | Evaluate flag |

### Example: Create Flag with Rules

```bash
curl -X POST http://localhost:8000/flags \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "new_feature",
    "default": false,
    "rules": [
      {
        "rule_type": "attribute_match",
        "parameters": {
          "attribute": "subscription_tier",
          "operator": "in",
          "values": ["premium", "enterprise"]
        },
        "on": true,
        "priority": 10
      },
      {
        "rule_type": "percentage_rollout",
        "parameters": {
          "attribute": "user_id",
          "percentage": 25
        },
        "on": true,
        "priority": 5
      }
    ]
  }'
```

### Rule Types

#### attribute_match
Match context attributes using comparison operators.

```json
{
  "rule_type": "attribute_match",
  "parameters": {
    "attribute": "region",
    "operator": "in",
    "values": ["us", "eu"]
  },
  "on": true,
  "priority": 10
}
```

Operators: `"eq"` (equals), `"in"` (contains in list)

#### percentage_rollout
Deterministic percentage-based rollout using SHA256 bucketing.

```json
{
  "rule_type": "percentage_rollout",
  "parameters": {
    "attribute": "user_id",
    "percentage": 25
  },
  "on": true,
  "priority": 5
}
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test category
pytest tests/test_routes.py -v       # Integration tests
pytest tests/test_auth.py -v         # Security tests
pytest tests/test_evaluator.py -v    # Unit tests

# Generate coverage report
pytest tests/ --cov=app --cov-report=html
```

**Test Coverage**: 132+ tests covering:
- Route/CRUD operations
- Authentication and authorization
- Input validation and error handling
- Evaluation logic and rule matching
- Caching behavior
- Schema validation

## Configuration

### Environment Variables

```env
# Database
DATABASE_URL=sqlite:///./flag_service.db  # Dev
# DATABASE_URL=postgresql://user:pass@localhost/flags  # Prod

# Security (IMPORTANT: Change in production)
JWT_SECRET=your-secure-secret-key-min-32-chars

# Caching
CACHE_TTL_SECONDS=30

# Logging
LOG_LEVEL=INFO
```

⚠️ **Security Warning**: Never commit JWT_SECRET. Generate a strong value:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Performance

### Caching Strategy
- **Cache Hit**: < 1ms (in-memory TTL cache)
- **Cache Miss**: 10-50ms (database load + evaluation)
- **Default TTL**: 30 seconds (configurable)

### Scaling
- Single instance: suitable for < 1000 RPS
- Multi-instance: consider Redis for distributed cache
- Database: PostgreSQL recommended for production

## Troubleshooting

| Issue | Solution |
|-------|----------|
| JWT_SECRET warning | Generate strong key: `secrets.token_urlsafe(32)` |
| Database connection error | Verify DATABASE_URL and server is running |
| Flag evaluation slow | Check cache TTL, consider increase for stable flags |
| 422 Validation error | Verify request schema matches requirements (see RULES.md) |
| 403 Permission denied | Ensure JWT token has "admin" scope for write ops |

## Project Structure

```
app/
├── routes/        # API endpoints
├── services/      # Business logic (evaluator, flag_service)
├── models/        # SQLModel definitions
├── schemas/       # Pydantic validation schemas
├── cache/         # Caching layer
├── db/            # Database setup
└── core/          # Config, exceptions, security, logging

tests/
├── test_routes.py      # Integration tests
├── test_auth.py        # Security tests
├── test_evaluator.py   # Unit tests
├── test_errors.py      # Error handling
├── test_cache.py       # Cache behavior
└── test_validation.py  # Schema validation
```

## Next Steps

1. **Read [ARCHITECTURE.md](ARCHITECTURE.md)** for system design
2. **Check [RULES.md](RULES.md)** for detailed rule specifications
3. **See [DEPLOYMENT.md](DEPLOYMENT.md)** for production setup
4. **Review tests/** for more usage examples

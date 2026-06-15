# Feature Flag Service - Architecture

## System Overview

This document describes the architecture of the Feature Flag Service, a production-ready REST API for managing and evaluating feature flags with contextual rules and caching.

## Request Lifecycle Flow

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ HTTP Request
       │ (POST /evaluate or CRUD)
       ▼
┌──────────────────────────────────────────┐
│      FastAPI Route Handler              │
│  (routes/flags.py)                      │
│  - Request validation (Pydantic)        │
│  - Authorization checks                 │
└──────────┬──────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│    Service Layer                           │
│  (services/flag_service.py or             │
│   services/evaluator.py)                  │
│  - Business logic                          │
│  - Input validation                        │
│  - Exception handling                      │
└──────────┬──────────────────────────────┘
           │
           ├─────────────────┬──────────────────┐
           │                 │                  │
  (for create/update/delete) │           (for evaluate)
           │                 │                  │
           ▼                 ▼                  ▼
    ┌────────────┐    ┌──────────────┐   ┌──────────────┐
    │ Database   │    │  Cache Layer │   │  Evaluator   │
    │ (SQLModel) │    │  (FlagCache) │   │  Logic       │
    └────────────┘    └──────────────┘   └────┬─────────┘
           │                │                   │
           │         cache hit? ←──────────────┤
           │                │                   │
           │                No                  │
           │                │                   │
           └────────────────┼───────────────────┤
                            │                   │
                            Load from DB ──────┘
                            │
                            ▼
                      ┌──────────────┐
                      │  Evaluation  │
                      │  Algorithm   │
                      │  - Filter by │
                      │    priority  │
                      │  - Match     │
                      │    rules     │
                      │  - Return    │
                      │    value &   │
                      │    reason    │
                      └──────┬───────┘
                             │
                             ▼
                      ┌──────────────┐
                      │ Store result │
                      │ in cache     │
                      └──────┬───────┘
                             │
                             ▼
┌──────────────────────────────────────┐
│  HTTP Response (JSON)                  │
│  - Status code                         │
│  - Response body                       │
└──────────────────────────────────────┘
       │
       ▼
┌─────────────┐
│   Client    │
└─────────────┘
```

## Component Architecture

### 1. **API Layer** (`app/routes/flags.py`)
- **Responsibility**: HTTP request/response handling, authentication, authorization
- **Endpoints**:
  - `GET /flags` - List all flags (no auth required)
  - `POST /flags` - Create flag (requires admin JWT)
  - `GET /flags/{name}` - Get specific flag (no auth required)
  - `PUT /flags/{name}` - Update flag (requires admin JWT)
  - `DELETE /flags/{name}` - Delete flag (requires admin JWT)
  - `POST /evaluate` - Evaluate flag (no auth required)
- **Error Handling**: Catches exceptions from services and returns appropriate HTTP error responses

### 2. **Service Layer** 
#### `app/services/flag_service.py`
- **Responsibility**: CRUD operations, input validation, database transactions
- **Functions**:
  - `create_flag()` - Create new flag with validation
  - `get_flag()` - Retrieve flag by name
  - `list_flags()` - List all flags
  - `update_flag()` - Update flag and invalidate cache
  - `delete_flag()` - Delete flag and invalidate cache
- **Validation**: Flag name format, rule definitions, operator types, percentage ranges

#### `app/services/evaluator.py`
- **Responsibility**: Flag evaluation logic, rule matching, caching orchestration
- **Functions**:
  - `evaluate()` - Evaluate flag against user context
  - `_evaluate_attribute_match_rule()` - Match rules based on context attributes
  - `_evaluate_percentage_rollout_rule()` - Deterministic bucketing for percentage rollouts
  - `invalidate_flag()` - Clear flag from cache
- **Rule Types Supported**:
  - `attribute_match`: "eq" (equals) and "in" (contains) operators
  - `percentage_rollout`: Deterministic SHA256-based bucketing

### 3. **Data Layer**

#### `app/models/flag.py`
- **FeatureFlag** SQLModel:
  - `id` (int): Primary key
  - `name` (str): Unique flag name
  - `default` (bool): Default value when no rules match
  - `rules` (JSON): List of rule definitions
  - `created_at` (datetime): Creation timestamp
  - `updated_at` (datetime): Last update timestamp

#### `app/db/session.py`
- Database engine initialization
- Session management (context manager pattern)
- Supports PostgreSQL (production) or SQLite (testing)

### 4. **Caching Layer** (`app/cache/cache.py`)
- **FlagCache**: TTL-based in-memory cache using `cachetools.TTLCache`
- **TTL**: Configurable via `CACHE_TTL_SECONDS` (default: 30 seconds)
- **Key**: Flag name
- **Value**: `{"default": bool, "rules": list}`
- **Invalidation**: Triggered on flag create/update/delete
- **Limitation**: Single-instance only (no distributed caching)

### 5. **Schema Layer** (`app/schemas/flag.py`)
- **FlagCreate**: Request schema for flag creation/update
- **FlagOut**: Response schema for flag retrieval
- **EvalRequest**: Request schema for flag evaluation
- **EvalResponse**: Response schema for evaluation result
- **RuleIn**: Base rule validation model
- **AttributeMatchParameters**: Parameter validation for attribute_match rules
- **PercentageRolloutParameters**: Parameter validation for percentage_rollout rules
- **Pydantic Validators**: Input validation with detailed error messages

### 6. **Security Layer** (`app/core/security.py`)
- JWT token creation and validation
- HTTP Bearer authentication
- Scope-based authorization (admin vs user)

### 7. **Exception Handling** (`app/core/exceptions.py`)
- Custom exception classes for specific error conditions:
  - `InvalidRuleDefinitionError`
  - `InvalidContextError`
  - `InvalidPercentageError`
  - `FlagNotFoundError`
  - `DuplicateFlagError`
  - `InvalidFlagNameError`
  - `InvalidOperatorError`
  - `DatabaseError`

## Rule Evaluation Algorithm

```
1. Load flag from cache (or database if cache miss)
2. Sort rules by priority (highest first)
3. For each rule in sorted order:
   a. Validate rule structure (type, parameters)
   b. If rule_type == "attribute_match":
      - Check if context contains the attribute
      - If not, skip to next rule
      - Compare context[attribute] against rule values
      - If match, return on_state value
   c. If rule_type == "percentage_rollout":
      - Check if context contains the bucketing attribute
      - If not, skip to next rule
      - Hash attribute value using SHA256
      - Bucket = hash % 100
      - If bucket < percentage, return on_state value
   d. If invalid rule or error, skip to next rule
4. No rules matched:
   - Return flag.default value
5. Cache the flag data (with TTL)
6. Return result with reason
```

## Request/Response Examples

### Create Flag
```
POST /flags
Authorization: Bearer <jwt_token>

{
  "name": "dark_mode",
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
}

Response 200 OK:
{
  "name": "dark_mode",
  "default": false,
  "rules": [...]
}
```

### Evaluate Flag
```
POST /evaluate

{
  "flag": "dark_mode",
  "context": {
    "user_id": "user-123",
    "subscription_tier": "premium",
    "region": "us"
  }
}

Response 200 OK:
{
  "flag": "dark_mode",
  "value": true,
  "reason": "rule:0"  // First rule matched
}
```

## Cache Behavior

### Cache Hit Scenario
```
1. Flag "feature-x" is evaluated
2. Evaluator checks cache.get("feature-x")
3. Cache HIT: Returns cached data immediately
4. Evaluation proceeds with cached rule definitions
5. Cache hit count incremented
6. TTL refreshed (30 seconds from now)
```

### Cache Miss Scenario
```
1. Flag "feature-x" is evaluated for the first time
2. Evaluator checks cache.get("feature-x")
3. Cache MISS: Database query executed
4. Flag loaded from database
5. Cache entry created: cache.set("feature-x", {"default": bool, "rules": [...]})
6. Evaluation proceeds with fresh data
7. Miss count incremented
```

### Cache Invalidation
```
1. Flag updated or deleted
2. Service calls evaluator.invalidate_flag("feature-x")
3. Cache entry removed: cache.invalidate("feature-x")
4. Next evaluation will load fresh from database
```

## Error Handling Flow

```
┌─────────────────────────────────┐
│   Input Validation Error        │
│   (Pydantic)                    │
└──────────────┬──────────────────┘
               │ HTTP 422
               ▼
          ┌────────────────────┐
          │ Bad Request        │
          │ Response           │
          └────────────────────┘

┌─────────────────────────────────┐
│   Authentication Error          │
│   (Missing/Invalid JWT)         │
└──────────────┬──────────────────┘
               │ HTTP 401/403
               ▼
          ┌────────────────────┐
          │ Unauthorized       │
          │ Response           │
          └────────────────────┘

┌─────────────────────────────────┐
│   Business Logic Error          │
│   (DuplicateFlag,               │
│    FlagNotFound, etc.)          │
└──────────────┬──────────────────┘
               │ HTTP 400/404
               ▼
          ┌────────────────────┐
          │ Error Response     │
          └────────────────────┘

┌─────────────────────────────────┐
│   Database/System Error         │
│   (Connection failed,           │
│    IntegrityError, etc.)        │
└──────────────┬──────────────────┘
               │ HTTP 500
               ▼
          ┌────────────────────┐
          │ Internal Server    │
          │ Error Response     │
          └────────────────────┘
```

## Database Schema

```sql
CREATE TABLE featureflag (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) UNIQUE NOT NULL,
    default BOOLEAN DEFAULT FALSE,
    rules JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_name (name)
);
```

## Scaling Considerations

### Single Instance (Current)
- ✅ In-memory TTL cache (30s default)
- ✅ Suitable for < 1000 RPS with normal flag evaluation latency
- ❌ No distributed caching
- ❌ Cache not shared across instances

### Multi-Instance Deployment
- ❌ Each instance has its own cache
- ⚠️  Cache invalidation not propagated (stale data possible)
- 💡 **Solution**: Implement distributed cache (Redis) for cache layer

### High-Traffic Optimization
1. **Increase cache TTL**: Trade freshness for fewer DB hits
2. **Redis Cache**: Replace in-memory cache with Redis for distributed deployments
3. **Database Read Replicas**: Load balance read operations to replicas
4. **Batch Evaluation**: Evaluate multiple flags per request (future feature)
5. **Flag Analytics**: Minimal instrumentation to avoid performance impact

## Security Considerations

1. **JWT Authentication**: Required for write operations (create, update, delete)
2. **Authorization**: Admin scope enforced on delete operations
3. **Input Validation**: All inputs validated via Pydantic schemas
4. **SQL Injection**: Protected by SQLModel/SQLAlchemy ORM
5. **Rate Limiting**: Not implemented (recommended for production)
6. **CORS**: Not implemented (configure if needed)
7. **Secrets Management**: JWT_SECRET should be environment-specific, never hardcoded

## Performance Metrics

### Typical Response Times (Single Instance)
- Cache hit evaluation: < 1ms
- Cache miss (DB load + evaluation): 10-50ms
- Flag create/update/delete: 20-100ms

### Limits (Testing)
- Database connection pool: configurable
- Cache max size: configurable
- Request timeout: 30s (FastAPI default)
- JSON body size: 1MB (FastAPI default)

## Future Enhancements

1. **Distributed Caching**: Redis integration
2. **Flag Audit Trail**: Track all changes to flags
3. **Batch Evaluation**: `/evaluate-batch` endpoint
4. **Flag Dependencies**: Feature A depends on Feature B
5. **Complex Rule Logic**: AND/OR combinations
6. **Segment Targeting**: User cohort/segment rules
7. **Experimentation API**: Variant tracking
8. **Analytics Dashboard**: Flag usage metrics
9. **Database Migrations**: Alembic for schema versioning
10. **Gray Deployment**: Canary deployments with flags

# Feature Flag Service

A FastAPI-based feature-flag service with contextual evaluation, caching, and deterministic percentage rollouts.

Quick start (dev):

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run the app:

```bash
uvicorn app.main:app --reload
```

Evaluation example:

POST /evaluate

```json
{ "flag": "new-ui", "context": { "user_id": "123", "region": "us", "tier": "pro" } }
```
# digital_ocean_feature_flag
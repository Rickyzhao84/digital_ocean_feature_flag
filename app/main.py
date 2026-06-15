from fastapi import FastAPI
from app.routes import flags
from app.db.session import init_db

app = FastAPI(title="Feature Flag Service")

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "healthy"}


# Root endpoint
@app.get("/")
def root():
    return {
        "service": "Feature Flag Service",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "create_flag": "POST /flags",
            "get_flag": "GET /flags/{name}",
            "update_flag": "PUT /flags/{name}",
            "delete_flag": "DELETE /flags/{name}",
            "list_flags": "GET /flags",
            "evaluate": "POST /evaluate"
        }
    }


app.include_router(flags.router)


@app.on_event("startup")
def on_startup():
    init_db()

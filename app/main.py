from fastapi import FastAPI
from app.routes import flags
from app.db.session import init_db

app = FastAPI(title="Feature Flag Service")

app.include_router(flags.router)


@app.on_event("startup")
def on_startup():
    init_db()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
import models
from cors_config import allowed_origins
from routers import auth, jobs, shops, firebase, admin, health

# Keep automatic schema creation limited to disposable/local SQLite development.
# PostgreSQL schema changes are migration-only; startup must never mutate a deployed DB.
if engine.dialect.name == "sqlite":
    Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ERRNO API Backend",
    description="Production-ready FastAPI backend for ERRNO On-Demand Workforce Platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(shops.router)
app.include_router(firebase.router)
app.include_router(admin.router)
app.include_router(health.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db, engine, Base
import models
from routers import auth, jobs, shops, firebase

# Keep automatic schema creation limited to disposable/local SQLite development.
# PostgreSQL schema changes are migration-only; startup must never mutate a deployed DB.
if engine.dialect.name == "sqlite":
    Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ERRNO API Backend",
    description="Production-ready FastAPI backend for ERRNO On-Demand Workforce Platform",
    version="1.0.0"
)

# Enable CORS for Android client & web callers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(shops.router)
app.include_router(firebase.router)

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "message": "ERRNO Backend Server is active & operational",
            "database": "connected"
        }
    except Exception as e:
        return {
            "status": "partial_ok",
            "message": "ERRNO Backend is active",
            "database_error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

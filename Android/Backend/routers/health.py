import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "message": "ERRNO Backend Server is active & operational",
            "database": "connected",
        }
    except Exception:
        # Keep diagnostic detail in controlled server logs, not the public response.
        logger.exception("Database health check failed")
        return JSONResponse(status_code=503, content={
            "status": "partial_ok",
            "message": "ERRNO Backend is active; database is unavailable",
            "database": "unavailable",
        })

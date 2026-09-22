from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_database


app = FastAPI(title="Payment Ledger API")


@app.get("/health")
def health_check(
    database: Session = Depends(get_database),
) -> dict[str, str]:
    database.execute(text("SELECT 1"))

    return {
        "status": "healthy",
        "database": "connected",
    }
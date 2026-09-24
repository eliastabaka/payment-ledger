from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.routers.accounts import router as accounts_router
from app.routers.payments import router as payments_router

from app.database import get_database


app = FastAPI(title="Payment Ledger API")
app.include_router(accounts_router)
app.include_router(payments_router)


@app.get("/health")
def health_check(
    database: Session = Depends(get_database),
) -> dict[str, str]:
    database.execute(text("SELECT 1"))

    return {
        "status": "healthy",
        "database": "connected",
    }
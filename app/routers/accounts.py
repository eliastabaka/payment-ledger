import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_database
from app.models import Account
from app.schemas import AccountCreate, AccountResponse


router = APIRouter(
    prefix="/accounts",
    tags=["accounts"],
)


@router.post(
    "",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_account(
    account_data: AccountCreate,
    database: Session = Depends(get_database),
) -> Account:
    account = Account(
        owner_name=account_data.owner_name,
        currency=account_data.currency,
    )

    database.add(account)
    database.commit()
    database.refresh(account)

    return account


@router.get("/{account_id}", response_model=AccountResponse)
def get_account(
    account_id: uuid.UUID,
    database: Session = Depends(get_database),
) -> Account:
    account = database.get(Account, account_id)

    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    return account
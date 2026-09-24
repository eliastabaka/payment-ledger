import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_database
from app.models import Account, LedgerEntry, Payment
from app.schemas import PaymentCreate, PaymentResponse


router = APIRouter(
    prefix="/payments",
    tags=["payments"],
)


def payment_matches(
    payment: Payment,
    request: PaymentCreate,
) -> bool:
    return (
        payment.source_account_id == request.source_account_id
        and payment.destination_account_id == request.destination_account_id
        and payment.amount_pence == request.amount_pence
    )


@router.post(
    "",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_payment(
    payment_data: PaymentCreate,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=1,
            max_length=100,
        ),
    ],
    database: Session = Depends(get_database),
) -> Payment:
    if payment_data.source_account_id == payment_data.destination_account_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source and destination accounts must be different",
        )

    existing_payment = database.scalar(
        select(Payment).where(
            Payment.idempotency_key == idempotency_key
        )
    )

    if existing_payment is not None:
        if not payment_matches(existing_payment, payment_data):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency key already used for another payment",
            )

        return existing_payment

    # Lock accounts in a consistent order to reduce deadlock risk.
    accounts = database.scalars(
        select(Account)
        .where(
            Account.id.in_(
                [
                    payment_data.source_account_id,
                    payment_data.destination_account_id,
                ]
            )
        )
        .order_by(Account.id)
        .with_for_update()
    ).all()

    accounts_by_id = {account.id: account for account in accounts}

    source = accounts_by_id.get(payment_data.source_account_id)
    destination = accounts_by_id.get(payment_data.destination_account_id)

    if source is None or destination is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source or destination account not found",
        )

    if source.currency != destination.currency:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Accounts must use the same currency",
        )

    if source.balance_pence < payment_data.amount_pence:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Insufficient funds",
        )

    source.balance_pence -= payment_data.amount_pence
    destination.balance_pence += payment_data.amount_pence

    payment = Payment(
        source_account_id=source.id,
        destination_account_id=destination.id,
        amount_pence=payment_data.amount_pence,
        currency=source.currency,
        status="completed",
        idempotency_key=idempotency_key,
    )

    database.add(payment)
    database.flush()

    database.add_all(
        [
            LedgerEntry(
                payment_id=payment.id,
                account_id=source.id,
                amount_pence=-payment.amount_pence,
            ),
            LedgerEntry(
                payment_id=payment.id,
                account_id=destination.id,
                amount_pence=payment.amount_pence,
            ),
        ]
    )

    try:
        database.commit()
    except IntegrityError:
        # Handles two simultaneous requests using the same key.
        database.rollback()

        existing_payment = database.scalar(
            select(Payment).where(
                Payment.idempotency_key == idempotency_key
            )
        )

        if (
            existing_payment is not None
            and payment_matches(existing_payment, payment_data)
        ):
            return existing_payment

        raise

    database.refresh(payment)
    return payment
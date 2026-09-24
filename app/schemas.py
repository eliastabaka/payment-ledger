import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AccountCreate(BaseModel):
    owner_name: str = Field(min_length=1, max_length=100)
    currency: str = Field(default="GBP", min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str) -> str:
        return value.upper()


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_name: str
    balance_pence: int
    currency: str
    created_at: datetime

class PaymentCreate(BaseModel):
    source_account_id: uuid.UUID
    destination_account_id: uuid.UUID
    amount_pence: int = Field(gt=0)


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_account_id: uuid.UUID
    destination_account_id: uuid.UUID
    amount_pence: int
    currency: str
    status: str
    idempotency_key: str
    created_at: datetime
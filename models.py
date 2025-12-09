from datetime import date
from typing import Optional
from sqlmodel import SQLModel, Field

# -------- Purchases --------

class PurchaseBase(SQLModel):
    alloy_type: str
    purity: float
    quantity_kg: float
    price_per_kg: float
    purchase_date: date
    supplier: Optional[str] = None
    notes: Optional[str] = None

class Purchase(PurchaseBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    remaining_quantity_kg: float = 0.0

class PurchaseCreate(PurchaseBase):
    pass

# -------- Sales Targets --------

class SalesTargetBase(SQLModel):
    alloy_type: str
    target_quantity_kg: float
    month: int
    year: int

class SalesTarget(SalesTargetBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

class SalesTargetCreate(SalesTargetBase):
    pass

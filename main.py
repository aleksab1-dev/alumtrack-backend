from typing import List, Dict, Any

import pandas as pd
from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from database import create_db_and_tables, get_session
from models import Purchase, PurchaseCreate, SalesTarget, SalesTargetCreate
from optimizer import calculate_optimal_mix

app = FastAPI(title="AlumTrack Backend")

# Allow Lovable and your phone to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    create_db_and_tables()

# =========================
#       PURCHASES
# =========================

# Create a purchase
@app.post("/purchases", response_model=Purchase)
def add_purchase(data: PurchaseCreate, session: Session = Depends(get_session)):
    purchase = Purchase(**data.dict(), remaining_quantity_kg=data.quantity_kg)
    session.add(purchase)
    session.commit()
    session.refresh(purchase)
    return purchase


# List purchases
@app.get("/purchases", response_model=List[Purchase])
def list_purchases(session: Session = Depends(get_session)):
    return session.exec(select(Purchase)).all()


# Upload CSV/Excel for purchases
@app.post("/purchases/upload")
async def upload_purchase_file(file: UploadFile = File(...), session: Session = Depends(get_session)):
    fname = file.filename.lower()

    if fname.endswith(".csv"):
        df = pd.read_csv(file.file)
    elif fname.endswith(".xlsx") or fname.endswith(".xls"):
        df = pd.read_excel(file.file)
    else:
        raise HTTPException(400, "File must be CSV or Excel")

    for _, row in df.iterrows():
        p = Purchase(
            alloy_type=row["alloy_type"],
            purity=row["purity"],
            quantity_kg=row["quantity_kg"],
            price_per_kg=row["price_per_kg"],
            purchase_date=pd.to_datetime(row["purchase_date"]).date(),
            supplier=row.get("supplier"),
            notes=row.get("notes"),
            remaining_quantity_kg=row["quantity_kg"],
        )
        session.add(p)

    session.commit()
    return {"status": "ok", "rows_imported": len(df)}


# UPDATE purchase
@app.put("/purchases/{purchase_id}", response_model=Purchase)
def update_purchase(
    purchase_id: int = Path(...),
    data: PurchaseCreate = None,
    session: Session = Depends(get_session)
):
    purchase = session.get(Purchase, purchase_id)
    if not purchase:
        raise HTTPException(404, "Purchase not found")

    for key, value in data.dict().items():
        setattr(purchase, key, value)

    purchase.remaining_quantity_kg = data.quantity_kg

    session.add(purchase)
    session.commit()
    session.refresh(purchase)
    return purchase


# DELETE purchase
@app.delete("/purchases/{purchase_id}")
def delete_purchase(
    purchase_id: int,
    session: Session = Depends(get_session)
):
    purchase = session.get(Purchase, purchase_id)
    if not purchase:
        raise HTTPException(404, "Not found")

    session.delete(purchase)
    session.commit()
    return {"status": "deleted"}


# =========================
#    SALES TARGETS
# =========================

# Create a sales target
@app.post("/sales-targets", response_model=SalesTarget)
def add_target(data: SalesTargetCreate, session: Session = Depends(get_session)):
    target = SalesTarget.from_orm(data)
    session.add(target)
    session.commit()
    session.refresh(target)
    return target


# List targets (optional filters)
@app.get("/sales-targets", response_model=List[SalesTarget])
def list_targets(
    year: int | None = Query(default=None),
    month: int | None = Query(default=None),
    session: Session = Depends(get_session),
):
    q = select(SalesTarget)
    if year is not None:
        q = q.where(SalesTarget.year == year)
    if month is not None:
        q = q.where(SalesTarget.month == month)

    return session.exec(q).all()


# UPDATE sales target
@app.put("/sales-targets/{target_id}", response_model=SalesTarget)
def update_sales_target(
    target_id: int,
    data: SalesTargetCreate,
    session: Session = Depends(get_session)
):
    target = session.get(SalesTarget, target_id)
    if not target:
        raise HTTPException(404, "Sales target not found")

    for key, value in data.dict().items():
        setattr(target, key, value)

    session.add(target)
    session.commit()
    session.refresh(target)
    return target


# DELETE sales target
@app.delete("/sales-targets/{target_id}")
def delete_sales_target(
    target_id: int,
    session: Session = Depends(get_session)
):
    target = session.get(SalesTarget, target_id)
    if not target:
        raise HTTPException(404, "Not found")

    session.delete(target)
    session.commit()
    return {"status": "deleted"}


# =========================
#     INVENTORY
# =========================

@app.get("/inventory/summary")
def inventory_summary(session: Session = Depends(get_session)) -> Dict[str, Any]:
    purchases = session.exec(
        select(Purchase).where(Purchase.remaining_quantity_kg > 0)
    ).all()

    total_kg = sum(p.remaining_quantity_kg for p in purchases)
    total_value = sum(p.remaining_quantity_kg * p.price_per_kg for p in purchases)

    by_alloy: Dict[str, Dict[str, float]] = {}
    for p in purchases:
        rec = by_alloy.setdefault(
            p.alloy_type,
            {"alloy_type": p.alloy_type, "quantity_kg": 0.0, "value": 0.0},
        )
        rec["quantity_kg"] += p.remaining_quantity_kg
        rec["value"] += p.remaining_quantity_kg * p.price_per_kg

    return {
        "total_inventory_kg": total_kg,
        "total_inventory_value": total_value,
        "by_alloy": list(by_alloy.values()),
    }


# =========================
#     OPTIMIZATION
# =========================

@app.get("/optimize")
def optimize(year: int, month: int, session: Session = Depends(get_session)):
    result = calculate_optimal_mix(session, year, month)
    return result

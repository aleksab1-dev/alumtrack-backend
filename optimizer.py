from collections import defaultdict
from typing import Dict, Any, List
from sqlmodel import Session, select
from models import Purchase, SalesTarget

def calculate_optimal_mix(session: Session, year: int, month: int) -> Dict[str, Any]:
    # 1. Get targets for that month
    targets = session.exec(
        select(SalesTarget).where(SalesTarget.year == year, SalesTarget.month == month)
    ).all()

    target_by_alloy = defaultdict(float)
    for t in targets:
        target_by_alloy[t.alloy_type] += t.target_quantity_kg

    # 2. Get all inventory (purchases with remaining stock)
    purchases = session.exec(
        select(Purchase).where(Purchase.remaining_quantity_kg > 0)
    ).all()

    inventory = defaultdict(list)
    for p in purchases:
        inventory[p.alloy_type].append(p)

    result: Dict[str, Any] = {
        "optimal_mix": [],
        "to_buy": [],
        "total_cost_for_targets": 0.0,
    }

    # 3. For each alloy, use cheapest stock first
    for alloy, need_qty in target_by_alloy.items():
        left = need_qty

        batches: List[Purchase] = sorted(
            inventory.get(alloy, []),
            key=lambda x: x.price_per_kg
        )

        for b in batches:
            if left <= 0:
                break

            use = min(b.remaining_quantity_kg, left)
            if use <= 0:
                continue

            cost = use * b.price_per_kg
            result["total_cost_for_targets"] += cost

            result["optimal_mix"].append({
                "alloy_type": alloy,
                "purchase_id": b.id,
                "quantity_used_kg": use,
                "price_per_kg": b.price_per_kg,
                "cost": cost,
            })

            left -= use

        if left > 0:
            # not enough stock -> need to buy
            result["to_buy"].append({
                "alloy_type": alloy,
                "missing_quantity_kg": left,
            })

    return result

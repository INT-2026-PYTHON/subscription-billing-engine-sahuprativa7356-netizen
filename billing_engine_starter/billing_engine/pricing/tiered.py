"""
TieredPricing — different price per unit depending on the tier the quantity falls into.

This is the "cumulative" / "stacked" tier model, NOT the "volume" model:
    Tiers: [(0, 1000, ₹2.00), (1000, 5000, ₹1.50), (5000, None, ₹1.00)]
    Quantity = 6000:
        First 1000 units  @ ₹2.00 = ₹2000
        Next  4000 units  @ ₹1.50 = ₹6000
        Last  1000 units  @ ₹1.00 = ₹1000
        ------------------------------------
        Total                     = ₹9000

A tier with `to_units = None` is the open-ended top tier.

Tier boundaries are HALF-OPEN on the right: a tier (from, to, price)
covers units strictly less than `to` (i.e. [from, to)).
"""

from dataclasses import dataclass
from typing import Optional

from billing_engine.money import Money
from billing_engine.pricing.base import PricingStrategy


@dataclass(frozen=True)
class Tier:
    from_units: int
    to_units: Optional[int]   # None means "unlimited" / open-ended
    unit_price: Money


class TieredPricing(PricingStrategy):
    """Charges across multiple price tiers based on cumulative quantity."""

    def __init__(self, tiers: list[Tier]) -> None:
       if not tiers:
            raise ValueError("tiers list cannot be empty")
        for tier in tiers:
            if tier.from_units < 0:
                raise ValueError("from_units must be non-negative")
            if tier.to_units is not None and tier.to_units <= tier.from_units:
                raise ValueError("to_units must be greater than from_units")
            if tier.unit_price.is_negative():
                raise ValueError("unit_price must be non-negative")
        for i in range(1, len(tiers)):
            if tiers[i].from_units < tiers[i - 1].from_units:
               raise ValueError("tiers must be in ascending order")

        self.tiers=tiers

    def calculate(self, quantity: int) -> Money:
        if quantity < 0:
            raise ValueError("quantity must be non-negative")
        total_cost = Money(0, self.tiers[0].unit_price.currency)
        for tier in self.tiers:
            if tier.to_units is None or quantity < tier.to_units:
                units_in_tier = max(0, quantity - tier.from_units)
            else:
                units_in_tier = max(0, tier.to_units - tier.from_units)
            total_cost += units_in_tier * tier.unit_price
        return total_cost
        

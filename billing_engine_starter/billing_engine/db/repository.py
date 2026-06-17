"""
Repositories — the ONLY place SQL lives.

Each repository wraps the Database connection and exposes methods that
take/return domain dataclasses (defined in billing_engine/models/).

⚠️ YOU IMPLEMENT every method body marked TODO.
   The signatures, docstrings, and the LedgerRepository's append-only
   guarantee are already in place — do not change them.

Conventions:
  - Always use parameterized queries (`?` placeholders) — NEVER f-string SQL.
  - Money values are persisted as TEXT using `money.to_storage()`.
  - Dates are persisted as ISO strings (`date.isoformat()`).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from billing_engine.db.database import Database
from billing_engine.money import Money
from billing_engine.models import (
    Customer,
    Plan, PricingType, BillingPeriod,
    Subscription, SubscriptionStatus,
    Invoice, InvoiceStatus, InvoiceLineItem, LineItemKind,
    LedgerEntry, LedgerDirection,
)


# ============================================================
# CUSTOMERS
# ============================================================
class CustomerRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, customer: Customer) -> Customer:
        """Insert and return the customer with `id` populated."""
        # TODO Day 2
       with self.db.conn as conn:
            cursor = conn.execute(
                "INSERT INTO customers (email, name) VALUES (?, ?)",
                (customer.email, customer.name)
            )
            customer_id = cursor.lastrowid
            return Customer(id=customer_id, email=customer.email, name=customer.name)

    def get(self, customer_id: int) -> Optional[Customer]:
        # TODO Day 2
        with self.db.conn as conn:
            row = conn.execute(
                "SELECT id, email, name FROM customers WHERE id = ?",
                (customer_id,)
            ).fetchone()
            if row is None:
                return None
            return Customer(id=row[0], email=row[1], name=row[2])
        
    def find_by_email(self, email: str) -> Optional[Customer]:
        # TODO Day 2
        with self.db.conn as conn:
            row = conn.execute(
                "SELECT id, email, name FROM customers WHERE email = ?",
                (email,)
            ).fetchone()
            if row is None:
                return None
            return Customer(id=row[0], email=row[1], name=row[2])
        
    def list_all(self) -> list[Customer]:
        # TODO Day 2
        with self.db.conn as conn:
            rows = conn.execute("SELECT id, email, name FROM customers").fetchall()
            return [Customer(id=row[0], email=row[1], name=row[2]) for row in rows]


# ============================================================
# PLANS  +  PLAN TIERS
# ============================================================
class PlanRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, plan: Plan) -> Plan:
        # TODO Day 2.
        with self.db.conn as conn:
            cursor = conn.execute(
                "INSERT INTO plans (name, pricing_type, billing_period, currency) VALUES (?, ?, ?, ?)",
                (plan.name, plan.pricing_type.value, plan.billing_period.value, plan.currency)
            )
            plan_id = cursor.lastrowid
            return Plan(
                id=plan_id,
                name=plan.name,
                pricing_type=plan.pricing_type,
                billing_period=plan.billing_period,
                currency=plan.currency
            )

    def get(self, plan_id: int) -> Optional[Plan]:
        # TODO Day 2.
        with self.db.conn as conn:
            row = conn.execute(
                "SELECT id, name, pricing_type, billing_period, currency FROM plans WHERE id = ?",
                (plan_id,)
            ).fetchone()
            if row is None:
                return None
            return Plan(
                id=row[0],
                name=row[1],
                pricing_type=PricingType(row[2]),
                billing_period=BillingPeriod(row[3]),
                currency=row[4]
            )

    def list_all(self) -> list[Plan]:
        # TODO Day 2.
        with self.db.conn as conn:
            rows = conn.execute("SELECT id, name, pricing_type, billing_period, currency FROM plans").fetchall()
            return [
                Plan(
                    id=row[0],
                    name=row[1],
                    pricing_type=PricingType(row[2]),
                    billing_period=BillingPeriod(row[3]),
                    currency=row[4]
                )
                for row in rows
            ]


class PlanTierRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, plan_id: int, from_units: int, to_units: Optional[int], unit_price: Money) -> int:
        """Insert a tier; return new id."""
        # TODO Day 2.
        with self.db.conn as conn:
            cursor = conn.execute(
                "INSERT INTO plan_tiers (plan_id, from_units, to_units, unit_price) VALUES (?, ?, ?, ?)",
                (plan_id, from_units, to_units, unit_price.to_storage())
            )
            return cursor.lastrowid

    def list_for_plan(self, plan_id: int, currency: str) -> list[tuple[int, Optional[int], Money]]:
        """Return [(from_units, to_units, unit_price)] ordered by from_units.

        Currency is passed in (the plan_tiers table stores only the amount;
        currency lives on the parent plan).
        """
        # TODO Day 2.
        with self.db.conn as conn:
            rows = conn.execute(
                "SELECT from_units, to_units, unit_price FROM plan_tiers WHERE plan_id = ? ORDER BY from_units",
                (plan_id,)
            ).fetchall()
            return [
                (row[0], row[1], Money.from_storage(row[2], currency))
                for row in rows
            ]   


# ============================================================
# DISCOUNTS
# ============================================================
class DiscountRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, code: str, discount_type: str, value: str, currency: Optional[str] = None) -> int:
        # TODO Day 2.
        with self.db.conn as conn:
            cursor = conn.execute(
                "INSERT INTO discounts (code, discount_type, value, currency) VALUES (?, ?, ?, ?)",
                (code, discount_type, value, currency)
            )
            return cursor.lastrowid
        
    def get_by_code(self, code: str) -> Optional[dict]:
        """Return raw row as dict, or None. (Discount has no dataclass yet — we use a dict for now.)"""
        # TODO Day 2.
        with self.db.conn as conn:
            row = conn.execute(
                "SELECT id, code, discount_type, value, currency FROM discounts WHERE code = ?",
                (code,)
            ).fetchone()
            if row is None:
                return None
            return {
                "id": row[0],
                "code": row[1],
                "discount_type": row[2],
                "value": row[3],
                "currency": row[4]
            }


# ============================================================
# SUBSCRIPTIONS
# ============================================================
class SubscriptionRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, subscription: Subscription) -> Subscription:
        # TODO Day 2.
        with self.db.conn as conn:
            cursor = conn.execute(
                "INSERT INTO subscriptions (plan_id, customer_id, status) VALUES (?, ?, ?)",
                (subscription.plan_id, subscription.customer_id, subscription.status)
            )
            return cursor.lastrowid

    def get(self, subscription_id: int) -> Optional[Subscription]:
        # TODO Day 2.
        with self.db.conn as conn:
            row = conn.execute(
                "SELECT id, plan_id, customer_id, status FROM subscriptions WHERE id = ?",
                (subscription_id,)
            ).fetchone()
            if row is None:
                return None
            return Subscription(
                id=row[0],
                plan_id=row[1],
                customer_id=row[2],
                status=SubscriptionStatus(row[3])
            )

    def list_all(self) -> list[Subscription]:
        """All subscriptions, regardless of status. Used by BillingCycle trial scan."""
        # TODO Day 2.
        with self.db.conn as conn:
            rows = conn.execute(
                "SELECT id, plan_id, customer_id, status FROM subscriptions"
            ).fetchall()
            return [
                Subscription(
                    id=row[0],
                    plan_id=row[1],
                    customer_id=row[2],
                    status=SubscriptionStatus(row[3])
                )
                for row in rows
            ]

    def get_due_for_billing(self, as_of: date) -> list[Subscription]:
        """Subscriptions whose current_period_end <= as_of AND status is ACTIVE.
        (Hint: trial subscriptions whose trial_end <= as_of should also become billable —
         either handle that here or transition them to ACTIVE first in BillingCycle.)
        """
        # TODO Day 2.
        with self.db.conn as conn:
            rows = conn.execute(
                "SELECT id, plan_id, customer_id, status FROM subscriptions WHERE current_period_end <= ? AND status = ?",
                (as_of, SubscriptionStatus.ACTIVE)
            ).fetchall()
            return [
                Subscription(
                    id=row[0],
                    plan_id=row[1],
                    customer_id=row[2],
                    status=SubscriptionStatus(row[3])
                )
                for row in rows
            ]

    def update_period(self, subscription_id: int, new_start: date, new_end: date) -> None:
        # TODO Day 2.
        with self.db.conn as conn:
            conn.execute(
                "UPDATE subscriptions SET current_period_start = ?, current_period_end = ? WHERE id = ?",
                (new_start, new_end, subscription_id)
            )


    def update_status(
        self,
        subscription_id: int,
        new_status: SubscriptionStatus,
        past_due_since: Optional[date] = None,
    ) -> None:
        # TODO Day 2.
        with self.db.conn as conn:
            conn.execute(
                "UPDATE subscriptions SET status = ?, past_due_since = ? WHERE id = ?",
                (new_status, past_due_since, subscription_id)
            )

    def update_plan(self, subscription_id: int, new_plan_id: int) -> None:
        """Switch the subscription to a different plan (used by upgrade flow)."""
        # TODO Day 4.
        with self.db.conn as conn:
            conn.execute(
                "UPDATE subscriptions SET plan_id = ? WHERE id = ?",
                (new_plan_id, subscription_id)
            )

# ============================================================
# USAGE
# ============================================================
class UsageRecordRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, subscription_id: int, metric: str, quantity: int) -> int:
        # TODO Day 2.
        with self.db.conn as conn:
            cursor = conn.execute(
                "INSERT INTO usage_records (subscription_id, metric, quantity) VALUES (?, ?, ?)",
                (subscription_id, metric, quantity)
            )
            return cursor.lastrowid

    def sum_for_period(
        self, subscription_id: int, metric: str, period_start: date, period_end: date
    ) -> int:
        # TODO Day 2: SELECT COALESCE(SUM(quantity), 0) ...
        with self.db.conn as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(quantity), 0) FROM usage_records WHERE subscription_id = ? AND metric = ? AND created_at >= ? AND created_at < ?",
                (subscription_id, metric, period_start, period_end)
            ).fetchone()
            return row[0] if row else 0

# ============================================================
# INVOICES + LINE ITEMS
# ============================================================
class InvoiceRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, invoice: Invoice) -> Invoice:
        """Insert invoice (NOT line items — that's the other repo).

        Must respect the UNIQUE(subscription_id, period_start) constraint.
        If a duplicate is attempted, raise sqlite3.IntegrityError naturally
        (caller is responsible for handling it — this gives idempotency).
        """
        # TODO Day 2.
        with self.db.conn as conn:
            cursor = conn.execute(
                "INSERT INTO invoices (subscription_id, plan_id, status, base, discount, taxable, tax, total, period_start, period_end) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    invoice.subscription_id,
                    invoice.plan_id,
                    invoice.status.value,
                    invoice.base.to_storage(),
                    invoice.discount.to_storage(),
                    invoice.taxable.to_storage(),
                    invoice.tax.to_storage(),
                    invoice.total.to_storage(),
                    invoice.period_start.isoformat(),
                    invoice.period_end.isoformat()
                )
            )
            invoice_id = cursor.lastrowid
            return Invoice(
                id=invoice_id,
                status=invoice.status,
                subscription_id=invoice.subscription_id,
                plan_id=invoice.plan_id,
                base=invoice.base,
                discount=invoice.discount,
                taxable=invoice.taxable,
                tax=invoice.tax,
                total=invoice.total,
                period_start=invoice.period_start,
                period_end=invoice.period_end
            )

    def get(self, invoice_id: int) -> Optional[Invoice]:
        # TODO Day 2.
        with self.db.conn as conn:
            row = conn.execute(
                "SELECT id, subscription_id, plan_id, status, base, discount, taxable, tax, total, period_start, period_end FROM invoices WHERE id = ?",
                (invoice_id,)
            ).fetchone()
            if row is None:
                return None
            return Invoice(
                id=row[0],
                subscription_id=row[1],
                plan_id=row[2],
                status=InvoiceStatus(row[3]),
                base=Money.from_storage(row[4], "USD"),  # Assuming USD for simplicity; adjust as needed
                discount=Money.from_storage(row[5], "USD"),
                taxable=Money.from_storage(row[6], "USD"),
                tax=Money.from_storage(row[7], "USD"),
                total=Money.from_storage(row[8], "USD"),
                period_start=date.fromisoformat(row[9]),
                period_end=date.fromisoformat(row[10])
            )

    def count_for_subscription(self, subscription_id: int) -> int:
        """Used by FirstMonthFree discount."""
        # TODO Day 2.
        with self.db.conn as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM invoices WHERE subscription_id = ?",
                (subscription_id,)
            ).fetchone()
            return row[0] if row else 0
        

    def mark_paid(self, invoice_id: int) -> None:
        # TODO Day 2.
        with self.db.conn as conn:
            conn.execute(
                "UPDATE invoices SET status = ? WHERE id = ?",
                (InvoiceStatus.PAID.value, invoice_id)
            )

    def mark_failed(self, invoice_id: int) -> None:
        # TODO Day 2.
        with self.db.conn as conn:
            conn.execute(
                "UPDATE invoices SET status = ? WHERE id = ?",
                (InvoiceStatus.FAILED.value, invoice_id)
            )

    def set_pdf_path(self, invoice_id: int, path: str) -> None:
        # TODO Day 4.
        with self.db.conn as conn:
            conn.execute(
                "UPDATE invoices SET pdf_path = ? WHERE id = ?",
                (path, invoice_id)
            )

class InvoiceLineItemRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, line_item: InvoiceLineItem) -> InvoiceLineItem:
        # TODO Day 2.
        with self.db.conn as conn:
            cursor = conn.execute(
                "INSERT INTO invoice_line_items (invoice_id, kind, description, amount) VALUES (?, ?, ?, ?)",
                (
                    line_item.invoice_id,
                    line_item.kind.value,
                    line_item.description,
                    line_item.amount.to_storage()
                )
            )
            line_item_id = cursor.lastrowid
            return InvoiceLineItem(
                id=line_item_id,
                invoice_id=line_item.invoice_id,
                kind=line_item.kind,
                description=line_item.description,
                amount=line_item.amount
            )

    def list_for_invoice(self, invoice_id: int) -> list[InvoiceLineItem]:
        # TODO Day 2.
        with self.db.conn as conn:
            rows = conn.execute(
                "SELECT id, invoice_id, kind, description, amount FROM invoice_line_items WHERE invoice_id = ?",
                (invoice_id,)
            ).fetchall()
            return [
                InvoiceLineItem(
                    id=row[0],
                    invoice_id=row[1],
                    kind=InvoiceLineItemKind(row[2]),
                    description=row[3],
                    amount=Money.from_storage(row[4], "USD")
                )
                for row in rows
            ]


# ============================================================
# LEDGER — APPEND-ONLY (do not implement update/delete)
# ============================================================
class LedgerRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, entry: LedgerEntry) -> LedgerEntry:
        # TODO Day 2.
        with self.db.conn as conn:
            cursor = conn.execute(
                "INSERT INTO ledger (customer_id, invoice_id, direction, amount, description, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    entry.customer_id,
                    entry.invoice_id,
                    entry.direction.value,
                    entry.amount.to_storage(),
                    entry.description,
                    entry.created_at.isoformat()
                )
            )
            entry_id = cursor.lastrowid
            return LedgerEntry(
                id=entry_id,
                customer_id=entry.customer_id,
                invoice_id=entry.invoice_id,
                direction=entry.direction,
                amount=entry.amount,
                description=entry.description,
                created_at=entry.created_at
            )

    def list_for_customer(self, customer_id: int) -> list[LedgerEntry]:
        # TODO Day 2.
        with self.db.conn as conn:
            rows = conn.execute(
                "SELECT id, customer_id, invoice_id, direction, amount, description, created_at FROM ledger WHERE customer_id = ?",
                (customer_id,)
            ).fetchall()
            return [
                LedgerEntry(
                    id=row[0],
                    customer_id=row[1],
                    invoice_id=row[2],
                    direction=LedgerDirection(row[3]),
                    amount=Money.from_storage(row[4], "USD"),
                    description=row[5],
                    created_at=datetime.fromisoformat(row[6])
                )
                for row in rows
            ]

    # ✅ These two methods are intentionally implemented to REJECT — do not override.
    def update(self, *args, **kwargs):
        with self.db.conn as conn:
            conn.execute("ROLLBACK")

            

    def delete(self, *args, **kwargs):
        with self.db.conn as conn:
            conn.execute("ROLLBACK")


# ============================================================
# PAYMENT ATTEMPTS
# ============================================================
class PaymentAttemptRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(
        self,
        invoice_id: int,
        attempt_no: int,
        status: str,
        failure_reason: Optional[str],
        next_retry_at: Optional[datetime],
    ) -> int:
        # TODO Day 3.
        with self.db.conn as conn:
            cursor = conn.execute(
                "INSERT INTO payment_attempts (invoice_id, attempt_no, status, failure_reason, next_retry_at) VALUES (?, ?, ?, ?, ?)",
                (
                    invoice_id,
                    attempt_no,
                    status,
                    failure_reason,
                    next_retry_at.isoformat() if next_retry_at else None
                )
            )
            return cursor.lastrowid

    def list_for_invoice(self, invoice_id: int) -> list[dict]:
        # TODO Day 3.
        with self.db.conn as conn:
            rows = conn.execute(
                "SELECT id, invoice_id, attempt_no, status, failure_reason, next_retry_at FROM payment_attempts WHERE invoice_id = ?",
                (invoice_id,)
            ).fetchall()
            return [
                {
                    "id": row[0],
                    "invoice_id": row[1],
                    "attempt_no": row[2],
                    "status": row[3],
                    "failure_reason": row[4],
                    "next_retry_at": datetime.fromisoformat(row[5]) if row[5] else None
                }
                for row in rows
            ]

    def count_for_invoice(self, invoice_id: int) -> int:
        # TODO Day 3.
        with self.db.conn as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM payment_attempts WHERE invoice_id = ?",
                (invoice_id,)
            ).fetchone()
            return row[0] if row else 0
        

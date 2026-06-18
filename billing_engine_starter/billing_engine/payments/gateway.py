"""
PaymentGateway — abstract + two mock implementations.

In real life this would talk to Stripe / Razorpay / Adyen. For the project
we use mocks so tests are deterministic and the demo never hits the network.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from billing_engine.models import Invoice


@dataclass(frozen=True)
class PaymentResult:
    success: bool
    failure_reason: Optional[str] = None


class PaymentGateway(ABC):
    @abstractmethod
    def charge(self, invoice: Invoice) -> PaymentResult:
        raise NotImplementedError


# ----------------------------------------------------------------
# Scripted — for deterministic tests
# ----------------------------------------------------------------
class ScriptedGateway(PaymentGateway):
    """Returns pre-set results from a queue. Used in tests.

    Example:
        gateway = ScriptedGateway([
            PaymentResult(False, "INSUFFICIENT_FUNDS"),
            PaymentResult(False, "INSUFFICIENT_FUNDS"),
            PaymentResult(True),
        ])
    """

    def __init__(self, results: list[PaymentResult]) -> None:
       with self.invoice_repo.db.conn as conn:
            self.results = results
            self.index = 0


    def charge(self, invoice: Invoice) -> PaymentResult:
        # TODO Day 3
        with self.invoice_repo.db.conn as conn:
            if self.index < len(self.results):
                result = self.results[self.index]
                self.index += 1
                return result
            else:
                raise ValueError("No more payment results available")"


# ----------------------------------------------------------------
# Fake-random — for the CLI demo
# ----------------------------------------------------------------
class FakeRandomGateway(PaymentGateway):
    """Succeeds at a configurable rate; seeded for reproducibility."""

    def __init__(self, success_rate: float = 0.7, seed: Optional[int] = None) -> None:
        # TODO Day 3
        with self.invoice_repo.db.conn as conn:
            self.success_rate = success_rate
            self.seed = seed
            if seed is not None:
                import random
                random.seed(seed)

    def charge(self, invoice: Invoice) -> PaymentResult:
        # TODO Day 3
        with self.invoice_repo.db.conn as conn:
            import random
            if random.random() < self.success_rate:
                return PaymentResult(success=True)
            else:
                return PaymentResult(success=False, failure_reason="RANDOM_FAILURE")

   

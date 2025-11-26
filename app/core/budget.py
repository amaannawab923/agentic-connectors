"""Budget controller for tracking and enforcing spending limits."""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime

from ..models.schemas import BudgetStatus, CostLogEntry
from ..models.enums import AgentType

logger = logging.getLogger(__name__)


@dataclass
class BudgetController:
    """Tracks and enforces budget limits for connector generation.

    This controller ensures that the pipeline doesn't exceed the maximum
    budget allocated for generating a single connector.

    Attributes:
        max_budget: Maximum allowed budget in USD.
        warning_threshold: Budget threshold to trigger warnings.
        force_publish_threshold: Budget threshold to force early publishing.
    """

    max_budget: float = 7.00
    warning_threshold: float = 5.00
    force_publish_threshold: float = 6.00
    spent: float = 0.00

    costs: Dict[str, float] = field(default_factory=lambda: {
        "research": 0.60,
        "generate": 1.20,
        "test": 0.30,
        "fix": 0.50,
        "review": 0.15,
        "improve": 0.50,
        "publish": 0.05,
    })

    cost_log: List[CostLogEntry] = field(default_factory=list)

    def configure_costs(self, costs: Dict[str, float]) -> None:
        """Update cost configuration.

        Args:
            costs: Dictionary mapping operation names to costs.
        """
        self.costs.update(costs)
        logger.info(f"Budget costs configured: {self.costs}")

    def can_afford(self, operation: str) -> bool:
        """Check if we can afford the next operation.

        Args:
            operation: Name of the operation (e.g., 'research', 'test').

        Returns:
            True if operation can be afforded within budget.
        """
        cost = self.costs.get(operation, 0)
        can_afford = (self.spent + cost) <= self.max_budget

        if not can_afford:
            logger.warning(
                f"Cannot afford operation '{operation}' (cost: ${cost:.2f}). "
                f"Budget: ${self.spent:.2f}/${self.max_budget:.2f}"
            )

        return can_afford

    def estimate_remaining_operations(self) -> Dict[str, bool]:
        """Estimate which operations can still be afforded.

        Returns:
            Dictionary mapping operation names to affordability.
        """
        return {op: self.can_afford(op) for op in self.costs}

    def charge(
        self,
        operation: str,
        agent: AgentType,
        details: Optional[str] = None,
        actual_cost: Optional[float] = None,
    ) -> float:
        """Charge for an operation and record in log.

        Args:
            operation: Name of the operation.
            agent: Agent performing the operation.
            details: Additional details for the log.
            actual_cost: Override the default cost (for tracking actual API costs).

        Returns:
            New total spent amount.
        """
        cost = actual_cost if actual_cost is not None else self.costs.get(operation, 0)
        self.spent += cost

        entry = CostLogEntry(
            timestamp=datetime.utcnow(),
            operation=operation,
            agent=agent,
            cost=cost,
            total_spent=self.spent,
            details=details,
        )
        self.cost_log.append(entry)

        logger.info(
            f"Budget charged: {operation} = ${cost:.2f} "
            f"(total: ${self.spent:.2f}/${self.max_budget:.2f})"
        )

        return self.spent

    def remaining(self) -> float:
        """Get remaining budget.

        Returns:
            Remaining budget in USD.
        """
        return max(0, self.max_budget - self.spent)

    def percent_used(self) -> float:
        """Get percentage of budget used.

        Returns:
            Percentage of budget used (0-100).
        """
        if self.max_budget == 0:
            return 100.0
        return round((self.spent / self.max_budget) * 100, 1)

    def is_warning(self) -> bool:
        """Check if we're in warning zone.

        Returns:
            True if spent >= warning threshold.
        """
        return self.spent >= self.warning_threshold

    def is_exceeded(self) -> bool:
        """Check if budget is exceeded.

        Returns:
            True if spent > max budget.
        """
        return self.spent > self.max_budget

    def should_force_publish(self) -> bool:
        """Check if we should force publish due to budget constraints.

        Returns:
            True if spent >= force publish threshold.
        """
        return self.spent >= self.force_publish_threshold

    def get_status(self) -> BudgetStatus:
        """Get current budget status.

        Returns:
            BudgetStatus object with current state.
        """
        return BudgetStatus(
            spent=round(self.spent, 2),
            remaining=round(self.remaining(), 2),
            max_budget=self.max_budget,
            percent_used=self.percent_used(),
            warning=self.is_warning(),
            exceeded=self.is_exceeded(),
        )

    def get_cost_log(self) -> List[CostLogEntry]:
        """Get the full cost log.

        Returns:
            List of cost log entries.
        """
        return self.cost_log.copy()

    def reset(self) -> None:
        """Reset the budget controller to initial state."""
        self.spent = 0.0
        self.cost_log.clear()
        logger.info("Budget controller reset")

    def __repr__(self) -> str:
        return (
            f"BudgetController(spent=${self.spent:.2f}, "
            f"max=${self.max_budget:.2f}, "
            f"remaining=${self.remaining():.2f})"
        )

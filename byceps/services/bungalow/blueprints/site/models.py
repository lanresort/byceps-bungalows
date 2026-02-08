"""
byceps.services.bungalow.blueprints.site.models
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from dataclasses import dataclass

from moneyed import Money

from byceps.services.bungalow.models.category import BungalowCategoryID


@dataclass(frozen=True, kw_only=True)
class BungalowCategorySummary:
    id: BungalowCategoryID
    title: str
    capacity: int
    total_price: Money
    quantity_available: int
    quantity_occupied: int
    quantity_total: int
    available: bool

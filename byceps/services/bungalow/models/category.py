"""
byceps.services.bungalow.models.category
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2025 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import NewType
from uuid import UUID

from moneyed import Money

from byceps.services.party.models import PartyID
from byceps.services.shop.product.models import ProductID, ProductNumber
from byceps.services.ticketing.models.ticket import TicketCategoryID


BungalowCategoryID = NewType('BungalowCategoryID', UUID)


@dataclass(frozen=True, kw_only=True)
class Product:
    id: ProductID
    item_number: ProductNumber
    name: str
    price: Money
    available_from: datetime | None
    available_until: datetime | None
    quantity: int


@dataclass(frozen=True, kw_only=True)
class BungalowCategory:
    id: BungalowCategoryID
    party_id: PartyID
    title: str
    capacity: int
    ticket_category_id: TicketCategoryID
    ticket_category_title: str
    product: Product
    image_filename: str | None
    image_width: int | None
    image_height: int | None

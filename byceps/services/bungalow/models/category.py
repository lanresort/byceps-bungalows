"""
byceps.services.bungalow.models.category
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2023 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from dataclasses import dataclass
from datetime import datetime
from typing import NewType, Optional
from uuid import UUID

from moneyed import Money

from byceps.services.shop.article.models import ArticleID, ArticleNumber
from byceps.services.ticketing.models.ticket import TicketCategoryID
from byceps.typing import PartyID


BungalowCategoryID = NewType('BungalowCategoryID', UUID)


@dataclass(frozen=True)
class Article:
    id: ArticleID
    item_number: ArticleNumber
    description: str
    price: Money
    available_from: Optional[datetime]
    available_until: Optional[datetime]
    quantity: int


@dataclass(frozen=True)
class BungalowCategory:
    id: BungalowCategoryID
    party_id: PartyID
    title: str
    capacity: int
    ticket_category_id: TicketCategoryID
    ticket_category_title: str
    article: Article
    image_filename: Optional[str]
    image_width: Optional[int]
    image_height: Optional[int]

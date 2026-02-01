"""
byceps.services.bungalow.dbmodels.category
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from __future__ import annotations

from sqlalchemy.orm import Mapped, mapped_column, relationship

from byceps.database import db
from byceps.services.bungalow.models.category import BungalowCategoryID
from byceps.services.party.models import PartyID
from byceps.services.shop.product.dbmodels.product import DbProduct
from byceps.services.shop.product.models import ProductID
from byceps.services.ticketing.dbmodels.category import DbTicketCategory
from byceps.services.ticketing.models.ticket import TicketCategoryID
from byceps.util.instances import ReprBuilder


class DbBungalowCategory(db.Model):
    """A party-specific bungalow category."""

    __tablename__ = 'bungalow_categories'
    __table_args__ = (db.UniqueConstraint('party_id', 'title', 'capacity'),)

    id: Mapped[BungalowCategoryID] = mapped_column(primary_key=True)
    party_id: Mapped[PartyID] = mapped_column(
        db.UnicodeText, db.ForeignKey('parties.id'), index=True
    )
    title: Mapped[str] = mapped_column(db.UnicodeText)
    capacity: Mapped[int] = mapped_column(db.SmallInteger)
    ticket_category_id: Mapped[TicketCategoryID] = mapped_column(
        db.ForeignKey('ticket_categories.id')
    )
    ticket_category: Mapped[DbTicketCategory] = relationship()
    product_id: Mapped[ProductID] = mapped_column(
        db.ForeignKey('shop_products.id'), unique=True
    )
    product: Mapped[DbProduct] = relationship()
    image_filename: Mapped[str | None] = mapped_column(db.UnicodeText)
    image_width: Mapped[int | None] = mapped_column(db.SmallInteger)
    image_height: Mapped[int | None] = mapped_column(db.SmallInteger)

    def __init__(
        self,
        category_id: BungalowCategoryID,
        party_id: PartyID,
        title: str,
        capacity: int,
        ticket_category_id: TicketCategoryID,
        product_id: ProductID,
        *,
        image_filename: str | None = None,
        image_width: int | None = None,
        image_height: int | None = None,
    ) -> None:
        self.id = category_id
        self.party_id = party_id
        self.title = title
        self.capacity = capacity
        self.ticket_category_id = ticket_category_id
        self.product_id = product_id
        self.image_filename = image_filename
        self.image_width = image_width
        self.image_height = image_height

    def __repr__(self) -> str:
        return (
            ReprBuilder(self)
            .add_with_lookup('id')
            .add_with_lookup('title')
            .add('party', self.party_id)
            .add_with_lookup('capacity')
            .build()
        )

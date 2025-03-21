"""
byceps.services.bungalow.dbmodels.category
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2025 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from __future__ import annotations

from byceps.database import db
from byceps.services.party.models import PartyID
from byceps.services.shop.product.dbmodels.product import DbProduct
from byceps.services.shop.product.models import ProductID
from byceps.services.ticketing.dbmodels.category import DbTicketCategory
from byceps.services.ticketing.models.ticket import TicketCategoryID
from byceps.util.instances import ReprBuilder
from byceps.util.uuid import generate_uuid7


class DbBungalowCategory(db.Model):
    """A party-specific bungalow category."""

    __tablename__ = 'bungalow_categories'
    __table_args__ = (db.UniqueConstraint('party_id', 'title', 'capacity'),)

    id = db.Column(db.Uuid, default=generate_uuid7, primary_key=True)
    party_id = db.Column(
        db.UnicodeText, db.ForeignKey('parties.id'), index=True, nullable=False
    )
    title = db.Column(db.UnicodeText, nullable=False)
    capacity = db.Column(db.SmallInteger, nullable=False)
    ticket_category_id = db.Column(
        db.Uuid, db.ForeignKey('ticket_categories.id'), nullable=False
    )
    ticket_category = db.relationship(DbTicketCategory)
    product_id = db.Column(
        db.Uuid, db.ForeignKey('shop_products.id'), unique=True, nullable=False
    )
    product = db.relationship(DbProduct)
    image_filename = db.Column(db.UnicodeText, nullable=True)
    image_width = db.Column(db.SmallInteger, nullable=True)
    image_height = db.Column(db.SmallInteger, nullable=True)

    def __init__(
        self,
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

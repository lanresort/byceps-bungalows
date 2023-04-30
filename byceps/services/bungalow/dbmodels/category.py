"""
byceps.services.bungalow.dbmodels.category
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2023 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from typing import Optional

from byceps.database import db, generate_uuid7
from byceps.services.shop.article.dbmodels.article import DbArticle
from byceps.services.shop.article.models import ArticleID
from byceps.services.ticketing.dbmodels.category import DbTicketCategory
from byceps.services.ticketing.models.ticket import TicketCategoryID
from byceps.typing import PartyID
from byceps.util.instances import ReprBuilder


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
    article_id = db.Column(
        db.Uuid, db.ForeignKey('shop_articles.id'), unique=True, nullable=False
    )
    article = db.relationship(DbArticle)
    image_filename = db.Column(db.UnicodeText, nullable=True)
    image_width = db.Column(db.SmallInteger, nullable=True)
    image_height = db.Column(db.SmallInteger, nullable=True)

    def __init__(
        self,
        party_id: PartyID,
        title: str,
        capacity: int,
        ticket_category_id: TicketCategoryID,
        article_id: ArticleID,
        *,
        image_filename: Optional[str] = None,
        image_width: Optional[int] = None,
        image_height: Optional[int] = None,
    ) -> None:
        self.party_id = party_id
        self.title = title
        self.capacity = capacity
        self.ticket_category_id = ticket_category_id
        self.article_id = article_id
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

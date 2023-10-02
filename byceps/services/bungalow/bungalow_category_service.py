"""
byceps.services.bungalow.bungalow_category_service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2023 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from __future__ import annotations

from sqlalchemy import select

from byceps.database import db
from byceps.services.party.models import PartyID
from byceps.services.shop.article.models import ArticleID
from byceps.services.ticketing.models.ticket import TicketCategoryID

from .dbmodels.category import DbBungalowCategory
from .model_converters import _db_entity_to_bungalow_category
from .models.category import BungalowCategory, BungalowCategoryID


def create_category(
    party_id: PartyID,
    title: str,
    capacity: int,
    ticket_category_id: TicketCategoryID,
    article_id: ArticleID,
    *,
    image_filename: str | None = None,
    image_width: int | None = None,
    image_height: int | None = None,
) -> BungalowCategory:
    """Create a bungalow category."""
    db_bungalow_category = DbBungalowCategory(
        party_id,
        title,
        capacity,
        ticket_category_id,
        article_id,
        image_filename=image_filename,
        image_width=image_width,
        image_height=image_height,
    )

    db.session.add(db_bungalow_category)
    db.session.commit()

    return _db_entity_to_bungalow_category(db_bungalow_category)


def update_category(
    category_id: BungalowCategoryID,
    title: str,
    capacity: int,
    ticket_category_id: TicketCategoryID,
    article_id: ArticleID,
    image_filename: str,
    image_width: int,
    image_height: int,
) -> BungalowCategory:
    """Update a bungalow category."""
    db_bungalow_category = _find_db_category(category_id)

    if db_bungalow_category is None:
        raise ValueError(f'Unknown bungalow category ID "{category_id}"')

    db_bungalow_category.title = title
    db_bungalow_category.capacity = capacity
    db_bungalow_category.ticket_category_id = ticket_category_id
    db_bungalow_category.article_id = article_id
    db_bungalow_category.image_filename = image_filename
    db_bungalow_category.image_width = image_width
    db_bungalow_category.image_height = image_height

    db.session.commit()

    return _db_entity_to_bungalow_category(db_bungalow_category)


def find_category(
    category_id: BungalowCategoryID,
) -> BungalowCategory | None:
    """Return the category with that id, or `None` if not found."""
    db_bungalow_category = _find_db_category(category_id)

    if db_bungalow_category is None:
        return None

    return _db_entity_to_bungalow_category(db_bungalow_category)


def _find_db_category(
    category_id: BungalowCategoryID,
) -> DbBungalowCategory | None:
    return db.session.get(DbBungalowCategory, category_id)


def get_categories_for_party(party_id: PartyID) -> list[BungalowCategory]:
    """Return the bungalow categories for the party."""
    db_bungalow_categories = db.session.scalars(
        select(DbBungalowCategory)
        .options(
            db.joinedload(DbBungalowCategory.ticket_category),
            db.joinedload(DbBungalowCategory.article),
        )
        .filter_by(party_id=party_id)
        .order_by(DbBungalowCategory.title, DbBungalowCategory.capacity)
    ).all()

    return [
        _db_entity_to_bungalow_category(db_bungalow_category)
        for db_bungalow_category in db_bungalow_categories
    ]

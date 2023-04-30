"""
byceps.services.bungalow.model_converters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2023 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from __future__ import annotations

from .dbmodels.bungalow import DbBungalow
from .dbmodels.category import DbBungalowCategory
from .dbmodels.occupancy import DbBungalowOccupancy, DbBungalowReservation
from .models.bungalow import Bungalow
from .models.category import Article, BungalowCategory
from .models.occupation import BungalowOccupancy, BungalowReservation


def _db_entity_to_bungalow(db_bungalow: DbBungalow) -> Bungalow:
    category = _db_entity_to_bungalow_category(db_bungalow.category)

    db_occupancy = db_bungalow.occupancy
    occupancy = _db_entity_to_occupancy(db_occupancy) if db_occupancy else None

    avatar_url = (
        db_occupancy.get_avatar_url(db_bungalow.party_id)
        if db_occupancy
        else None
    )

    return Bungalow(
        id=db_bungalow.id,
        party_id=db_bungalow.party_id,
        number=db_bungalow.number,
        category=category,
        occupation_state=db_bungalow.occupation_state,
        distributes_network=db_bungalow.distributes_network,
        available=db_bungalow.available,
        reserved=db_bungalow.reserved,
        occupied=db_bungalow.occupied,
        reserved_or_occupied=db_bungalow.reserved_or_occupied,
        occupancy=occupancy,
        avatar_url=avatar_url,
    )


def _db_entity_to_bungalow_category(
    db_bungalow_category: DbBungalowCategory,
) -> BungalowCategory:
    db_article = db_bungalow_category.article

    article = Article(
        id=db_article.id,
        item_number=db_article.item_number,
        description=db_article.description,
        price=db_article.price,
        available_from=db_article.available_from,
        available_until=db_article.available_until,
        quantity=db_article.quantity,
    )

    return BungalowCategory(
        id=db_bungalow_category.id,
        party_id=db_bungalow_category.party_id,
        title=db_bungalow_category.title,
        capacity=db_bungalow_category.capacity,
        ticket_category_id=db_bungalow_category.ticket_category.id,
        ticket_category_title=db_bungalow_category.ticket_category.title,
        article=article,
        image_filename=db_bungalow_category.image_filename,
        image_width=db_bungalow_category.image_width,
        image_height=db_bungalow_category.image_height,
    )


def _db_entity_to_reservation(
    db_reservation: DbBungalowReservation,
) -> BungalowReservation:
    return BungalowReservation(
        id=db_reservation.id,
        bungalow_id=db_reservation.bungalow_id,
        reserved_by_id=db_reservation.reserved_by_id,
        order_number=db_reservation.order_number,
        pinned=db_reservation.pinned,
        internal_remark=db_reservation.internal_remark,
    )


def _db_entity_to_occupancy(
    db_occupancy: DbBungalowOccupancy,
) -> BungalowOccupancy:
    return BungalowOccupancy(
        id=db_occupancy.id,
        bungalow_id=db_occupancy.bungalow_id,
        occupied_by_id=db_occupancy.occupied_by_id,
        order_number=db_occupancy.order_number,
        state=db_occupancy.state,
        ticket_bundle_id=db_occupancy.ticket_bundle_id,
        pinned=db_occupancy.pinned,
        manager_id=db_occupancy.manager_id,
        title=db_occupancy.title,
        description=db_occupancy.description,
        avatar_id=db_occupancy.avatar_id,
        internal_remark=db_occupancy.internal_remark,
    )

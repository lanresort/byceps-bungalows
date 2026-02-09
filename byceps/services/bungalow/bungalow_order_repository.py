"""
byceps.services.bungalow.bungalow_order_repository
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from sqlalchemy import select

from byceps.database import db
from byceps.services.party.models import PartyID
from byceps.services.shop.order.dbmodels.order import DbLineItem, DbOrder
from byceps.services.shop.product.dbmodels.product import DbProduct
from byceps.services.user.models import UserID

from .dbmodels.category import DbBungalowCategory


def has_user_ordered_any_bungalow_category(
    user_id: UserID, party_id: PartyID
) -> bool:
    """Return `True` if the user has already ordered any bungalow
    category for the party (ignored canceled orders).
    """
    return (
        db.session.scalar(
            select(
                select(DbLineItem)
                .join(DbProduct)
                .join(DbBungalowCategory)
                .filter(DbBungalowCategory.party_id == party_id)
                .filter(DbOrder.placed_by_id == user_id)
                .filter(DbOrder._payment_state.in_(('open', 'paid')))
                .exists()
            )
        )
        or False
    )

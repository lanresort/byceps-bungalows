"""
byceps.services.bungalow.bungalow_offer_service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2024 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from sqlalchemy import delete

from byceps.database import db
from byceps.services.party.models import PartyID

from . import bungalow_service
from .bungalow_service import _db_entity_to_bungalow
from .dbmodels.bungalow import DbBungalow
from .dbmodels.log import DbBungalowLogEntry
from .models.building import BungalowBuilding
from .models.bungalow import Bungalow, BungalowID
from .models.category import BungalowCategoryID


def offer_bungalow(
    party_id: PartyID,
    building: BungalowBuilding,
    bungalow_category_id: BungalowCategoryID,
) -> Bungalow:
    """Offer this building in that category."""
    db_bungalow = _offer_bungalow(party_id, building, bungalow_category_id)
    db.session.commit()

    return _db_entity_to_bungalow(db_bungalow)


def offer_bungalows(
    party_id: PartyID,
    buildings: list[BungalowBuilding],
    bungalow_category_id: BungalowCategoryID,
) -> None:
    """Offer these buildings in that category."""
    for building in buildings:
        _offer_bungalow(party_id, building, bungalow_category_id)

    db.session.commit()


def _offer_bungalow(
    party_id: PartyID,
    building: BungalowBuilding,
    bungalow_category_id: BungalowCategoryID,
) -> DbBungalow:
    db_bungalow = DbBungalow(party_id, building.number, bungalow_category_id)
    db.session.add(db_bungalow)

    return db_bungalow


def delete_offer(bungalow_id: BungalowID) -> None:
    """Remove bungalow offer."""
    db_bungalow = bungalow_service.get_db_bungalow(bungalow_id)

    if db_bungalow.reserved_or_occupied:
        raise ValueError(
            'Bungalow is reserved or occupied, it must not be deleted.'
        )

    db.session.execute(
        delete(DbBungalowLogEntry).where(
            DbBungalowLogEntry.bungalow_id == bungalow_id
        )
    )
    db.session.delete(db_bungalow)
    db.session.commit()


def set_distributes_network_flag(bungalow_id: BungalowID) -> None:
    """Set the bungalow's network distributor flag."""
    db_bungalow = bungalow_service.get_db_bungalow(bungalow_id)

    db_bungalow.distributes_network = True
    db.session.commit()


def unset_distributes_network_flag(bungalow_id: BungalowID) -> None:
    """Unset the bungalow's network distributor flag."""
    db_bungalow = bungalow_service.get_db_bungalow(bungalow_id)

    db_bungalow.distributes_network = False
    db.session.commit()

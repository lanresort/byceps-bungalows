"""
byceps.services.bungalow.bungalow_occupancy_repository
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select

from byceps.database import db
from byceps.services.party.models import PartyID
from byceps.services.shop.product.models import ProductID
from byceps.services.ticketing.dbmodels.ticket import DbTicket
from byceps.services.ticketing.dbmodels.ticket_bundle import DbTicketBundle
from byceps.services.ticketing.models.ticket import TicketBundleID, TicketID
from byceps.services.user.models import UserID
from byceps.util.image.image_type import ImageType
from byceps.util.result import Err, Ok, Result

from . import bungalow_log_service
from .dbmodels.avatar import DbBungalowAvatar
from .dbmodels.bungalow import DbBungalow
from .dbmodels.category import DbBungalowCategory
from .dbmodels.occupancy import DbBungalowOccupancy, DbBungalowReservation
from .models.bungalow import BungalowID, BungalowOccupationState
from .models.occupation import OccupancyID, ReservationID


def find_reservation(
    reservation_id: ReservationID,
) -> DbBungalowReservation | None:
    """Return the reservation with that id, or `None` if not found."""
    return db.session.get(DbBungalowReservation, reservation_id)


def get_reservation(
    reservation_id: ReservationID,
) -> Result[DbBungalowReservation, str]:
    """Return the reservation with that id."""
    db_reservation = find_reservation(reservation_id)

    if db_reservation is None:
        return Err(f'Unknown reservation ID "{reservation_id}"')

    return Ok(db_reservation)


def find_occupancy(
    occupancy_id: OccupancyID,
) -> DbBungalowOccupancy | None:
    """Return the occupancy with that id, or `None` if not found."""
    return db.session.get(DbBungalowOccupancy, occupancy_id)


def get_occupancy(
    occupancy_id: OccupancyID,
) -> Result[DbBungalowOccupancy, str]:
    """Return the occupancy with that id."""
    db_occupancy = find_occupancy(occupancy_id)

    if db_occupancy is None:
        return Err(f'Unknown occupancy ID "{occupancy_id}"')

    return Ok(db_occupancy)


def find_occupancy_for_bungalow(
    bungalow_id: BungalowID,
) -> DbBungalowOccupancy | None:
    """Return the occupancy for the bungalow with that id.

    Return `None` if either no bungalow with that ID or no occupation
    for the bungalow with that ID was found.
    """
    return db.session.execute(
        select(DbBungalowOccupancy).filter_by(bungalow_id=bungalow_id)
    ).scalar_one_or_none()


def get_product_id_for_occupancy(occupancy_id: OccupancyID) -> ProductID:
    """Return the shop product for the occupied bungalow's category."""
    return db.session.execute(
        select(DbBungalowCategory.product_id)
        .join(DbBungalow)
        .join(DbBungalowOccupancy)
        .filter(DbBungalowOccupancy.id == occupancy_id)
    ).scalar_one()


def find_occupancy_managed_by_user(
    party_id: PartyID, user_id: UserID
) -> DbBungalowOccupancy | None:
    """Try to find a bungalow occupancy managed by that user that party."""
    return db.session.scalars(
        select(DbBungalowOccupancy)
        .join(DbBungalow)
        .filter(DbBungalow.party_id == party_id)
        .filter(
            db.or_(
                DbBungalowOccupancy.occupied_by_id == user_id,
                DbBungalowOccupancy.managed_by_id == user_id,
            )
        )
    ).one_or_none()


def get_occupied_bungalows_for_party(party_id: PartyID) -> Sequence[DbBungalow]:
    """Return all occupied (but not reserved) bungalows for the party,
    ordered by number.
    """
    return (
        db.session.scalars(
            select(DbBungalow)
            .options(
                db.load_only(
                    DbBungalow.party_id,
                    DbBungalow.number,
                    DbBungalow._occupation_state,
                ),
                db.joinedload(DbBungalow.occupancy),
            )
            .filter_by(party_id=party_id)
            .filter_by(_occupation_state=BungalowOccupationState.occupied.name)
            .order_by(DbBungalow.number)
        )
        .unique()
        .all()
    )


def get_occupied_bungalow_numbers_and_titles(
    party_id: PartyID,
) -> Sequence[tuple[int, str]]:
    """Return the numbers and titles of all occupied bungalows for the
    party, ordered by number.
    """
    return (
        db.session.execute(
            select(
                DbBungalow.number,
                DbBungalowOccupancy.title,
            )
            .join(DbBungalowOccupancy)
            .filter(DbBungalow.party_id == party_id)
            .filter(
                DbBungalowOccupancy._state
                == BungalowOccupationState.occupied.name
            )
            .order_by(DbBungalow.number)
        )
        .tuples()
        .all()
    )


def has_user_occupied_any_bungalow(party_id: PartyID, user_id: UserID) -> bool:
    """Return `True` if the user has occupied a bungalow for the party."""
    count = (
        db.session.scalar(
            select(db.func.count(DbBungalowOccupancy.id))
            .join(DbBungalow)
            .filter(DbBungalow.party_id == party_id)
            .filter(DbBungalowOccupancy.occupied_by_id == user_id)
        )
        or 0
    )

    return count > 0


def get_occupant_slots_for_occupancies(
    occupancy_ids: set[OccupancyID],
) -> Sequence[tuple[OccupancyID, TicketID, UserID | None]]:
    """Return the occupant slots for multiple occupancies."""
    return (
        db.session.execute(
            select(DbBungalowOccupancy.id, DbTicket.id, DbTicket.used_by_id)
            .join(
                DbTicketBundle,
                DbTicketBundle.id == DbBungalowOccupancy.ticket_bundle_id,
            )
            .join(DbTicket)
            .filter(DbBungalowOccupancy.id.in_(occupancy_ids))
            .order_by(DbTicket.created_at)
        )
        .tuples()
        .all()
    )


def get_bungalow_for_ticket_bundle(
    ticket_bundle_id: TicketBundleID,
) -> DbBungalow:
    """Return the bungalow occupied by this ticket bundle."""
    return db.session.execute(
        select(DbBungalow)
        .join(DbBungalowOccupancy)
        .join(DbTicketBundle)
        .filter(DbTicketBundle.id == ticket_bundle_id)
    ).scalar_one()


def get_bungalows_for_ticket_bundles(
    ticket_bundle_ids: set[TicketBundleID],
) -> Sequence[tuple[TicketBundleID, DbBungalow]]:
    """Return the bungalows occupied by these ticket bundles."""
    return (
        db.session.execute(
            select(DbTicketBundle.id, DbBungalow)
            .join(
                DbBungalowOccupancy,
                DbBungalowOccupancy.bungalow_id == DbBungalow.id,
            )
            .join(DbTicketBundle)
            .filter(DbTicketBundle.id.in_(ticket_bundle_ids))
        )
        .tuples()
        .all()
    )


def appoint_bungalow_manager(
    occupancy_id: OccupancyID, new_manager_id: UserID, initiator_id: UserID
) -> Result[None, str]:
    """Appoint the user as the bungalow's new manager."""
    match get_occupancy(occupancy_id):
        case Ok(db_occupancy):
            pass
        case Err(e):
            return Err(e)

    db_occupancy.managed_by_id = new_manager_id

    db_log_entry = bungalow_log_service.build_entry(
        'manager-appointed',
        db_occupancy.bungalow_id,
        data={
            'initiator_id': str(initiator_id),
            'new_manager_id': str(new_manager_id),
        },
    )
    db.session.add(db_log_entry)

    db.session.commit()

    return Ok(None)


def set_internal_remark(
    occupancy_id: OccupancyID, remark: str | None
) -> Result[None, str]:
    """Set an internal remark."""
    match get_occupancy(occupancy_id):
        case Ok(db_occupancy):
            pass
        case Err(e):
            return Err(e)

    db_occupancy.internal_remark = remark

    db.session.commit()

    return Ok(None)


def update_description(
    occupancy_id: OccupancyID,
    title: str | None,
    description: str | None,
) -> Result[None, str]:
    """Update the occupancy's title and description."""
    match get_occupancy(occupancy_id):
        case Ok(db_occupancy):
            pass
        case Err(e):
            return Err(e)

    db_occupancy.title = title
    db_occupancy.description = description

    db.session.commit()

    return Ok(None)


def create_avatar_image(
    avatar_id: UUID, creator_id: UserID, image_type: ImageType
) -> DbBungalowAvatar:
    """Create avatar image for occupancy."""
    db_avatar = DbBungalowAvatar(avatar_id, creator_id, image_type)

    db.session.add(db_avatar)

    db.session.commit()

    return db_avatar


def assign_avatar_image(
    avatar_id: UUID, occupancy_id: OccupancyID
) -> Result[None, str]:
    """Assign avatar image to occupancy."""
    match get_occupancy(occupancy_id):
        case Ok(db_occupancy):
            pass
        case Err(e):
            return Err(e)

    db_occupancy.avatar_id = avatar_id

    db.session.commit()

    return Ok(None)


def remove_avatar_image(occupancy_id: OccupancyID) -> Result[None, str]:
    """Remove the occupancy's avatar image.

    The avatar will be unlinked from the bungalow, but the database record
    won't be removed, though.
    """
    match get_occupancy(occupancy_id):
        case Ok(db_occupancy):
            pass
        case Err(e):
            return Err(e)

    db_occupancy.avatar_id = None

    db.session.commit()

    return Ok(None)

"""
byceps.services.bungalow.bungalow_occupancy_service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2024 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from sqlalchemy import select

from byceps.database import db
from byceps.events.base import EventUser
from byceps.events.bungalow import (
    BungalowOccupancyMovedEvent,
    BungalowOccupiedEvent,
    BungalowReleasedEvent,
    BungalowReservedEvent,
)
from byceps.events.shop import ShopOrderPlacedEvent
from byceps.services.party.models import PartyID
from byceps.services.shop.article import article_service
from byceps.services.shop.article.models import Article
from byceps.services.shop.order.models.order import Order, Orderer
from byceps.services.shop.storefront.models import Storefront
from byceps.services.ticketing import (
    ticket_bundle_service,
    ticket_user_management_service,
)
from byceps.services.ticketing.dbmodels.ticket import DbTicket
from byceps.services.ticketing.dbmodels.ticket_bundle import DbTicketBundle
from byceps.services.ticketing.models.ticket import TicketBundleID
from byceps.services.user import user_service
from byceps.services.user.models.user import User, UserForAdmin, UserID
from byceps.util.result import Err, Ok, Result

from . import bungalow_log_service, bungalow_order_service, bungalow_service
from .dbmodels.bungalow import DbBungalow
from .dbmodels.category import DbBungalowCategory
from .dbmodels.occupancy import DbBungalowOccupancy, DbBungalowReservation
from .model_converters import _db_entity_to_occupancy, _db_entity_to_reservation
from .models.bungalow import BungalowID, BungalowOccupationState
from .models.occupation import (
    BungalowOccupancy,
    BungalowReservation,
    OccupancyID,
    OccupancyState,
    OccupantSlot,
    ReservationID,
)


def find_reservation(
    reservation_id: ReservationID,
) -> BungalowReservation | None:
    """Return the reservation with that id, or `None` if not found."""
    db_reservation = find_db_reservation(reservation_id)

    if db_reservation is None:
        return None

    return _db_entity_to_reservation(db_reservation)


def find_db_reservation(
    reservation_id: ReservationID,
) -> DbBungalowReservation | None:
    """Return the reservation with that id, or `None` if not found."""
    return db.session.get(DbBungalowReservation, reservation_id)


def get_reservation(
    reservation_id: ReservationID,
) -> Result[BungalowReservation, str]:
    """Return the reservation with that id."""
    reservation = find_reservation(reservation_id)

    if reservation is None:
        return Err(f'Unknown reservation ID "{reservation_id}"')

    return Ok(reservation)


def get_db_reservation(
    reservation_id: ReservationID,
) -> Result[DbBungalowReservation, str]:
    """Return the reservation with that id."""
    db_reservation = find_db_reservation(reservation_id)

    if db_reservation is None:
        return Err(f'Unknown reservation ID "{reservation_id}"')

    return Ok(db_reservation)


def find_occupancy(occupancy_id: OccupancyID) -> BungalowOccupancy | None:
    """Return the occupancy with that id, or `None` if not found."""
    db_occupancy = find_db_occupancy(occupancy_id)

    if db_occupancy is None:
        return None

    return _db_entity_to_occupancy(db_occupancy)


def find_db_occupancy(
    occupancy_id: OccupancyID,
) -> DbBungalowOccupancy | None:
    """Return the occupancy with that id, or `None` if not found."""
    return db.session.get(DbBungalowOccupancy, occupancy_id)


def get_occupancy(occupancy_id: OccupancyID) -> Result[BungalowOccupancy, str]:
    """Return the occupancy with that id."""
    occupancy = find_occupancy(occupancy_id)

    if occupancy is None:
        return Err(f'Unknown occupancy ID "{occupancy_id}"')

    return Ok(occupancy)


def get_db_occupancy(
    occupancy_id: OccupancyID,
) -> Result[DbBungalowOccupancy, str]:
    """Return the occupancy with that id."""
    db_occupancy = find_db_occupancy(occupancy_id)

    if db_occupancy is None:
        return Err(f'Unknown occupancy ID "{occupancy_id}"')

    return Ok(db_occupancy)


def find_occupancy_for_bungalow(
    bungalow_id: BungalowID,
) -> BungalowOccupancy | None:
    """Return the occupancy for the bungalow with that id.

    Return `None` if either no bungalow with that ID or no occupation
    for the bungalow with that ID was found.
    """
    db_occupancy = db.session.execute(
        select(DbBungalowOccupancy).filter_by(bungalow_id=bungalow_id)
    ).scalar_one_or_none()

    if db_occupancy is None:
        return None

    return _db_entity_to_occupancy(db_occupancy)


def reserve_bungalow(
    bungalow_id: BungalowID, occupier: User
) -> Result[
    tuple[BungalowReservation, BungalowOccupancy, BungalowReservedEvent], str
]:
    """Create a reservation for this bungalow."""
    db_bungalow = bungalow_service.get_db_bungalow(bungalow_id)
    if not db_bungalow.available:
        return Err('Bungalow is not available')

    db_bungalow.occupation_state = BungalowOccupationState.reserved

    db_reservation = DbBungalowReservation(db_bungalow.id, occupier.id)
    db.session.add(db_reservation)

    db_occupancy = DbBungalowOccupancy(
        db_bungalow.id, occupier.id, OccupancyState.reserved
    )
    db_occupancy.title = f'Bungalow {db_bungalow.number}'
    db.session.add(db_occupancy)

    db_log_entry = bungalow_log_service.build_entry(
        'bungalow-reserved',
        db_bungalow.id,
        data={'initiator_id': str(occupier.id)},
    )
    db.session.add(db_log_entry)

    db.session.commit()

    bungalow_reserved_event = BungalowReservedEvent(
        occurred_at=datetime.utcnow(),
        initiator=EventUser.from_user(occupier),
        bungalow_id=db_bungalow.id,
        bungalow_number=db_bungalow.number,
        occupier=EventUser.from_user(occupier),
    )

    reservation = _db_entity_to_reservation(db_reservation)
    occupancy = _db_entity_to_occupancy(db_occupancy)

    return Ok((reservation, occupancy, bungalow_reserved_event))


def place_bungalow_order(
    storefront: Storefront,
    reservation_id: ReservationID,
    occupancy_id: OccupancyID,
    orderer: Orderer,
) -> Result[tuple[Order, ShopOrderPlacedEvent], str]:
    """Place an order for the bungalow."""
    db_reservation_result = get_db_reservation(reservation_id)
    if db_reservation_result.is_err():
        return Err(db_reservation_result.unwrap_err())

    db_reservation = db_reservation_result.unwrap()

    db_occupancy_result = get_db_occupancy(occupancy_id)
    if db_occupancy_result.is_err():
        return Err(db_occupancy_result.unwrap_err())

    db_occupancy = db_occupancy_result.unwrap()

    article = _get_article_for_occupancy(occupancy_id)

    placement_result = bungalow_order_service.place_bungalow_order(
        storefront, article, orderer
    )
    if placement_result.is_err():
        return Err('Placing the order for the bungalow failed.')

    order, order_placed_event = placement_result.unwrap()

    db_reservation.order_number = order.order_number
    db_occupancy.order_number = order.order_number
    db.session.commit()

    return Ok((order, order_placed_event))


def _get_article_for_occupancy(occupancy_id: OccupancyID) -> Article:
    """Return the shop article for the occupied bungalow's category."""
    article_id = db.session.execute(
        select(DbBungalowCategory.article_id)
        .join(DbBungalow)
        .join(DbBungalowOccupancy)
        .filter(DbBungalowOccupancy.id == occupancy_id)
    ).scalar_one()

    return article_service.get_article(article_id)


def occupy_bungalow(
    reservation_id: ReservationID,
    occupancy_id: OccupancyID,
    ticket_bundle_id: TicketBundleID,
) -> Result[tuple[BungalowOccupancy, BungalowOccupiedEvent], str]:
    """Mark the bungalow as occupied."""
    db_reservation_result = get_db_reservation(reservation_id)
    if db_reservation_result.is_err():
        return Err(db_reservation_result.unwrap_err())

    db_reservation = db_reservation_result.unwrap()

    db_occupancy_result = get_db_occupancy(occupancy_id)
    if db_occupancy_result.is_err():
        return Err(db_occupancy_result.unwrap_err())

    db_occupancy = db_occupancy_result.unwrap()

    db_bungalow = bungalow_service.get_db_bungalow(db_occupancy.bungalow_id)

    if db_occupancy.state != OccupancyState.reserved:
        return Err(
            "Not in state 'reserved', cannot change to state 'occupied'."
        )

    occupier_id = db_occupancy.occupied_by_id

    db_bungalow.occupation_state = BungalowOccupationState.occupied

    db.session.delete(db_reservation)

    db_occupancy.state = OccupancyState.occupied
    db_occupancy.ticket_bundle_id = ticket_bundle_id

    db_log_entry = bungalow_log_service.build_entry(
        'bungalow-occupied',
        db_bungalow.id,
        data={'initiator_id': str(occupier_id)},
    )
    db.session.add(db_log_entry)

    db.session.commit()

    occupancy = _db_entity_to_occupancy(db_occupancy)

    occupier = user_service.get_user(occupier_id)

    event = BungalowOccupiedEvent(
        occurred_at=datetime.utcnow(),
        initiator=EventUser.from_user(occupier),
        bungalow_id=db_bungalow.id,
        bungalow_number=db_bungalow.number,
        occupier=EventUser.from_user(occupier),
    )

    return Ok((occupancy, event))


def move_occupancy(
    occupancy_id: OccupancyID,
    target_bungalow_id: BungalowID,
    initiator: User,
) -> Result[BungalowOccupancyMovedEvent, str]:
    """Move occupancy to another bungalow and reset the source bungalow."""
    db_occupancy_result = get_db_occupancy(occupancy_id)
    if db_occupancy_result.is_err():
        return Err(db_occupancy_result.unwrap_err())

    db_occupancy = db_occupancy_result.unwrap()

    db_source_bungalow = db_occupancy.bungalow
    db_target_bungalow = bungalow_service.get_db_bungalow(target_bungalow_id)

    if db_occupancy.pinned:
        return Err(
            f'Bungalow {db_source_bungalow.number} ist fest zugewiesen und '
            'kann nicht gewechselt werden.'
        )

    if db_target_bungalow.id == db_source_bungalow.id:
        # Source and target bungalow are the same; nothing to do.
        return Err(
            f'Die Belegung ist bereits Bungalow {db_source_bungalow.number} zugewiesen.'
        )

    # Abort if source and target bungalows have different capacities.
    if (
        db_source_bungalow.category.capacity
        != db_target_bungalow.category.capacity
    ):
        return Err('Der Ziel-Bungalow bietet eine unpassende Anzahl Plätze.')

    # Abort if source and target bungalows belong to different ticket
    # categories.
    if (
        db_source_bungalow.category.ticket_category_id
        != db_target_bungalow.category.ticket_category_id
    ):
        return Err(
            'Der Ziel-Bungalow gehört zu einer anderen Ticket-Kategorie.'
        )

    if db_target_bungalow.reserved_or_occupied:
        return Err(f'Bungalow {db_target_bungalow.number} ist bereits belegt.')

    db_target_bungalow.occupation_state = db_source_bungalow.occupation_state
    db_source_bungalow.occupation_state = BungalowOccupationState.available

    db_occupancy.bungalow = db_target_bungalow

    db_log_entry = bungalow_log_service.build_entry(
        'occupancy-moved-away',
        db_source_bungalow.id,
        data={
            'initiator_id': str(initiator.id),
            'target_bungalow_id': str(db_target_bungalow.id),
            'target_bungalow_number': db_target_bungalow.number,
        },
    )
    db.session.add(db_log_entry)

    db_log_entry = bungalow_log_service.build_entry(
        'occupancy-moved-here',
        db_target_bungalow.id,
        data={
            'initiator_id': str(initiator.id),
            'source_bungalow_id': str(db_source_bungalow.id),
            'source_bungalow_number': db_source_bungalow.number,
        },
    )
    db.session.add(db_log_entry)

    db.session.commit()

    return Ok(
        BungalowOccupancyMovedEvent(
            occurred_at=datetime.utcnow(),
            initiator=EventUser.from_user(initiator),
            source_bungalow_id=db_source_bungalow.id,
            source_bungalow_number=db_source_bungalow.number,
            target_bungalow_id=db_target_bungalow.id,
            target_bungalow_number=db_target_bungalow.number,
        )
    )


def release_bungalow(
    bungalow_id: BungalowID, *, initiator: User | None = None
) -> BungalowReleasedEvent:
    """Release a bungalow from its occupancy so it becomes available
    again.
    """
    db_bungalow = bungalow_service.get_db_bungalow(bungalow_id)

    db_bungalow.occupation_state = BungalowOccupationState.available

    if db_bungalow.reservation:
        db.session.delete(db_bungalow.reservation)

    db.session.delete(db_bungalow.occupancy)

    log_entry_data = {}
    if initiator:
        log_entry_data = {'initiator_id': str(initiator.id)}
    db_log_entry = bungalow_log_service.build_entry(
        'bungalow-released', db_bungalow.id, log_entry_data
    )
    db.session.add(db_log_entry)

    db.session.commit()

    return BungalowReleasedEvent(
        occurred_at=datetime.utcnow(),
        initiator=EventUser.from_user(initiator) if initiator else None,
        bungalow_id=db_bungalow.id,
        bungalow_number=db_bungalow.number,
    )


def appoint_bungalow_manager(
    occupancy_id: OccupancyID, new_manager: User, initiator: User
) -> Result[None, str]:
    """Appoint the user as the bungalow's new manager."""
    db_occupancy_result = get_db_occupancy(occupancy_id)
    if db_occupancy_result.is_err():
        return Err(db_occupancy_result.unwrap_err())

    db_occupancy = db_occupancy_result.unwrap()

    # Set bungalow manager.
    db_occupancy.managed_by_id = new_manager.id
    db_log_entry = bungalow_log_service.build_entry(
        'manager-appointed',
        db_occupancy.bungalow_id,
        data={
            'initiator_id': str(initiator.id),
            'new_manager_id': str(new_manager.id),
        },
    )
    db.session.add(db_log_entry)
    db.session.commit()

    # Set tickets' user manager.
    ticket_bundle_id = db_occupancy.ticket_bundle.id
    tickets = ticket_bundle_service.get_tickets_for_bundle(ticket_bundle_id)
    for ticket in tickets:
        ticket_user_management_service.appoint_user_manager(
            ticket.id, new_manager.id, initiator.id
        )

    return Ok(None)


def set_internal_remark(
    occupancy_id: OccupancyID, remark: str | None
) -> Result[None, str]:
    """Set an internal remark."""
    db_occupancy_result = get_db_occupancy(occupancy_id)
    if db_occupancy_result.is_err():
        return Err(db_occupancy_result.unwrap_err())

    db_occupancy = db_occupancy_result.unwrap()

    db_occupancy.internal_remark = remark
    db.session.commit()

    return Ok(None)


def find_occupancy_managed_by_user(
    party_id: PartyID, user_id: UserID
) -> DbBungalow | None:
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


def get_occupied_bungalows_for_party(party_id: PartyID) -> list[DbBungalow]:
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
) -> list[tuple[int, str]]:
    """Return the numbers and titles of all occupied bungalows for the
    party, ordered by number.
    """
    return db.session.execute(
        select(
            DbBungalow.number,
            DbBungalowOccupancy.title,
        )
        .join(DbBungalowOccupancy)
        .filter(DbBungalow.party_id == party_id)
        .filter(
            DbBungalowOccupancy._state == BungalowOccupationState.occupied.name
        )
        .order_by(DbBungalow.number)
    ).all()


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


def get_occupant_slots_for_occupancy(
    occupancy_id: OccupancyID,
) -> list[OccupantSlot]:
    """Return the occupant slots for an occupancy."""
    occupant_slots_by_occupancy_id = get_occupant_slots_for_occupancies(
        {occupancy_id}
    )
    return occupant_slots_by_occupancy_id[occupancy_id]


def get_occupant_slots_for_occupancies(
    occupancy_ids: set[OccupancyID], *, for_admin: bool = False
) -> dict[OccupancyID, list[OccupantSlot]]:
    """Return the occupant slots for multiple occupancies."""
    rows = db.session.execute(
        select(DbBungalowOccupancy.id, DbTicket.id, DbTicket.used_by_id)
        .join(
            DbTicketBundle,
            DbTicketBundle.id == DbBungalowOccupancy.ticket_bundle_id,
        )
        .join(DbTicket)
        .filter(DbBungalowOccupancy.id.in_(occupancy_ids))
        .order_by(DbTicket.created_at)
    ).all()

    user_ids = {user_id for _, _, user_id in rows if user_id is not None}
    users: set[User] | set[UserForAdmin]
    if for_admin:
        users = user_service.get_users_for_admin(user_ids)
    else:
        users = user_service.get_users(user_ids, include_avatars=True)
    users_by_id = {user.id: user for user in users}

    occupant_slots_by_occupancy_id = defaultdict(list)
    for occupancy_id, ticket_id, user_id in rows:
        occupant = users_by_id[user_id] if user_id else None
        occupant_slot = OccupantSlot(ticket_id=ticket_id, occupant=occupant)
        occupant_slots_by_occupancy_id[occupancy_id].append(occupant_slot)

    return dict(occupant_slots_by_occupancy_id)


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
) -> dict[TicketBundleID, DbBungalow]:
    """Return the bungalows occupied by these ticket bundles."""
    rows = (
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

    return dict(rows)

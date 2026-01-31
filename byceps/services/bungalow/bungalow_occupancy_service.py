"""
byceps.services.bungalow.bungalow_occupancy_service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime

from byceps.database import db
from byceps.services.party.models import PartyID
from byceps.services.shop.order import order_command_service, order_service
from byceps.services.shop.order.email import order_email_service
from byceps.services.shop.order.events import ShopOrderPlacedEvent
from byceps.services.shop.order.models.order import Order, Orderer
from byceps.services.shop.product import product_service
from byceps.services.shop.product.models import Product, ProductType
from byceps.services.shop.storefront.models import Storefront
from byceps.services.ticketing import (
    ticket_bundle_service,
    ticket_user_management_service,
)
from byceps.services.ticketing.models.ticket import TicketBundleID
from byceps.services.user import user_service
from byceps.services.user.models import User, UserForAdmin, UserID
from byceps.util.result import Err, Ok, Result
from byceps.util.uuid import generate_uuid7

from . import (
    bungalow_log_service,
    bungalow_occupancy_repository,
    bungalow_order_service,
    bungalow_service,
)
from .dbmodels.bungalow import DbBungalow
from .dbmodels.occupancy import DbBungalowOccupancy, DbBungalowReservation
from .events import (
    BungalowOccupancyDescriptionUpdatedEvent,
    BungalowOccupancyMovedEvent,
    BungalowOccupiedEvent,
    BungalowReleasedEvent,
    BungalowReservedEvent,
)
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
    db_reservation = bungalow_occupancy_repository.find_reservation(
        reservation_id
    )

    if db_reservation is None:
        return None

    return _db_entity_to_reservation(db_reservation)


def get_reservation(
    reservation_id: ReservationID,
) -> Result[BungalowReservation, str]:
    """Return the reservation with that id."""
    reservation = find_reservation(reservation_id)

    if reservation is None:
        return Err(f'Unknown reservation ID "{reservation_id}"')

    return Ok(reservation)


def find_occupancy(occupancy_id: OccupancyID) -> BungalowOccupancy | None:
    """Return the occupancy with that id, or `None` if not found."""
    db_occupancy = bungalow_occupancy_repository.find_occupancy(occupancy_id)

    if db_occupancy is None:
        return None

    return _db_entity_to_occupancy(db_occupancy)


def get_occupancy(occupancy_id: OccupancyID) -> Result[BungalowOccupancy, str]:
    """Return the occupancy with that id."""
    occupancy = find_occupancy(occupancy_id)

    if occupancy is None:
        return Err(f'Unknown occupancy ID "{occupancy_id}"')

    return Ok(occupancy)


def find_occupancy_for_bungalow(
    bungalow_id: BungalowID,
) -> BungalowOccupancy | None:
    """Return the occupancy for the bungalow with that id.

    Return `None` if either no bungalow with that ID or no occupation
    for the bungalow with that ID was found.
    """
    db_occupancy = bungalow_occupancy_repository.find_occupancy_for_bungalow(
        bungalow_id
    )

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

    reservation_id = ReservationID(generate_uuid7())
    db_reservation = DbBungalowReservation(
        reservation_id, db_bungalow.id, occupier.id
    )
    db.session.add(db_reservation)

    occupancy_id = OccupancyID(generate_uuid7())
    db_occupancy = DbBungalowOccupancy(
        occupancy_id, db_bungalow.id, occupier.id, OccupancyState.reserved
    )
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
        initiator=occupier,
        bungalow_id=db_bungalow.id,
        bungalow_number=db_bungalow.number,
        occupier=occupier,
    )

    reservation = _db_entity_to_reservation(db_reservation)
    occupancy = _db_entity_to_occupancy(db_occupancy)

    return Ok((reservation, occupancy, bungalow_reserved_event))


def place_bungalow_with_preselection_order(
    storefront: Storefront,
    reservation_id: ReservationID,
    occupancy_id: OccupancyID,
    orderer: Orderer,
) -> Result[tuple[Order, ShopOrderPlacedEvent], str]:
    """Place an order for the bungalow."""
    match bungalow_occupancy_repository.get_reservation(reservation_id):
        case Ok(db_reservation):
            pass
        case Err(reservation_error):
            return Err(reservation_error)

    match bungalow_occupancy_repository.get_occupancy(occupancy_id):
        case Ok(db_occupancy):
            pass
        case Err(occupancy_lookup_error):
            return Err(occupancy_lookup_error)

    product = _get_product_for_occupancy(occupancy_id)

    match bungalow_order_service.place_bungalow_order(
        storefront, product, orderer
    ):
        case Ok((order, order_placed_event)):
            pass
        case Err(_):
            return Err('Placing the order for the bungalow failed.')

    for line_item in order.line_items:
        if line_item.product_type == ProductType.bungalow_with_preselection:
            data = line_item.processing_result
            data['bungalow_reservation_id'] = str(reservation_id)
            data['bungalow_occupancy_id'] = str(occupancy_id)
            order_command_service.update_line_item_processing_result(
                line_item.id, data
            )

    db_reservation.order_number = order.order_number
    db_occupancy.order_number = order.order_number
    db.session.commit()

    return Ok((order, order_placed_event))


def _get_product_for_occupancy(occupancy_id: OccupancyID) -> Product:
    """Return the shop product for the occupied bungalow's category."""
    product_id = bungalow_occupancy_repository.get_product_id_for_occupancy(
        occupancy_id
    )
    return product_service.get_product(product_id)


def transfer_reservation(
    db_bungalow: DbBungalow, recipient: User, initiator: User
) -> Result[None, str]:
    """Transfer bungalow order and reservation to another user."""
    if not db_bungalow.reserved:
        return Err("'Bungalow is not in state 'reserved'.")

    order = order_service.find_order_by_order_number(
        db_bungalow.occupancy.order_number
    )

    if not order:
        return Err('Order {order.order_number} not found.')

    if not order.is_open:
        return Err(f'Order {order.order_number} is not open.')

    recipient_orderer = _build_recipient_orderer(recipient)

    # Notify original orderer of (from their perspective) cancellation.
    # Do this before changing the order.
    order_email_service.send_email_for_canceled_order_to_orderer(order)

    # Update order with new orderer.
    match order_command_service.update_orderer(
        order.id, recipient_orderer, initiator
    ):
        case Ok(updated_order):
            pass
        case Err(update_error):
            return Err(update_error)

    # Set new bungalow occupier.
    db_bungalow.occupancy.occupied_by_id = recipient.id
    db_bungalow.reservation.reserved_by = recipient.id
    db.session.commit()

    # Notify new orderer of order transferred to them.
    order_email_service.send_email_for_incoming_order_to_orderer(updated_order)

    return Ok(None)


def _build_recipient_orderer(recipient: User) -> Orderer:
    user_detail = user_service.get_detail(recipient.id)

    if (
        (user_detail.first_name is None)
        or (user_detail.last_name is None)
        or (user_detail.country is None)
        or (user_detail.postal_code is None)
        or (user_detail.city is None)
        or (user_detail.street is None)
    ):
        raise ValueError('User details incomplete')

    return Orderer(
        user=recipient,
        company=None,
        first_name=user_detail.first_name,
        last_name=user_detail.last_name,
        country=user_detail.country,
        postal_code=user_detail.postal_code,
        city=user_detail.city,
        street=user_detail.street,
    )


def occupy_bungalow(
    reservation_id: ReservationID,
    occupancy_id: OccupancyID,
    ticket_bundle_id: TicketBundleID,
) -> Result[tuple[BungalowOccupancy, BungalowOccupiedEvent], str]:
    """Mark the bungalow as occupied."""
    match bungalow_occupancy_repository.get_reservation(reservation_id):
        case Ok(db_reservation):
            pass
        case Err(reservation_lookup_error):
            return Err(reservation_lookup_error)

    match bungalow_occupancy_repository.get_occupancy(occupancy_id):
        case Ok(db_occupancy):
            pass
        case Err(occupancy_lookup_error):
            return Err(occupancy_lookup_error)

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
        initiator=occupier,
        bungalow_id=db_bungalow.id,
        bungalow_number=db_bungalow.number,
        occupier=occupier,
    )

    return Ok((occupancy, event))


def move_occupancy(
    occupancy_id: OccupancyID,
    target_bungalow_id: BungalowID,
    initiator: User,
) -> Result[BungalowOccupancyMovedEvent, str]:
    """Move occupancy to another bungalow and reset the source bungalow."""
    match bungalow_occupancy_repository.get_occupancy(occupancy_id):
        case Ok(db_occupancy):
            pass
        case Err(occupancy_lookup_error):
            return Err(occupancy_lookup_error)

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
            initiator=initiator,
            source_bungalow_id=db_source_bungalow.id,
            source_bungalow_number=db_source_bungalow.number,
            target_bungalow_id=db_target_bungalow.id,
            target_bungalow_number=db_target_bungalow.number,
        )
    )


def release_bungalow(
    occupancy_id: OccupancyID, initiator: User
) -> Result[BungalowReleasedEvent, str]:
    """Release the bungalow occupied by the occupancy so it becomes available
    again.
    """
    match get_occupancy(occupancy_id):
        case Ok(occupancy):
            pass
        case Err(e):
            return Err(e)

    try:
        db_bungalow = bungalow_service.get_db_bungalow(occupancy.bungalow_id)
    except ValueError:
        return Err(f'No bungalow found with ID "{occupancy.bungalow_id}"')

    db_bungalow.occupation_state = BungalowOccupationState.available

    if db_bungalow.reservation:
        db.session.delete(db_bungalow.reservation)

    db.session.delete(db_bungalow.occupancy)

    log_entry_data = {'initiator_id': str(initiator.id)}
    db_log_entry = bungalow_log_service.build_entry(
        'bungalow-released', db_bungalow.id, log_entry_data
    )
    db.session.add(db_log_entry)

    db.session.commit()

    event = BungalowReleasedEvent(
        occurred_at=datetime.utcnow(),
        initiator=initiator,
        bungalow_id=db_bungalow.id,
        bungalow_number=db_bungalow.number,
    )

    return Ok(event)


def appoint_bungalow_manager(
    occupancy_id: OccupancyID, new_manager: User, initiator: User
) -> Result[None, str]:
    """Appoint the user as the bungalow's new manager."""
    match get_occupancy(occupancy_id):
        case Ok(occupancy):
            pass
        case Err(occupancy_lookup_error):
            return Err(occupancy_lookup_error)

    if occupancy.state != OccupancyState.occupied:
        return Err('Bungalow is not occupied, cannot appoint bungalow manager.')

    ticket_bundle_id = occupancy.ticket_bundle_id
    if ticket_bundle_id is None:
        return Err('Occupancy has no ticket bundle assigned.')

    # Set bungalow manager.
    match bungalow_occupancy_repository.appoint_bungalow_manager(
        occupancy.id, new_manager.id, initiator.id
    ):
        case Ok(None):
            pass
        case Err(appointment_error):
            return Err(appointment_error)

    # Set tickets' user manager.
    tickets = ticket_bundle_service.get_tickets_for_bundle(ticket_bundle_id)
    for ticket in tickets:
        ticket_user_management_service.appoint_user_manager(
            ticket.id, new_manager, initiator
        )

    return Ok(None)


def set_internal_remark(
    occupancy_id: OccupancyID, remark: str | None
) -> Result[None, str]:
    """Set an internal remark."""
    return bungalow_occupancy_repository.set_internal_remark(
        occupancy_id, remark
    )


def update_description(
    occupancy_id: OccupancyID,
    title: str | None,
    description: str | None,
    initiator: User,
) -> Result[BungalowOccupancyDescriptionUpdatedEvent, str]:
    """Update the occupancy's title and description."""
    match get_occupancy(occupancy_id):
        case Ok(occupancy):
            pass
        case Err(occupancy_lookup_error):
            return Err(occupancy_lookup_error)

    match bungalow_occupancy_repository.update_description(
        occupancy.id, title, description
    ):
        case Ok(_):
            pass
        case Err(e):
            return Err(e)

    updated_at = datetime.utcnow()
    bungalow = bungalow_service.get_db_bungalow(occupancy.bungalow_id)

    event = BungalowOccupancyDescriptionUpdatedEvent(
        occurred_at=updated_at,
        initiator=initiator,
        bungalow_id=bungalow.id,
        bungalow_number=bungalow.number,
    )

    return Ok(event)


def find_occupancy_managed_by_user(
    party_id: PartyID, user_id: UserID
) -> DbBungalowOccupancy | None:
    """Try to find a bungalow occupancy managed by that user that party."""
    return bungalow_occupancy_repository.find_occupancy_managed_by_user(
        party_id, user_id
    )


def get_occupied_bungalows_for_party(party_id: PartyID) -> Sequence[DbBungalow]:
    """Return all occupied (but not reserved) bungalows for the party,
    ordered by number.
    """
    return bungalow_occupancy_repository.get_occupied_bungalows_for_party(
        party_id
    )


def get_occupied_bungalow_numbers_and_titles(
    party_id: PartyID,
) -> Sequence[tuple[int, str]]:
    """Return the numbers and titles of all occupied bungalows for the
    party, ordered by number.
    """
    return (
        bungalow_occupancy_repository.get_occupied_bungalow_numbers_and_titles(
            party_id
        )
    )


def has_user_occupied_any_bungalow(party_id: PartyID, user_id: UserID) -> bool:
    """Return `True` if the user has occupied a bungalow for the party."""
    return bungalow_occupancy_repository.has_user_occupied_any_bungalow(
        party_id, user_id
    )


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
    rows = bungalow_occupancy_repository.get_occupant_slots_for_occupancies(
        occupancy_ids
    )

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
    return bungalow_occupancy_repository.get_bungalow_for_ticket_bundle(
        ticket_bundle_id
    )


def get_bungalows_for_ticket_bundles(
    ticket_bundle_ids: set[TicketBundleID],
) -> dict[TicketBundleID, DbBungalow]:
    """Return the bungalows occupied by these ticket bundles."""
    rows = bungalow_occupancy_repository.get_bungalows_for_ticket_bundles(
        ticket_bundle_ids
    )

    return dict(rows)

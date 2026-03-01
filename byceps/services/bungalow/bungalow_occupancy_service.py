"""
byceps.services.bungalow.bungalow_occupancy_service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from __future__ import annotations

from collections import defaultdict
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

from . import (
    bungalow_log_service,
    bungalow_occupancy_domain_service,
    bungalow_occupancy_repository,
    bungalow_order_service,
    bungalow_service,
)
from .dbmodels.bungalow import DbBungalow
from .dbmodels.occupancy import DbBungalowOccupancy
from .events import (
    BungalowOccupancyDescriptionUpdatedEvent,
    BungalowOccupancyMovedEvent,
    BungalowOccupiedEvent,
    BungalowReleasedEvent,
    BungalowReservedEvent,
)
from .model_converters import (
    _db_entity_to_bungalow,
    _db_entity_to_occupancy,
    _db_entity_to_reservation,
)
from .models.bungalow import BungalowID, BungalowOccupationState
from .models.log import BungalowLogEntry
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
    """Return the reservation with that ID, or `None` if not found."""
    db_reservation = bungalow_occupancy_repository.find_reservation(
        reservation_id
    )

    if db_reservation is None:
        return None

    return _db_entity_to_reservation(db_reservation)


def get_reservation(
    reservation_id: ReservationID,
) -> Result[BungalowReservation, str]:
    """Return the reservation with that ID."""
    reservation = find_reservation(reservation_id)

    if reservation is None:
        return Err(f'Unknown reservation ID "{reservation_id}"')

    return Ok(reservation)


def find_occupancy(occupancy_id: OccupancyID) -> BungalowOccupancy | None:
    """Return the occupancy with that ID, or `None` if not found."""
    db_occupancy = bungalow_occupancy_repository.find_occupancy(occupancy_id)

    if db_occupancy is None:
        return None

    return _db_entity_to_occupancy(db_occupancy)


def get_occupancy(occupancy_id: OccupancyID) -> Result[BungalowOccupancy, str]:
    """Return the occupancy with that ID."""
    occupancy = find_occupancy(occupancy_id)

    if occupancy is None:
        return Err(f'Unknown occupancy ID "{occupancy_id}"')

    return Ok(occupancy)


def find_occupancy_for_ticket_bundle(
    ticket_bundle_id: TicketBundleID,
) -> BungalowOccupancy | None:
    """Return the occupancy for the ticket bundle with that ID.

    Return `None` if either no ticket bundle with that ID or no occupation
    for the ticket bundle with that ID was found.
    """
    db_occupancy = (
        bungalow_occupancy_repository.find_occupancy_for_ticket_bundle(
            ticket_bundle_id
        )
    )

    if db_occupancy is None:
        return None

    return _db_entity_to_occupancy(db_occupancy)


def find_occupancy_for_bungalow(
    bungalow_id: BungalowID,
) -> BungalowOccupancy | None:
    """Return the occupancy for the bungalow with that ID.

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
    bungalow = _db_entity_to_bungalow(db_bungalow)

    match bungalow_occupancy_domain_service.reserve_bungalow(
        bungalow, occupier
    ):
        case Ok((reservation, occupancy, event, log_entry)):
            pass
        case Err(e):
            return Err(e)

    bungalow_occupancy_repository.reserve_bungalow(
        db_bungalow, reservation, occupancy, log_entry
    )

    return Ok((reservation, occupancy, event))


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
    bungalow_occupancy_repository.transfer_reservation(
        db_bungalow, recipient.id
    )

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


def occupy_reserved_bungalow(
    reservation_id: ReservationID,
    occupancy_id: OccupancyID,
    ticket_bundle_id: TicketBundleID,
) -> Result[tuple[BungalowOccupancy, BungalowOccupiedEvent], str]:
    """Mark a reserved bungalow as occupied."""
    match get_occupancy(occupancy_id):
        case Ok(current_occupancy):
            pass
        case Err(occupancy_lookup_error):
            return Err(occupancy_lookup_error)

    db_bungalow = bungalow_service.get_db_bungalow(
        current_occupancy.bungalow_id
    )

    bungalow = _db_entity_to_bungalow(db_bungalow)

    db_ticket_bundle = ticket_bundle_service.get_bundle(ticket_bundle_id)
    ticket_bundle = ticket_bundle_service.db_entity_to_ticket_bundle(
        db_ticket_bundle
    )

    occupier_id = current_occupancy.occupied_by_id
    occupier = user_service.get_user(occupier_id)

    match bungalow_occupancy_domain_service.occupy_reserved_bungalow(
        bungalow,
        current_occupancy,
        occupier,
        ticket_bundle,
    ):
        case Ok((updated_occupancy, event, log_entry)):
            pass
        case Err(e):
            return Err(e)

    bungalow_occupancy_repository.occupy_reserved_bungalow(
        db_bungalow, reservation_id, updated_occupancy, log_entry
    )

    return Ok((updated_occupancy, event))


def occupy_bungalow_without_reservation(
    bungalow_id: BungalowID,
    ticket_bundle_id: TicketBundleID,
) -> Result[tuple[BungalowOccupancy, BungalowOccupiedEvent], str]:
    """Occupy the bungalow without previous reservation."""
    db_bungalow = bungalow_service.get_db_bungalow(bungalow_id)

    bungalow = _db_entity_to_bungalow(db_bungalow)

    db_ticket_bundle = ticket_bundle_service.get_bundle(ticket_bundle_id)
    ticket_bundle = ticket_bundle_service.db_entity_to_ticket_bundle(
        db_ticket_bundle
    )
    occupier = ticket_bundle.owned_by
    order_number = db_ticket_bundle.tickets[0].order_number

    match bungalow_occupancy_domain_service.occupy_bungalow_without_reservation(
        bungalow,
        occupier,
        order_number,
        ticket_bundle,
    ):
        case Ok((occupancy, event, log_entry)):
            pass
        case Err(e):
            return Err(e)

    bungalow_occupancy_repository.occupy_bungalow_without_reservation(
        db_bungalow, occupancy, log_entry
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

    log_entry = _build_bungalow_occupany_moved_away_log_entry(
        db_source_bungalow.id,
        db_target_bungalow.id,
        db_target_bungalow.number,
        initiator,
    )
    db_log_entry = bungalow_log_service.to_db_entry(log_entry)
    db.session.add(db_log_entry)

    log_entry = _build_bungalow_occupany_moved_here_log_entry(
        db_target_bungalow.id,
        db_source_bungalow.id,
        db_source_bungalow.number,
        initiator,
    )
    db_log_entry = bungalow_log_service.to_db_entry(log_entry)
    db.session.add(db_log_entry)

    db.session.commit()

    event = _build_bungalow_occupancy_moved_event(
        initiator,
        db_source_bungalow.id,
        db_source_bungalow.number,
        db_target_bungalow.id,
        db_target_bungalow.number,
    )

    return Ok(event)


def _build_bungalow_occupany_moved_away_log_entry(
    source_bungalow_id: BungalowID,
    target_bungalow_id: BungalowID,
    target_bungalow_number: int,
    initiator: User,
) -> BungalowLogEntry:
    return bungalow_log_service.build_entry(
        'occupancy-moved-away',
        source_bungalow_id,
        data={
            'target_bungalow_id': str(target_bungalow_id),
            'target_bungalow_number': target_bungalow_number,
            'initiator_id': str(initiator.id),
        },
    )


def _build_bungalow_occupany_moved_here_log_entry(
    target_bungalow_id: BungalowID,
    source_bungalow_id: BungalowID,
    source_bungalow_number: int,
    initiator: User,
) -> BungalowLogEntry:
    return bungalow_log_service.build_entry(
        'occupancy-moved-here',
        target_bungalow_id,
        data={
            'source_bungalow_id': str(source_bungalow_id),
            'source_bungalow_number': source_bungalow_number,
            'initiator_id': str(initiator.id),
        },
    )


def _build_bungalow_occupancy_moved_event(
    initiator: User,
    source_bungalow_id: BungalowID,
    source_bungalow_number: int,
    target_bungalow_id: BungalowID,
    target_bungalow_number: int,
) -> BungalowOccupancyMovedEvent:
    return BungalowOccupancyMovedEvent(
        occurred_at=datetime.utcnow(),
        initiator=initiator,
        source_bungalow_id=source_bungalow_id,
        source_bungalow_number=source_bungalow_number,
        target_bungalow_id=target_bungalow_id,
        target_bungalow_number=target_bungalow_number,
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

    bungalow = _db_entity_to_bungalow(db_bungalow)

    match bungalow_occupancy_domain_service.release_bungalow(
        bungalow, initiator
    ):
        case Ok((event, log_entry)):
            pass
        case Err(e):
            return Err(e)

    db_log_entry = bungalow_log_service.to_db_entry(log_entry)

    bungalow_occupancy_repository.release_bungalow(db_bungalow, db_log_entry)

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
    log_entry = _build_manager_appointed_log_entry(
        occupancy.bungalow_id, new_manager, initiator
    )
    db_log_entry = bungalow_log_service.to_db_entry(log_entry)
    match bungalow_occupancy_repository.appoint_bungalow_manager(
        occupancy.id, new_manager.id, db_log_entry
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


def _build_manager_appointed_log_entry(
    bungalow_id: BungalowID, new_manager: User, initiator: User
) -> BungalowLogEntry:
    return bungalow_log_service.build_entry(
        'manager-appointed',
        bungalow_id,
        data={
            'new_manager_id': str(new_manager.id),
            'initiator_id': str(initiator.id),
        },
    )


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
    db_bungalow = bungalow_service.get_db_bungalow(occupancy.bungalow_id)

    event = _build_bungalow_occupancy_description_updated_event(
        updated_at, initiator, db_bungalow.id, db_bungalow.number
    )

    return Ok(event)


def _build_bungalow_occupancy_description_updated_event(
    occurred_at: datetime,
    initiator: User,
    bungalow_id: BungalowID,
    bungalow_number: int,
) -> BungalowOccupancyDescriptionUpdatedEvent:
    return BungalowOccupancyDescriptionUpdatedEvent(
        occurred_at=occurred_at,
        initiator=initiator,
        bungalow_id=bungalow_id,
        bungalow_number=bungalow_number,
    )


def find_occupancy_managed_by_user(
    party_id: PartyID, user_id: UserID
) -> DbBungalowOccupancy | None:
    """Try to find a bungalow occupancy managed by that user that party."""
    return bungalow_occupancy_repository.find_occupancy_managed_by_user(
        party_id, user_id
    )


def get_occupied_bungalows_for_party(party_id: PartyID) -> list[DbBungalow]:
    """Return all occupied (but not reserved) bungalows for the party,
    ordered by number.
    """
    db_bungalows = (
        bungalow_occupancy_repository.get_occupied_bungalows_for_party(party_id)
    )

    return list(db_bungalows)


def get_occupied_bungalow_numbers_and_titles(
    party_id: PartyID,
) -> list[tuple[int, str | None]]:
    """Return the numbers and titles of all occupied bungalows for the
    party, ordered by number.
    """
    numbers_and_titles = (
        bungalow_occupancy_repository.get_occupied_bungalow_numbers_and_titles(
            party_id
        )
    )

    return list(numbers_and_titles)


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

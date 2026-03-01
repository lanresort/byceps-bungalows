"""
byceps.services.bungalow.bungalow_occupancy_domain_service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

import dataclasses
from datetime import datetime

from byceps.services.shop.order.models.number import OrderNumber
from byceps.services.ticketing.models.ticket import TicketBundle, TicketBundleID
from byceps.services.user.models import User
from byceps.util.result import Err, Ok, Result
from byceps.util.uuid import generate_uuid7

from . import bungalow_log_service
from .events import (
    BungalowOccupiedEvent,
    BungalowReleasedEvent,
    BungalowReservedEvent,
)
from .models.bungalow import Bungalow, BungalowID
from .models.log import BungalowLogEntry
from .models.occupation import (
    BungalowOccupancy,
    BungalowReservation,
    OccupancyID,
    OccupancyState,
    ReservationID,
)


def reserve_bungalow(
    bungalow: Bungalow, occupier: User
) -> Result[
    tuple[
        BungalowReservation,
        BungalowOccupancy,
        BungalowReservedEvent,
        BungalowLogEntry,
    ],
    str,
]:
    """Create a reservation for this bungalow."""
    if not bungalow.available:
        return Err('Bungalow is not available.')

    reservation = _build_reservation(bungalow.id, occupier)

    occupancy = _build_reservation_occupancy(reservation)

    event = _build_bungalow_reserved_event(
        occupier, bungalow.id, bungalow.number
    )

    log_entry = _build_bungalow_reserved_log_entry(bungalow.id, occupier)

    return Ok((reservation, occupancy, event, log_entry))


def _build_reservation(
    bungalow_id: BungalowID, occupier: User
) -> BungalowReservation:
    reservation_id = ReservationID(generate_uuid7())

    return BungalowReservation(
        id=reservation_id,
        bungalow_id=bungalow_id,
        reserved_by_id=occupier.id,
        order_number=None,
        pinned=False,
        internal_remark=None,
    )


def _build_reservation_occupancy(
    reservation: BungalowReservation,
) -> BungalowOccupancy:
    occupancy_id = OccupancyID(generate_uuid7())
    occupier_id = reservation.reserved_by_id

    return BungalowOccupancy(
        id=occupancy_id,
        bungalow_id=reservation.bungalow_id,
        occupied_by_id=occupier_id,
        order_number=None,
        state=OccupancyState.reserved,
        ticket_bundle_id=None,
        pinned=False,
        manager_id=occupier_id,
        title=None,
        description=None,
        avatar_id=None,
        internal_remark=None,
    )


def _build_bungalow_reserved_event(
    occupier: User, bungalow_id: BungalowID, bungalow_number: int
) -> BungalowReservedEvent:
    return BungalowReservedEvent(
        occurred_at=datetime.utcnow(),
        initiator=occupier,
        bungalow_id=bungalow_id,
        bungalow_number=bungalow_number,
        occupier=occupier,
    )


def _build_bungalow_reserved_log_entry(
    bungalow_id: BungalowID, initiator: User
) -> BungalowLogEntry:
    return bungalow_log_service.build_entry(
        'bungalow-reserved',
        bungalow_id,
        data={'initiator_id': str(initiator.id)},
    )


def occupy_reserved_bungalow(
    bungalow: Bungalow,
    current_occupancy: BungalowOccupancy,
    ticket_bundle: TicketBundle,
    initiator: User,
) -> Result[
    tuple[BungalowOccupancy, BungalowOccupiedEvent, BungalowLogEntry], str
]:
    """Mark a reserved bungalow as occupied."""
    if current_occupancy.state != OccupancyState.reserved:
        return Err(
            "Not in state 'reserved', cannot change to state 'occupied'."
        )

    if bungalow.category.ticket_category_id != ticket_bundle.ticket_category.id:
        return Err('Ticket categories do not match.')

    occupier = ticket_bundle.owned_by

    updated_occupancy = dataclasses.replace(
        current_occupancy,
        state=OccupancyState.occupied,
        ticket_bundle_id=ticket_bundle.id,
    )

    event = _build_bungalow_occupied_event(
        bungalow.id, bungalow.number, occupier, initiator
    )

    log_entry = _build_bungalow_occupied_log_entry(bungalow.id, initiator)

    return Ok((updated_occupancy, event, log_entry))


def occupy_bungalow_without_reservation(
    bungalow: Bungalow, ticket_bundle: TicketBundle, initiator: User
) -> Result[
    tuple[BungalowOccupancy, BungalowOccupiedEvent, BungalowLogEntry], str
]:
    """Occupy the bungalow without previous reservation."""
    if not bungalow.available:
        return Err('Bungalow is not available.')

    if bungalow.category.ticket_category_id != ticket_bundle.ticket_category.id:
        return Err('Ticket categories do not match.')

    occupier = ticket_bundle.owned_by

    occupancy = _build_occupancy_without_reservation(
        bungalow.id, occupier, ticket_bundle.order_number, ticket_bundle.id
    )

    event = _build_bungalow_occupied_event(
        bungalow.id, bungalow.number, occupier, initiator
    )

    log_entry = _build_bungalow_occupied_log_entry(bungalow.id, initiator)

    return Ok((occupancy, event, log_entry))


def _build_occupancy_without_reservation(
    bungalow_id: BungalowID,
    occupier: User,
    order_number: OrderNumber | None,
    ticket_bundle_id: TicketBundleID,
) -> BungalowOccupancy:
    occupancy_id = OccupancyID(generate_uuid7())

    return BungalowOccupancy(
        id=occupancy_id,
        bungalow_id=bungalow_id,
        occupied_by_id=occupier.id,
        order_number=order_number,
        state=OccupancyState.occupied,
        ticket_bundle_id=ticket_bundle_id,
        pinned=False,
        manager_id=occupier.id,
        title=None,
        description=None,
        avatar_id=None,
        internal_remark=None,
    )


def _build_bungalow_occupied_event(
    bungalow_id: BungalowID,
    bungalow_number: int,
    occupier: User,
    initiator: User,
) -> BungalowOccupiedEvent:
    return BungalowOccupiedEvent(
        occurred_at=datetime.utcnow(),
        initiator=initiator,
        bungalow_id=bungalow_id,
        bungalow_number=bungalow_number,
        occupier=occupier,
    )


def _build_bungalow_occupied_log_entry(
    bungalow_id: BungalowID, initiator: User
) -> BungalowLogEntry:
    return bungalow_log_service.build_entry(
        'bungalow-occupied',
        bungalow_id,
        data={'initiator_id': str(initiator.id)},
    )


def release_bungalow(
    bungalow: Bungalow, initiator: User
) -> Result[tuple[BungalowReleasedEvent, BungalowLogEntry], str]:
    """Release the bungalow occupied by the occupancy so it becomes available
    again.
    """
    if not bungalow.reserved_or_occupied:
        return Err('Bungalow is not reserved or occupied.')

    event = _build_bungalow_released_event(
        initiator, bungalow.id, bungalow.number
    )

    log_entry = _build_bungalow_released_log_entry(bungalow.id, initiator)

    return Ok((event, log_entry))


def _build_bungalow_released_event(
    initiator: User, bungalow_id: BungalowID, bungalow_number: int
) -> BungalowReleasedEvent:
    return BungalowReleasedEvent(
        occurred_at=datetime.utcnow(),
        initiator=initiator,
        bungalow_id=bungalow_id,
        bungalow_number=bungalow_number,
    )


def _build_bungalow_released_log_entry(
    bungalow_id: BungalowID, initiator: User
) -> BungalowLogEntry:
    return bungalow_log_service.build_entry(
        'bungalow-released',
        bungalow_id,
        data={'initiator_id': str(initiator.id)},
    )

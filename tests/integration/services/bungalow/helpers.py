"""
:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from byceps.services.bungalow import bungalow_occupancy_service
from byceps.services.bungalow.models.bungalow import BungalowID
from byceps.services.bungalow.models.occupation import (
    BungalowOccupancy,
    OccupancyID,
    ReservationID,
)
from byceps.services.ticketing.models.ticket import TicketBundle
from byceps.services.user.models import User


def reserve_bungalow(
    bungalow_id: BungalowID, occupier: User
) -> tuple[ReservationID, OccupancyID]:
    reservation, occupancy, _ = bungalow_occupancy_service.reserve_bungalow(
        bungalow_id, occupier
    ).unwrap()

    return reservation.id, occupancy.id


def occupy_reserved_bungalow(
    reservation_id: ReservationID,
    occupancy_id: OccupancyID,
    ticket_bundle: TicketBundle,
    initiator: User,
) -> BungalowOccupancy:
    occupancy, _ = bungalow_occupancy_service.occupy_reserved_bungalow(
        reservation_id, occupancy_id, ticket_bundle, initiator
    ).unwrap()

    return occupancy

"""
:Copyright: 2014-2023 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from byceps.services.bungalow import bungalow_occupancy_service
from byceps.services.bungalow.models.bungalow import BungalowID
from byceps.services.bungalow.models.occupation import (
    BungalowOccupancy,
    OccupancyID,
    ReservationID,
)
from byceps.services.ticketing.models.ticket import TicketBundleID
from byceps.typing import UserID


def reserve_bungalow(
    bungalow_id: BungalowID, occupier_id: UserID
) -> tuple[ReservationID, OccupancyID]:
    reservation, occupancy, _ = bungalow_occupancy_service.reserve_bungalow(
        bungalow_id, occupier_id
    ).unwrap()

    return reservation.id, occupancy.id


def occupy_bungalow(
    reservation_id: ReservationID,
    occupancy_id: OccupancyID,
    ticket_bundle_id: TicketBundleID,
) -> BungalowOccupancy:
    occupancy, _ = bungalow_occupancy_service.occupy_bungalow(
        reservation_id, occupancy_id, ticket_bundle_id
    ).unwrap()

    return occupancy

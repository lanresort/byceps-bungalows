"""
:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from byceps.services.bungalow import bungalow_occupancy_service
from byceps.services.bungalow.models.bungalow import BungalowOccupationState
from byceps.services.bungalow.models.occupation import OccupancyState
from byceps.services.shop.order.models.order import Orderer
from byceps.services.user.models import User

from tests.integration.services.bungalow.helpers import (
    occupy_bungalow,
    reserve_bungalow,
)


def test_release_bungalow(
    make_bungalow, admin_user: User, orderer: Orderer, make_ticket_bundle
):
    ticket_bundle = make_ticket_bundle()

    bungalow = make_bungalow()

    reservation_id, occupancy_id = reserve_bungalow(bungalow.id, orderer.user)
    occupy_bungalow(reservation_id, occupancy_id, ticket_bundle.id)

    reservation = bungalow_occupancy_service.find_reservation(reservation_id)
    occupancy = bungalow_occupancy_service.find_occupancy(occupancy_id)

    assert bungalow.occupation_state == BungalowOccupationState.occupied
    assert not bungalow.available
    assert bungalow.reserved_or_occupied

    assert occupancy is not None
    assert occupancy.state == OccupancyState.occupied
    assert occupancy.manager_id == orderer.user.id

    release_event = bungalow_occupancy_service.release_bungalow(
        bungalow.id, admin_user
    )
    assert release_event.initiator == admin_user
    assert release_event.bungalow_id == bungalow.id
    assert release_event.bungalow_number == bungalow.number

    reservation = bungalow_occupancy_service.find_reservation(reservation_id)
    occupancy = bungalow_occupancy_service.find_occupancy(occupancy_id)

    assert bungalow.occupation_state == BungalowOccupationState.available
    assert bungalow.available
    assert not bungalow.reserved_or_occupied

    assert reservation is None

    assert occupancy is None

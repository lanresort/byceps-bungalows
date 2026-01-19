"""
:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from byceps.services.bungalow import bungalow_occupancy_service
from byceps.services.bungalow.models.bungalow import BungalowOccupationState
from byceps.services.bungalow.models.occupation import OccupancyState
from byceps.services.shop.order.models.order import Orderer

from tests.integration.services.bungalow.helpers import (
    occupy_bungalow,
    reserve_bungalow,
)


def test_occupy_bungalow(
    site_app, make_bungalow, orderer: Orderer, make_ticket_bundle
):
    occupier = orderer.user
    ticket_bundle = make_ticket_bundle()

    bungalow = make_bungalow()

    reservation_id, occupancy_id = reserve_bungalow(bungalow.id, occupier)

    reservation = bungalow_occupancy_service.find_reservation(reservation_id)
    occupancy = bungalow_occupancy_service.get_occupancy(occupancy_id).unwrap()

    assert bungalow.occupation_state == BungalowOccupationState.reserved
    assert not bungalow.available
    assert bungalow.reserved_or_occupied

    assert reservation is not None

    assert occupancy.state == OccupancyState.reserved
    assert occupancy.ticket_bundle_id is None
    assert occupancy.manager_id == occupier.id

    occupy_bungalow(reservation_id, occupancy_id, ticket_bundle.id)

    reservation = bungalow_occupancy_service.find_reservation(reservation_id)
    occupancy = bungalow_occupancy_service.get_occupancy(occupancy_id).unwrap()

    assert bungalow.occupation_state == BungalowOccupationState.occupied
    assert not bungalow.available
    assert bungalow.reserved_or_occupied

    assert reservation is None

    assert occupancy.state == OccupancyState.occupied
    assert occupancy.ticket_bundle_id is not None
    assert occupancy.manager_id == occupier.id

"""
:Copyright: 2014-2024 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from byceps.services.bungalow import bungalow_occupancy_service
from byceps.services.bungalow.models.bungalow import BungalowOccupationState
from byceps.services.bungalow.models.occupation import OccupancyState
from byceps.services.shop.order import order_sequence_service, order_service
from byceps.services.shop.order.models.number import OrderNumber
from byceps.services.shop.order.models.order import Orderer, PaymentState
from byceps.services.shop.storefront.models import Storefront


def test_reserve_bungalow(
    storefront: Storefront, make_bungalow, orderer: Orderer
):
    occupier = orderer.user

    order_number_sequence = order_sequence_service.get_order_number_sequence(
        storefront.order_number_sequence_id
    )

    expected_order_number = OrderNumber(
        f'{order_number_sequence.prefix}{(order_number_sequence.value + 1):05d}'
    )

    bungalow = make_bungalow()

    assert bungalow.occupation_state == BungalowOccupationState.available
    assert bungalow.available
    assert not bungalow.reserved_or_occupied

    assert bungalow.occupancy is None

    reservation_result = bungalow_occupancy_service.reserve_bungalow(
        bungalow.id, occupier
    )
    assert reservation_result.is_ok()

    reservation, occupancy, _ = reservation_result.unwrap()

    bungalow_occupancy_service.place_bungalow_order(
        storefront, reservation.id, occupancy.id, orderer
    ).unwrap()

    reservation = bungalow_occupancy_service.get_reservation(
        reservation.id
    ).unwrap()

    occupancy = bungalow_occupancy_service.get_occupancy(occupancy.id).unwrap()

    assert bungalow.occupation_state == BungalowOccupationState.reserved
    assert not bungalow.available
    assert bungalow.reserved_or_occupied

    assert reservation is not None
    assert reservation.id is not None
    assert reservation.reserved_by_id == occupier.id
    assert reservation.order_number == expected_order_number

    assert occupancy is not None
    assert occupancy.id is not None
    assert occupancy.occupied_by_id == occupier.id
    assert occupancy.order_number == expected_order_number
    assert occupancy.state == OccupancyState.reserved
    assert occupancy.manager_id == occupier.id

    order = order_service.find_order_by_order_number(occupancy.order_number)
    assert order is not None
    assert order.order_number == expected_order_number
    assert order.placed_by.id == occupier.id
    assert order.payment_state == PaymentState.open

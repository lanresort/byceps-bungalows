"""
:Copyright: 2014-2023 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

import pytest

from byceps.services.brand.models import Brand
from byceps.services.bungalow import (
    bungalow_building_service,
    bungalow_offer_service,
    bungalow_service,
)
from byceps.services.bungalow.dbmodels.category import DbBungalowCategory
from byceps.services.bungalow.models.building import (
    BungalowBuilding,
    BungalowLayout,
)
from byceps.services.ticketing.models.ticket import TicketCategory
from byceps.typing import PartyID


BUNGALOW_CAPACITY = 6
BUNGALOW_NUMBERS = {991, 992}
BUNGALOW_COUNT = len(BUNGALOW_NUMBERS)


@pytest.fixture()
def layout(brand: Brand) -> BungalowLayout:
    return bungalow_building_service.create_layout(
        brand.id,
        'Classic',
        BUNGALOW_CAPACITY,
        image_filename='classic_6.png',
        image_width=640,
        image_height=480,
    )


@pytest.fixture()
def buildings(layout: BungalowLayout) -> list[BungalowBuilding]:
    return [
        bungalow_building_service.create_building(layout, number)
        for number in BUNGALOW_NUMBERS
    ]


def test_offer_bungalows(
    site_app,
    brand: Brand,
    make_party,
    buildings: list[BungalowBuilding],
    bungalow_category: DbBungalowCategory,
    ticket_category: TicketCategory,
):
    party = make_party(brand.id)

    assert count_bungalows(party.id) == 0

    bungalow_offer_service.offer_bungalows(
        party.id, buildings, bungalow_category.id
    )

    assert count_bungalows(party.id) == BUNGALOW_COUNT


# helpers


def count_bungalows(party_id: PartyID) -> int:
    bungalows = bungalow_service.get_bungalows_for_party(party_id)
    return len(bungalows)

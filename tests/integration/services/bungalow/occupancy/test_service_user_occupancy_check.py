"""
:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

import pytest

from byceps.services.brand.models import Brand
from byceps.services.bungalow import bungalow_occupancy_service
from byceps.services.party.models import Party
from byceps.services.user.models.user import User

from tests.integration.services.bungalow.helpers import reserve_bungalow


@pytest.fixture(scope='module')
def party1(bungalows_brand: Brand, make_party) -> Party:
    return make_party(bungalows_brand)


@pytest.fixture(scope='module')
def party2(bungalows_brand: Brand, make_party) -> Party:
    return make_party(bungalows_brand)


@pytest.fixture()
def bungalow1(party1: Party, bungalow_category, make_bungalow):
    return make_bungalow(
        party_id=party1.id,
        number=674,
        bungalow_category_id=bungalow_category.id,
    )


@pytest.fixture()
def bungalow2(party2: Party, bungalow_category, make_bungalow):
    return make_bungalow(
        party_id=party2.id,
        number=666,
        bungalow_category_id=bungalow_category.id,
    )


@pytest.fixture()
def user1(admin_app, make_user) -> User:
    return make_user()


@pytest.fixture()
def user2(admin_app, make_user) -> User:
    return make_user()


@pytest.fixture()
def user3(admin_app, make_user) -> User:
    return make_user()


def test_user_occupies_any_bungalow_for_this_party(
    site_app, bungalow1, party1: Party, user1: User
):
    reserve_bungalow(bungalow1.id, user1)

    assert bungalow_occupancy_service.has_user_occupied_any_bungalow(
        party1.id, user1.id
    )


def test_user_occupies_any_bungalow_for_another_party(
    site_app, bungalow2, party1: Party, user2: User
):
    reserve_bungalow(bungalow2.id, user2)

    assert not bungalow_occupancy_service.has_user_occupied_any_bungalow(
        party1.id, user2.id
    )


def test_user_occupies_no_bungalow_for_any_party(
    site_app, party1: Party, party2: Party, user3: User
):
    assert not bungalow_occupancy_service.has_user_occupied_any_bungalow(
        party1.id, user3.id
    )

    assert not bungalow_occupancy_service.has_user_occupied_any_bungalow(
        party2.id, user3.id
    )

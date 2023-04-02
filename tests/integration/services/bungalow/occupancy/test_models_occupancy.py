"""
:Copyright: 2014-2023 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

import pytest

from byceps.services.user.models.user import User

from ..helpers import occupy_bungalow, reserve_bungalow


@pytest.fixture(scope='module')
def user1(admin_app, make_user) -> User:
    return make_user()


@pytest.fixture(scope='module')
def user2(admin_app, make_user) -> User:
    return make_user()


def test_is_managed_by_when_occupied_by_this_user(
    site_app, make_bungalow, user1: User, make_ticket_bundle
):
    bungalow = make_bungalow()
    ticket_bundle = make_ticket_bundle()

    reservation_id, occupancy_id = reserve_bungalow(bungalow.id, user1.id)
    occupancy = occupy_bungalow(reservation_id, occupancy_id, ticket_bundle.id)

    assert occupancy.manager_id == user1.id


def test_is_managed_by_when_occupied_by_another_user(
    site_app, make_bungalow, user1: User, user2: User, make_ticket_bundle
):
    bungalow = make_bungalow()
    ticket_bundle = make_ticket_bundle()

    reservation_id, occupancy_id = reserve_bungalow(bungalow.id, user2.id)
    occupancy = occupy_bungalow(reservation_id, occupancy_id, ticket_bundle.id)

    assert occupancy.manager_id != user1.id

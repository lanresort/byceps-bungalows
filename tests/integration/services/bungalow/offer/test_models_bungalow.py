"""
:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

import pytest

from byceps.services.user.models import User

from tests.integration.services.bungalow.helpers import (
    occupy_reserved_bungalow,
    reserve_bungalow,
)


@pytest.fixture()
def user(admin_app, make_user) -> User:
    return make_user()


def test_is_reserved_or_occupied_when_available(site_app, make_bungalow):
    bungalow = make_bungalow()

    assert bungalow.available
    assert not bungalow.reserved_or_occupied


def test_is_reserved_or_occupied_when_reserved(
    site_app, make_bungalow, user: User
):
    bungalow = make_bungalow()

    reserve_bungalow(bungalow.id, user)

    assert not bungalow.available
    assert bungalow.reserved_or_occupied


def test_is_reserved_or_occupied_when_occupied(
    site_app, make_bungalow, user: User, make_ticket_bundle
):
    bungalow = make_bungalow()
    ticket_bundle = make_ticket_bundle()

    reservation_id, occupancy_id = reserve_bungalow(bungalow.id, user)
    occupy_reserved_bungalow(reservation_id, occupancy_id, ticket_bundle, user)

    assert not bungalow.available
    assert bungalow.reserved_or_occupied

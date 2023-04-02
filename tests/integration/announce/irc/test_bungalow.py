"""
:Copyright: 2014-2023 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

import pytest

import byceps.announce.connections  # Connect signal handlers.  # noqa: F401
from byceps.events.bungalow import (
    BungalowOccupancyAvatarUpdated,
    BungalowOccupancyDescriptionUpdated,
    BungalowOccupancyMoved,
    BungalowOccupantAdded,
    BungalowOccupantRemoved,
    BungalowOccupied,
    BungalowReleased,
    BungalowReserved,
)
from byceps.services.bungalow import (
    bungalow_building_service,
    bungalow_offer_service,
)
from byceps.services.bungalow.models.building import BungalowLayout
from byceps.services.bungalow.models.bungalow import Bungalow
from byceps.services.bungalow.models.category import BungalowCategory
from byceps.services.party.models import Party
from byceps.services.user.models.user import User
from byceps.signals import bungalow as bungalow_signals

from .helpers import assert_submitted_text, mocked_irc_bot, now


def test_announce_bungalow_reserved(app, bungalow666, occupier):
    expected_text = 'Lucifer hat Bungalow 666 reserviert.'

    event = BungalowReserved(
        occurred_at=now(),
        initiator_id=occupier.id,
        initiator_screen_name=occupier.screen_name,
        bungalow_id=bungalow666.id,
        occupier_id=occupier.id,
        occupier_screen_name=occupier.screen_name,
    )

    with mocked_irc_bot() as mock:
        bungalow_signals.bungalow_reserved.send(None, event=event)

    assert_submitted_text(mock, expected_text)


def test_announce_bungalow_occupied(app, bungalow666, occupier):
    expected_text = 'Lucifer hat Bungalow 666 belegt.'

    event = BungalowOccupied(
        occurred_at=now(),
        initiator_id=occupier.id,
        initiator_screen_name=occupier.screen_name,
        bungalow_id=bungalow666.id,
        occupier_id=occupier.id,
        occupier_screen_name=occupier.screen_name,
    )

    with mocked_irc_bot() as mock:
        bungalow_signals.bungalow_occupied.send(None, event=event)

    assert_submitted_text(mock, expected_text)


def test_announce_bungalow_released(app, bungalow666):
    expected_text = 'Bungalow 666 wurde wieder freigegeben.'

    event = BungalowReleased(
        occurred_at=now(),
        initiator_id=None,
        initiator_screen_name=None,
        bungalow_id=bungalow666.id,
    )

    with mocked_irc_bot() as mock:
        bungalow_signals.bungalow_released.send(None, event=event)

    assert_submitted_text(mock, expected_text)


def test_announce_bungalow_occupancy_moved(app, bungalow666, bungalow851):
    expected_text = (
        'Die Belegung von Bungalow 666 hat zu Bungalow 851 gewechselt.'
    )

    event = BungalowOccupancyMoved(
        occurred_at=now(),
        initiator_id=None,
        initiator_screen_name=None,
        source_bungalow_id=bungalow666.id,
        target_bungalow_id=bungalow851.id,
    )

    with mocked_irc_bot() as mock:
        bungalow_signals.occupancy_moved.send(None, event=event)

    assert_submitted_text(mock, expected_text)


def test_announce_bungalow_avatar_updated(app, bungalow666, main_occupant):
    expected_text = 'Lucifer hat das Avatarbild für Bungalow 666 aktualisiert.'

    event = BungalowOccupancyAvatarUpdated(
        occurred_at=now(),
        initiator_id=main_occupant.id,
        initiator_screen_name=main_occupant.screen_name,
        bungalow_id=bungalow666.id,
    )

    with mocked_irc_bot() as mock:
        bungalow_signals.avatar_updated.send(None, event=event)

    assert_submitted_text(mock, expected_text)


def test_announce_bungalow_description_updated(app, bungalow666, main_occupant):
    expected_text = 'Lucifer hat das Grußwort für Bungalow 666 aktualisiert.'

    event = BungalowOccupancyDescriptionUpdated(
        occurred_at=now(),
        initiator_id=main_occupant.id,
        initiator_screen_name=main_occupant.screen_name,
        bungalow_id=bungalow666.id,
    )

    with mocked_irc_bot() as mock:
        bungalow_signals.description_updated.send(None, event=event)

    assert_submitted_text(mock, expected_text)


def test_announce_bungalow_occupant_added(
    app, bungalow666, main_occupant, other_occupant
):
    expected_text = 'Lucifer hat Mad_Dämon in Bungalow 666 aufgenommen.'

    event = BungalowOccupantAdded(
        occurred_at=now(),
        initiator_id=main_occupant.id,
        initiator_screen_name=main_occupant.screen_name,
        bungalow_id=bungalow666.id,
        occupant_id=other_occupant.id,
        occupant_screen_name=other_occupant.screen_name,
    )

    with mocked_irc_bot() as mock:
        bungalow_signals.occupant_added.send(None, event=event)

    assert_submitted_text(mock, expected_text)


def test_announce_bungalow_occupant_removed(
    app, bungalow666, main_occupant, other_occupant
):
    expected_text = 'Lucifer hat Mad_Dämon aus Bungalow 666 rausgeworfen.'

    event = BungalowOccupantRemoved(
        occurred_at=now(),
        initiator_id=main_occupant.id,
        initiator_screen_name=main_occupant.screen_name,
        bungalow_id=bungalow666.id,
        occupant_id=other_occupant.id,
        occupant_screen_name=other_occupant.screen_name,
    )

    with mocked_irc_bot() as mock:
        bungalow_signals.occupant_removed.send(None, event=event)

    assert_submitted_text(mock, expected_text)


# helpers


@pytest.fixture(scope='module')
def bungalow666(
    party: Party,
    bungalow_layout: BungalowLayout,
    bungalow_category: BungalowCategory,
) -> Bungalow:
    return _create_bungalow_offer(
        party, bungalow_layout, 666, bungalow_category
    )


@pytest.fixture(scope='module')
def bungalow851(
    party: Party,
    bungalow_layout: BungalowLayout,
    bungalow_category: BungalowCategory,
) -> Bungalow:
    return _create_bungalow_offer(
        party, bungalow_layout, 851, bungalow_category
    )


@pytest.fixture(scope='module')
def occupier(main_occupant) -> User:
    return main_occupant


@pytest.fixture(scope='module')
def main_occupant(make_user) -> User:
    return make_user('Lucifer')


@pytest.fixture(scope='module')
def other_occupant(make_user) -> User:
    return make_user('Mad_Dämon')


def _create_bungalow_offer(
    party: Party,
    bungalow_layout: BungalowLayout,
    number: int,
    bungalow_category: BungalowCategory,
) -> Bungalow:
    building = bungalow_building_service.create_building(
        bungalow_layout, number
    )
    return bungalow_offer_service.offer_bungalow(
        party.id, building, bungalow_category.id
    )

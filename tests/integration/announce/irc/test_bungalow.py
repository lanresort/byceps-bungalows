"""
:Copyright: 2014-2023 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

import pytest

from byceps.announce.connections import build_announcement_request
from byceps.events.bungalow import (
    BungalowOccupancyAvatarUpdatedEvent,
    BungalowOccupancyDescriptionUpdatedEvent,
    BungalowOccupancyMovedEvent,
    BungalowOccupantAddedEvent,
    BungalowOccupantRemovedEvent,
    BungalowOccupiedEvent,
    BungalowReleasedEvent,
    BungalowReservedEvent,
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

from .helpers import build_announcement_request_for_irc, now


def test_announce_bungalow_reserved(
    admin_app, bungalow666, occupier, webhook_for_irc
):
    expected_text = 'Lucifer hat Bungalow 666 reserviert.'
    expected = build_announcement_request_for_irc(expected_text)

    event = BungalowReservedEvent(
        occurred_at=now(),
        initiator_id=occupier.id,
        initiator_screen_name=occupier.screen_name,
        bungalow_id=bungalow666.id,
        bungalow_number=bungalow666.number,
        occupier_id=occupier.id,
        occupier_screen_name=occupier.screen_name,
    )

    assert build_announcement_request(event, webhook_for_irc) == expected


def test_announce_bungalow_occupied(
    admin_app, bungalow666, occupier, webhook_for_irc
):
    expected_text = 'Lucifer hat Bungalow 666 belegt.'
    expected = build_announcement_request_for_irc(expected_text)

    event = BungalowOccupiedEvent(
        occurred_at=now(),
        initiator_id=occupier.id,
        initiator_screen_name=occupier.screen_name,
        bungalow_id=bungalow666.id,
        bungalow_number=bungalow666.number,
        occupier_id=occupier.id,
        occupier_screen_name=occupier.screen_name,
    )

    assert build_announcement_request(event, webhook_for_irc) == expected


def test_announce_bungalow_released(admin_app, bungalow666, webhook_for_irc):
    expected_text = 'Bungalow 666 wurde wieder freigegeben.'
    expected = build_announcement_request_for_irc(expected_text)

    event = BungalowReleasedEvent(
        occurred_at=now(),
        initiator_id=None,
        initiator_screen_name=None,
        bungalow_id=bungalow666.id,
        bungalow_number=bungalow666.number,
    )

    assert build_announcement_request(event, webhook_for_irc) == expected


def test_announce_bungalow_occupancy_moved(
    admin_app, bungalow666, bungalow851, webhook_for_irc
):
    expected_text = (
        'Die Belegung von Bungalow 666 hat zu Bungalow 851 gewechselt.'
    )
    expected = build_announcement_request_for_irc(expected_text)

    event = BungalowOccupancyMovedEvent(
        occurred_at=now(),
        initiator_id=None,
        initiator_screen_name=None,
        source_bungalow_id=bungalow666.id,
        source_bungalow_number=bungalow666.number,
        target_bungalow_id=bungalow851.id,
        target_bungalow_number=bungalow851.number,
    )

    assert build_announcement_request(event, webhook_for_irc) == expected


def test_announce_bungalow_avatar_updated(
    admin_app, bungalow666, main_occupant, webhook_for_irc
):
    expected_text = 'Lucifer hat das Avatarbild für Bungalow 666 aktualisiert.'
    expected = build_announcement_request_for_irc(expected_text)

    event = BungalowOccupancyAvatarUpdatedEvent(
        occurred_at=now(),
        initiator_id=main_occupant.id,
        initiator_screen_name=main_occupant.screen_name,
        bungalow_id=bungalow666.id,
        bungalow_number=bungalow666.number,
    )

    assert build_announcement_request(event, webhook_for_irc) == expected


def test_announce_bungalow_description_updated(
    admin_app, bungalow666, main_occupant, webhook_for_irc
):
    expected_text = 'Lucifer hat das Grußwort für Bungalow 666 aktualisiert.'
    expected = build_announcement_request_for_irc(expected_text)

    event = BungalowOccupancyDescriptionUpdatedEvent(
        occurred_at=now(),
        initiator_id=main_occupant.id,
        initiator_screen_name=main_occupant.screen_name,
        bungalow_id=bungalow666.id,
        bungalow_number=bungalow666.number,
    )

    assert build_announcement_request(event, webhook_for_irc) == expected


def test_announce_bungalow_occupant_added(
    admin_app, bungalow666, main_occupant, other_occupant, webhook_for_irc
):
    expected_text = 'Lucifer hat Mad_Dämon in Bungalow 666 aufgenommen.'
    expected = build_announcement_request_for_irc(expected_text)

    event = BungalowOccupantAddedEvent(
        occurred_at=now(),
        initiator_id=main_occupant.id,
        initiator_screen_name=main_occupant.screen_name,
        bungalow_id=bungalow666.id,
        bungalow_number=bungalow666.number,
        occupant_id=other_occupant.id,
        occupant_screen_name=other_occupant.screen_name,
    )

    assert build_announcement_request(event, webhook_for_irc) == expected


def test_announce_bungalow_occupant_removed(
    admin_app, bungalow666, main_occupant, other_occupant, webhook_for_irc
):
    expected_text = 'Lucifer hat Mad_Dämon aus Bungalow 666 rausgeworfen.'
    expected = build_announcement_request_for_irc(expected_text)

    event = BungalowOccupantRemovedEvent(
        occurred_at=now(),
        initiator_id=main_occupant.id,
        initiator_screen_name=main_occupant.screen_name,
        bungalow_id=bungalow666.id,
        bungalow_number=bungalow666.number,
        occupant_id=other_occupant.id,
        occupant_screen_name=other_occupant.screen_name,
    )

    assert build_announcement_request(event, webhook_for_irc) == expected


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

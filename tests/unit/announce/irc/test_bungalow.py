"""
:Copyright: 2014-2023 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from flask import Flask

from byceps.announce.announce import build_announcement_request
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
from byceps.services.bungalow.models.bungalow import BungalowID
from byceps.services.user.models.user import UserID

from tests.helpers import generate_uuid

from .helpers import assert_text, now


OCCURRED_AT = now()
OCCUPIER_ID = UserID(generate_uuid())
MAIN_OCCUPANT_ID = UserID(generate_uuid())
OTHER_OCCUPANT_ID = UserID(generate_uuid())
BUNGALOW_666_ID = BungalowID(generate_uuid())
BUNGALOW_851_ID = BungalowID(generate_uuid())


def test_announce_bungalow_reserved(app: Flask, webhook_for_irc):
    expected_text = 'Lucifer hat Bungalow 666 reserviert.'

    event = BungalowReservedEvent(
        occurred_at=OCCURRED_AT,
        initiator_id=OCCUPIER_ID,
        initiator_screen_name='Lucifer',
        bungalow_id=BUNGALOW_666_ID,
        bungalow_number=666,
        occupier_id=OCCUPIER_ID,
        occupier_screen_name='Lucifer',
    )

    actual = build_announcement_request(event, webhook_for_irc)

    assert_text(actual, expected_text)


def test_announce_bungalow_occupied(app: Flask, webhook_for_irc):
    expected_text = 'Lucifer hat Bungalow 666 belegt.'

    event = BungalowOccupiedEvent(
        occurred_at=OCCURRED_AT,
        initiator_id=OCCUPIER_ID,
        initiator_screen_name='Lucifer',
        bungalow_id=BUNGALOW_666_ID,
        bungalow_number=666,
        occupier_id=OCCUPIER_ID,
        occupier_screen_name='Lucifer',
    )

    actual = build_announcement_request(event, webhook_for_irc)

    assert_text(actual, expected_text)


def test_announce_bungalow_released(app: Flask, webhook_for_irc):
    expected_text = 'Bungalow 666 wurde wieder freigegeben.'

    event = BungalowReleasedEvent(
        occurred_at=OCCURRED_AT,
        initiator_id=None,
        initiator_screen_name=None,
        bungalow_id=BUNGALOW_666_ID,
        bungalow_number=666,
    )

    actual = build_announcement_request(event, webhook_for_irc)

    assert_text(actual, expected_text)


def test_announce_bungalow_occupancy_moved(app: Flask, webhook_for_irc):
    expected_text = (
        'Die Belegung von Bungalow 666 hat zu Bungalow 851 gewechselt.'
    )

    event = BungalowOccupancyMovedEvent(
        occurred_at=OCCURRED_AT,
        initiator_id=None,
        initiator_screen_name=None,
        source_bungalow_id=BUNGALOW_666_ID,
        source_bungalow_number=666,
        target_bungalow_id=BUNGALOW_851_ID,
        target_bungalow_number=851,
    )

    actual = build_announcement_request(event, webhook_for_irc)

    assert_text(actual, expected_text)


def test_announce_bungalow_avatar_updated(app: Flask, webhook_for_irc):
    expected_text = 'Lucifer hat das Avatarbild für Bungalow 666 aktualisiert.'

    event = BungalowOccupancyAvatarUpdatedEvent(
        occurred_at=OCCURRED_AT,
        initiator_id=MAIN_OCCUPANT_ID,
        initiator_screen_name='Lucifer',
        bungalow_id=BUNGALOW_666_ID,
        bungalow_number=666,
    )

    actual = build_announcement_request(event, webhook_for_irc)

    assert_text(actual, expected_text)


def test_announce_bungalow_description_updated(app: Flask, webhook_for_irc):
    expected_text = 'Lucifer hat das Grußwort für Bungalow 666 aktualisiert.'

    event = BungalowOccupancyDescriptionUpdatedEvent(
        occurred_at=OCCURRED_AT,
        initiator_id=MAIN_OCCUPANT_ID,
        initiator_screen_name='Lucifer',
        bungalow_id=BUNGALOW_666_ID,
        bungalow_number=666,
    )

    actual = build_announcement_request(event, webhook_for_irc)

    assert_text(actual, expected_text)


def test_announce_bungalow_occupant_added(app: Flask, webhook_for_irc):
    expected_text = 'Lucifer hat Mad_Dämon in Bungalow 666 aufgenommen.'

    event = BungalowOccupantAddedEvent(
        occurred_at=OCCURRED_AT,
        initiator_id=MAIN_OCCUPANT_ID,
        initiator_screen_name='Lucifer',
        bungalow_id=BUNGALOW_666_ID,
        bungalow_number=666,
        occupant_id=OTHER_OCCUPANT_ID,
        occupant_screen_name='Mad_Dämon',
    )

    actual = build_announcement_request(event, webhook_for_irc)

    assert_text(actual, expected_text)


def test_announce_bungalow_occupant_removed(app: Flask, webhook_for_irc):
    expected_text = 'Lucifer hat Mad_Dämon aus Bungalow 666 rausgeworfen.'

    event = BungalowOccupantRemovedEvent(
        occurred_at=OCCURRED_AT,
        initiator_id=MAIN_OCCUPANT_ID,
        initiator_screen_name='Lucifer',
        bungalow_id=BUNGALOW_666_ID,
        bungalow_number=666,
        occupant_id=OTHER_OCCUPANT_ID,
        occupant_screen_name='Mad_Dämon',
    )

    actual = build_announcement_request(event, webhook_for_irc)

    assert_text(actual, expected_text)

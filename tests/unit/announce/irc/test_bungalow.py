"""
:Copyright: 2014-2024 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from datetime import datetime

from flask import Flask
import pytest

from byceps.announce.announce import build_announcement_request
from byceps.events.base import EventUser
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

from tests.helpers import generate_uuid

from .helpers import assert_text


BUNGALOW_666_ID = BungalowID(generate_uuid())
BUNGALOW_851_ID = BungalowID(generate_uuid())


def test_announce_bungalow_reserved(
    app: Flask, now: datetime, main_occupant: EventUser, webhook_for_irc
):
    expected_text = 'Lucifer hat Bungalow 666 reserviert.'

    event = BungalowReservedEvent(
        occurred_at=now,
        initiator=main_occupant,
        bungalow_id=BUNGALOW_666_ID,
        bungalow_number=666,
        occupier=main_occupant,
    )

    actual = build_announcement_request(event, webhook_for_irc)

    assert_text(actual, expected_text)


def test_announce_bungalow_occupied(
    app: Flask, now: datetime, main_occupant: EventUser, webhook_for_irc
):
    expected_text = 'Lucifer hat Bungalow 666 belegt.'

    event = BungalowOccupiedEvent(
        occurred_at=now,
        initiator=main_occupant,
        bungalow_id=BUNGALOW_666_ID,
        bungalow_number=666,
        occupier=main_occupant,
    )

    actual = build_announcement_request(event, webhook_for_irc)

    assert_text(actual, expected_text)


def test_announce_bungalow_released(app: Flask, now: datetime, webhook_for_irc):
    expected_text = 'Bungalow 666 wurde wieder freigegeben.'

    event = BungalowReleasedEvent(
        occurred_at=now,
        initiator=None,
        bungalow_id=BUNGALOW_666_ID,
        bungalow_number=666,
    )

    actual = build_announcement_request(event, webhook_for_irc)

    assert_text(actual, expected_text)


def test_announce_bungalow_occupancy_moved(
    app: Flask, now: datetime, webhook_for_irc
):
    expected_text = (
        'Die Belegung von Bungalow 666 hat zu Bungalow 851 gewechselt.'
    )

    event = BungalowOccupancyMovedEvent(
        occurred_at=now,
        initiator=None,
        source_bungalow_id=BUNGALOW_666_ID,
        source_bungalow_number=666,
        target_bungalow_id=BUNGALOW_851_ID,
        target_bungalow_number=851,
    )

    actual = build_announcement_request(event, webhook_for_irc)

    assert_text(actual, expected_text)


def test_announce_bungalow_avatar_updated(
    app: Flask, now: datetime, main_occupant: EventUser, webhook_for_irc
):
    expected_text = 'Lucifer hat das Avatarbild für Bungalow 666 aktualisiert.'

    event = BungalowOccupancyAvatarUpdatedEvent(
        occurred_at=now,
        initiator=main_occupant,
        bungalow_id=BUNGALOW_666_ID,
        bungalow_number=666,
    )

    actual = build_announcement_request(event, webhook_for_irc)

    assert_text(actual, expected_text)


def test_announce_bungalow_description_updated(
    app: Flask, now: datetime, main_occupant: EventUser, webhook_for_irc
):
    expected_text = 'Lucifer hat das Grußwort für Bungalow 666 aktualisiert.'

    event = BungalowOccupancyDescriptionUpdatedEvent(
        occurred_at=now,
        initiator=main_occupant,
        bungalow_id=BUNGALOW_666_ID,
        bungalow_number=666,
    )

    actual = build_announcement_request(event, webhook_for_irc)

    assert_text(actual, expected_text)


def test_announce_bungalow_occupant_added(
    app: Flask,
    now: datetime,
    main_occupant: EventUser,
    other_occupant: EventUser,
    webhook_for_irc,
):
    expected_text = 'Lucifer hat Mad_Dämon in Bungalow 666 aufgenommen.'

    event = BungalowOccupantAddedEvent(
        occurred_at=now,
        initiator=main_occupant,
        bungalow_id=BUNGALOW_666_ID,
        bungalow_number=666,
        occupant=other_occupant,
    )

    actual = build_announcement_request(event, webhook_for_irc)

    assert_text(actual, expected_text)


def test_announce_bungalow_occupant_removed(
    app: Flask,
    now: datetime,
    main_occupant: EventUser,
    other_occupant: EventUser,
    webhook_for_irc,
):
    expected_text = 'Lucifer hat Mad_Dämon aus Bungalow 666 rausgeworfen.'

    event = BungalowOccupantRemovedEvent(
        occurred_at=now,
        initiator=main_occupant,
        bungalow_id=BUNGALOW_666_ID,
        bungalow_number=666,
        occupant=other_occupant,
    )

    actual = build_announcement_request(event, webhook_for_irc)

    assert_text(actual, expected_text)


# helpers


@pytest.fixture(scope='module')
def main_occupant(make_event_user) -> EventUser:
    return make_event_user(screen_name='Lucifer')


@pytest.fixture(scope='module')
def other_occupant(make_event_user) -> EventUser:
    return make_event_user(screen_name='Mad_Dämon')

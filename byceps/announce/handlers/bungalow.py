"""
byceps.announce.handlers.bungalow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Announce bungalow events.

:Copyright: 2014-2023 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from __future__ import annotations

from byceps.announce.helpers import get_screen_name_or_fallback
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
from byceps.services.webhooks.models import Announcement, OutgoingWebhook


def announce_bungalow_reserved(
    event: BungalowReservedEvent, webhook: OutgoingWebhook
) -> Announcement | None:
    """Announce that a bungalow has been reserved."""
    occupier_screen_name = get_screen_name_or_fallback(
        event.occupier_screen_name
    )

    text = f'{occupier_screen_name} hat Bungalow {event.bungalow_number} reserviert.'

    return Announcement(text)


def announce_bungalow_occupied(
    event: BungalowOccupiedEvent, webhook: OutgoingWebhook
) -> Announcement | None:
    """Announce that a bungalow has been occupied."""
    occupier_screen_name = get_screen_name_or_fallback(
        event.occupier_screen_name
    )

    text = (
        f'{occupier_screen_name} hat Bungalow {event.bungalow_number} belegt.'
    )

    return Announcement(text)


def announce_bungalow_released(
    event: BungalowReleasedEvent, webhook: OutgoingWebhook
) -> Announcement | None:
    """Announce that a bungalow has been released."""
    text = f'Bungalow {event.bungalow_number} wurde wieder freigegeben.'

    return Announcement(text)


def announce_bungalow_occupancy_moved(
    event: BungalowOccupancyMovedEvent, webhook: OutgoingWebhook
) -> Announcement | None:
    """Announce that a bungalow's occupancy has been moved to another
    bungalow.
    """
    text = (
        f'Die Belegung von Bungalow {event.source_bungalow_number} '
        f'hat zu Bungalow {event.target_bungalow_number} gewechselt.'
    )

    return Announcement(text)


def announce_bungalow_avatar_updated(
    event: BungalowOccupancyAvatarUpdatedEvent, webhook: OutgoingWebhook
) -> Announcement | None:
    """Announce that a bungalow's avatar image has been updated."""
    initiator_screen_name = get_screen_name_or_fallback(
        event.initiator_screen_name
    )

    text = (
        f'{initiator_screen_name} hat das Avatarbild für Bungalow '
        f'{event.bungalow_number} aktualisiert.'
    )

    return Announcement(text)


def announce_bungalow_description_updated(
    event: BungalowOccupancyDescriptionUpdatedEvent,
    webhook: OutgoingWebhook,
) -> Announcement | None:
    """Announce that a bungalow's description has been updated."""
    initiator_screen_name = get_screen_name_or_fallback(
        event.initiator_screen_name
    )

    text = (
        f'{initiator_screen_name} hat das Grußwort für Bungalow '
        f'{event.bungalow_number} aktualisiert.'
    )

    return Announcement(text)


def announce_bungalow_occupant_added(
    event: BungalowOccupantAddedEvent, webhook: OutgoingWebhook
) -> Announcement | None:
    """Announce that a bungalow occupant has been updated."""
    initiator_screen_name = get_screen_name_or_fallback(
        event.initiator_screen_name
    )
    occupant_screen_name = get_screen_name_or_fallback(
        event.occupant_screen_name
    )

    text = (
        f'{initiator_screen_name} hat {occupant_screen_name} in Bungalow '
        f'{event.bungalow_number} aufgenommen.'
    )

    return Announcement(text)


def announce_bungalow_occupant_removed(
    event: BungalowOccupantRemovedEvent, webhook: OutgoingWebhook
) -> Announcement | None:
    """Announce that a bungalow occupant has been removed."""
    initiator_screen_name = get_screen_name_or_fallback(
        event.initiator_screen_name
    )
    occupant_screen_name = get_screen_name_or_fallback(
        event.occupant_screen_name
    )

    text = (
        f'{initiator_screen_name} hat {occupant_screen_name} aus Bungalow '
        f'{event.bungalow_number} rausgeworfen.'
    )

    return Announcement(text)

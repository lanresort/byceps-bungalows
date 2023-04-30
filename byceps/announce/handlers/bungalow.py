"""
byceps.announce.handlers.bungalow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Announce bungalow events.

:Copyright: 2014-2023 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from __future__ import annotations

from byceps.announce.helpers import Announcement, get_screen_name_or_fallback
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
from byceps.services.bungalow import bungalow_service
from byceps.services.webhooks.models import OutgoingWebhook


def announce_bungalow_reserved(
    event: BungalowReserved, webhook: OutgoingWebhook
) -> Announcement | None:
    """Announce that a bungalow has been reserved."""
    bungalow = bungalow_service.get_db_bungalow(event.bungalow_id)
    occupier_screen_name = get_screen_name_or_fallback(
        event.occupier_screen_name
    )

    text = f'{occupier_screen_name} hat Bungalow {bungalow.number} reserviert.'

    return Announcement(text)


def announce_bungalow_occupied(
    event: BungalowOccupied, webhook: OutgoingWebhook
) -> Announcement | None:
    """Announce that a bungalow has been occupied."""
    bungalow = bungalow_service.get_db_bungalow(event.bungalow_id)
    occupier_screen_name = get_screen_name_or_fallback(
        event.occupier_screen_name
    )

    text = f'{occupier_screen_name} hat Bungalow {bungalow.number} belegt.'

    return Announcement(text)


def announce_bungalow_released(
    event: BungalowReleased, webhook: OutgoingWebhook
) -> Announcement | None:
    """Announce that a bungalow has been released."""
    bungalow = bungalow_service.get_db_bungalow(event.bungalow_id)

    text = f'Bungalow {bungalow.number} wurde wieder freigegeben.'

    return Announcement(text)


def announce_bungalow_occupancy_moved(
    event: BungalowOccupancyMoved, webhook: OutgoingWebhook
) -> Announcement | None:
    """Announce that a bungalow's occupancy has been moved to another
    bungalow.
    """
    source_bungalow = bungalow_service.get_db_bungalow(event.source_bungalow_id)
    target_bungalow = bungalow_service.get_db_bungalow(event.target_bungalow_id)

    text = (
        f'Die Belegung von Bungalow {source_bungalow.number} '
        f'hat zu Bungalow {target_bungalow.number} gewechselt.'
    )

    return Announcement(text)


def announce_bungalow_avatar_updated(
    event: BungalowOccupancyAvatarUpdated, webhook: OutgoingWebhook
) -> Announcement | None:
    """Announce that a bungalow's avatar image has been updated."""
    bungalow = bungalow_service.get_db_bungalow(event.bungalow_id)
    initiator_screen_name = get_screen_name_or_fallback(
        event.initiator_screen_name
    )

    text = (
        f'{initiator_screen_name} hat das Avatarbild für Bungalow '
        f'{bungalow.number} aktualisiert.'
    )

    return Announcement(text)


def announce_bungalow_description_updated(
    event: BungalowOccupancyDescriptionUpdated,
    webhook: OutgoingWebhook,
) -> Announcement | None:
    """Announce that a bungalow's description has been updated."""
    bungalow = bungalow_service.get_db_bungalow(event.bungalow_id)
    initiator_screen_name = get_screen_name_or_fallback(
        event.initiator_screen_name
    )

    text = (
        f'{initiator_screen_name} hat das Grußwort für Bungalow '
        f'{bungalow.number} aktualisiert.'
    )

    return Announcement(text)


def announce_bungalow_occupant_added(
    event: BungalowOccupantAdded, webhook: OutgoingWebhook
) -> Announcement | None:
    """Announce that a bungalow occupant has been updated."""
    bungalow = bungalow_service.get_db_bungalow(event.bungalow_id)
    initiator_screen_name = get_screen_name_or_fallback(
        event.initiator_screen_name
    )
    occupant_screen_name = get_screen_name_or_fallback(
        event.occupant_screen_name
    )

    text = (
        f'{initiator_screen_name} hat {occupant_screen_name} in Bungalow '
        f'{bungalow.number} aufgenommen.'
    )

    return Announcement(text)


def announce_bungalow_occupant_removed(
    event: BungalowOccupantRemoved, webhook: OutgoingWebhook
) -> Announcement | None:
    """Announce that a bungalow occupant has been removed."""
    bungalow = bungalow_service.get_db_bungalow(event.bungalow_id)
    initiator_screen_name = get_screen_name_or_fallback(
        event.initiator_screen_name
    )
    occupant_screen_name = get_screen_name_or_fallback(
        event.occupant_screen_name
    )

    text = (
        f'{initiator_screen_name} hat {occupant_screen_name} aus Bungalow '
        f'{bungalow.number} rausgeworfen.'
    )

    return Announcement(text)

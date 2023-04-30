"""
byceps.announce.handlers.bungalow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Announce bungalow events.

:Copyright: 2014-2023 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from byceps.announce.helpers import call_webhook
from byceps.announce.text_assembly import bungalow
from byceps.events.bungalow import (
    _BungalowEvent,
    BungalowOccupancyAvatarUpdated,
    BungalowOccupancyDescriptionUpdated,
    BungalowOccupancyMoved,
    BungalowOccupantAdded,
    BungalowOccupantRemoved,
    BungalowOccupied,
    BungalowReleased,
    BungalowReserved,
)
from byceps.services.webhooks.models import OutgoingWebhook


def announce_bungalow_reserved(
    event: BungalowReserved, webhook: OutgoingWebhook
) -> None:
    """Announce that a bungalow has been reserved."""
    text = bungalow.assemble_text_for_bungalow_reserved(event)

    send_bungalow_message(event, webhook, text)


def announce_bungalow_occupied(
    event: BungalowOccupied, webhook: OutgoingWebhook
) -> None:
    """Announce that a bungalow has been occupied."""
    text = bungalow.assemble_text_for_bungalow_occupied(event)

    send_bungalow_message(event, webhook, text)


def announce_bungalow_released(
    event: BungalowReleased, webhook: OutgoingWebhook
) -> None:
    """Announce that a bungalow has been released."""
    text = bungalow.assemble_text_for_bungalow_released(event)

    send_bungalow_message(event, webhook, text)


def announce_bungalow_occupancy_moved(
    event: BungalowOccupancyMoved, webhook: OutgoingWebhook
) -> None:
    """Announce that a bungalow's occupancy has been moved to another
    bungalow.
    """
    text = bungalow.assemble_text_for_bungalow_occupancy_moved(event)

    send_bungalow_message(event, webhook, text)


def announce_bungalow_avatar_updated(
    event: BungalowOccupancyAvatarUpdated, webhook: OutgoingWebhook
) -> None:
    """Announce that a bungalow's avatar image has been updated."""
    text = bungalow.assemble_text_for_bungalow_avatar_updated(event)

    send_bungalow_message(event, webhook, text)


def announce_bungalow_description_updated(
    event: BungalowOccupancyDescriptionUpdated,
    webhook: OutgoingWebhook,
) -> None:
    """Announce that a bungalow's description has been updated."""
    text = bungalow.assemble_text_for_bungalow_description_updated(event)

    send_bungalow_message(event, webhook, text)


def announce_bungalow_occupant_added(
    event: BungalowOccupantAdded, webhook: OutgoingWebhook
) -> None:
    """Announce that a bungalow occupant has been updated."""
    text = bungalow.assemble_text_for_bungalow_occupant_added(event)

    send_bungalow_message(event, webhook, text)


def announce_bungalow_occupant_removed(
    event: BungalowOccupantRemoved, webhook: OutgoingWebhook
) -> None:
    """Announce that a bungalow occupant has been removed."""
    text = bungalow.assemble_text_for_bungalow_occupant_removed(event)

    send_bungalow_message(event, webhook, text)


# helpers


def send_bungalow_message(
    event: _BungalowEvent, webhook: OutgoingWebhook, text: str
) -> None:
    call_webhook(webhook, text)

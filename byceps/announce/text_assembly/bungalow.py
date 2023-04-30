"""
byceps.announce.text_assembly.bungalow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Announce bungalow events.

:Copyright: 2014-2023 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

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

from ._helpers import get_screen_name_or_fallback


def assemble_text_for_bungalow_reserved(event: BungalowReserved) -> str:
    bungalow = bungalow_service.get_db_bungalow(event.bungalow_id)
    occupier_screen_name = get_screen_name_or_fallback(
        event.occupier_screen_name
    )

    return f'{occupier_screen_name} hat Bungalow {bungalow.number} reserviert.'


def assemble_text_for_bungalow_occupied(event: BungalowOccupied) -> str:
    bungalow = bungalow_service.get_db_bungalow(event.bungalow_id)
    occupier_screen_name = get_screen_name_or_fallback(
        event.occupier_screen_name
    )

    return f'{occupier_screen_name} hat Bungalow {bungalow.number} belegt.'


def assemble_text_for_bungalow_released(event: BungalowReleased) -> str:
    bungalow = bungalow_service.get_db_bungalow(event.bungalow_id)

    return f'Bungalow {bungalow.number} wurde wieder freigegeben.'


def assemble_text_for_bungalow_occupancy_moved(
    event: BungalowOccupancyMoved,
) -> str:
    source_bungalow = bungalow_service.get_db_bungalow(event.source_bungalow_id)
    target_bungalow = bungalow_service.get_db_bungalow(event.target_bungalow_id)

    return (
        f'Die Belegung von Bungalow {source_bungalow.number} '
        f'hat zu Bungalow {target_bungalow.number} gewechselt.'
    )


def assemble_text_for_bungalow_avatar_updated(
    event: BungalowOccupancyAvatarUpdated,
) -> str:
    bungalow = bungalow_service.get_db_bungalow(event.bungalow_id)
    initiator_screen_name = get_screen_name_or_fallback(
        event.initiator_screen_name
    )

    return (
        f'{initiator_screen_name} hat das Avatarbild für Bungalow '
        f'{bungalow.number} aktualisiert.'
    )


def assemble_text_for_bungalow_description_updated(
    event: BungalowOccupancyDescriptionUpdated,
) -> str:
    bungalow = bungalow_service.get_db_bungalow(event.bungalow_id)
    initiator_screen_name = get_screen_name_or_fallback(
        event.initiator_screen_name
    )

    return (
        f'{initiator_screen_name} hat das Grußwort für Bungalow '
        f'{bungalow.number} aktualisiert.'
    )


def assemble_text_for_bungalow_occupant_added(
    event: BungalowOccupantAdded,
) -> str:
    bungalow = bungalow_service.get_db_bungalow(event.bungalow_id)
    initiator_screen_name = get_screen_name_or_fallback(
        event.initiator_screen_name
    )
    occupant_screen_name = get_screen_name_or_fallback(
        event.occupant_screen_name
    )

    return (
        f'{initiator_screen_name} hat {occupant_screen_name} in Bungalow '
        f'{bungalow.number} aufgenommen.'
    )


def assemble_text_for_bungalow_occupant_removed(
    event: BungalowOccupantRemoved,
) -> str:
    bungalow = bungalow_service.get_db_bungalow(event.bungalow_id)
    initiator_screen_name = get_screen_name_or_fallback(
        event.initiator_screen_name
    )
    occupant_screen_name = get_screen_name_or_fallback(
        event.occupant_screen_name
    )

    return (
        f'{initiator_screen_name} hat {occupant_screen_name} aus Bungalow '
        f'{bungalow.number} rausgeworfen.'
    )

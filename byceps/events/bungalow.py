"""
byceps.events.bungalow
~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2023 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from __future__ import annotations

from dataclasses import dataclass

from byceps.services.bungalow.models.bungalow import BungalowID
from byceps.typing import UserID

from .base import _BaseEvent


@dataclass(frozen=True)
class _BungalowEvent(_BaseEvent):
    pass


@dataclass(frozen=True)
class _BungalowOccupancyEvent(_BungalowEvent):
    bungalow_id: BungalowID
    bungalow_number: int
    occupier_id: UserID
    occupier_screen_name: str | None


@dataclass(frozen=True)
class BungalowReservedEvent(_BungalowOccupancyEvent):
    pass


@dataclass(frozen=True)
class BungalowOccupiedEvent(_BungalowOccupancyEvent):
    pass


@dataclass(frozen=True)
class BungalowReleasedEvent(_BungalowEvent):
    bungalow_id: BungalowID
    bungalow_number: int


@dataclass(frozen=True)
class BungalowOccupancyMovedEvent(_BungalowEvent):
    source_bungalow_id: BungalowID
    source_bungalow_number: int
    target_bungalow_id: BungalowID
    target_bungalow_number: int


@dataclass(frozen=True)
class BungalowOccupancyAvatarUpdatedEvent(_BungalowEvent):
    bungalow_id: BungalowID
    bungalow_number: int


@dataclass(frozen=True)
class BungalowOccupancyDescriptionUpdatedEvent(_BungalowEvent):
    bungalow_id: BungalowID
    bungalow_number: int


@dataclass(frozen=True)
class _BungalowOccupantEvent(_BungalowEvent):
    bungalow_id: BungalowID
    bungalow_number: int
    occupant_id: UserID
    occupant_screen_name: str | None


@dataclass(frozen=True)
class BungalowOccupantAddedEvent(_BungalowOccupantEvent):
    pass


@dataclass(frozen=True)
class BungalowOccupantRemovedEvent(_BungalowOccupantEvent):
    pass

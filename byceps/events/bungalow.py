"""
byceps.events.bungalow
~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2023 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from dataclasses import dataclass
from typing import Optional

from ..services.bungalow.models.bungalow import BungalowID
from ..typing import UserID

from .base import _BaseEvent


@dataclass(frozen=True)
class _BungalowEvent(_BaseEvent):
    pass


@dataclass(frozen=True)
class _BungalowOccupancyEvent(_BungalowEvent):
    bungalow_id: BungalowID
    occupier_id: UserID
    occupier_screen_name: Optional[str]


@dataclass(frozen=True)
class BungalowReserved(_BungalowOccupancyEvent):
    pass


@dataclass(frozen=True)
class BungalowOccupied(_BungalowOccupancyEvent):
    pass


@dataclass(frozen=True)
class BungalowReleased(_BungalowEvent):
    bungalow_id: BungalowID


@dataclass(frozen=True)
class BungalowOccupancyMoved(_BungalowEvent):
    source_bungalow_id: BungalowID
    target_bungalow_id: BungalowID


@dataclass(frozen=True)
class BungalowOccupancyAvatarUpdated(_BungalowEvent):
    bungalow_id: BungalowID


@dataclass(frozen=True)
class BungalowOccupancyDescriptionUpdated(_BungalowEvent):
    bungalow_id: BungalowID


@dataclass(frozen=True)
class _BungalowOccupantEvent(_BungalowEvent):
    bungalow_id: BungalowID
    occupant_id: UserID
    occupant_screen_name: Optional[str]


@dataclass(frozen=True)
class BungalowOccupantAdded(_BungalowOccupantEvent):
    pass


@dataclass(frozen=True)
class BungalowOccupantRemoved(_BungalowOccupantEvent):
    pass

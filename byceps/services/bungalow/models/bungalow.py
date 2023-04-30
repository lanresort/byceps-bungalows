"""
byceps.services.bungalow.models.bungalow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2023 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import NewType, Optional
from uuid import UUID

from byceps.typing import PartyID

from .category import BungalowCategory


BungalowID = NewType('BungalowID', UUID)


BungalowOccupationState = Enum(
    'BungalowOccupationState', ['available', 'reserved', 'occupied']
)


@dataclass(frozen=True)
class Bungalow:
    id: BungalowID
    party_id: PartyID
    number: int
    category: BungalowCategory
    occupation_state: BungalowOccupationState
    distributes_network: bool
    available: bool
    reserved: bool
    occupied: bool
    reserved_or_occupied: bool
    occupancy: Optional['BungalowOccupancy']
    avatar_url: str | None

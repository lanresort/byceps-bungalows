"""
byceps.services.bungalow.models.occupation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2023 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum
from typing import NewType, Optional
from uuid import UUID

from byceps.services.shop.order.models.number import OrderNumber
from byceps.services.ticketing.models.ticket import TicketBundleID, TicketID
from byceps.services.user.models.user import User
from byceps.typing import UserID

from .bungalow import BungalowID, BungalowOccupationState


OccupancyState = Enum('OccupancyState', ['reserved', 'occupied'])


ReservationID = NewType('ReservationID', UUID)


OccupancyID = NewType('OccupancyID', UUID)


@dataclass(frozen=True)
class BungalowReservation:
    id: ReservationID
    bungalow_id: BungalowID
    reserved_by_id: UserID
    order_number: Optional[OrderNumber]
    pinned: bool
    internal_remark: Optional[str]


@dataclass(frozen=True)
class BungalowOccupancy:
    id: OccupancyID
    bungalow_id: BungalowID
    occupied_by_id: UserID
    order_number: Optional[OrderNumber]
    state: OccupancyState
    ticket_bundle_id: Optional[TicketBundleID]
    pinned: bool
    manager_id: UserID
    title: Optional[str]
    description: Optional[str]
    avatar_id: Optional[UUID]
    internal_remark: Optional[str]


@dataclass(frozen=True)
class OccupantSlot:
    ticket_id: TicketID
    occupant: Optional[User]


@dataclass(frozen=True)
class OccupationStateTotals:
    available: int
    reserved: int
    occupied: int


@dataclass(frozen=True)
class CategoryOccupationSummary:
    available: int
    reserved: int
    occupied: int
    total: int

    @classmethod
    def from_counts(
        cls, available: int, reserved: int, occupied: int
    ) -> CategoryOccupationSummary:
        """Create instance from state values, but have total calculated."""
        total = available + reserved + occupied

        return cls(available, reserved, occupied, total)

    @classmethod
    def from_counts_by_state(
        cls, counts_by_state: dict[BungalowOccupationState, int]
    ) -> CategoryOccupationSummary:
        counter = Counter(counts_by_state)

        available = counter[BungalowOccupationState.available]
        reserved = counter[BungalowOccupationState.reserved]
        occupied = counter[BungalowOccupationState.occupied]

        return cls.from_counts(available, reserved, occupied)

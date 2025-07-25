"""
byceps.services.bungalow.models.occupation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2025 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum
from typing import NewType
from uuid import UUID

from byceps.services.shop.order.models.number import OrderNumber
from byceps.services.ticketing.models.ticket import TicketBundleID, TicketID
from byceps.services.user.models.user import User, UserID

from .bungalow import BungalowID, BungalowOccupationState


OccupancyState = Enum('OccupancyState', ['reserved', 'occupied'])


ReservationID = NewType('ReservationID', UUID)


OccupancyID = NewType('OccupancyID', UUID)


@dataclass(frozen=True, kw_only=True)
class BungalowReservation:
    id: ReservationID
    bungalow_id: BungalowID
    reserved_by_id: UserID
    order_number: OrderNumber | None
    pinned: bool
    internal_remark: str | None


@dataclass(frozen=True, kw_only=True)
class BungalowOccupancy:
    id: OccupancyID
    bungalow_id: BungalowID
    occupied_by_id: UserID
    order_number: OrderNumber | None
    state: OccupancyState
    ticket_bundle_id: TicketBundleID | None
    pinned: bool
    manager_id: UserID
    title: str | None
    description: str | None
    avatar_id: UUID | None
    internal_remark: str | None


@dataclass(frozen=True, kw_only=True)
class OccupantSlot:
    ticket_id: TicketID
    occupant: User | None


@dataclass(frozen=True, kw_only=True)
class OccupationStateTotals:
    available: int
    reserved: int
    occupied: int


@dataclass(frozen=True, kw_only=True)
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

        return cls(
            available=available,
            reserved=reserved,
            occupied=occupied,
            total=total,
        )

    @classmethod
    def from_counts_by_state(
        cls, counts_by_state: dict[BungalowOccupationState, int]
    ) -> CategoryOccupationSummary:
        counter = Counter(counts_by_state)

        available = counter[BungalowOccupationState.available]
        reserved = counter[BungalowOccupationState.reserved]
        occupied = counter[BungalowOccupationState.occupied]

        return cls.from_counts(available, reserved, occupied)

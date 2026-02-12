"""
byceps.services.bungalow.dbmodels.occupancy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    hybrid_property = property
else:
    from sqlalchemy.ext.hybrid import hybrid_property

from byceps.database import db
from byceps.services.bungalow.models.bungalow import BungalowID
from byceps.services.bungalow.models.occupation import (
    OccupancyID,
    OccupancyState,
    ReservationID,
)
from byceps.services.party.models import PartyID
from byceps.services.shop.order.models.number import OrderNumber
from byceps.services.ticketing.dbmodels.ticket_bundle import DbTicketBundle
from byceps.services.ticketing.models.ticket import TicketBundleID
from byceps.services.user.models import UserID
from byceps.util.instances import ReprBuilder

from .avatar import DbBungalowAvatar
from .bungalow import DbBungalow


class DbBungalowReservation(db.Model):
    """A reservation for a bungalow."""

    __tablename__ = 'bungalow_reservations'

    id: Mapped[ReservationID] = mapped_column(primary_key=True)
    bungalow_id: Mapped[BungalowID] = mapped_column(
        db.ForeignKey('bungalows.id'), unique=True, index=True
    )
    bungalow: Mapped[DbBungalow] = relationship(
        backref=db.backref('reservation', uselist=False)
    )
    reserved_by_id: Mapped[UserID] = mapped_column(db.ForeignKey('users.id'))
    order_number: Mapped[OrderNumber | None] = mapped_column(
        db.UnicodeText,
        db.ForeignKey('shop_orders.order_number'),
        unique=True,
        index=True,
    )
    pinned: Mapped[bool]
    internal_remark: Mapped[str | None] = mapped_column(db.UnicodeText)

    def __init__(
        self,
        reservation_id: ReservationID,
        bungalow_id: BungalowID,
        reserved_by_id: UserID,
        pinned: bool,
    ) -> None:
        self.id = reservation_id
        self.bungalow_id = bungalow_id
        self.reserved_by_id = reserved_by_id
        self.pinned = pinned


class DbBungalowOccupancy(db.Model):
    """The occupancy of a bungalow."""

    __tablename__ = 'bungalow_occupancies'

    id: Mapped[OccupancyID] = mapped_column(primary_key=True)
    bungalow_id: Mapped[BungalowID] = mapped_column(
        db.ForeignKey('bungalows.id'), unique=True, index=True
    )
    bungalow: Mapped[DbBungalow] = relationship(
        backref=db.backref('occupancy', uselist=False)
    )
    occupied_by_id: Mapped[UserID] = mapped_column(db.ForeignKey('users.id'))
    order_number: Mapped[OrderNumber | None] = mapped_column(
        db.UnicodeText,
        db.ForeignKey('shop_orders.order_number'),
        unique=True,
        index=True,
    )
    _state: Mapped[str] = mapped_column('state', db.UnicodeText)
    ticket_bundle_id: Mapped[TicketBundleID | None] = mapped_column(
        db.ForeignKey('ticket_bundles.id'), unique=True, index=True
    )
    ticket_bundle: Mapped[DbTicketBundle] = relationship(
        backref=db.backref('bungalow_occupancy', uselist=False)
    )
    pinned: Mapped[bool]
    managed_by_id: Mapped[UserID | None] = mapped_column(
        db.ForeignKey('users.id')
    )
    title: Mapped[str | None] = mapped_column(db.UnicodeText)
    description: Mapped[str | None] = mapped_column(db.UnicodeText)
    avatar_id: Mapped[UUID | None] = mapped_column(
        db.ForeignKey('bungalow_occupancy_avatars.id')
    )
    avatar: Mapped[DbBungalowAvatar] = relationship()
    internal_remark: Mapped[str | None] = mapped_column(db.UnicodeText)

    def __init__(
        self,
        occupancy_id: OccupancyID,
        bungalow_id: BungalowID,
        occupier_id: UserID,
        state: OccupancyState,
        pinned: bool,
        *,
        order_number: OrderNumber | None = None,
        ticket_bundle_id: TicketBundleID | None = None,
    ) -> None:
        self.id = occupancy_id
        self.bungalow_id = bungalow_id
        self.occupied_by_id = occupier_id
        self.order_number = order_number
        self._state = state.name
        self.ticket_bundle_id = ticket_bundle_id
        self.pinned = pinned

    @hybrid_property
    def state(self) -> OccupancyState:
        return OccupancyState[self._state]

    @state.setter
    def state(self, state: OccupancyState) -> None:
        self._state = state.name

    @property
    def manager_id(self) -> UserID:
        return self.managed_by_id or self.occupied_by_id

    def get_avatar_url(self, party_id: PartyID) -> str | None:
        if not self.avatar:
            return None

        return self.avatar.get_url(party_id)

    def __repr__(self) -> str:
        return (
            ReprBuilder(self)
            .add('bungalow', self.bungalow.number)
            .add('occupied_by_id', self.occupied_by_id)
            .add('state', self.state.name)
            .build()
        )

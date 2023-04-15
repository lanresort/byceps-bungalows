"""
byceps.services.bungalow.dbmodels.occupancy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2023 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    hybrid_property = property
else:
    from sqlalchemy.ext.hybrid import hybrid_property

from ....database import db, generate_uuid7
from ....typing import PartyID, UserID
from ....util.instances import ReprBuilder

from ...ticketing.dbmodels.ticket_bundle import DbTicketBundle

from ..models.bungalow import BungalowID
from ..models.occupation import OccupancyState

from .avatar import DbBungalowAvatar
from .bungalow import DbBungalow


class DbBungalowReservation(db.Model):
    """A reservation for a bungalow."""

    __tablename__ = 'bungalow_reservations'

    id = db.Column(db.Uuid, default=generate_uuid7, primary_key=True)
    bungalow_id = db.Column(
        db.Uuid,
        db.ForeignKey('bungalows.id'),
        unique=True,
        index=True,
        nullable=False,
    )
    bungalow = db.relationship(
        DbBungalow, backref=db.backref('reservation', uselist=False)
    )
    reserved_by_id = db.Column(
        db.Uuid, db.ForeignKey('users.id'), nullable=False
    )
    order_number = db.Column(
        db.UnicodeText,
        db.ForeignKey('shop_orders.order_number'),
        unique=True,
        index=True,
        nullable=True,
    )
    pinned = db.Column(db.Boolean, default=False, nullable=False)
    internal_remark = db.Column(db.UnicodeText, nullable=True)

    def __init__(self, bungalow_id: BungalowID, reserved_by_id: UserID) -> None:
        self.bungalow_id = bungalow_id
        self.reserved_by_id = reserved_by_id


class DbBungalowOccupancy(db.Model):
    """The occupancy of a bungalow."""

    __tablename__ = 'bungalow_occupancies'

    id = db.Column(db.Uuid, default=generate_uuid7, primary_key=True)
    bungalow_id = db.Column(
        db.Uuid,
        db.ForeignKey('bungalows.id'),
        unique=True,
        index=True,
        nullable=False,
    )
    bungalow = db.relationship(
        DbBungalow, backref=db.backref('occupancy', uselist=False)
    )
    occupied_by_id = db.Column(
        db.Uuid, db.ForeignKey('users.id'), nullable=False
    )
    order_number = db.Column(
        db.UnicodeText,
        db.ForeignKey('shop_orders.order_number'),
        unique=True,
        index=True,
        nullable=True,
    )
    _state = db.Column('state', db.UnicodeText, nullable=False)
    ticket_bundle_id = db.Column(
        db.Uuid,
        db.ForeignKey('ticket_bundles.id'),
        unique=True,
        index=True,
        nullable=True,
    )
    ticket_bundle = db.relationship(
        DbTicketBundle, backref=db.backref('bungalow_occupancy', uselist=False)
    )
    pinned = db.Column(db.Boolean, default=False, nullable=False)
    managed_by_id = db.Column(db.Uuid, db.ForeignKey('users.id'), nullable=True)
    title = db.Column(db.UnicodeText, nullable=True)
    description = db.Column(db.UnicodeText, nullable=True)
    avatar_id = db.Column(
        db.Uuid, db.ForeignKey('bungalow_occupancy_avatars.id'), nullable=True
    )
    avatar = db.relationship(DbBungalowAvatar)
    internal_remark = db.Column(db.UnicodeText, nullable=True)

    def __init__(
        self,
        bungalow_id: BungalowID,
        occupier_id: UserID,
        state: OccupancyState,
    ) -> None:
        self.bungalow_id = bungalow_id
        self.occupied_by_id = occupier_id
        self._state = state.name

    @hybrid_property
    def state(self) -> OccupancyState:
        return OccupancyState[self._state]

    @state.setter
    def state(self, state: OccupancyState) -> None:
        assert state is not None
        self._state = state.name

    @property
    def manager_id(self) -> UserID:
        return self.managed_by_id or self.occupied_by_id

    def get_avatar_url(self, party_id: PartyID) -> Optional[str]:
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

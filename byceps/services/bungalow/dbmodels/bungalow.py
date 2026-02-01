"""
byceps.services.bungalow.dbmodels.bungalow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    hybrid_property = property
else:
    from sqlalchemy.ext.hybrid import hybrid_property

from byceps.database import db
from byceps.services.bungalow.models.bungalow import (
    BungalowID,
    BungalowOccupationState,
)
from byceps.services.bungalow.models.category import BungalowCategoryID
from byceps.services.party.models import PartyID
from byceps.util.instances import ReprBuilder

from .category import DbBungalowCategory


class DbBungalow(db.Model):
    """A bungalow."""

    __tablename__ = 'bungalows'
    __table_args__ = (db.UniqueConstraint('party_id', 'number'),)

    id: Mapped[BungalowID] = mapped_column(primary_key=True)
    party_id: Mapped[PartyID] = mapped_column(
        db.UnicodeText, db.ForeignKey('parties.id'), index=True
    )
    number: Mapped[int] = mapped_column(db.SmallInteger, index=True)
    category_id: Mapped[BungalowCategoryID] = mapped_column(
        db.ForeignKey('bungalow_categories.id'), index=True
    )
    category: Mapped[DbBungalowCategory] = relationship()
    _occupation_state: Mapped[str] = mapped_column(
        'occupation_state', db.UnicodeText
    )
    distributes_network: Mapped[bool]

    def __init__(
        self,
        bungalow_id: BungalowID,
        party_id: PartyID,
        number: int,
        category_id: BungalowCategoryID,
        distributes_network: bool,
    ) -> None:
        self.id = bungalow_id
        self.party_id = party_id
        self.number = number
        self.category_id = category_id
        self._occupation_state = BungalowOccupationState.available.name
        self.distributes_network = distributes_network

    @hybrid_property
    def occupation_state(self) -> BungalowOccupationState:
        return BungalowOccupationState[self._occupation_state]

    @occupation_state.setter
    def occupation_state(self, state: BungalowOccupationState) -> None:
        self._occupation_state = state.name

    @property
    def available(self) -> bool:
        return self.occupation_state == BungalowOccupationState.available

    @property
    def reserved(self) -> bool:
        return self.occupation_state == BungalowOccupationState.reserved

    @property
    def occupied(self) -> bool:
        return self.occupation_state == BungalowOccupationState.occupied

    @property
    def reserved_or_occupied(self) -> bool:
        """Return `True` if the bungalow is reserved or occupied."""
        return self.reserved or self.occupied

    @property
    def avatar_url(self) -> str | None:
        if not self.occupancy:
            return None

        return self.occupancy.get_avatar_url(self.party_id)

    def __repr__(self) -> str:
        return (
            ReprBuilder(self)
            .add_with_lookup('id')
            .add('party', self.party_id)
            .add_with_lookup('number')
            .add('occupation_state', self.occupation_state.name)
            .build()
        )

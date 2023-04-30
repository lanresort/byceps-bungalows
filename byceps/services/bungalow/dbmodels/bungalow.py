"""
byceps.services.bungalow.dbmodels.bungalow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2023 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from typing import Optional, TYPE_CHECKING


if TYPE_CHECKING:
    hybrid_property = property
else:
    from sqlalchemy.ext.hybrid import hybrid_property

from byceps.database import db, generate_uuid7
from byceps.services.bungalow.models.bungalow import BungalowOccupationState
from byceps.services.bungalow.models.category import BungalowCategoryID
from byceps.typing import PartyID
from byceps.util.instances import ReprBuilder

from .category import DbBungalowCategory


class DbBungalow(db.Model):
    """A bungalow."""

    __tablename__ = 'bungalows'
    __table_args__ = (db.UniqueConstraint('party_id', 'number'),)

    id = db.Column(db.Uuid, default=generate_uuid7, primary_key=True)
    party_id = db.Column(
        db.UnicodeText, db.ForeignKey('parties.id'), index=True, nullable=False
    )
    number = db.Column(db.SmallInteger, index=True, nullable=False)
    category_id = db.Column(
        db.Uuid,
        db.ForeignKey('bungalow_categories.id'),
        index=True,
        nullable=False,
    )
    category = db.relationship(DbBungalowCategory)
    _occupation_state = db.Column(
        'occupation_state', db.UnicodeText, nullable=False
    )
    distributes_network = db.Column(db.Boolean, default=False, nullable=False)

    def __init__(
        self,
        party_id: PartyID,
        number: int,
        category_id: BungalowCategoryID,
    ) -> None:
        self.party_id = party_id
        self.number = number
        self.category_id = category_id
        self._occupation_state = BungalowOccupationState.available.name

    @hybrid_property
    def occupation_state(self) -> BungalowOccupationState:
        return BungalowOccupationState[self._occupation_state]

    @occupation_state.setter
    def occupation_state(self, state: BungalowOccupationState) -> None:
        assert state is not None
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
    def avatar_url(self) -> Optional[str]:
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

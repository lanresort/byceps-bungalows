"""
byceps.services.bungalow.dbmodels.accommodation_request
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.orm import Mapped, mapped_column

if TYPE_CHECKING:
    hybrid_property = property
else:
    from sqlalchemy.ext.hybrid import hybrid_property

from byceps.database import db
from byceps.services.bungalow.models.accommodation_request import (
    AccommodationRequestID,
    AccommodationRequestState,
)
from byceps.services.bungalow.models.bungalow import BungalowID
from byceps.services.user.models import UserID


class DbAccommodationRequest(db.Model):
    """An invitation from the main occupant or a request from a user to
    join a specific bungalow.
    """

    __tablename__ = 'bungalow_accommodation_requests'

    id: Mapped[AccommodationRequestID] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime | None]
    bungalow_id: Mapped[BungalowID] = mapped_column(
        db.ForeignKey('bungalows.id'), index=True
    )
    candidate_id: Mapped[UserID] = mapped_column(db.ForeignKey('users.id'))
    _state: Mapped[str] = mapped_column('state', db.UnicodeText)
    token: Mapped[UUID | None]

    def __init__(
        self,
        request_id: AccommodationRequestID,
        bungalow_id: BungalowID,
        candidate_id: UserID,
        state: AccommodationRequestState,
        token: UUID,
    ) -> None:
        self.id = request_id
        self.bungalow_id = bungalow_id
        self.candidate_id = candidate_id
        self.state = state
        self.token = token

    @hybrid_property
    def state(self) -> AccommodationRequestState:
        return AccommodationRequestState[self._state]

    @state.setter
    def state(self, state: AccommodationRequestState) -> None:
        if not state:
            raise ValueError('A state must be specified.')

        self._state = state.name

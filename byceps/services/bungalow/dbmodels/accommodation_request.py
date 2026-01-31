"""
byceps.services.bungalow.dbmodels.accommodation_request
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID


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

    id = db.Column(db.Uuid, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=True)
    bungalow_id = db.Column(
        db.Uuid, db.ForeignKey('bungalows.id'), index=True, nullable=False
    )
    candidate_id = db.Column(db.Uuid, db.ForeignKey('users.id'), nullable=False)
    _state = db.Column('state', db.UnicodeText, nullable=False)
    token = db.Column(db.Uuid, nullable=True)

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

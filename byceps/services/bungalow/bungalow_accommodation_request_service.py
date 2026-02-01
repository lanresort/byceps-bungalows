"""
byceps.services.bungalow.bungalow_accomodation_request_service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from __future__ import annotations

from datetime import datetime

from byceps.database import db
from byceps.services.user.models import UserID
from byceps.util.uuid import generate_uuid4, generate_uuid7

from .dbmodels.accommodation_request import DbAccommodationRequest
from .models.accommodation_request import (
    AccommodationRequestID,
    AccommodationRequestState,
)
from .models.bungalow import BungalowID


def create_request(
    bungalow_id: BungalowID, candidate_id: UserID
) -> DbAccommodationRequest:
    """Create an accommodation request for that bungalow."""
    request_id = AccommodationRequestID(generate_uuid7())
    created_at = datetime.utcnow()
    state = AccommodationRequestState.open
    token = generate_uuid4()

    db_request = DbAccommodationRequest(
        request_id, created_at, bungalow_id, candidate_id, state, token
    )

    db.session.add(db_request)
    db.session.commit()

    return db_request


def accept_request(
    db_request: DbAccommodationRequest,
) -> DbAccommodationRequest:
    """Accept the accommodation request."""
    return _update_request(db_request, AccommodationRequestState.accepted)


def deny_request(db_request: DbAccommodationRequest) -> DbAccommodationRequest:
    """Deny the accommodation request."""
    return _update_request(db_request, AccommodationRequestState.denied)


def _update_request(
    db_request: DbAccommodationRequest, state: AccommodationRequestState
) -> DbAccommodationRequest:
    db_request.updated_at = datetime.utcnow()
    db_request.state = state
    db_request.token = None

    db.session.commit()

    return db_request


def find_request(
    request_id: AccommodationRequestID,
) -> DbAccommodationRequest | None:
    """Return the accommodation request with that ID, or `None` if not found."""
    return db.session.get(DbAccommodationRequest, request_id)

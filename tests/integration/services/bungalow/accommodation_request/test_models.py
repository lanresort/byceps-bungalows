"""
:Copyright: 2014-2023 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

import pytest

from byceps.services.bungalow import bungalow_accommodation_request_service
from byceps.services.bungalow.models.accommodation_request import (
    AccommodationRequestState,
)


@pytest.fixture(scope='module')
def bungalow(make_bungalow):
    return make_bungalow()


@pytest.fixture(scope='module')
def candidate(make_user):
    return make_user('BungalowCandidate')


def test_creation(site_app, bungalow, candidate):
    request = bungalow_accommodation_request_service.create_request(
        bungalow.id, candidate.id
    )

    assert request.created_at is not None
    assert request.updated_at is None
    assert request.bungalow_id == bungalow.id
    assert request.candidate_id == candidate.id
    assert request.state == AccommodationRequestState.open
    assert request.token is not None


def test_accept(site_app, bungalow, candidate):
    request = bungalow_accommodation_request_service.create_request(
        bungalow.id, candidate.id
    )

    request = bungalow_accommodation_request_service.accept_request(request)

    assert request.updated_at is not None
    assert request.state == AccommodationRequestState.accepted
    assert request.token is None


def test_deny(site_app, bungalow, candidate):
    request = bungalow_accommodation_request_service.create_request(
        bungalow.id, candidate.id
    )

    request = bungalow_accommodation_request_service.deny_request(request)

    assert request.updated_at is not None
    assert request.state == AccommodationRequestState.denied
    assert request.token is None

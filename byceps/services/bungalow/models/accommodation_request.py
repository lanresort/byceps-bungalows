"""
byceps.services.bungalow.models.accommodation_request
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2024 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from enum import Enum
from typing import NewType
from uuid import UUID


AccommodationRequestState = Enum(
    'AccommodationRequestState', ['open', 'accepted', 'denied']
)


AccommodationRequestID = NewType('AccommodationRequestID', UUID)

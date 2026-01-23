"""
byceps.services.bungalow.first_attendance_service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from collections import defaultdict
from collections.abc import Iterable

from sqlalchemy import select

from byceps.database import db
from byceps.services.brand.models import BrandID
from byceps.services.bungalow import bungalow_service
from byceps.services.party.models import Party, PartyID
from byceps.services.ticketing import ticket_attendance_service
from byceps.services.ticketing.dbmodels.category import DbTicketCategory
from byceps.services.ticketing.dbmodels.ticket import DbTicket
from byceps.services.user import user_service
from byceps.services.user.dbmodels import DbUser
from byceps.services.user.models import User


def get_first_time_attendees_by_bungalow(party: Party) -> dict[int, list[User]]:
    """List users that attend the party series for the first time,
    grouped by bungalow number.
    """
    first_time_attendees = _get_first_time_attendees(party)
    return _group_attendees_by_bungalow_number(first_time_attendees, party.id)


def _get_first_time_attendees(party: Party) -> list[User]:
    return [
        attendee
        for attendee in _get_party_attendees(party.id)
        if not _has_attended_brand_parties(attendee, party.brand_id)
    ]


def _get_party_attendees(party_id: PartyID) -> list[User]:
    rows = db.session.scalars(
        select(DbUser)
        .join(DbTicket, DbTicket.used_by_id == DbUser.id)
        .filter(DbTicket.revoked == False)  # noqa: E712
        .join(DbTicketCategory)
        .filter(DbTicketCategory.party_id == party_id)
    ).all()

    return [user_service._db_entity_to_user(row) for row in rows]


def _has_attended_brand_parties(attendee: User, brand_id: BrandID) -> bool:
    attended_parties = ticket_attendance_service.get_attended_parties(
        attendee.id, limit_to_brand_id=brand_id
    )
    return bool(attended_parties)


def _group_attendees_by_bungalow_number(
    attendees: Iterable[User], party_id: PartyID
) -> dict[int, list[User]]:
    def add_bungalow_number(attendee: User) -> tuple[User, int]:
        bungalow = bungalow_service.find_bungalow_inhabited_by_user(
            attendee.id, party_id
        )

        return attendee, bungalow.number

    attendees_with_bungalow_numbers = map(add_bungalow_number, attendees)

    attendees_by_bungalow_number = defaultdict(list)

    for attendee, bungalow_number in attendees_with_bungalow_numbers:
        attendees_by_bungalow_number[bungalow_number].append(attendee)

    return attendees_by_bungalow_number

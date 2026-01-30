"""
byceps.services.bungalow.bungalow_service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select

from byceps.database import db, paginate, Pagination
from byceps.services.brand import brand_setting_service
from byceps.services.brand.models import BrandID
from byceps.services.party import party_service
from byceps.services.party.models import Party, PartyID
from byceps.services.shop.product.dbmodels.product import DbProduct
from byceps.services.ticketing import ticket_bundle_service, ticket_service
from byceps.services.ticketing.dbmodels.ticket import DbTicket
from byceps.services.ticketing.dbmodels.ticket_bundle import DbTicketBundle
from byceps.services.user.dbmodels import DbUser
from byceps.services.user.models import User, UserID

from .dbmodels.bungalow import DbBungalow
from .dbmodels.category import DbBungalowCategory
from .dbmodels.occupancy import DbBungalowOccupancy
from .model_converters import _db_entity_to_bungalow
from .models.bungalow import Bungalow, BungalowID
from .models.occupation import BungalowOccupancy


def get_active_bungalow_parties() -> list[Party]:
    """Return active parties that use bungalows."""
    return [
        party
        for party in party_service.get_active_parties()
        if has_brand_bungalows(party.brand_id)
    ]


# -------------------------------------------------------------------- #
# bungalow


def has_brand_bungalows(brand_id: BrandID) -> bool:
    """Return `True` if the brand's parties are built on bungalows."""
    has_bungalows = brand_setting_service.find_setting_value(
        brand_id, 'has_bungalows'
    )

    return has_bungalows == 'true'


def find_bungalow(bungalow_id: BungalowID) -> Bungalow | None:
    """Return the bungalow with that id, or `None` if not found."""
    db_bungalow = db.session.execute(
        select(DbBungalow)
        .options(
            db.joinedload(DbBungalow.category),
            db.joinedload(DbBungalow.occupancy),
        )
        .filter_by(id=bungalow_id)
    ).scalar_one_or_none()

    if db_bungalow is None:
        return None

    return _db_entity_to_bungalow(db_bungalow)


def find_db_bungalow(bungalow_id: BungalowID) -> DbBungalow | None:
    """Return the bungalow with that id, or `None` if not found."""
    return db.session.get(DbBungalow, bungalow_id)


def get_db_bungalow(bungalow_id: BungalowID) -> DbBungalow:
    """Return the bungalow with that id."""
    db_bungalow = find_db_bungalow(bungalow_id)

    if db_bungalow is None:
        raise ValueError('Unknown bungalow ID')

    return db_bungalow


def find_db_bungalow_by_number(
    party_id: PartyID, number: int
) -> DbBungalow | None:
    """Return the bungalow with that number during that party, or `None`
    if not found.
    """
    return db.session.scalars(
        select(DbBungalow).filter_by(party_id=party_id).filter_by(number=number)
    ).one_or_none()


def get_bungalow_numbers_for_party(party_id: PartyID) -> set[int]:
    """Return the numbers of all bungalows that are offered for the party."""
    numbers = db.session.scalars(
        select(DbBungalow.number).filter_by(party_id=party_id)
    ).all()

    return set(numbers)


def get_bungalows_for_party(party_id: PartyID) -> Sequence[DbBungalow]:
    """Return all bungalows for the party, ordered by number."""
    return db.session.scalars(
        select(DbBungalow)
        .filter_by(party_id=party_id)
        .options(
            db.load_only(
                DbBungalow.party_id,
                DbBungalow.number,
                DbBungalow._occupation_state,
                DbBungalow.distributes_network,
            ),
            db.joinedload(DbBungalow.category).load_only(
                DbBungalowCategory.title, DbBungalowCategory.capacity
            ),
            db.joinedload(DbBungalow.category)
            .joinedload(DbBungalowCategory.product)
            .load_only(DbProduct.id, DbProduct.item_number, DbProduct.name),
            db.joinedload(DbBungalow.occupancy).joinedload(
                DbBungalowOccupancy.ticket_bundle
            ),
        )
        .order_by(DbBungalow.number)
    ).all()


def get_bungalows_extended_for_party(party_id: PartyID) -> Sequence[DbBungalow]:
    """Return all bungalows for the party, ordered by number."""
    return db.session.scalars(
        select(DbBungalow)
        .filter_by(party_id=party_id)
        .options(db.joinedload(DbBungalow.occupancy))
        .order_by(DbBungalow.number)
    ).all()


# -------------------------------------------------------------------- #
# ticket


def assign_first_ticket_to_main_occupant(occupancy: BungalowOccupancy) -> None:
    """Assign the bundle's first ticket to the bungalow's main occupant.

    If the user already uses another ticket, none of this bundle will be
    assigned to them.
    """
    db_ticket_bundle = ticket_bundle_service.get_bundle(
        occupancy.ticket_bundle_id
    )
    if not db_ticket_bundle.tickets:
        return

    db_tickets = list(
        sorted(db_ticket_bundle.tickets, key=lambda t: t.created_at)
    )
    first_ticket = db_tickets[0]

    main_occupant_id = occupancy.occupied_by_id

    party_id = first_ticket.category.party_id
    already_uses_ticket = ticket_service.uses_any_ticket_for_party(
        main_occupant_id, party_id
    )
    if already_uses_ticket:
        return

    first_ticket.used_by_id = main_occupant_id
    db.session.commit()


def find_bungalow_inhabited_by_user(
    user_id: UserID, party_id: PartyID
) -> DbBungalow | None:
    """Try to find the bungalow the current user resides (i.e. uses a
    ticket) in.
    """
    return db.session.execute(
        select(DbBungalow)
        .join(DbBungalowOccupancy)
        .join(DbTicketBundle)
        .join(DbTicket)
        .filter(DbTicket.party_id == party_id)
        # A user should not be able to occupy
        # more than one occupant slot.
        .filter(DbTicket.used_by_id == user_id)
        .filter(DbTicket.revoked == False)  # noqa: E712
    ).scalar_one_or_none()


def is_user_allowed_to_manage_any_occupant_slots(
    user: User, db_occupancy: DbBungalowOccupancy
) -> bool:
    """Return `True` if the given user is entitled to manage at least
    one of the bungalow's occupant slots.
    """
    db_tickets = db_occupancy.ticket_bundle.tickets
    return any(
        db_ticket.is_user_managed_by(user.id) for db_ticket in db_tickets
    )


def get_all_occupant_tickets_paginated(
    party_id: PartyID,
    page: int,
    items_per_page: int,
    *,
    search_term: str | None = None,
) -> Pagination:
    """Return tickets for which a user has been assigned for all
    bungalows of the party.
    """
    stmt = (
        select(DbTicket)
        .filter(DbTicket.party_id == party_id)
        .filter(DbTicket.revoked == False)  # noqa: E712
        .join(DbTicket.used_by)
        .options(
            db.joinedload(DbTicket.used_by).joinedload(DbUser.avatar),
            db.joinedload(DbTicket.used_by).joinedload(
                DbUser.orga_team_memberships
            ),
        )
        .order_by(db.func.lower(DbUser.screen_name))
    )

    if search_term:
        stmt = stmt.filter(DbUser.screen_name.ilike(f'%{search_term}%'))

    return paginate(stmt, page, items_per_page)

"""
byceps.services.bungalow.bungalow_stats_service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2023 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Iterator
from operator import attrgetter
from typing import Callable

from sqlalchemy import select

from byceps.database import db
from byceps.services.party.models import PartyID
from byceps.services.ticketing import ticket_category_service
from byceps.services.ticketing.dbmodels.category import DbTicketCategory
from byceps.services.ticketing.models.ticket import TicketCategory

from .dbmodels.bungalow import DbBungalow
from .dbmodels.category import DbBungalowCategory
from .models.bungalow import BungalowOccupationState
from .models.occupation import CategoryOccupationSummary, OccupationStateTotals


BungalowCountByCategoryAndState = list[
    tuple[TicketCategory, BungalowOccupationState, int]
]


def get_occupation_state_totals_for_party(
    party_id: PartyID,
) -> OccupationStateTotals:
    """Return bungalow totals per occupation state for that party."""
    rows = db.session.execute(
        select(
            DbBungalow._occupation_state,
            db.func.count(DbBungalow._occupation_state),
        )
        .join(DbBungalowCategory)
        .join(DbTicketCategory)
        .filter(DbTicketCategory.party_id == party_id)
        .group_by(DbBungalow._occupation_state)
    ).all()

    state_names = {state.name for state in BungalowOccupationState}
    total_by_state = dict.fromkeys(state_names, 0)

    for state_name, count in rows:
        total_by_state[state_name] = count

    return OccupationStateTotals(**total_by_state)


def get_statistics_by_category(
    party_id: PartyID,
    *,
    get_counts_func: Callable[[PartyID], BungalowCountByCategoryAndState]
    | None = None,
) -> Iterator[tuple[TicketCategory, CategoryOccupationSummary]]:
    """Return the number of available/reserved/occupied/total bungalows
    per category.
    """
    if get_counts_func is None:
        get_counts_func = _get_bungalow_counts_by_category_and_state

    d: dict[tuple[TicketCategory, BungalowOccupationState], int] = defaultdict(
        int
    )

    counts = get_counts_func(party_id)
    for category, state_name, count in counts:
        state = BungalowOccupationState[state_name]
        d[(category, state)] = count

    categories = ticket_category_service.get_categories_for_party(party_id)
    states = frozenset(BungalowOccupationState)

    for category in categories:
        counts_by_state = {state: d[(category, state)] for state in states}
        counts = CategoryOccupationSummary.from_counts_by_state(counts_by_state)
        yield category, counts


def _get_bungalow_counts_by_category_and_state(
    party_id: PartyID,
) -> BungalowCountByCategoryAndState:
    rows = db.session.execute(
        select(
            DbTicketCategory,
            DbBungalow._occupation_state,
            db.func.count(DbBungalow._occupation_state),
        )
        .join(
            DbBungalowCategory,
            DbBungalowCategory.ticket_category_id == DbTicketCategory.id,
        )
        .join(DbBungalow)
        .filter(DbTicketCategory.party_id == party_id)
        .group_by(DbTicketCategory, DbBungalow._occupation_state)
    ).all()

    return [
        (_to_ticket_category(db_ticket_category), state, count)
        for db_ticket_category, state, count in rows
    ]


def _to_ticket_category(category: DbTicketCategory) -> TicketCategory:
    return ticket_category_service._db_entity_to_category(category)


def get_statistics_total(
    summary_by_category: Iterable[
        tuple[TicketCategory, CategoryOccupationSummary]
    ],
) -> CategoryOccupationSummary:
    summaries = [summary for category, summary in summary_by_category]
    return _get_statistics_total(summaries)


def _get_statistics_total(
    summaries: Iterable[CategoryOccupationSummary],
) -> CategoryOccupationSummary:
    counts_by_field_name = {
        field_name: sum(map(attrgetter(field_name), summaries))
        for field_name in ('available', 'reserved', 'occupied')
    }

    return CategoryOccupationSummary.from_counts(
        counts_by_field_name['available'],
        counts_by_field_name['reserved'],
        counts_by_field_name['occupied'],
    )

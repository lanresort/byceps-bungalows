"""
:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from byceps.services.bungalow import bungalow_stats_service
from byceps.services.bungalow.models.bungalow import BungalowOccupationState
from byceps.services.bungalow.models.occupation import CategoryOccupationSummary


def test_get_statistics_by_category_with_realistic_values(
    site_app,
    party,
    ticket_category1,
    ticket_category2,
    ticket_category3,
):
    expected = [
        (ticket_category1, CategoryOccupationSummary.from_counts(5, 1, 2)),
        (ticket_category2, CategoryOccupationSummary.from_counts(19, 3, 4)),
        (ticket_category3, CategoryOccupationSummary.from_counts(1, 0, 2)),
    ]

    def get_counts(party_id):
        return [
            (ticket_category1, BungalowOccupationState.available.name, 5),
            (ticket_category1, BungalowOccupationState.reserved.name, 1),
            (ticket_category1, BungalowOccupationState.occupied.name, 2),
            (ticket_category2, BungalowOccupationState.available.name, 19),
            (ticket_category2, BungalowOccupationState.reserved.name, 3),
            (ticket_category2, BungalowOccupationState.occupied.name, 4),
            (ticket_category3, BungalowOccupationState.available.name, 1),
            (ticket_category3, BungalowOccupationState.reserved.name, 0),
            (ticket_category3, BungalowOccupationState.occupied.name, 2),
        ]

    actual = bungalow_stats_service.get_statistics_by_category(
        party.id, get_counts_func=get_counts
    )

    assert list(actual) == expected


def test_get_statistics_by_category_expecting_defaults(
    site_app,
    party,
    ticket_category1,
    ticket_category2,
    ticket_category3,
):
    expected = [
        (ticket_category1, CategoryOccupationSummary.from_counts(0, 0, 0)),
        (ticket_category2, CategoryOccupationSummary.from_counts(0, 0, 0)),
        (ticket_category3, CategoryOccupationSummary.from_counts(0, 0, 0)),
    ]

    def get_counts(party_id):
        return []

    actual = bungalow_stats_service.get_statistics_by_category(
        party.id, get_counts_func=get_counts
    )

    assert list(actual) == expected

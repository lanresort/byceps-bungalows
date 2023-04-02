"""
:Copyright: 2014-2023 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from byceps.services.bungalow import bungalow_stats_service
from byceps.services.bungalow.models.occupation import CategoryOccupationSummary


def test_get_statistics_total_with_realistic_values(
    site_app, ticket_category1, ticket_category2, ticket_category3
):
    summary_by_category = [
        (ticket_category1, CategoryOccupationSummary.from_counts(5, 1, 2)),
        (ticket_category2, CategoryOccupationSummary.from_counts(19, 3, 4)),
        (ticket_category3, CategoryOccupationSummary.from_counts(1, 0, 2)),
    ]

    actual = bungalow_stats_service.get_statistics_total(summary_by_category)

    assert actual.available == 25
    assert actual.reserved == 4
    assert actual.occupied == 8
    assert actual.total == 37


def test_get_statistics_total_expecting_defaults(site_app, ticket_category1):
    summary_by_category = [
        (ticket_category1, CategoryOccupationSummary.from_counts(0, 7, 0)),
    ]

    actual = bungalow_stats_service.get_statistics_total(summary_by_category)

    assert actual.available == 0
    assert actual.reserved == 7
    assert actual.occupied == 0
    assert actual.total == 7

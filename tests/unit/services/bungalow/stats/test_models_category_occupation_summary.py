"""
:Copyright: 2014-2025 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from byceps.services.bungalow.models.bungalow import BungalowOccupationState
from byceps.services.bungalow.models.occupation import CategoryOccupationSummary


def test_from_counts_by_state_with_counts_for_all_states_specified():
    counts_by_state = {
        BungalowOccupationState.available: 5,
        BungalowOccupationState.reserved: 2,
        BungalowOccupationState.occupied: 9,
    }

    actual = CategoryOccupationSummary.from_counts_by_state(counts_by_state)

    assert_equals_values(actual, 5, 2, 9, 16)


def test_from_counts_by_state_with_counts_for_some_states_not_specified():
    counts_by_state = {
        BungalowOccupationState.reserved: 7,
    }

    actual = CategoryOccupationSummary.from_counts_by_state(counts_by_state)

    assert_equals_values(actual, 0, 7, 0, 7)


# helpers


def assert_equals_values(actual, available, reserved, occupied, total):
    assert actual.available == available
    assert actual.reserved == reserved
    assert actual.occupied == occupied
    assert actual.total == total

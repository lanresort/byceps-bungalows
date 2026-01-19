"""
:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

import pytest

from byceps.services.party.models import Party
from byceps.services.ticketing.models.ticket import TicketCategory


@pytest.fixture(scope='session')
def party(brand, make_party):
    return make_party(brand)


@pytest.fixture(scope='package')
def ticket_category1(party: Party, make_ticket_category) -> TicketCategory:
    return make_ticket_category(party.id, 'classic')


@pytest.fixture(scope='package')
def ticket_category2(party: Party, make_ticket_category) -> TicketCategory:
    return make_ticket_category(party.id, 'premium')


@pytest.fixture(scope='package')
def ticket_category3(party: Party, make_ticket_category) -> TicketCategory:
    return make_ticket_category(party.id, 'vip')

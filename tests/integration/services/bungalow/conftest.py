"""
:Copyright: 2014-2025 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from __future__ import annotations

from random import randint

import pytest

from byceps.database import db
from byceps.services.bungalow import bungalow_category_service
from byceps.services.bungalow.dbmodels.bungalow import DbBungalow
from byceps.services.bungalow.models.category import (
    BungalowCategory,
    BungalowCategoryID,
)
from byceps.services.party.models import Party, PartyID
from byceps.services.shop.order.models.order import Orderer
from byceps.services.shop.product.models import Product
from byceps.services.shop.shop.models import Shop
from byceps.services.shop.storefront.models import Storefront
from byceps.services.ticketing import ticket_bundle_service
from byceps.services.ticketing.models.ticket import TicketBundle, TicketCategory

from tests.helpers import generate_token


@pytest.fixture(scope='session')
def party(bungalows_party: Party) -> Party:
    return bungalows_party


@pytest.fixture(scope='session')
def shop(bungalows_shop: Shop) -> Shop:
    return bungalows_shop


@pytest.fixture()
def storefront(
    shop: Shop, make_order_number_sequence, make_storefront
) -> Storefront:
    order_number_sequence = make_order_number_sequence(shop.id)

    return make_storefront(shop.id, order_number_sequence.id)


@pytest.fixture(scope='module')
def product(make_product, shop: Shop) -> Product:
    return make_product(shop.id)


@pytest.fixture(scope='session')
def ticket_category(make_ticket_category, party: Party) -> TicketCategory:
    title = f'Premium {generate_token()}'
    return make_ticket_category(party.id, title)


@pytest.fixture(scope='module')
def make_ticket_bundle(
    party: Party, ticket_category: TicketCategory, orderer: Orderer
):
    def _wrapper(*, ticket_quantity: int = 4) -> TicketBundle:
        return ticket_bundle_service.create_bundle(
            ticket_category, ticket_quantity, orderer.user
        )

    return _wrapper


@pytest.fixture(scope='module')
def bungalow_category(
    party: Party, ticket_category: TicketCategory, product: Product
) -> BungalowCategory:
    title = f'Premium {generate_token()}'
    capacity = 6

    return bungalow_category_service.create_category(
        party.id, title, capacity, ticket_category.id, product.id
    )


@pytest.fixture(scope='module')
def make_bungalow(party: Party, bungalow_category: BungalowCategory):
    def _wrapper(
        *,
        party_id: PartyID | None = None,
        number: int | None = None,
        bungalow_category_id: BungalowCategoryID | None = None,
    ) -> DbBungalow:
        if party_id is None:
            party_id = party.id

        if number is None:
            number = randint(100, 9999)  # noqa: S311

        if bungalow_category_id is None:
            bungalow_category_id = bungalow_category.id

        db_bungalow = DbBungalow(party_id, number, bungalow_category_id)

        db.session.add(db_bungalow)
        db.session.commit()

        return db_bungalow

    return _wrapper


@pytest.fixture(scope='module')
def orderer(make_orderer, admin_app, make_user) -> Orderer:
    user = make_user()
    return make_orderer(user)

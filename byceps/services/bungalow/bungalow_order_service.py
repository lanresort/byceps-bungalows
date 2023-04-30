"""
byceps.services.bungalow.bungalow_order_service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2023 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from __future__ import annotations

from sqlalchemy import select

from byceps.database import db
from byceps.events.shop import ShopOrderPlaced
from byceps.services.shop.article import article_service
from byceps.services.shop.article.dbmodels.article import DbArticle
from byceps.services.shop.cart.models import Cart
from byceps.services.shop.order import order_checkout_service
from byceps.services.shop.order.models.number import OrderNumber
from byceps.services.shop.order.models.order import Order, Orderer
from byceps.services.shop.storefront import storefront_service
from byceps.services.shop.storefront.models import StorefrontID
from byceps.util.result import Err, Ok, Result

from .dbmodels.bungalow import DbBungalow
from .dbmodels.occupancy import DbBungalowOccupancy


def place_bungalow_order(
    storefront_id: StorefrontID, db_article: DbArticle, orderer: Orderer
) -> Result[tuple[Order, ShopOrderPlaced], None]:
    """Place an order for that bungalow."""
    storefront = storefront_service.get_storefront(storefront_id)
    cart = _build_cart(db_article)

    placement_result = order_checkout_service.place_order(
        storefront.id, orderer, cart
    )
    if placement_result.is_err():
        return Err(placement_result.unwrap_err())

    order, event = placement_result.unwrap()

    return Ok((order, event))


def _build_cart(db_article: DbArticle) -> Cart:
    article_compilation = (
        article_service.get_article_compilation_for_single_article(
            db_article.id
        )
    )

    cart = Cart(db_article.price.currency)

    for item in article_compilation:
        cart.add_item(item.article, item.fixed_quantity)

    return cart


def find_bungalow_by_order(order_number: OrderNumber) -> DbBungalow | None:
    """Return the bungalow that was occupied with this order, if any."""
    return db.session.scalars(
        select(DbBungalow)
        .join(DbBungalowOccupancy)
        .filter(DbBungalowOccupancy.order_number == order_number)
    ).one_or_none()

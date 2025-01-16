"""
byceps.services.bungalow.bungalow_order_service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2025 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from __future__ import annotations

from sqlalchemy import select

from byceps.database import db
from byceps.events.shop import ShopOrderPlacedEvent
from byceps.services.shop.cart.models import Cart
from byceps.services.shop.order import order_checkout_service
from byceps.services.shop.order.models.number import OrderNumber
from byceps.services.shop.order.models.order import Order, Orderer
from byceps.services.shop.product import product_service
from byceps.services.shop.product.models import Product
from byceps.services.shop.storefront.models import Storefront
from byceps.util.result import Err, Ok, Result

from .dbmodels.bungalow import DbBungalow
from .dbmodels.occupancy import DbBungalowOccupancy


def place_bungalow_order(
    storefront: Storefront,
    product: Product,
    orderer: Orderer,
) -> Result[tuple[Order, ShopOrderPlacedEvent], None]:
    """Place an order for that bungalow."""
    cart = _build_cart(product)

    placement_result = order_checkout_service.place_order(
        storefront, orderer, cart
    )
    if placement_result.is_err():
        return Err(placement_result.unwrap_err())

    order, event = placement_result.unwrap()

    return Ok((order, event))


def _build_cart(product: Product) -> Cart:
    product_compilation = (
        product_service.get_product_compilation_for_single_product(product.id)
    )

    cart = Cart(product.price.currency)

    for item in product_compilation:
        cart.add_item(item.product, item.fixed_quantity)

    return cart


def find_bungalow_by_order(order_number: OrderNumber) -> DbBungalow | None:
    """Return the bungalow that was occupied with this order, if any."""
    return db.session.scalars(
        select(DbBungalow)
        .join(DbBungalowOccupancy)
        .filter(DbBungalowOccupancy.order_number == order_number)
    ).one_or_none()

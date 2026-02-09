"""
byceps.services.bungalow.bungalow_order_service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from __future__ import annotations

from byceps.services.party.models import PartyID
from byceps.services.shop.cart.models import Cart
from byceps.services.shop.order import order_checkout_service
from byceps.services.shop.order.events import ShopOrderPlacedEvent
from byceps.services.shop.order.models.order import Order, Orderer
from byceps.services.shop.product import product_domain_service, product_service
from byceps.services.shop.product.models import Product, ProductType
from byceps.services.shop.storefront.models import Storefront
from byceps.services.user.models import UserID
from byceps.util.result import Err, Ok, Result

from . import bungalow_order_repository
from .errors import (
    BungalowOrderingError,
    ProductBelongsToDifferentShopError,
    ProductTypeUnexpectedError,
    ProductUnavailableError,
    StorefrontClosedError,
)


def check_order_without_preselection_preconditions(
    storefront: Storefront, product: Product
) -> Result[None, BungalowOrderingError]:
    """Check preconditions for ordering a bungalow category."""
    if product.type_ != ProductType.bungalow_without_preselection:
        return Err(ProductTypeUnexpectedError())

    if product.shop_id != storefront.shop_id:
        return Err(ProductBelongsToDifferentShopError())

    if storefront.closed:
        return Err(StorefrontClosedError())

    if (
        product.quantity < 1
        or not product_domain_service.is_product_available_now(product)
    ):
        return Err(ProductUnavailableError())

    return Ok(None)


def has_user_ordered_any_bungalow_category(
    user_id: UserID, party_id: PartyID
) -> bool:
    """Return `True` if the user has already ordered any bungalow
    category for the party.
    """
    return bungalow_order_repository.has_user_ordered_any_bungalow_category(
        user_id, party_id
    )


def place_bungalow_order(
    storefront: Storefront,
    product: Product,
    orderer: Orderer,
) -> Result[tuple[Order, ShopOrderPlacedEvent], None]:
    """Place an order for that bungalow."""
    cart = _build_cart(product)

    match order_checkout_service.place_order(storefront, orderer, cart):
        case Ok((order, event)):
            pass
        case Err(e):
            return Err(e)

    return Ok((order, event))


def _build_cart(product: Product) -> Cart:
    product_compilation = (
        product_service.get_product_compilation_for_single_product(product.id)
    )

    cart = Cart(product.price.currency)

    for item in product_compilation:
        cart.add_item(item.product, item.fixed_quantity)

    return cart

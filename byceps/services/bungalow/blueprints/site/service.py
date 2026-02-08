"""
byceps.services.bungalow.blueprints.site.service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from byceps.services.bungalow import bungalow_category_service
from byceps.services.party.models import PartyID
from byceps.services.shop.product import product_domain_service, product_service

from .models import BungalowCategorySummary


def get_bungalow_category_summaries(
    party_id: PartyID,
) -> list[BungalowCategorySummary]:
    """Assemble bungalow category summaries."""
    categories = bungalow_category_service.get_categories_for_party(party_id)

    product_ids = {category.product.id for category in categories}

    products = product_service.get_products(product_ids)
    products_by_id = {product.id: product for product in products}

    product_compilations_by_product_id = (
        product_service.get_product_compilations_for_single_products(
            product_ids
        )
    )

    total_amounts_by_product_id = {
        product_id: product_domain_service.calculate_product_compilation_total_amount(
            product_compilations_by_product_id[product_id]
        ).unwrap()
        for product_id in product_ids
    }

    summaries = []

    for category in categories:
        product = products_by_id[category.product.id]
        summaries.append(
            BungalowCategorySummary(
                id=category.id,
                title=category.title,
                capacity=category.capacity,
                total_price=total_amounts_by_product_id[product.id],
                quantity_available=product.quantity,
                quantity_occupied=product.total_quantity - product.quantity,
                quantity_total=product.total_quantity,
                available=product.quantity > 0
                and product_domain_service.is_product_available_now(product),
            )
        )

    return summaries

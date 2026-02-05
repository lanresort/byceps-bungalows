"""
byceps.services.shop.order.actions.bungalow_without_preselection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from uuid import UUID

from byceps.services.bungalow import (
    bungalow_occupancy_service,
    signals as bungalow_signals,
)
from byceps.services.seating.errors import SeatingError
from byceps.services.shop.order import (
    order_command_service,
    order_event_service,
)
from byceps.services.shop.order.errors import OrderActionFailedError
from byceps.services.shop.order.log import (
    order_log_domain_service,
    order_log_service,
)
from byceps.services.shop.order.models.action import (
    ActionParameters,
    ActionProcedure,
)
from byceps.services.shop.order.models.order import (
    LineItem,
    Order,
    OrderID,
    PaidOrder,
)
from byceps.services.shop.product import product_service
from byceps.services.ticketing import (
    ticket_bundle_service,
    ticket_category_service,
)
from byceps.services.ticketing.models.ticket import (
    TicketBundle,
    TicketBundleID,
    TicketCategory,
    TicketCategoryID,
)
from byceps.services.user.models import User
from byceps.util.result import Err, Ok, Result


def get_action_procedure() -> ActionProcedure:
    return ActionProcedure(
        on_payment=on_payment,
        on_cancellation_after_payment=on_cancellation_after_payment,
    )


def on_payment(
    order: PaidOrder,
    line_item: LineItem,
    initiator: User,
    parameters: ActionParameters,
) -> Result[None, OrderActionFailedError]:
    """Create ticket bundle."""
    product = product_service.get_product(line_item.product_id)

    ticket_category_id = TicketCategoryID(
        UUID(product.type_params['ticket_category_id'])
    )
    ticket_quantity = int(product.type_params['ticket_quantity'])

    ticket_category = ticket_category_service.get_category(ticket_category_id)

    _create_ticket_bundle(
        order, line_item, ticket_category, ticket_quantity, initiator
    )

    return Ok(None)


def on_cancellation_after_payment(
    order: Order,
    line_item: LineItem,
    initiator: User,
    parameters: ActionParameters,
) -> Result[None, OrderActionFailedError]:
    """Revoke ticket bundle and release the bungalow that have been created for
    that order.
    """
    match _revoke_ticket_bundle(order, line_item, initiator):
        case Err(seating_error):
            return Err(OrderActionFailedError(seating_error))

    match _release_bungalow(line_item, initiator):
        case Err(e):
            return Err(e)

    return Ok(None)


def _create_ticket_bundle(
    order: PaidOrder,
    line_item: LineItem,
    ticket_category: TicketCategory,
    ticket_quantity: int,
    initiator: User,
) -> None:
    """Create ticket bundle."""
    owner = order.placed_by
    order_number = order.order_number

    bundle = ticket_bundle_service.create_bundle(
        ticket_category,
        ticket_quantity,
        owner,
        order_number=order_number,
        user=None,  # Do not assign owner as user.
    )
    _create_creation_order_log_entry(order.id, bundle)

    data = line_item.processing_result
    data['ticket_bundle_id'] = str(bundle.id)
    order_command_service.update_line_item_processing_result(line_item.id, data)

    tickets_sold_event = order_event_service.create_tickets_sold_event(
        order, initiator, ticket_category, owner, ticket_quantity
    )
    order_event_service.send_tickets_sold_event(tickets_sold_event)


def _create_creation_order_log_entry(
    order_id: OrderID, ticket_bundle: TicketBundle
) -> None:
    log_entry = order_log_domain_service.build_ticket_bundle_created_entry(
        order_id,
        ticket_bundle.id,
        ticket_bundle.ticket_category.id,
        ticket_bundle.ticket_quantity,
        ticket_bundle.owned_by.id,
    )

    order_log_service.persist_entry(log_entry)


def _revoke_ticket_bundle(
    order: Order, line_item: LineItem, initiator: User
) -> Result[None, SeatingError]:
    """Revoke ticket bundle related to the line item."""
    bundle_id_str = line_item.processing_result['ticket_bundle_id']
    bundle_id = TicketBundleID(UUID(bundle_id_str))

    match ticket_bundle_service.revoke_bundle(bundle_id, initiator):
        case Err(e):
            return Err(e)

    _create_revocation_order_log_entry(order.id, bundle_id, initiator)

    return Ok(None)


def _create_revocation_order_log_entry(
    order_id: OrderID, ticket_bundle_id: TicketBundleID, initiator: User
) -> None:
    log_entry = order_log_domain_service.build_ticket_bundle_revoked_entry(
        order_id, ticket_bundle_id, initiator
    )

    order_log_service.persist_entry(log_entry)


def _release_bungalow(
    line_item: LineItem, initiator: User
) -> Result[None, OrderActionFailedError]:
    ticket_bundle_id_str = line_item.processing_result['ticket_bundle_id']
    ticket_bundle_id = TicketBundleID(UUID(ticket_bundle_id_str))

    occupancy = bungalow_occupancy_service.find_occupancy_for_ticket_bundle(
        ticket_bundle_id
    )
    if not occupancy:
        return Err(
            OrderActionFailedError(
                f'Could not find bungalow occupancy for ticket bundle "{ticket_bundle_id}".'
            )
        )

    match bungalow_occupancy_service.release_bungalow(occupancy.id, initiator):
        case Ok(bungalow_released_event):
            bungalow_signals.bungalow_released.send(
                None, event=bungalow_released_event
            )
        case Err(e):
            return Err(
                OrderActionFailedError(
                    f'Fehler bei der Freigabe von Bungalow-Belegung {occupancy.id}: {e}'
                )
            )

    return Ok(None)

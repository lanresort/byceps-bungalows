"""
byceps.services.shop.order.actions.bungalow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from typing import Any
from uuid import UUID

from byceps.services.bungalow import (
    bungalow_order_service,
    bungalow_occupancy_service,
    bungalow_service,
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
)
from byceps.services.user.models import User
from byceps.util.result import Err, Ok, Result


def get_action_procedure() -> ActionProcedure:
    return ActionProcedure(
        on_payment=on_payment,
        on_cancellation_before_payment=on_cancellation_before_payment,
        on_cancellation_after_payment=on_cancellation_after_payment,
    )


def on_payment(
    order: PaidOrder,
    line_item: LineItem,
    initiator: User,
    parameters: ActionParameters,
) -> Result[None, OrderActionFailedError]:
    """Create ticket bundle and occupy reserved bungalow."""
    product = product_service.get_product(line_item.product_id)

    if parameters:
        ticket_category_id = parameters['ticket_category_id']
        ticket_quantity = int(parameters['ticket_quantity'])
    else:
        ticket_category_id = product.type_params['ticket_category_id']
        ticket_quantity = int(product.type_params['ticket_quantity'])

    ticket_category = ticket_category_service.get_category(ticket_category_id)

    ticket_bundle_id = _create_ticket_bundle(
        order, line_item, ticket_category, ticket_quantity, initiator
    )

    _occupy_bungalow(line_item, ticket_bundle_id)

    return Ok(None)


def on_cancellation_before_payment(
    order: Order,
    line_item: LineItem,
    initiator: User,
    parameters: ActionParameters,
) -> Result[None, OrderActionFailedError]:
    """Release the bungalow that had been created for that order."""
    match _release_bungalow(line_item, initiator):
        case Err(e):
            return Err(e)

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
) -> TicketBundleID:
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

    data: dict[str, Any] = {'ticket_bundle_id': str(bundle.id)}
    order_command_service.update_line_item_processing_result(line_item.id, data)

    tickets_sold_event = order_event_service.create_tickets_sold_event(
        order, initiator, ticket_category, owner, ticket_quantity
    )
    order_event_service.send_tickets_sold_event(tickets_sold_event)

    return bundle.id


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


def _occupy_bungalow(
    line_item: LineItem, ticket_bundle_id: TicketBundleID
) -> Result[None, OrderActionFailedError]:
    """Occupy reserved bungalow."""
    order_number = line_item.order_number

    db_bungalow = bungalow_order_service.find_bungalow_by_order(order_number)
    if not db_bungalow:
        return Err(
            OrderActionFailedError(
                f'Could not find bungalow for order number {order_number}.'
            )
        )

    if not db_bungalow.reserved:
        return Err(
            OrderActionFailedError(
                f'Bungalow {db_bungalow.number} muss reserviert sein um belegt werden zu können.'
            )
        )

    try:
        occupation_result = bungalow_occupancy_service.occupy_bungalow(
            db_bungalow.reservation.id,
            db_bungalow.occupancy.id,
            ticket_bundle_id,
        )
        if occupation_result.is_err():
            return Err(
                OrderActionFailedError(
                    f'Bungalow {db_bungalow.number} konnte nicht belegt werden.'
                )
            )

        occupancy, bungalow_occupied_event = occupation_result.unwrap()
    except ValueError as e:
        return Err(
            OrderActionFailedError(
                f'Fehler bei der Belegung von Bungalow {db_bungalow.number}: {e}'
            )
        )

    bungalow_signals.bungalow_occupied.send(None, event=bungalow_occupied_event)

    bungalow_service.assign_first_ticket_to_main_occupant(occupancy)

    return Ok(None)


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
    order_number = line_item.order_number

    db_bungalow = bungalow_order_service.find_bungalow_by_order(order_number)
    if not db_bungalow:
        return Err(
            OrderActionFailedError(
                f'Could not find bungalow for order number {order_number}.'
            )
        )

    bungalow_number = db_bungalow.number

    db_occupancy = db_bungalow.occupancy
    if not db_occupancy:
        return Err(
            OrderActionFailedError(
                f'Could not find occupancy for bungalow {bungalow_number} for order number {order_number}.'
            )
        )

    match bungalow_occupancy_service.release_bungalow(
        db_occupancy.id, initiator
    ):
        case Ok(bungalow_released_event):
            bungalow_signals.bungalow_released.send(
                None, event=bungalow_released_event
            )
        case Err(e):
            return Err(
                OrderActionFailedError(
                    f'Fehler bei der Freigabe von Bungalow {bungalow_number}: {e}'
                )
            )

    return Ok(None)

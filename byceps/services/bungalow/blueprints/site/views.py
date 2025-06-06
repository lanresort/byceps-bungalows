"""
byceps.services.bungalow.blueprints.site.views
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2025 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from datetime import datetime
from functools import wraps

from flask import abort, g, render_template, request
from flask_babel import gettext

from byceps.database import db
from byceps.services.bungalow import (
    bungalow_category_service,
    bungalow_occupancy_avatar_service,
    bungalow_occupancy_service,
    bungalow_service,
    bungalow_stats_service,
    signals as bungalow_signals,
)
from byceps.services.bungalow.dbmodels.bungalow import DbBungalow
from byceps.services.bungalow.events import (
    BungalowOccupancyAvatarUpdatedEvent,
    BungalowOccupancyDescriptionUpdatedEvent,
    BungalowOccupantAddedEvent,
    BungalowOccupantRemovedEvent,
)
from byceps.services.bungalow.models.bungalow import BungalowOccupationState
from byceps.services.bungalow.models.occupation import (
    BungalowOccupancy,
    OccupancyID,
    OccupantSlot,
)
from byceps.services.core.events import EventUser
from byceps.services.country import country_service
from byceps.services.orga_team import orga_team_service
from byceps.services.party import party_service
from byceps.services.shop.order import signals as shop_order_signals
from byceps.services.shop.order.blueprints.site.forms import OrderForm
from byceps.services.shop.order.email import order_email_service
from byceps.services.shop.product import product_domain_service, product_service
from byceps.services.shop.storefront import storefront_service
from byceps.services.site.blueprints.site.navigation import (
    subnavigation_for_view,
)
from byceps.services.ticketing import (
    ticket_service,
    ticket_user_management_service,
)
from byceps.services.ticketing.models.ticket import TicketBundleID
from byceps.services.user import user_service
from byceps.util.framework.blueprint import create_blueprint
from byceps.util.framework.flash import flash_error, flash_notice, flash_success
from byceps.util.framework.templating import templated
from byceps.util.image.image_type import get_image_type_names
from byceps.util.views import login_required, redirect_to, respond_no_content

from .forms import AvatarUpdateForm, DescriptionUpdateForm, OccupantAddForm


blueprint = create_blueprint('bungalow', __name__)


def bungalow_support_required(func):
    """Ensure that the site is configured to support bungalows."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not g.has_bungalows:
            abort(404)

        return func(*args, **kwargs)

    return wrapper


def enabled_bungalow_customization_required(func):
    """Require bungalow customization to be enabled."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not _get_bungalow_customization_enabled():
            flash_error(
                'Die Präsentation des Bungalows kann nicht mehr verändert werden.'
            )
            abort(403)

        return func(*args, **kwargs)

    return wrapper


def enabled_ticket_management_required(func):
    """Require ticket management to be enabled."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not _is_ticket_management_enabled():
            flash_error(
                'Die Liste der Bewohner kann nicht mehr verändert werden.'
            )
            abort(403)

        return func(*args, **kwargs)

    return wrapper


@blueprint.get('/')
@bungalow_support_required
@templated
@subnavigation_for_view('bungalows')
def index():
    """List all bungalows."""
    bungalows = bungalow_service.get_bungalows_extended_for_party(g.party.id)

    bungalows_by_number = {b.number: b for b in bungalows}

    bungalow_categories = bungalow_category_service.get_categories_for_party(
        g.party.id
    )
    bungalow_categories_by_id = {c.id: c for c in bungalow_categories}

    product_ids = {c.product.id for c in bungalow_categories}
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

    occupancy_ids = {
        bungalow.occupancy.id for bungalow in bungalows if bungalow.occupancy
    }
    occupant_slots_by_occupancy_id = (
        bungalow_occupancy_service.get_occupant_slots_for_occupancies(
            occupancy_ids
        )
    )

    occupancy_user_ids = {
        bungalow.occupancy.occupied_by_id
        for bungalow in bungalows
        if bungalow.occupancy
    }
    user_ids = occupancy_user_ids
    users_by_id = user_service.get_users_indexed_by_id(
        user_ids, include_avatars=True
    )

    my_bungalow = bungalow_service.find_bungalow_inhabited_by_user(
        g.user.id, g.party.id
    )

    ticket_categories_and_occupation_summaries = list(
        bungalow_stats_service.get_statistics_by_category(g.party.id)
    )

    occupation_summaries_by_ticket_category_id = {
        tc.id: os for tc, os in ticket_categories_and_occupation_summaries
    }

    statistics_total = bungalow_stats_service.get_statistics_total(
        ticket_categories_and_occupation_summaries
    )

    return {
        'bungalows': bungalows,
        'bungalows_by_number': bungalows_by_number,
        'bungalow_categories_by_id': bungalow_categories_by_id,
        'total_amounts_by_product_id': total_amounts_by_product_id,
        'occupant_slots_by_occupancy_id': occupant_slots_by_occupancy_id,
        'users_by_id': users_by_id,
        'is_product_available_now': product_domain_service.is_product_available_now,
        'my_bungalow_id': my_bungalow.id if my_bungalow is not None else None,
        'occupation_summaries_by_ticket_category_id': occupation_summaries_by_ticket_category_id,
        'statistics_total': statistics_total,
    }


@blueprint.get('/<int:number>')
@bungalow_support_required
@templated
@subnavigation_for_view('bungalows')
def view(number: int):
    """Show the bungalow."""
    bungalow = _get_bungalow_for_number_or_404(number)

    ticket_management_enabled = _is_ticket_management_enabled()
    bungalow_customization_enabled = _get_bungalow_customization_enabled()

    if bungalow.reserved:
        reserved_by = user_service.find_user(
            bungalow.occupancy.occupied_by_id, include_avatar=True
        )
    else:
        reserved_by = None

    if bungalow.occupied:
        manager_id = bungalow.occupancy.manager_id
        manager = user_service.get_user(manager_id)

        current_user_is_main_occupant = (
            bungalow.occupancy.occupied_by_id == g.user.id
        )
        current_user_is_manager = manager.id == g.user.id

        occupant_slots = (
            bungalow_occupancy_service.get_occupant_slots_for_occupancy(
                bungalow.occupancy.id
            )
        )
    else:
        current_user_is_main_occupant = False
        current_user_is_manager = False
        manager = None
        occupant_slots = None

    return {
        'bungalow': bungalow,
        'reserved_by': reserved_by,
        'current_user_is_main_occupant': current_user_is_main_occupant,
        'current_user_is_manager': current_user_is_manager,
        'manager': manager,
        'ticket_management_enabled': ticket_management_enabled,
        'bungalow_customization_enabled': bungalow_customization_enabled,
        'occupant_slots': occupant_slots,
    }


@blueprint.get('/mine')
@bungalow_support_required
@login_required
def view_mine():
    """Redirect to the current user's bungalow."""
    me_id = g.user.id
    party_id = g.party.id

    bungalow = bungalow_service.find_bungalow_inhabited_by_user(me_id, party_id)

    if bungalow:
        return redirect_to('.view', number=bungalow.number)
    else:
        return render_template('site/bungalow/no_bungalow_inhabited.html')


# -------------------------------------------------------------------- #
# ordering


@blueprint.get('/order/<uuid:bungalow_id>')
@login_required
@bungalow_support_required
@templated
@subnavigation_for_view('bungalows')
def order_form(bungalow_id, *, erroneous_form=None):
    """Show a form to order a bungalow."""
    bungalow = _get_bungalow_for_id_or_404(bungalow_id)
    product = bungalow.category.product

    storefront = _get_storefront_or_404()
    if product.shop_id != storefront.shop_id:
        abort(404)

    if storefront.closed:
        flash_notice(gettext('The shop is closed.'))
        return {'bungalow': None}

    if bungalow.reserved_or_occupied:
        flash_error(f'Bungalow {bungalow.number} ist bereits reserviert.')
        return {'bungalow': None}

    if (
        not product
        or product.quantity < 1
        or not product_domain_service.is_product_available_now(product)
    ):
        flash_error(
            f'Bungalow {bungalow.number} kann derzeit nicht reserviert werden.'
        )
        return {'bungalow': None}

    compilation = product_service.get_product_compilation_for_single_product(
        product.id
    )

    collection = product_service.get_product_collection_for_product_compilation(
        '', compilation
    )
    collections = [collection]

    user = user_service.find_user_with_details(g.user.id)

    if bungalow_occupancy_service.has_user_occupied_any_bungalow(
        g.party.id, user.id
    ):
        flash_error(
            'Du hast bereits einen Bungalow für diese Party reserviert.'
        )
        return {'bungalow': None}

    form = erroneous_form if erroneous_form else OrderForm(obj=user.detail)

    country_names = country_service.get_country_names()

    total_amount_result = (
        product_domain_service.calculate_product_compilation_total_amount(
            compilation
        )
    )

    if total_amount_result.is_err():
        flash_error('Für einige Artikel ist keine Stückzahl vorgegeben.')
        return {'bungalow': None}

    total_amount = total_amount_result.unwrap()

    return {
        'bungalow': bungalow,
        'form': form,
        'country_names': country_names,
        'collections': collections,
        'images_by_product_id': {},
        'total_amount': total_amount,
    }


@blueprint.post('/order/<uuid:bungalow_id>')
@bungalow_support_required
@login_required
def order(bungalow_id):
    """Order a bungalow."""
    bungalow = _get_bungalow_for_id_or_404(bungalow_id)
    product = bungalow.category.product

    storefront = _get_storefront_or_404()
    if product.shop_id != storefront.shop_id:
        abort(404)

    if storefront.closed:
        flash_notice(gettext('The shop is closed.'))
        return order_form(bungalow_id)

    if bungalow.reserved_or_occupied:
        flash_error(f'Bungalow {bungalow.number} ist bereits reserviert.')
        return order_form(bungalow_id)

    if (
        not product
        or product.quantity < 1
        or not product_domain_service.is_product_available_now(product)
    ):
        flash_error(
            f'Bungalow {bungalow.number} kann derzeit nicht reserviert werden.'
        )
        return order_form(bungalow_id)

    user = g.user

    if bungalow_occupancy_service.has_user_occupied_any_bungalow(
        g.party.id, user.id
    ):
        flash_error(
            'Du hast bereits einen Bungalow für diese Party reserviert.'
        )
        return order_form(bungalow_id)

    form = OrderForm(request.form)
    if not form.validate():
        return order_form(bungalow_id, erroneous_form=form)

    orderer = form.get_orderer(user)

    reservation_result = bungalow_occupancy_service.reserve_bungalow(
        bungalow.id, user
    )
    if reservation_result.is_err():
        flash_error(f'Bungalow {bungalow.number} ist bereits reserviert.')
        return order_form(bungalow_id)

    (
        reservation,
        occupancy,
        bungalow_reserved_event,
    ) = reservation_result.unwrap()
    bungalow_signals.bungalow_reserved.send(None, event=bungalow_reserved_event)
    flash_success(
        f'Bungalow {bungalow.number} wurde als von dir reserviert markiert.'
    )

    place_bungalow_order_result = (
        bungalow_occupancy_service.place_bungalow_order(
            storefront, reservation.id, occupancy.id, orderer
        )
    )
    if place_bungalow_order_result.is_err():
        flash_error(gettext('Placing the order has failed.'))
        return order_form(bungalow_id)

    order, order_placed_event = place_bungalow_order_result.unwrap()
    shop_order_signals.order_placed.send(None, event=order_placed_event)

    flash_success(
        gettext(
            'Your order <strong>%(order_number)s</strong> has been placed. '
            'Thank you!',
            order_number=order.order_number,
        ),
        text_is_safe=True,
    )

    order_email_service.send_email_for_incoming_order_to_orderer(order)

    return redirect_to('shop_orders.view', order_id=order.id)


def _get_storefront_or_404():
    storefront_id = g.site.storefront_id
    if storefront_id is None:
        abort(404)

    return storefront_service.get_storefront(storefront_id)


# -------------------------------------------------------------------- #
# occupants


@blueprint.get('/occupants', defaults={'page': 1})
@blueprint.get('/occupants/pages/<int:page>')
@bungalow_support_required
@templated
@subnavigation_for_view('occupants')
def occupant_index_all(page):
    """List occupants of all bungalows."""
    per_page = request.args.get('per_page', type=int, default=20)
    search_term = request.args.get('search_term', default='').strip()

    tickets = bungalow_service.get_all_occupant_tickets_paginated(
        g.party.id, page, per_page, search_term=search_term
    )

    ticket_user_ids = {
        ticket.used_by_id for ticket in tickets.items if ticket.used_by_id
    }
    if g.party:
        orga_ids = orga_team_service.select_orgas_for_party(
            ticket_user_ids, g.party.id
        )
    else:
        orga_ids = set()

    ticket_bundle_ids = {t.bundle_id for t in tickets.items}
    bungalows_by_ticket_bundle_id = (
        bungalow_occupancy_service.get_bungalows_for_ticket_bundles(
            ticket_bundle_ids
        )
    )

    tickets_and_bungalows = tickets
    tickets_and_bungalows.items = [
        (ticket, bungalows_by_ticket_bundle_id[ticket.bundle_id])
        for ticket in tickets.items
    ]

    return {
        'tickets_and_bungalows': tickets_and_bungalows,
        'orga_ids': orga_ids,
        'per_page': per_page,
        'search_term': search_term,
    }


@blueprint.get('/<int:number>/occupants')
@bungalow_support_required
@enabled_ticket_management_required
@login_required
@templated
@subnavigation_for_view('bungalows')
def occupant_index(number: int):
    """Show occupants management view."""
    bungalow = _get_bungalow_for_number_or_404(number)

    user = g.user
    if (
        not user.authenticated
        or bungalow.occupation_state != BungalowOccupationState.occupied
        or (
            bungalow.occupancy.manager_id != user.id
            and not bungalow_service.is_user_allowed_to_manage_any_occupant_slots(
                user, bungalow.occupancy
            )
        )
    ):
        abort(403)

    occupant_slots = (
        bungalow_occupancy_service.get_occupant_slots_for_occupancy(
            bungalow.occupancy.id
        )
    )

    ticket_ids = {slot.ticket_id for slot in occupant_slots}
    tickets = ticket_service.get_tickets(ticket_ids)
    tickets_by_id = {t.id: t for t in tickets}

    if g.party:
        occupant_ids = {
            slot.occupant.id for slot in occupant_slots if slot.occupant
        }
        orga_ids = orga_team_service.select_orgas_for_party(
            occupant_ids, g.party.id
        )
    else:
        orga_ids = set()

    occupant_slots_and_tickets = [
        (slot, tickets_by_id[slot.ticket_id]) for slot in occupant_slots
    ]

    return {
        'bungalow': bungalow,
        'occupant_slots_and_tickets': occupant_slots_and_tickets,
        'orga_ids': orga_ids,
    }


@blueprint.get('/tickets/<ticket_id>/user/add')
@bungalow_support_required
@enabled_ticket_management_required
@login_required
@templated
@subnavigation_for_view('bungalows')
def occupant_add_form(ticket_id, erroneous_form=None):
    """Show a form to add a user as an occupant to the bungalow."""
    ticket = _get_ticket_or_404(ticket_id)
    manager = g.user

    if not ticket.is_user_managed_by(manager.id):
        abort(403)

    bungalow = _get_bungalow_for_ticket_bundle(ticket.bundle_id)

    occupant_id = ticket.used_by_id
    if occupant_id:
        flash_error('Diesem Platz ist bereits ein Bewohner zugeordnet.')
        return redirect_to('.occupant_index', number=bungalow.number)

    occupant_slot = OccupantSlot(ticket_id=ticket.id, occupant=None)

    form = erroneous_form if erroneous_form else OccupantAddForm()

    return {
        'occupant_slot': occupant_slot,
        'form': form,
        'bungalow': bungalow,
    }


@blueprint.post('/tickets/<ticket_id>/user/add')
@bungalow_support_required
@enabled_ticket_management_required
@login_required
def occupant_add(ticket_id):
    """Add a user as occupant to the bungalow."""
    ticket = _get_ticket_or_404(ticket_id)
    manager = g.user

    if not ticket.is_user_managed_by(manager.id):
        abort(403)

    bungalow = _get_bungalow_for_ticket_bundle(ticket.bundle_id)

    if ticket.used_by_id:
        flash_error('Diesem Platz ist bereits ein Bewohner zugeordnet.')
        return redirect_to('.occupant_index', number=bungalow.number)

    form = OccupantAddForm(request.form)
    if not form.validate():
        return occupant_add_form(ticket_id, form)

    occupant = form.occupant.data

    ticket_user_management_service.appoint_user(
        ticket.id, occupant.id, manager.id
    )

    flash_success(
        f'"{occupant.screen_name}" wurde als Mitbewohner '
        f'in Bungalow {bungalow.number} aufgenommen.'
    )

    event = BungalowOccupantAddedEvent(
        occurred_at=datetime.utcnow(),
        initiator=EventUser.from_user(manager),
        bungalow_id=bungalow.id,
        bungalow_number=bungalow.number,
        occupant=EventUser.from_user(occupant),
    )
    bungalow_signals.occupant_added.send(None, event=event)

    return redirect_to('.occupant_index', number=bungalow.number)


@blueprint.get('/tickets/<ticket_id>/user/remove')
@bungalow_support_required
@enabled_ticket_management_required
@login_required
@templated
@subnavigation_for_view('bungalows')
def occupant_remove_form(ticket_id):
    """Show a form to remove an occupant from the bungalow."""
    ticket = _get_ticket_or_404(ticket_id)
    manager = g.user

    if not ticket.is_user_managed_by(manager.id):
        abort(403)

    bungalow = _get_bungalow_for_ticket_bundle(ticket.bundle_id)

    occupant_id = ticket.used_by_id
    if not occupant_id:
        flash_error('Diesem Platz ist kein Bewohner zugeordnet.')
        return redirect_to('.occupant_index', number=bungalow.number)

    occupant = user_service.get_user(occupant_id)
    occupant_slot = OccupantSlot(ticket_id=ticket.id, occupant=occupant)

    return {
        'occupant_slot': occupant_slot,
        'bungalow': bungalow,
    }


@blueprint.post('/tickets/<ticket_id>/user/remove')
@bungalow_support_required
@enabled_ticket_management_required
@login_required
def occupant_remove(ticket_id):
    """Remove an occupant from the bungalow."""
    ticket = _get_ticket_or_404(ticket_id)
    manager = g.user

    if not ticket.is_user_managed_by(manager.id):
        abort(403)

    bungalow = _get_bungalow_for_ticket_bundle(ticket.bundle_id)

    occupant_id = ticket.used_by_id
    if not occupant_id:
        flash_error('Diesem Platz ist kein Bewohner zugeordnet.')
        return redirect_to('.occupant_index', number=bungalow.number)

    occupant = user_service.get_user(occupant_id)

    ticket_user_management_service.withdraw_user(ticket.id, manager.id)

    flash_success(
        f'"{occupant.screen_name}" wurde als Mitbewohner '
        f'aus Bungalow {bungalow.number} entfernt.'
    )

    event = BungalowOccupantRemovedEvent(
        occurred_at=datetime.utcnow(),
        initiator=EventUser.from_user(manager),
        bungalow_id=bungalow.id,
        bungalow_number=bungalow.number,
        occupant=EventUser.from_user(occupant),
    )
    bungalow_signals.occupant_removed.send(None, event=event)

    return redirect_to('.occupant_index', number=bungalow.number)


# -------------------------------------------------------------------- #
# occupancy title and description


@blueprint.get('/occupancies/<occupancy_id>/description/update')
@bungalow_support_required
@enabled_bungalow_customization_required
@login_required
@templated
@subnavigation_for_view('bungalows')
def description_update_form(occupancy_id, *, erroneous_form=None):
    """Show a form to update the bungalow occupancy's description."""
    occupancy = _get_occupancy_or_404(occupancy_id)

    bungalow = bungalow_service.get_db_bungalow(occupancy.bungalow_id)

    if occupancy.manager_id != g.user.id:
        abort(403)

    form = (
        erroneous_form
        if erroneous_form
        else DescriptionUpdateForm(obj=occupancy)
    )

    return {
        'bungalow': bungalow,
        'form': form,
    }


@blueprint.post('/occupancies/<occupancy_id>/description')
@bungalow_support_required
@enabled_bungalow_customization_required
@login_required
def description_update(occupancy_id):
    """Update the bungalow occupancy's description."""
    occupancy = _get_occupancy_or_404(occupancy_id)

    bungalow = bungalow_service.get_db_bungalow(occupancy.bungalow_id)

    if occupancy.manager_id != g.user.id:
        abort(403)

    manager = g.user

    form = DescriptionUpdateForm(request.form)
    if not form.validate():
        return description_update_form(occupancy_id, erroneous_form=form)

    db_occupancy = bungalow_occupancy_service.get_db_occupancy(
        occupancy.id
    ).unwrap()

    db_occupancy.title = form.title.data.strip()
    db_occupancy.description = form.description.data.strip()

    db.session.commit()

    flash_success('Die Beschreibung wurde aktualisiert.')

    event = BungalowOccupancyDescriptionUpdatedEvent(
        occurred_at=datetime.utcnow(),
        initiator=EventUser.from_user(manager),
        bungalow_id=bungalow.id,
        bungalow_number=bungalow.number,
    )
    bungalow_signals.description_updated.send(None, event=event)

    return redirect_to('.view', number=bungalow.number)


# -------------------------------------------------------------------- #
# occupancy avatar


@blueprint.get('/occupancies/<occupancy_id>/avatar/update')
@bungalow_support_required
@enabled_bungalow_customization_required
@login_required
@templated
@subnavigation_for_view('bungalows')
def avatar_update_form(occupancy_id, *, erroneous_form=None):
    """Show a form to update the bungalow occupancy's avatar image."""
    occupancy = _get_occupancy_or_404(occupancy_id)

    bungalow = bungalow_service.get_db_bungalow(occupancy.bungalow_id)

    if occupancy.manager_id != g.user.id:
        abort(403)

    form = erroneous_form if erroneous_form else AvatarUpdateForm()

    allowed_image_types = (
        bungalow_occupancy_avatar_service.get_allowed_image_types()
    )
    image_type_names = get_image_type_names(allowed_image_types)

    return {
        'bungalow': bungalow,
        'form': form,
        'allowed_types': image_type_names,
        'maximum_dimensions': bungalow_occupancy_avatar_service.MAXIMUM_DIMENSIONS,
    }


@blueprint.post('/occupancies/<occupancy_id>/avatar')
@bungalow_support_required
@enabled_bungalow_customization_required
@login_required
def avatar_update(occupancy_id):
    """Update the bungalow occupancy's avatar image."""
    occupancy = _get_occupancy_or_404(occupancy_id)

    bungalow = bungalow_service.get_db_bungalow(occupancy.bungalow_id)

    if occupancy.manager_id != g.user.id:
        abort(403)

    manager = g.user

    # Make `InputRequired` work on `FileField`.
    form_fields = request.form.copy()
    if request.files:
        form_fields.update(request.files)

    form = AvatarUpdateForm(form_fields)

    if not form.validate():
        return avatar_update_form(occupancy.id, erroneous_form=form)

    image = request.files.get('image')
    if not image or not image.filename:
        abort(400, 'No file to upload has been specified.')

    try:
        update_result = bungalow_occupancy_avatar_service.update_avatar_image(
            occupancy.id, manager.id, image.stream
        )
        if update_result.is_err():
            abort(400, update_result.unwrap_err())
    except FileExistsError:
        abort(409, 'File already exists, not overwriting.')

    flash_success(
        f'Das Avatarbild für Bungalow {bungalow.number:d} wurde aktualisiert.',
        icon='upload',
    )

    event = BungalowOccupancyAvatarUpdatedEvent(
        occurred_at=datetime.utcnow(),
        initiator=EventUser.from_user(manager),
        bungalow_id=bungalow.id,
        bungalow_number=bungalow.number,
    )
    bungalow_signals.avatar_updated.send(None, event=event)

    return redirect_to('.view', number=bungalow.number)


@blueprint.delete('/occupancies/<occupancy_id>/avatar')
@bungalow_support_required
@enabled_bungalow_customization_required
@login_required
@respond_no_content
def avatar_remove(occupancy_id):
    """Remove the bungalow occupancy's avatar image."""
    occupancy = _get_occupancy_or_404(occupancy_id)

    bungalow = bungalow_service.get_db_bungalow(occupancy.bungalow_id)

    if occupancy.manager_id != g.user.id:
        abort(403)

    bungalow_occupancy_avatar_service.remove_avatar_image(occupancy.id)

    flash_success(
        f'Das Avatarbild für Bungalow {bungalow.number:d} wurde entfernt.'
    )


# -------------------------------------------------------------------- #


def _get_bungalow_for_id_or_404(bungalow_id):
    bungalow = bungalow_service.find_db_bungalow(bungalow_id)

    if (bungalow is None) or (bungalow.party_id != g.party.id):
        abort(404)

    return bungalow


def _get_bungalow_for_number_or_404(number: int):
    bungalow = bungalow_service.find_db_bungalow_by_number(g.party.id, number)

    if bungalow is None:
        abort(404)

    return bungalow


def _get_occupancy_or_404(occupancy_id: OccupancyID) -> BungalowOccupancy:
    occupancy = bungalow_occupancy_service.find_occupancy(occupancy_id)

    if occupancy is None:
        abort(404)

    return occupancy


def _is_ticket_management_enabled():
    if not g.party:
        return False

    party = party_service.get_party(g.party.id)
    return party.ticket_management_enabled


def _get_bungalow_customization_enabled() -> bool:
    return not g.party.is_over


def _get_ticket_or_404(ticket_id):
    ticket = ticket_service.find_ticket(ticket_id)

    if (ticket is None) or (ticket.category.party_id != g.party.id):
        abort(404)

    return ticket


def _get_bungalow_for_ticket_bundle(
    ticket_bundle_id: TicketBundleID,
) -> DbBungalow:
    return bungalow_occupancy_service.get_bungalow_for_ticket_bundle(
        ticket_bundle_id
    )

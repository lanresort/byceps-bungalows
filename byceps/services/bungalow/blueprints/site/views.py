"""
byceps.services.bungalow.blueprints.site.views
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from datetime import datetime
from functools import wraps

from flask import abort, g, render_template, request
from flask_babel import gettext

from byceps.services.bungalow import (
    bungalow_category_service,
    bungalow_occupancy_avatar_service,
    bungalow_occupancy_service,
    bungalow_order_service,
    bungalow_service,
    bungalow_stats_service,
    signals as bungalow_signals,
)
from byceps.services.bungalow.dbmodels.bungalow import DbBungalow
from byceps.services.bungalow.errors import (
    ProductBelongsToDifferentShopError,
    ProductTypeUnexpectedError,
    ProductUnavailableError,
    StorefrontClosedError,
)
from byceps.services.bungalow.events import (
    BungalowOccupancyAvatarUpdatedEvent,
    BungalowOccupantAddedEvent,
    BungalowOccupantRemovedEvent,
)
from byceps.services.bungalow.models.bungalow import (
    BungalowID,
    BungalowOccupationState,
)
from byceps.services.bungalow.models.category import (
    BungalowCategory,
    BungalowCategoryID,
)
from byceps.services.bungalow.models.occupation import (
    BungalowOccupancy,
    OccupancyID,
    OccupantSlot,
)
from byceps.services.country import country_service
from byceps.services.orga_team import orga_team_service
from byceps.services.party import party_service
from byceps.services.shop.order import signals as shop_order_signals
from byceps.services.shop.order.blueprints.site.forms import OrderForm
from byceps.services.shop.order.email import order_email_service
from byceps.services.shop.product import product_domain_service, product_service
from byceps.services.shop.product.models import ProductType
from byceps.services.shop.storefront import storefront_service
from byceps.services.shop.storefront.models import Storefront
from byceps.services.site.blueprints.site.navigation import (
    subnavigation_for_view,
)
from byceps.services.ticketing import (
    ticket_service,
    ticket_user_management_service,
)
from byceps.services.ticketing.dbmodels.ticket import DbTicket
from byceps.services.ticketing.models.ticket import TicketBundleID, TicketID
from byceps.services.user import user_service
from byceps.util.framework.blueprint import create_blueprint
from byceps.util.framework.flash import flash_error, flash_notice, flash_success
from byceps.util.framework.templating import templated
from byceps.util.image.image_type import get_image_type_names
from byceps.util.result import Err, Ok
from byceps.util.views import login_required, redirect_to, respond_no_content

from . import service
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
    db_bungalows = bungalow_service.get_bungalows_extended_for_party(g.party.id)

    bungalows_by_number = {
        db_bungalow.number: db_bungalow for db_bungalow in db_bungalows
    }

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
        db_bungalow.occupancy.id
        for db_bungalow in db_bungalows
        if db_bungalow.occupancy
    }
    occupant_slots_by_occupancy_id = (
        bungalow_occupancy_service.get_occupant_slots_for_occupancies(
            occupancy_ids
        )
    )

    occupancy_user_ids = {
        db_bungalow.occupancy.occupied_by_id
        for db_bungalow in db_bungalows
        if db_bungalow.occupancy
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
        'bungalows': db_bungalows,
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
    db_bungalow = _get_bungalow_for_number_or_404(number)

    ticket_management_enabled = _is_ticket_management_enabled()
    bungalow_customization_enabled = _get_bungalow_customization_enabled()

    if db_bungalow.reserved:
        reserved_by = user_service.find_user(
            db_bungalow.occupancy.occupied_by_id, include_avatar=True
        )
    else:
        reserved_by = None

    if db_bungalow.occupied:
        manager_id = db_bungalow.occupancy.manager_id
        manager = user_service.get_user(manager_id)

        current_user_is_main_occupant = (
            db_bungalow.occupancy.occupied_by_id == g.user.id
        )
        current_user_is_manager = manager.id == g.user.id

        occupant_slots = (
            bungalow_occupancy_service.get_occupant_slots_for_occupancy(
                db_bungalow.occupancy.id
            )
        )
    else:
        current_user_is_main_occupant = False
        current_user_is_manager = False
        manager = None
        occupant_slots = None

    return {
        'bungalow': db_bungalow,
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

    db_bungalow = bungalow_service.find_bungalow_inhabited_by_user(
        me_id, party_id
    )

    if db_bungalow:
        return redirect_to('.view', number=db_bungalow.number)
    else:
        return render_template('site/bungalow/no_bungalow_inhabited.html')


# -------------------------------------------------------------------- #
# ordering


@blueprint.get('/order_with_preselection/<uuid:bungalow_id>')
@login_required
@bungalow_support_required
@templated
@subnavigation_for_view('bungalows')
def order_with_preselection_form(
    bungalow_id: BungalowID, *, erroneous_form: OrderForm | None = None
):
    """Show a form to order a bungalow."""
    db_bungalow = _get_bungalow_for_id_or_404(bungalow_id)

    db_product = db_bungalow.category.product
    if db_product.type_ != ProductType.bungalow_with_preselection:
        abort(404)

    storefront = _get_storefront_or_404()
    if db_product.shop_id != storefront.shop_id:
        abort(404)

    if storefront.closed:
        flash_notice(gettext('The shop is closed.'))
        return {'bungalow': None}

    if db_bungalow.reserved_or_occupied:
        flash_error(f'Bungalow {db_bungalow.number} ist bereits reserviert.')
        return {'bungalow': None}

    if (
        not db_product
        or db_product.quantity < 1
        or not product_domain_service.is_product_available_now(db_product)
    ):
        flash_error(
            f'Bungalow {db_bungalow.number} kann derzeit nicht reserviert werden.'
        )
        return {'bungalow': None}

    compilation = product_service.get_product_compilation_for_single_product(
        db_product.id
    )

    collection = product_service.get_product_collection_for_product_compilation(
        '', compilation
    )
    collections = [collection]

    user_detail = user_service.get_detail(g.user.id)

    if bungalow_occupancy_service.has_user_occupied_any_bungalow(
        g.party.id, g.user.id
    ):
        flash_error(
            'Du hast bereits einen Bungalow für diese Party reserviert.'
        )
        return {'bungalow': None}

    form = erroneous_form if erroneous_form else OrderForm(obj=user_detail)

    country_names = country_service.get_country_names()

    match product_domain_service.calculate_product_compilation_total_amount(
        compilation
    ):
        case Ok(total_amount):
            pass
        case Err(_):
            flash_error('Für einige Artikel ist keine Stückzahl vorgegeben.')
            return {'bungalow': None}

    return {
        'bungalow': db_bungalow,
        'form': form,
        'country_names': country_names,
        'collections': collections,
        'images_by_product_id': {},
        'total_amount': total_amount,
    }


@blueprint.post('/order_with_preselection/<uuid:bungalow_id>')
@bungalow_support_required
@login_required
def order_with_preselection(bungalow_id: BungalowID):
    """Order a bungalow."""
    db_bungalow = _get_bungalow_for_id_or_404(bungalow_id)

    db_product = db_bungalow.category.product
    if db_product.type_ != ProductType.bungalow_with_preselection:
        abort(404)

    storefront = _get_storefront_or_404()
    if db_product.shop_id != storefront.shop_id:
        abort(404)

    if storefront.closed:
        flash_notice(gettext('The shop is closed.'))
        return order_with_preselection_form(bungalow_id)

    if db_bungalow.reserved_or_occupied:
        flash_error(f'Bungalow {db_bungalow.number} ist bereits reserviert.')
        return order_with_preselection_form(bungalow_id)

    if (
        not db_product
        or db_product.quantity < 1
        or not product_domain_service.is_product_available_now(db_product)
    ):
        flash_error(
            f'Bungalow {db_bungalow.number} kann derzeit nicht reserviert werden.'
        )
        return order_with_preselection_form(bungalow_id)

    user = g.user

    if bungalow_occupancy_service.has_user_occupied_any_bungalow(
        g.party.id, user.id
    ):
        flash_error(
            'Du hast bereits einen Bungalow für diese Party reserviert.'
        )
        return order_with_preselection_form(bungalow_id)

    form = OrderForm(request.form)
    if not form.validate():
        return order_with_preselection_form(bungalow_id, erroneous_form=form)

    orderer = form.get_orderer(user)

    match bungalow_occupancy_service.reserve_bungalow(db_bungalow.id, user):
        case Ok((reservation, occupancy, bungalow_reserved_event)):
            pass
        case Err(_):
            flash_error(
                f'Bungalow {db_bungalow.number} ist bereits reserviert.'
            )
            return order_with_preselection_form(bungalow_id)

    bungalow_signals.bungalow_reserved.send(None, event=bungalow_reserved_event)
    flash_success(
        f'Bungalow {db_bungalow.number} wurde als von dir reserviert markiert.'
    )

    match bungalow_occupancy_service.place_bungalow_with_preselection_order(
        storefront, reservation.id, occupancy.id, orderer
    ):
        case Ok((order, order_placed_event)):
            pass
        case Err(_):
            flash_error(gettext('Placing the order has failed.'))
            return order_with_preselection_form(bungalow_id)

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


@blueprint.get('/order_without_preselection')
@bungalow_support_required
@templated
@subnavigation_for_view('bungalows')
def order_without_preselection_index():
    """Show bungalow categories."""
    category_summaries = service.get_bungalow_category_summaries(g.party.id)

    return {
        'category_summaries': category_summaries,
    }


@blueprint.get('/order_without_preselection/<uuid:category_id>')
@login_required
@bungalow_support_required
@templated
@subnavigation_for_view('bungalows')
def order_without_preselection_form(
    category_id: BungalowCategoryID, *, erroneous_form: OrderForm | None = None
):
    """Show a form to order a bungalow category."""
    category = _get_category_or_404(category_id)

    product = product_service.get_product(category.product.id)
    storefront = _get_storefront_or_404()

    match bungalow_order_service.check_order_without_preselection_preconditions(
        storefront, product
    ):
        case Err(err):
            match err:
                case ProductTypeUnexpectedError():
                    abort(404)
                case ProductBelongsToDifferentShopError():
                    abort(404)
                case StorefrontClosedError():
                    flash_notice(gettext('The shop is closed.'))
                    return {'category': None}
                case ProductUnavailableError():
                    flash_error(
                        f'Die Bungalow-Kategorie {category.title} kann derzeit nicht gebucht werden.'
                    )
                    return {'category': None}

    compilation = product_service.get_product_compilation_for_single_product(
        product.id
    )

    collection = product_service.get_product_collection_for_product_compilation(
        '', compilation
    )
    collections = [collection]

    user_detail = user_service.get_detail(g.user.id)

    if bungalow_order_service.has_user_ordered_any_bungalow_category(
        user.id, g.party.id
    ):
        flash_error(
            'Du hast bereits eine Bungalow-Bestellung für diese Party aufgegeben.'
        )
        return {'category': None}

    form = erroneous_form if erroneous_form else OrderForm(obj=user_detail)

    country_names = country_service.get_country_names()

    match product_domain_service.calculate_product_compilation_total_amount(
        compilation
    ):
        case Ok(total_amount):
            pass
        case Err(_):
            flash_error('Für einige Artikel ist keine Stückzahl vorgegeben.')
            return {'category': None}

    return {
        'category': category,
        'form': form,
        'country_names': country_names,
        'collections': collections,
        'images_by_product_id': {},
        'total_amount': total_amount,
    }


@blueprint.post('/order_without_preselection/<uuid:category_id>')
@bungalow_support_required
@login_required
def order_without_preselection(category_id: BungalowCategoryID):
    """Order a bungalow category."""
    category = _get_category_or_404(category_id)

    product = product_service.get_product(category.product.id)
    storefront = _get_storefront_or_404()

    match bungalow_order_service.check_order_without_preselection_preconditions(
        storefront, product
    ):
        case Err(err):
            match err:
                case ProductTypeUnexpectedError():
                    abort(404)
                case ProductBelongsToDifferentShopError():
                    abort(404)
                case StorefrontClosedError():
                    flash_notice(gettext('The shop is closed.'))
                    return order_without_preselection_form(category.id)
                case ProductUnavailableError():
                    flash_error(
                        f'Die Bungalow-Kategorie {category.title} kann derzeit nicht gebucht werden.'
                    )
                    return order_without_preselection_form(category.id)

    user = g.user

    if bungalow_order_service.has_user_ordered_any_bungalow_category(
        user.id, g.party.id
    ):
        flash_error(
            'Du hast bereits eine Bungalow-Bestellung für diese Party aufgegeben.'
        )
        return order_without_preselection_form(category.id)

    form = OrderForm(request.form)
    if not form.validate():
        return order_without_preselection_form(category.id, erroneous_form=form)

    orderer = form.get_orderer(user)

    match bungalow_order_service.place_bungalow_order(
        storefront, product, orderer
    ):
        case Ok((order, order_placed_event)):
            pass
        case Err(_):
            flash_error(gettext('Placing the order has failed.'))
            return order_without_preselection_form(category.id)

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


# -------------------------------------------------------------------- #
# occupants


@blueprint.get('/occupants', defaults={'page': 1})
@blueprint.get('/occupants/pages/<int:page>')
@bungalow_support_required
@templated
@subnavigation_for_view('occupants')
def occupant_index_all(page: int):
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
    db_bungalow = _get_bungalow_for_number_or_404(number)

    user = g.user
    if (
        not user.authenticated
        or db_bungalow.occupation_state != BungalowOccupationState.occupied
        or (
            db_bungalow.occupancy.manager_id != user.id
            and not bungalow_service.is_user_allowed_to_manage_any_occupant_slots(
                user, db_bungalow.occupancy
            )
        )
    ):
        abort(403)

    occupant_slots = (
        bungalow_occupancy_service.get_occupant_slots_for_occupancy(
            db_bungalow.occupancy.id
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
        'bungalow': db_bungalow,
        'occupant_slots_and_tickets': occupant_slots_and_tickets,
        'orga_ids': orga_ids,
    }


@blueprint.get('/tickets/<uuid:ticket_id>/user/add')
@bungalow_support_required
@enabled_ticket_management_required
@login_required
@templated
@subnavigation_for_view('bungalows')
def occupant_add_form(
    ticket_id: TicketID, *, erroneous_form: OccupantAddForm | None = None
):
    """Show a form to add a user as an occupant to the bungalow."""
    ticket = _get_ticket_or_404(ticket_id)
    manager = g.user

    if not ticket.is_user_managed_by(manager.id):
        abort(403)

    if not ticket.bundle_id:
        abort(404)

    db_bungalow = _get_bungalow_for_ticket_bundle(ticket.bundle_id)

    occupant_id = ticket.used_by_id
    if occupant_id:
        flash_error('Diesem Platz ist bereits ein Bewohner zugeordnet.')
        return redirect_to('.occupant_index', number=db_bungalow.number)

    occupant_slot = OccupantSlot(ticket_id=ticket.id, occupant=None)

    form = erroneous_form if erroneous_form else OccupantAddForm()

    return {
        'occupant_slot': occupant_slot,
        'form': form,
        'bungalow': db_bungalow,
    }


@blueprint.post('/tickets/<uuid:ticket_id>/user/add')
@bungalow_support_required
@enabled_ticket_management_required
@login_required
def occupant_add(ticket_id: TicketID):
    """Add a user as occupant to the bungalow."""
    ticket = _get_ticket_or_404(ticket_id)
    manager = g.user

    if not ticket.is_user_managed_by(manager.id):
        abort(403)

    if not ticket.bundle_id:
        abort(404)

    db_bungalow = _get_bungalow_for_ticket_bundle(ticket.bundle_id)

    if ticket.used_by_id:
        flash_error('Diesem Platz ist bereits ein Bewohner zugeordnet.')
        return redirect_to('.occupant_index', number=db_bungalow.number)

    form = OccupantAddForm(request.form)
    if not form.validate():
        return occupant_add_form(ticket_id, erroneous_form=form)

    occupant = form.occupant.data

    ticket_user_management_service.appoint_user(
        ticket.id, occupant.id, manager.id
    )

    flash_success(
        f'"{occupant.screen_name}" wurde als Mitbewohner '
        f'in Bungalow {db_bungalow.number} aufgenommen.'
    )

    event = BungalowOccupantAddedEvent(
        occurred_at=datetime.utcnow(),
        initiator=manager,
        bungalow_id=db_bungalow.id,
        bungalow_number=db_bungalow.number,
        occupant=occupant,
    )
    bungalow_signals.occupant_added.send(None, event=event)

    return redirect_to('.occupant_index', number=db_bungalow.number)


@blueprint.get('/tickets/<uuid:ticket_id>/user/remove')
@bungalow_support_required
@enabled_ticket_management_required
@login_required
@templated
@subnavigation_for_view('bungalows')
def occupant_remove_form(ticket_id: TicketID):
    """Show a form to remove an occupant from the bungalow."""
    ticket = _get_ticket_or_404(ticket_id)
    manager = g.user

    if not ticket.is_user_managed_by(manager.id):
        abort(403)

    if not ticket.bundle_id:
        abort(404)

    db_bungalow = _get_bungalow_for_ticket_bundle(ticket.bundle_id)

    occupant_id = ticket.used_by_id
    if not occupant_id:
        flash_error('Diesem Platz ist kein Bewohner zugeordnet.')
        return redirect_to('.occupant_index', number=db_bungalow.number)

    occupant = user_service.get_user(occupant_id)
    occupant_slot = OccupantSlot(ticket_id=ticket.id, occupant=occupant)

    return {
        'occupant_slot': occupant_slot,
        'bungalow': db_bungalow,
    }


@blueprint.post('/tickets/<uuid:ticket_id>/user/remove')
@bungalow_support_required
@enabled_ticket_management_required
@login_required
def occupant_remove(ticket_id: TicketID):
    """Remove an occupant from the bungalow."""
    ticket = _get_ticket_or_404(ticket_id)
    manager = g.user

    if not ticket.is_user_managed_by(manager.id):
        abort(403)

    if not ticket.bundle_id:
        abort(404)

    db_bungalow = _get_bungalow_for_ticket_bundle(ticket.bundle_id)

    occupant_id = ticket.used_by_id
    if not occupant_id:
        flash_error('Diesem Platz ist kein Bewohner zugeordnet.')
        return redirect_to('.occupant_index', number=db_bungalow.number)

    occupant = user_service.get_user(occupant_id)

    ticket_user_management_service.withdraw_user(ticket.id, manager.id)

    flash_success(
        f'"{occupant.screen_name}" wurde als Mitbewohner '
        f'aus Bungalow {db_bungalow.number} entfernt.'
    )

    event = BungalowOccupantRemovedEvent(
        occurred_at=datetime.utcnow(),
        initiator=manager,
        bungalow_id=db_bungalow.id,
        bungalow_number=db_bungalow.number,
        occupant=occupant,
    )
    bungalow_signals.occupant_removed.send(None, event=event)

    return redirect_to('.occupant_index', number=db_bungalow.number)


# -------------------------------------------------------------------- #
# occupancy title and description


@blueprint.get('/occupancies/<uuid:occupancy_id>/description/update')
@bungalow_support_required
@enabled_bungalow_customization_required
@login_required
@templated
@subnavigation_for_view('bungalows')
def description_update_form(
    occupancy_id: OccupancyID,
    *,
    erroneous_form: DescriptionUpdateForm | None = None,
):
    """Show a form to update the bungalow occupancy's description."""
    occupancy = _get_occupancy_or_404(occupancy_id)

    db_bungalow = bungalow_service.get_db_bungalow(occupancy.bungalow_id)

    if occupancy.manager_id != g.user.id:
        abort(403)

    form = (
        erroneous_form
        if erroneous_form
        else DescriptionUpdateForm(obj=occupancy)
    )

    return {
        'bungalow': db_bungalow,
        'form': form,
    }


@blueprint.post('/occupancies/<uuid:occupancy_id>/description')
@bungalow_support_required
@enabled_bungalow_customization_required
@login_required
def description_update(occupancy_id: OccupancyID):
    """Update the bungalow occupancy's description."""
    occupancy = _get_occupancy_or_404(occupancy_id)

    db_bungalow = bungalow_service.get_db_bungalow(occupancy.bungalow_id)

    if occupancy.manager_id != g.user.id:
        abort(403)

    manager = g.user

    form = DescriptionUpdateForm(request.form)
    if not form.validate():
        return description_update_form(occupancy_id, erroneous_form=form)

    title = form.title.data.strip()
    description = form.description.data.strip()

    match bungalow_occupancy_service.update_description(
        occupancy.id, title, description, manager
    ):
        case Ok(event):
            flash_success('Die Beschreibung wurde aktualisiert.')
            bungalow_signals.description_updated.send(None, event=event)
        case Err(_):
            flash_error(gettext('An unexpected error occurred.'))

    return redirect_to('.view', number=db_bungalow.number)


# -------------------------------------------------------------------- #
# occupancy avatar


@blueprint.get('/occupancies/<uuid:occupancy_id>/avatar/update')
@bungalow_support_required
@enabled_bungalow_customization_required
@login_required
@templated
@subnavigation_for_view('bungalows')
def avatar_update_form(
    occupancy_id: OccupancyID, *, erroneous_form: AvatarUpdateForm | None = None
):
    """Show a form to update the bungalow occupancy's avatar image."""
    occupancy = _get_occupancy_or_404(occupancy_id)

    db_bungalow = bungalow_service.get_db_bungalow(occupancy.bungalow_id)

    if occupancy.manager_id != g.user.id:
        abort(403)

    form = erroneous_form if erroneous_form else AvatarUpdateForm()

    allowed_image_types = (
        bungalow_occupancy_avatar_service.get_allowed_image_types()
    )
    image_type_names = get_image_type_names(allowed_image_types)

    return {
        'bungalow': db_bungalow,
        'form': form,
        'allowed_types': image_type_names,
        'maximum_dimensions': bungalow_occupancy_avatar_service.MAXIMUM_DIMENSIONS,
    }


@blueprint.post('/occupancies/<uuid:occupancy_id>/avatar')
@bungalow_support_required
@enabled_bungalow_customization_required
@login_required
def avatar_update(occupancy_id: OccupancyID):
    """Update the bungalow occupancy's avatar image."""
    occupancy = _get_occupancy_or_404(occupancy_id)

    db_bungalow = bungalow_service.get_db_bungalow(occupancy.bungalow_id)

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
        match bungalow_occupancy_avatar_service.update_avatar_image(
            occupancy.id, manager.id, image.stream
        ):
            case Err(err):
                abort(400, err)
    except FileExistsError:
        abort(409, 'File already exists, not overwriting.')

    flash_success(
        f'Das Avatarbild für Bungalow {db_bungalow.number:d} wurde aktualisiert.',
        icon='upload',
    )

    event = BungalowOccupancyAvatarUpdatedEvent(
        occurred_at=datetime.utcnow(),
        initiator=manager,
        bungalow_id=db_bungalow.id,
        bungalow_number=db_bungalow.number,
    )
    bungalow_signals.avatar_updated.send(None, event=event)

    return redirect_to('.view', number=db_bungalow.number)


@blueprint.delete('/occupancies/<occupancy_id>/avatar')
@bungalow_support_required
@enabled_bungalow_customization_required
@login_required
@respond_no_content
def avatar_remove(occupancy_id):
    """Remove the bungalow occupancy's avatar image."""
    occupancy = _get_occupancy_or_404(occupancy_id)

    db_bungalow = bungalow_service.get_db_bungalow(occupancy.bungalow_id)

    if occupancy.manager_id != g.user.id:
        abort(403)

    bungalow_occupancy_avatar_service.remove_avatar_image(occupancy.id)

    flash_success(
        f'Das Avatarbild für Bungalow {db_bungalow.number:d} wurde entfernt.'
    )


# -------------------------------------------------------------------- #


def _get_bungalow_for_id_or_404(bungalow_id) -> DbBungalow:
    db_bungalow = bungalow_service.find_db_bungalow(bungalow_id)

    if (db_bungalow is None) or (db_bungalow.party_id != g.party.id):
        abort(404)

    return db_bungalow


def _get_bungalow_for_number_or_404(number: int) -> DbBungalow:
    db_bungalow = bungalow_service.find_db_bungalow_by_number(
        g.party.id, number
    )

    if db_bungalow is None:
        abort(404)

    return db_bungalow


def _get_category_or_404(category_id) -> BungalowCategory:
    category = bungalow_category_service.find_category(category_id)

    if (category is None) or (category.party_id != g.party.id):
        abort(404)

    return category


def _get_occupancy_or_404(occupancy_id: OccupancyID) -> BungalowOccupancy:
    occupancy = bungalow_occupancy_service.find_occupancy(occupancy_id)

    if occupancy is None:
        abort(404)

    return occupancy


def _get_storefront_or_404() -> Storefront:
    storefront_id = g.site.storefront_id
    if storefront_id is None:
        abort(404)

    return storefront_service.get_storefront(storefront_id)


def _is_ticket_management_enabled() -> bool:
    if not g.party:
        return False

    party = party_service.get_party(g.party.id)
    return party.ticket_management_enabled


def _get_bungalow_customization_enabled() -> bool:
    return not g.party.is_over


def _get_ticket_or_404(ticket_id) -> DbTicket:
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

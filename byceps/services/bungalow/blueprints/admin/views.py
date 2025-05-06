"""
byceps.services.bungalow.blueprints.admin.views
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2025 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from collections.abc import Iterable, Iterator
from datetime import datetime

from flask import abort, g, request, url_for
from flask_babel import gettext

from byceps.services.brand import brand_service
from byceps.services.brand.models import Brand, BrandID
from byceps.services.bungalow import (
    bungalow_building_service,
    bungalow_category_service,
    bungalow_occupancy_service,
    bungalow_offer_service,
    bungalow_order_service,
    bungalow_service,
    bungalow_stats_service,
    first_attendance_service,
    signals as bungalow_signals,
)
from byceps.services.bungalow.bungalow_service import (
    UserAlreadyUsesATicketException,
)
from byceps.services.bungalow.dbmodels.bungalow import DbBungalow
from byceps.services.bungalow.dbmodels.occupancy import DbBungalowOccupancy
from byceps.services.bungalow.models.building import BungalowBuilding
from byceps.services.bungalow.models.bungalow import Bungalow, BungalowID
from byceps.services.bungalow.models.category import (
    BungalowCategory,
    BungalowCategoryID,
)
from byceps.services.bungalow.models.occupation import (
    BungalowOccupancy,
    CategoryOccupationSummary,
    OccupancyID,
    OccupantSlot,
)
from byceps.services.party import party_service
from byceps.services.party.models import Party, PartyID
from byceps.services.shop.order import (
    order_service,
    signals as shop_order_signals,
)
from byceps.services.shop.order.events import (
    ShopOrderCanceledEvent,
    ShopOrderPaidEvent,
)
from byceps.services.shop.order.models.order import Order
from byceps.services.shop.product import product_service
from byceps.services.shop.product.models import ProductNumber, ProductType
from byceps.services.shop.shop import shop_service
from byceps.services.ticketing import (
    ticket_bundle_service,
    ticket_category_service,
)
from byceps.services.ticketing.dbmodels.ticket_bundle import DbTicketBundle
from byceps.services.user import user_service
from byceps.services.user.models.user import UserID
from byceps.util.export import serialize_tuples_to_csv
from byceps.util.framework.blueprint import create_blueprint
from byceps.util.framework.flash import flash_error, flash_notice, flash_success
from byceps.util.framework.templating import templated
from byceps.util.iterables import find
from byceps.util.result import Err, Ok
from byceps.util.views import (
    permission_required,
    redirect_to,
    respond_no_content,
    respond_no_content_with_location,
    textified,
)

from . import service
from .forms import (
    AppointManagerForm,
    BuildingCreateForm,
    CategoryCreateForm,
    CategoryUpdateForm,
    InternalRemarkUpdateForm,
    OccupancyMoveForm,
    OfferCreateForm,
)


blueprint = create_blueprint('bungalow_admin', __name__)


# -------------------------------------------------------------------- #
# hooks


@shop_order_signals.order_canceled.connect
def release_bungalow(sender, *, event: ShopOrderCanceledEvent):
    """Release the bungalow that had been created for that order."""
    order = order_service.get_order(event.order_id)

    bungalow = bungalow_order_service.find_bungalow_by_order(order.order_number)
    if not bungalow:
        return

    try:
        bungalow_released_event = bungalow_occupancy_service.release_bungalow(
            bungalow.id, initiator=event.initiator
        )
    except ValueError as e:
        flash_error(
            f'Fehler bei der Freigabe von Bungalow {bungalow.number}: {e}'
        )
        return

    bungalow_signals.bungalow_released.send(None, event=bungalow_released_event)

    flash_success(
        f'Bungalow {bungalow.number} wurde wieder zur Reservierung freigegeben.'
    )


@shop_order_signals.order_paid.connect
def occupy_bungalow(sender, *, event: ShopOrderPaidEvent):
    """Mark a bungalow as occupied."""
    order = order_service.get_order(event.order_id)

    bungalow = bungalow_order_service.find_bungalow_by_order(order.order_number)
    if not bungalow:
        return

    if not bungalow.reserved:
        flash_error(
            f'Bungalow {bungalow.number} muss reserviert sein um belegt werden zu können.'
        )
        return

    product_number = bungalow.category.product.item_number
    try:
        ticket_bundle = _get_ticket_bundle_for_line_item(order, product_number)
        occupation_result = bungalow_occupancy_service.occupy_bungalow(
            bungalow.reservation.id, bungalow.occupancy.id, ticket_bundle.id
        )
        if occupation_result.is_err():
            flash_error(
                f'Bungalow {bungalow.number} konnte nicht belegt werden.'
            )
            return

        occupancy, bungalow_occupied_event = occupation_result.unwrap()
    except ValueError as e:
        flash_error(
            f'Fehler bei der Belegung von Bungalow {bungalow.number}: {e}'
        )
        return

    main_occupant_id = occupancy.occupied_by_id
    main_occupant = user_service.get_user(main_occupant_id)

    bungalow_signals.bungalow_occupied.send(None, event=bungalow_occupied_event)

    flash_success(
        f'Bungalow {bungalow.number} wurde '
        f'als von {main_occupant.screen_name} belegt markiert.'
    )

    if ticket_bundle.tickets:
        first_ticket = bungalow_service.get_first_ticket_in_bundle(
            ticket_bundle
        )

        assignment_result = bungalow_service.assign_ticket_to_main_occupant(
            first_ticket, main_occupant
        )
        if assignment_result.is_err():
            err = assignment_result.unwrap_err()
            if isinstance(err, UserAlreadyUsesATicketException):
                flash_notice(
                    f'Benutzer {main_occupant.screen_name} '
                    'nutzt bereits ein Ticket. '
                    f'Kein Ticket aus Bungalow {bungalow.number} '
                    'wurde einem Nutzer zugewiesen.'
                )
            else:
                flash_error(
                    f'Fehler beim zuweisen eines Tickets an Benutzer {main_occupant.screen_name}.'
                )
        else:
            flash_success(
                f'Benutzer {main_occupant.screen_name} wurde '
                'ein Ticket als Nutzer zugewiesen.'
            )


def _get_ticket_bundle_for_line_item(
    order: Order, product_number: ProductNumber
) -> DbTicketBundle:
    line_item = find(
        order.line_items,
        lambda li: li.product_number == product_number
        and li.product_type == ProductType.ticket_bundle,
    )

    if line_item is None:
        raise ValueError(
            f'Product number "{product_number!s} not in line items'
        )

    bundle_ids = line_item.processing_result['ticket_bundle_ids']
    bundle_id = bundle_ids[0]

    return ticket_bundle_service.get_bundle(bundle_id)


# -------------------------------------------------------------------- #
# view functions


@blueprint.get('/buildings/for_brand/<brand_id>')
@permission_required('bungalow.view')
@templated
def buildings(brand_id):
    """List all buildings and layouts for that brand."""
    brand = _get_brand_or_404(brand_id)

    layouts = bungalow_building_service.get_layouts(brand.id)
    buildings = bungalow_building_service.get_buildings(brand.id)

    return {
        'brand': brand,
        'layouts': layouts,
        'buildings': buildings,
    }


@blueprint.get('/buildings/for_brand/<brand_id>/create')
@permission_required('bungalow_building.create')
@templated
def building_create_form(brand_id, erroneous_form=None):
    """Show form to create a building for that brand."""
    brand = _get_brand_or_404(brand_id)

    layouts = bungalow_building_service.get_layouts(brand.id)

    form = erroneous_form if erroneous_form else BuildingCreateForm()
    form.set_layout_choices(layouts)

    return {
        'brand': brand,
        'form': form,
    }


@blueprint.post('/buildings/for_brand/<brand_id>')
@permission_required('bungalow_building.create')
def building_create(brand_id):
    """Create building for that brand."""
    brand = _get_brand_or_404(brand_id)

    layouts = bungalow_building_service.get_layouts(brand.id)

    form = BuildingCreateForm(request.form)
    form.set_layout_choices(layouts)

    if not form.validate():
        return building_create_form(brand_id, form)

    layout = bungalow_building_service.find_layout(form.layout_id.data)
    if not layout:
        abort(400, 'Unknown layout.')

    building = bungalow_building_service.create_building(
        layout, form.number.data
    )

    flash_success(
        f'Gebäude {building.number:d} wurde '
        f'für die Marke "{brand.title}" hinzugefügt.'
    )

    return redirect_to('.buildings', brand_id=brand.id)


@blueprint.get('/<party_id>')
@permission_required('bungalow.view')
@templated
def index_for_party(party_id):
    """List all bungalows for the party."""
    party = _get_party_or_404(party_id)

    bungalows = bungalow_service.get_bungalows_for_party(party.id)

    occupancies = {b.occupancy for b in bungalows if b.occupancy}

    order_numbers = {
        occupancy.order_number
        for occupancy in occupancies
        if occupancy.order_number is not None
    }
    orders = order_service.get_orders_for_order_numbers(order_numbers)
    orders_by_order_number = {order.order_number: order for order in orders}

    user_ids = frozenset(_collect_occupancy_user_ids(occupancies))
    users_by_id = user_service.get_users_indexed_by_id(
        user_ids, include_avatars=True
    )

    offered_seats_total = sum(
        bungalow.category.capacity for bungalow in bungalows
    )

    return {
        'party': party,
        'bungalows': bungalows,
        'users_by_id': users_by_id,
        'orders_by_order_number': orders_by_order_number,
        'offered_seats_total': offered_seats_total,
        'bungalow_statistics': _get_bungalow_statistics(party.id),
    }


def _get_bungalow_statistics(party_id: PartyID) -> CategoryOccupationSummary:
    statistics_by_category = list(
        bungalow_stats_service.get_statistics_by_category(party_id)
    )

    return bungalow_stats_service.get_statistics_total(statistics_by_category)


@blueprint.get('/offers/<bungalow_id>')
@permission_required('bungalow.view')
@templated
def offer_view(bungalow_id):
    """Show offered bungalow."""
    bungalow = _get_bungalow_or_404(bungalow_id)

    party = party_service.get_party(bungalow.party_id)

    occupancy = bungalow_occupancy_service.find_occupancy_for_bungalow(
        bungalow.id
    )

    order = None
    users_by_id = {}
    if occupancy:
        if occupancy.order_number:
            order = order_service.find_order_by_order_number(
                occupancy.order_number
            )

        user_ids = frozenset(_collect_occupancy_user_ids([occupancy]))
        users_by_id = user_service.get_users_indexed_by_id(
            user_ids, include_avatars=True
        )

    occupant_slots = _get_occupant_slots(bungalow, occupancy)

    log_entries = list(service.get_log_entries(bungalow.id))

    return {
        'party': party,
        'bungalow': bungalow,
        'occupancy': occupancy,
        'users_by_id': users_by_id,
        'order': order,
        'occupant_slots': occupant_slots,
        'log_entries': log_entries,
    }


def _collect_occupancy_user_ids(
    occupancies: Iterable[DbBungalowOccupancy],
) -> Iterator[UserID]:
    for occupancy in occupancies:
        occupier_id = occupancy.occupied_by_id
        if occupier_id:
            yield occupier_id

        manager_id = occupancy.manager_id
        if manager_id != occupier_id:
            yield manager_id


def _get_occupant_slots(
    bungalow: DbBungalow, occupancy: BungalowOccupancy | None
) -> list[OccupantSlot]:
    if not bungalow.occupied or occupancy is None:
        return None

    return bungalow_occupancy_service.get_occupant_slots_for_occupancy(
        occupancy.id
    )


@blueprint.get('/offers/for_party/<party_id>/create')
@permission_required('bungalow_offer.create')
@templated
def offer_create_form(party_id, erroneous_form=None):
    """Show form to offer bungalows for the party."""
    party = _get_party_or_404(party_id)

    buildings = _get_buildings_for_party(party)
    bungalow_categories = bungalow_category_service.get_categories_for_party(
        party.id
    )

    form = erroneous_form if erroneous_form else OfferCreateForm()
    form.set_building_choices(buildings)
    form.set_bungalow_category_choices(bungalow_categories)

    return {
        'party': party,
        'form': form,
    }


@blueprint.post('/offers/for_party/<party_id>')
@permission_required('bungalow_offer.create')
def offer_create(party_id):
    """Offer bungalows for the party."""
    party = _get_party_or_404(party_id)

    buildings_for_form = _get_buildings_for_party(party)
    bungalow_categories = bungalow_category_service.get_categories_for_party(
        party.id
    )

    form = OfferCreateForm(request.form)
    form.set_building_choices(buildings_for_form)
    form.set_bungalow_category_choices(bungalow_categories)

    if not form.validate():
        return offer_create_form(party_id, form)

    building_ids = form.building_ids.data
    bungalow_category_id = form.bungalow_category_id.data

    buildings = bungalow_building_service.get_buildings_for_ids(
        party.brand_id, building_ids
    )
    bungalow_category = bungalow_category_service.find_category(
        bungalow_category_id
    )

    bungalow_offer_service.offer_bungalows(
        party.id, buildings, bungalow_category.id
    )

    building_numbers_text = ', '.join(str(b.number) for b in buildings)
    flash_success(
        f'Diese Bungalows werden ab sofort angeboten: {building_numbers_text}'
    )

    return redirect_to('.index_for_party', party_id=party.id)


def _get_buildings_for_party(party: Party) -> list[BungalowBuilding]:
    all_buildings = bungalow_building_service.get_buildings(party.brand_id)

    offered_bungalow_numbers = bungalow_service.get_bungalow_numbers_for_party(
        party.id
    )

    return [
        b for b in all_buildings if b.number not in offered_bungalow_numbers
    ]


@blueprint.delete('/offers/<bungalow_id>')
@permission_required('bungalow_offer.delete')
@respond_no_content_with_location
def offer_delete(bungalow_id):
    """Remove the bungalow offer."""
    bungalow = _get_bungalow_or_404(bungalow_id)

    try:
        bungalow_offer_service.delete_offer(bungalow.id)
    except ValueError as e:
        abort(400, str(e))

    flash_success('Der Bungalow wird nun nicht mehr angeboten.')

    return url_for('.index_for_party', party_id=bungalow.party_id)


@blueprint.get('/<party_id>/occupants')
@permission_required('bungalow.view')
@templated
def occupants(party_id):
    party = _get_party_or_404(party_id)

    bungalows = bungalow_occupancy_service.get_occupied_bungalows_for_party(
        party.id
    )

    occupancy_ids = {
        bungalow.occupancy.id for bungalow in bungalows if bungalow.occupancy
    }
    occupant_slots_by_occupancy_id = (
        bungalow_occupancy_service.get_occupant_slots_for_occupancies(
            occupancy_ids, for_admin=True
        )
    )

    return {
        'party': party,
        'bungalows': bungalows,
        'occupant_slots_by_occupancy_id': occupant_slots_by_occupancy_id,
        'now': datetime.utcnow(),
    }


@blueprint.post('/<bungalow_id>/flags/distributes_network')
@permission_required('bungalow.update')
@respond_no_content
def set_distributes_network_flag(bungalow_id):
    """Set the bungalow's network distributor flag."""
    bungalow = _get_bungalow_or_404(bungalow_id)

    bungalow_offer_service.set_distributes_network_flag(bungalow.id)

    flash_success(
        f'Bungalow {bungalow.number:d} wurde als Netzwerk-Verteiler markiert.'
    )


@blueprint.delete('/<bungalow_id>/flags/distributes_network')
@permission_required('bungalow.update')
@respond_no_content
def unset_distributes_network_flag(bungalow_id):
    """Unset the bungalow's network distributor flag."""
    bungalow = _get_bungalow_or_404(bungalow_id)

    bungalow_offer_service.unset_distributes_network_flag(bungalow.id)

    flash_success(
        f'Bungalow {bungalow.number:d} ist nun nicht mehr '
        'als Netzwerk-Verteiler markiert.'
    )


@blueprint.get('/occupancies/<occupancy_id>/internal_remark')
@permission_required('bungalow.update')
@templated
def internal_remark_update_form(occupancy_id, erroneous_form=None):
    """Show a form to update the internal remark on the occupancy."""
    occupancy = _get_occupancy_or_404(occupancy_id)

    bungalow = bungalow_service.get_db_bungalow(occupancy.bungalow_id)
    if not bungalow.reserved_or_occupied:
        abort(403)

    party = party_service.find_party(bungalow.party_id)

    form = (
        erroneous_form
        if erroneous_form
        else InternalRemarkUpdateForm(obj=occupancy)
    )

    return {
        'party': party,
        'bungalow': bungalow,
        'form': form,
    }


@blueprint.post('/occupancies/<occupancy_id>/internal_remark')
@permission_required('bungalow.update')
def internal_remark_update(occupancy_id):
    """Update the internal remark on the occupancy."""
    occupancy = _get_occupancy_or_404(occupancy_id)

    bungalow = bungalow_service.get_db_bungalow(occupancy.bungalow_id)
    if not bungalow.reserved_or_occupied:
        abort(403)

    form = InternalRemarkUpdateForm(request.form)
    if not form.validate():
        return internal_remark_update_form(occupancy_id, form)

    remark = form.internal_remark.data.strip()

    bungalow_occupancy_service.set_internal_remark(
        occupancy.id, remark
    ).unwrap()

    flash_success(
        f'Die Anmerkung zu Bungalow {bungalow.number:d} wurde aktualisiert.'
    )

    return redirect_to('.index_for_party', party_id=bungalow.party_id)


@blueprint.get('/occupancies/<occupancy_id>/manager/update')
@permission_required('bungalow.update')
@templated
def appoint_manager_form(occupancy_id, erroneous_form=None):
    """Show form to appoint a user as occupancy manager."""
    occupancy = _get_occupancy_or_404(occupancy_id)

    bungalow = bungalow_service.get_db_bungalow(occupancy.bungalow_id)
    party = party_service.find_party(bungalow.party_id)

    form = erroneous_form if erroneous_form else AppointManagerForm()

    return {
        'party': party,
        'occupancy': occupancy,
        'form': form,
    }


@blueprint.post('/occupancies/<occupancy_id>/manager')
@permission_required('bungalow.update')
def appoint_manager(occupancy_id):
    """Appoint a user as occupancy manager."""
    occupancy = _get_occupancy_or_404(occupancy_id)

    bungalow = bungalow_service.get_db_bungalow(occupancy.bungalow_id)
    party = party_service.find_party(bungalow.party_id)

    form = AppointManagerForm(request.form)

    if not form.validate():
        return appoint_manager_form(occupancy_id, form)

    manager = form.manager.data
    initiator = g.user

    match bungalow_occupancy_service.appoint_bungalow_manager(
        occupancy_id, manager, initiator
    ):
        case Ok(_):
            flash_success('Die Verwaltung wurde übertragen.')
        case Err(_):
            flash_error('Die Verwaltung konnte nicht übertragen werden.')

    return redirect_to('.index_for_party', party_id=party.id)


@blueprint.get('/occupancies/<occupancy_id>/move')
@permission_required('bungalow.update')
@templated
def occupancy_move_form(occupancy_id, erroneous_form=None):
    """Show a form to move the occupancy to another bungalow."""
    occupancy = _get_occupancy_or_404(occupancy_id)

    source_bungalow = bungalow_service.get_db_bungalow(occupancy.bungalow_id)
    party = party_service.find_party(source_bungalow.party_id)

    form = erroneous_form if erroneous_form else OccupancyMoveForm()
    form.set_target_bungalow_choices(source_bungalow)

    if not form.target_bungalow_id.choices:
        flash_error('Es sind keine passenden Ziel-Bungalows frei.')
        return redirect_to('.index_for_party', party_id=party.id)

    return {
        'party': party,
        'bungalow': source_bungalow,
        'occupancy': occupancy,
        'form': form,
    }


@blueprint.post('/occupancies/<occupancy_id>/move')
@permission_required('bungalow.update')
def occupancy_move(occupancy_id):
    """Move the occupancy to another bungalow."""
    occupancy = _get_occupancy_or_404(occupancy_id)

    source_bungalow = bungalow_service.get_db_bungalow(occupancy.bungalow_id)
    party = party_service.find_party(source_bungalow.party_id)

    form = OccupancyMoveForm(request.form)
    form.set_target_bungalow_choices(source_bungalow)

    if not form.validate():
        return occupancy_move_form(occupancy.id, form)

    target_bungalow_id = form.target_bungalow_id.data
    target_bungalow = bungalow_service.get_db_bungalow(target_bungalow_id)

    try:
        move_result = bungalow_occupancy_service.move_occupancy(
            occupancy.id, target_bungalow.id, g.user
        )
        if move_result.is_err():
            flash_error(
                'Bungalow konnte nicht verschoben werden: '
                + move_result.unwrap_err()
            )
            return occupancy_move_form(occupancy.id, form)

        event = move_result.unwrap()
    except ValueError as e:
        flash_error(e)
        return occupancy_move_form(occupancy.id, form)

    bungalow_signals.occupancy_moved.send(None, event=event)

    flash_success(
        f'Die Belegung von Bungalow {source_bungalow.number:d} '
        f'wurde zu Bungalow {target_bungalow.number:d} verschoben.'
    )

    return redirect_to('.index_for_party', party_id=party.id)


@blueprint.get('/categories/<party_id>')
@permission_required('bungalow.view')
@templated
def categories(party_id):
    """List bungalow categories for that party."""
    party = _get_party_or_404(party_id)

    categories = bungalow_category_service.get_categories_for_party(party.id)

    return {
        'party': party,
        'categories': categories,
    }


@blueprint.get('/categories/for_party/<party_id>/create')
@permission_required('bungalow.update')
@templated
def category_create_form(party_id, erroneous_form=None):
    """Show form to create a bungalow category."""
    party = _get_party_or_404(party_id)

    shop = shop_service.find_shop_for_brand(party.brand_id)
    if shop is None:
        flash_error(
            'Für die Marke dieser Party ist kein Shop konfiguriert. '
            'Deshalb können keine Bungalowkategorien angelegt werden.'
        )
        return redirect_to('.categories', party_id=party.id)

    form = erroneous_form if erroneous_form else CategoryCreateForm()
    form.set_ticket_category_choices(party.id)
    form.set_product_choices(shop.id)

    return {
        'party': party,
        'form': form,
    }


@blueprint.post('/categories/for_party/<party_id>')
@permission_required('bungalow.update')
def category_create(party_id):
    """Create a bungalow category."""
    party = _get_party_or_404(party_id)

    shop = shop_service.find_shop_for_brand(party.brand_id)
    if shop is None:
        flash_error('Kein Shop für die Marke dieser Party gefunden.')
        return category_create_form(party.id)

    form = CategoryCreateForm(request.form)
    form.set_ticket_category_choices(party.id)
    form.set_product_choices(shop.id)

    if not form.validate():
        return category_create_form(party.id, form)

    title = form.title.data
    capacity = form.capacity.data
    ticket_category = ticket_category_service.find_category(
        form.ticket_category_id.data
    )
    product = product_service.get_product(form.product_id.data)
    image_filename = form.image_filename.data
    image_width = form.image_width.data
    image_height = form.image_height.data

    category = bungalow_category_service.create_category(
        party.id,
        title,
        capacity,
        ticket_category.id,
        product.id,
        image_filename=image_filename,
        image_width=image_width,
        image_height=image_height,
    )

    flash_success(
        gettext(
            'Category "%(category_title)s" has been created.',
            category_title=category.title,
        )
    )

    return redirect_to('.categories', party_id=party.id)


@blueprint.get('/categories/<category_id>/update')
@permission_required('bungalow.update')
@templated
def category_update_form(category_id, erroneous_form=None):
    """Show a form to update the category."""
    category = _get_category_or_404(category_id)

    party = party_service.find_party(category.party_id)

    shop = shop_service.find_shop_for_brand(party.brand_id)
    if shop is None:
        flash_error(
            'Für die Marke dieser Party ist kein Shop konfiguriert. '
            'Deshalb können keine Bungalowkategorien bearbeitet werden.'
        )
        return redirect_to('.categories', party_id=party.id)

    form = (
        erroneous_form
        if erroneous_form
        else CategoryUpdateForm(obj=category, product_id=category.product.id)
    )
    form.set_ticket_category_choices(party.id)
    form.set_product_choices(shop.id)

    return {
        'party': party,
        'category': category,
        'form': form,
    }


@blueprint.post('/categories/<category_id>')
@permission_required('bungalow.update')
def category_update(category_id):
    """Update the category."""
    category = _get_category_or_404(category_id)

    party = party_service.get_party(category.party_id)

    shop = shop_service.find_shop_for_brand(party.brand_id)
    if shop is None:
        flash_error('Kein Shop für die Marke dieser Party gefunden.')
        return category_update_form(category.id)

    form = CategoryUpdateForm(request.form)
    form.set_ticket_category_choices(category.party_id)
    form.set_product_choices(shop.id)

    if not form.validate():
        return category_update_form(category_id, form)

    title = form.title.data.strip()
    capacity = form.capacity.data
    ticket_category = ticket_category_service.find_category(
        form.ticket_category_id.data
    )
    product = product_service.get_product(form.product_id.data)
    image_filename = form.image_filename.data
    image_width = form.image_width.data
    image_height = form.image_height.data

    category = bungalow_category_service.update_category(
        category.id,
        title,
        capacity,
        ticket_category.id,
        product.id,
        image_filename=image_filename,
        image_width=image_width,
        image_height=image_height,
    )

    flash_success('Die Bungalow-Kategorie wurde aktualisiert.')

    return redirect_to('.categories', party_id=category.party_id)


@blueprint.get('/<party_id>/occupants/export')
@permission_required('bungalow.view')
@textified
def export_occupants(party_id):
    """Export bungalow occupants with realname, bungalow number, and
    main tenant flag.
    """
    party = _get_party_or_404(party_id)

    bungalows = bungalow_occupancy_service.get_occupied_bungalows_for_party(
        party.id
    )

    occupancy_ids = {
        bungalow.occupancy.id for bungalow in bungalows if bungalow.occupancy
    }
    occupant_slots_by_occupancy_id = (
        bungalow_occupancy_service.get_occupant_slots_for_occupancies(
            occupancy_ids, for_admin=True
        )
    )

    rows = [('Bungalow', 'Name', 'Bemerkung')]

    for bungalow in bungalows:
        occupancy = bungalow.occupancy
        occupant_slots = occupant_slots_by_occupancy_id[occupancy.id]
        for occupant_slot in occupant_slots:
            occupant = occupant_slot.occupant
            if occupant:
                full_name = occupant.detail.full_name or 'nicht angegeben'
                remark = (
                    'Hauptmieter/in'
                    if occupancy.manager_id == occupant.id
                    else ''
                )
                rows.append((bungalow.number, full_name, remark))

    return serialize_tuples_to_csv(rows)


@blueprint.get('/<party_id>/occupied_bungalow_numbers_and_titles')
@permission_required('bungalow.view')
@textified
def export_bungalow_numbers_and_titles(party_id):
    """Export numbers and titles of all occupied bungalows for this
    party, one set per line.

    For inclusion in the party flyer.
    """
    party = _get_party_or_404(party_id)

    numbers_and_titles = (
        bungalow_occupancy_service.get_occupied_bungalow_numbers_and_titles(
            party.id
        )
    )

    def generate() -> Iterator[str]:
        for number, title in numbers_and_titles:
            yield f'{number:d} {title}\n'

    return generate()


@blueprint.get('/<party_id>/first_time_attendees')
@permission_required('bungalow.view')
@textified
def export_first_time_attendees(party_id):
    party = _get_party_or_404(party_id)

    first_time_attendees_by_bungalow_number = (
        first_attendance_service.get_first_time_attendees_by_bungalow(party)
    )

    rows = [('Bungalow', 'Anzahl', 'Namen')]

    for bungalow_number, attendees in sorted(
        first_time_attendees_by_bungalow_number.items(),
        key=lambda item: item[0],
    ):
        attendee_count = len(attendees)
        joined_screen_names = ', '.join(
            attendee.screen_name for attendee in attendees
        )
        rows.append((bungalow_number, attendee_count, joined_screen_names))

    return serialize_tuples_to_csv(rows)


# -------------------------------------------------------------------- #


def _get_brand_or_404(brand_id: BrandID) -> Brand:
    brand = brand_service.find_brand(brand_id)

    if brand is None:
        abort(404)

    has_bungalows = bungalow_service.has_brand_bungalows(brand.id)
    if not has_bungalows:
        abort(404)

    return brand


def _get_bungalow_or_404(bungalow_id: BungalowID) -> Bungalow:
    bungalow = bungalow_service.find_bungalow(bungalow_id)

    if bungalow is None:
        abort(404)

    return bungalow


def _get_occupancy_or_404(occupancy_id: OccupancyID) -> BungalowOccupancy:
    occupancy = bungalow_occupancy_service.find_occupancy(occupancy_id)

    if occupancy is None:
        abort(404)

    return occupancy


def _get_category_or_404(category_id: BungalowCategoryID) -> BungalowCategory:
    category = bungalow_category_service.find_category(category_id)

    if category is None:
        abort(404)

    return category


def _get_party_or_404(party_id: PartyID) -> Party:
    party = party_service.find_party(party_id)

    if party is None:
        abort(404)

    has_bungalows = bungalow_service.has_brand_bungalows(party.brand_id)
    if not has_bungalows:
        abort(404)

    return party

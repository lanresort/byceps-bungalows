"""
byceps.blueprints.admin.bungalow.forms
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2024 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from flask_babel import lazy_gettext
from wtforms import (
    IntegerField,
    RadioField,
    SelectField,
    SelectMultipleField,
    StringField,
)
from wtforms.validators import InputRequired, Length, Optional

from byceps.services.bungalow import bungalow_service
from byceps.services.bungalow.dbmodels.bungalow import DbBungalow
from byceps.services.party.models import PartyID
from byceps.services.shop.product import product_service
from byceps.services.shop.shop.models import ShopID
from byceps.services.ticketing import ticket_category_service
from byceps.util.forms import UserScreenNameField
from byceps.util.l10n import LocalizedForm


class BuildingCreateForm(LocalizedForm):
    layout_id = SelectField('Typ', validators=[InputRequired()])
    number = IntegerField('Nummer', validators=[InputRequired()])

    def set_layout_choices(self, layouts):
        def generate():
            for layout in sorted(
                layouts, key=lambda lo: (lo.title, lo.capacity)
            ):
                label = f'{layout.title}, {layout.capacity:d} Plätze'
                yield str(layout.id), label

        choices = list(generate())
        choices.insert(0, ('', '<' + lazy_gettext('choose') + '>'))
        self.layout_id.choices = choices


class _CategoryBaseForm(LocalizedForm):
    title = StringField(lazy_gettext('Title'), validators=[InputRequired()])
    capacity = IntegerField('Kapazität', validators=[InputRequired()])
    ticket_category_id = SelectField(
        lazy_gettext('Ticket category'), validators=[InputRequired()]
    )
    product_id = SelectField(
        lazy_gettext('Product'), validators=[InputRequired()]
    )
    image_filename = StringField('Bild-Dateiname', validators=[Optional()])
    image_width = IntegerField('Bildbreite', validators=[Optional()])
    image_height = IntegerField('Bildhöhe', validators=[Optional()])

    def set_ticket_category_choices(self, party_id: PartyID) -> None:
        choices = [
            (str(category.id), category.title)
            for category in ticket_category_service.get_categories_for_party(
                party_id
            )
        ]
        choices.sort(key=lambda choice: choice[1])
        choices.insert(0, ('', '<' + lazy_gettext('choose') + '>'))
        self.ticket_category_id.choices = choices

    def set_product_choices(self, shop_id: ShopID):
        choices = [
            (str(product.id), f'{product.item_number} – {product.name}')
            for product in product_service.get_products_for_shop(shop_id)
            if not product.archived
        ]
        choices.insert(0, ('', '<' + lazy_gettext('choose') + '>'))
        self.product_id.choices = choices


class CategoryCreateForm(_CategoryBaseForm):
    pass


class CategoryUpdateForm(_CategoryBaseForm):
    pass


class OfferCreateForm(LocalizedForm):
    building_ids = SelectMultipleField('Gebäude', validators=[InputRequired()])
    bungalow_category_id = SelectField(
        'Bungalow-Kategorie', validators=[InputRequired()]
    )

    def set_building_choices(self, buildings):
        def generate():
            for building in buildings:
                label = (
                    f'{building.number:d} '
                    f'({building.layout.title}, '
                    f'{building.layout.capacity:d} Plätze)'
                )
                yield str(building.id), label

        self.building_ids.choices = list(generate())

    def set_bungalow_category_choices(self, categories):
        def generate():
            for category in categories:
                label = f'{category.title}, {category.capacity:d} Plätze'
                yield str(category.id), label

        choices = list(generate())
        choices.insert(0, ('', '<' + lazy_gettext('choose') + '>'))
        self.bungalow_category_id.choices = choices


class InternalRemarkUpdateForm(LocalizedForm):
    internal_remark = StringField('Anmerkung', [Optional(), Length(max=200)])


class AppointManagerForm(LocalizedForm):
    manager = UserScreenNameField(lazy_gettext('Username'), [InputRequired()])


class OccupancyMoveForm(LocalizedForm):
    target_bungalow_id = RadioField(
        lazy_gettext('Ziel-Bungalow'), validators=[InputRequired()]
    )

    def set_target_bungalow_choices(self, source_bungalow: DbBungalow) -> None:
        self.target_bungalow_id.choices = [
            (str(bungalow.id), bungalow.number)
            for bungalow in _get_occupancy_move_target_bungalows(
                source_bungalow
            )
        ]


def _get_occupancy_move_target_bungalows(
    source_bungalow: DbBungalow,
) -> list[DbBungalow]:
    party_bungalows = bungalow_service.get_bungalows_for_party(
        source_bungalow.party_id
    )
    return [
        bungalow
        for bungalow in party_bungalows
        if bungalow.available
        and bungalow.id != source_bungalow.id
        and bungalow.category_id == source_bungalow.category_id
    ]

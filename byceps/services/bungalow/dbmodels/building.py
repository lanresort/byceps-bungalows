"""
byceps.services.bungalow.dbmodels.building
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from byceps.database import db
from byceps.services.bungalow.models.building import BungalowLayout
from byceps.util.instances import ReprBuilder
from byceps.util.uuid import generate_uuid4

from .layout import DbBungalowLayout


class DbBungalowBuilding(db.Model):
    """A specific bungalow without party-specific attributes."""

    __tablename__ = 'bungalow_buildings'
    __table_args__ = (db.UniqueConstraint('brand_id', 'number'),)

    id = db.Column(db.Uuid, default=generate_uuid4, primary_key=True)
    brand_id = db.Column(
        db.UnicodeText, db.ForeignKey('brands.id'), index=True, nullable=False
    )
    layout_id = db.Column(
        db.Uuid,
        db.ForeignKey('bungalow_layouts.id'),
        index=True,
        nullable=False,
    )
    layout = db.relationship(DbBungalowLayout)
    number = db.Column(db.SmallInteger, index=True, nullable=False)

    def __init__(self, layout: BungalowLayout, number: int) -> None:
        self.brand_id = layout.brand_id
        self.layout_id = layout.id
        self.number = number

    def __repr__(self) -> str:
        return (
            ReprBuilder(self)
            .add_with_lookup('brand_id')
            .add_with_lookup('layout')
            .add_with_lookup('number')
            .build()
        )

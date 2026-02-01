"""
byceps.services.bungalow.dbmodels.building
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from sqlalchemy.orm import Mapped, mapped_column, relationship

from byceps.database import db
from byceps.services.brand.models import BrandID
from byceps.services.bungalow.models.building import (
    BungalowBuildingID,
    BungalowLayout,
    BungalowLayoutID,
)
from byceps.util.instances import ReprBuilder

from .layout import DbBungalowLayout


class DbBungalowBuilding(db.Model):
    """A specific bungalow without party-specific attributes."""

    __tablename__ = 'bungalow_buildings'
    __table_args__ = (db.UniqueConstraint('brand_id', 'number'),)

    id: Mapped[BungalowBuildingID] = mapped_column(primary_key=True)
    brand_id: Mapped[BrandID] = mapped_column(
        db.UnicodeText, db.ForeignKey('brands.id'), index=True
    )
    layout_id: Mapped[BungalowLayoutID] = mapped_column(
        db.ForeignKey('bungalow_layouts.id'), index=True
    )
    layout: Mapped[DbBungalowLayout] = relationship()
    number: Mapped[int] = mapped_column(db.SmallInteger, index=True)

    def __init__(
        self,
        building_id: BungalowBuildingID,
        layout: BungalowLayout,
        number: int,
    ) -> None:
        self.id = building_id
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

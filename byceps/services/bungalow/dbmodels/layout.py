"""
byceps.services.bungalow.dbmodels.layout
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from __future__ import annotations

from byceps.database import db
from byceps.services.brand.models import BrandID
from byceps.services.bungalow.models.building import BungalowLayoutID
from byceps.util.instances import ReprBuilder


class DbBungalowLayout(db.Model):
    """A bungalow layout/floor plan."""

    __tablename__ = 'bungalow_layouts'
    __table_args__ = (db.UniqueConstraint('brand_id', 'title', 'capacity'),)

    id = db.Column(db.Uuid, primary_key=True)
    brand_id = db.Column(
        db.UnicodeText, db.ForeignKey('brands.id'), index=True, nullable=False
    )
    title = db.Column(db.UnicodeText, nullable=False)
    capacity = db.Column(db.SmallInteger, nullable=False)
    image_filename = db.Column(db.UnicodeText, nullable=True)
    image_width = db.Column(db.SmallInteger, nullable=True)
    image_height = db.Column(db.SmallInteger, nullable=True)

    def __init__(
        self,
        layout_id: BungalowLayoutID,
        brand_id: BrandID,
        title: str,
        capacity: int,
        *,
        image_filename: str | None = None,
        image_width: int | None = None,
        image_height: int | None = None,
    ) -> None:
        self.id = layout_id
        self.brand_id = brand_id
        self.title = title
        self.capacity = capacity
        self.image_filename = image_filename
        self.image_width = image_width
        self.image_height = image_height

    def __repr__(self) -> str:
        return (
            ReprBuilder(self)
            .add_with_lookup('brand_id')
            .add_with_lookup('title')
            .add_with_lookup('capacity')
            .build()
        )

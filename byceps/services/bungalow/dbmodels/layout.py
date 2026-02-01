"""
byceps.services.bungalow.dbmodels.layout
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from __future__ import annotations

from sqlalchemy.orm import Mapped, mapped_column

from byceps.database import db
from byceps.services.brand.models import BrandID
from byceps.services.bungalow.models.building import BungalowLayoutID
from byceps.util.instances import ReprBuilder


class DbBungalowLayout(db.Model):
    """A bungalow layout/floor plan."""

    __tablename__ = 'bungalow_layouts'
    __table_args__ = (db.UniqueConstraint('brand_id', 'title', 'capacity'),)

    id: Mapped[BungalowLayoutID] = mapped_column(primary_key=True)
    brand_id: Mapped[BrandID] = mapped_column(
        db.UnicodeText, db.ForeignKey('brands.id'), index=True
    )
    title: Mapped[str] = mapped_column(db.UnicodeText)
    capacity: Mapped[int] = mapped_column(db.SmallInteger)
    image_filename: Mapped[str | None] = mapped_column(db.UnicodeText)
    image_width: Mapped[int | None] = mapped_column(db.SmallInteger)
    image_height: Mapped[int | None] = mapped_column(db.SmallInteger)

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

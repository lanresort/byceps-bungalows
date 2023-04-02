"""
byceps.services.bungalow.dbmodels.layout
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2023 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from typing import Optional

from ....database import db, generate_uuid4
from ....typing import BrandID
from ....util.instances import ReprBuilder


class DbBungalowLayout(db.Model):
    """A bungalow layout/floor plan."""

    __tablename__ = 'bungalow_layouts'
    __table_args__ = (db.UniqueConstraint('brand_id', 'title', 'capacity'),)

    id = db.Column(db.Uuid, default=generate_uuid4, primary_key=True)
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
        brand_id: BrandID,
        title: str,
        capacity: int,
        *,
        image_filename: Optional[str] = None,
        image_width: Optional[int] = None,
        image_height: Optional[int] = None,
    ) -> None:
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

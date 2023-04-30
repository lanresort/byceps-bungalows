"""
byceps.services.bungalow.bungalow_building_service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2023 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from typing import Optional

from sqlalchemy import delete, select

from byceps.database import db
from byceps.typing import BrandID

from .dbmodels.building import DbBungalowBuilding
from .dbmodels.layout import DbBungalowLayout
from .models.building import (
    BungalowBuilding,
    BungalowBuildingID,
    BungalowLayout,
    BungalowLayoutID,
)


# -------------------------------------------------------------------- #
# layout


def create_layout(
    brand_id: BrandID,
    title: str,
    capacity: int,
    *,
    image_filename: Optional[str] = None,
    image_width: Optional[int] = None,
    image_height: Optional[int] = None,
) -> BungalowLayout:
    """Create a layout."""
    db_layout = DbBungalowLayout(
        brand_id,
        title,
        capacity,
        image_filename=image_filename,
        image_width=image_width,
        image_height=image_height,
    )

    db.session.add(db_layout)
    db.session.commit()

    return _db_entity_to_layout(db_layout)


def delete_layout(layout_id: BungalowLayoutID):
    """Delete the layout."""
    db.session.execute(delete(DbBungalowLayout).filter_by(id=layout_id))
    db.session.commit()


def find_layout(layout_id: BungalowLayoutID) -> Optional[BungalowLayout]:
    """Return the layout with that id, or `None` if not found."""
    db_layout = db.session.get(DbBungalowLayout, layout_id)

    if db_layout is None:
        return None

    return _db_entity_to_layout(db_layout)


def get_layouts(brand_id: BrandID) -> list[BungalowLayout]:
    """Return all layouts for that brand."""
    db_layouts = db.session.scalars(
        select(DbBungalowLayout).filter_by(brand_id=brand_id)
    ).all()

    return [_db_entity_to_layout(db_layout) for db_layout in db_layouts]


def _db_entity_to_layout(db_layout: DbBungalowLayout) -> BungalowLayout:
    return BungalowLayout(
        id=db_layout.id,
        brand_id=db_layout.brand_id,
        title=db_layout.title,
        capacity=db_layout.capacity,
        image_filename=db_layout.image_filename,
        image_width=db_layout.image_width,
        image_height=db_layout.image_height,
    )


# -------------------------------------------------------------------- #
# building


def create_building(layout: BungalowLayout, number: int) -> BungalowBuilding:
    """Create a building."""
    db_building = DbBungalowBuilding(layout, number)

    db.session.add(db_building)
    db.session.commit()

    return _db_entity_to_building(db_building)


def delete_building(building_id: BungalowBuildingID):
    """Delete the building."""
    db.session.execute(delete(DbBungalowBuilding).filter_by(id=building_id))
    db.session.commit()


def get_buildings(brand_id: BrandID) -> list[BungalowBuilding]:
    """Return all buildings for that brand, ordered by number."""
    db_buildings = db.session.scalars(
        select(DbBungalowBuilding)
        .filter_by(brand_id=brand_id)
        .order_by(DbBungalowBuilding.number)
    ).all()

    return [_db_entity_to_building(db_building) for db_building in db_buildings]


def get_buildings_for_ids(
    brand_id: BrandID, building_ids: set[BungalowBuildingID]
) -> list[BungalowBuilding]:
    """Return the buildings with the given IDs, ordered by number."""
    if not building_ids:
        raise ValueError('No building IDs given.')

    db_buildings = db.session.scalars(
        select(DbBungalowBuilding)
        .filter_by(brand_id=brand_id)
        .filter(DbBungalowBuilding.id.in_(building_ids))
        .order_by(DbBungalowBuilding.number)
    ).all()

    return [_db_entity_to_building(db_building) for db_building in db_buildings]


def _db_entity_to_building(db_building: DbBungalowBuilding) -> BungalowBuilding:
    layout = _db_entity_to_layout(db_building.layout)

    return BungalowBuilding(
        id=db_building.id,
        brand_id=db_building.brand_id,
        layout=layout,
        number=db_building.number,
    )

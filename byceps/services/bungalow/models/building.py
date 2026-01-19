"""
byceps.services.bungalow.models.building
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import NewType
from uuid import UUID

from byceps.services.brand.models import BrandID


BungalowLayoutID = NewType('BungalowLayoutID', UUID)


@dataclass(frozen=True, kw_only=True)
class BungalowLayout:
    id: BungalowLayoutID
    brand_id: BrandID
    title: str
    capacity: int
    image_filename: str | None
    image_width: int | None
    image_height: int | None


BungalowBuildingID = NewType('BungalowBuildingID', UUID)


@dataclass(frozen=True, kw_only=True)
class BungalowBuilding:
    id: BungalowBuildingID
    brand_id: BrandID
    layout: BungalowLayout
    number: int

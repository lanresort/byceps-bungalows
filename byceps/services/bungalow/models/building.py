"""
byceps.services.bungalow.models.building
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2023 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from dataclasses import dataclass
from typing import NewType, Optional
from uuid import UUID

from ....typing import BrandID


BungalowLayoutID = NewType('BungalowLayoutID', UUID)


@dataclass(frozen=True)
class BungalowLayout:
    id: BungalowLayoutID
    brand_id: BrandID
    title: str
    capacity: int
    image_filename: Optional[str]
    image_width: Optional[int]
    image_height: Optional[int]


BungalowBuildingID = NewType('BungalowBuildingID', UUID)


@dataclass(frozen=True)
class BungalowBuilding:
    id: BungalowBuildingID
    brand_id: BrandID
    layout: BungalowLayout
    number: int

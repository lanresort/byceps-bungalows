"""
byceps.services.bungalow.bungalow_occupancy_avatar_service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2023 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from typing import BinaryIO

from byceps.database import db
from byceps.services.image import image_service
from byceps.typing import UserID
from byceps.util import upload
from byceps.util.image import create_thumbnail
from byceps.util.image.models import Dimensions, ImageType
from byceps.util.result import Err, Ok, Result

from . import bungalow_occupancy_service
from .dbmodels.avatar import DbBungalowAvatar
from .models.occupation import OccupancyID


ALLOWED_IMAGE_TYPES = {
    ImageType.jpeg,
    ImageType.png,
}


MAXIMUM_DIMENSIONS = Dimensions(512, 512)


def get_allowed_image_types() -> set[ImageType]:
    """Return the allowed image types."""
    return ALLOWED_IMAGE_TYPES


def update_avatar_image(
    occupancy_id: OccupancyID,
    creator_id: UserID,
    stream: BinaryIO,
    *,
    allowed_types: set[ImageType] = ALLOWED_IMAGE_TYPES,
    maximum_dimensions: Dimensions = MAXIMUM_DIMENSIONS,
) -> Result[None, str]:
    """Set a new avatar image for the bungalow occupancy."""
    db_occupancy = bungalow_occupancy_service.get_db_occupancy(
        occupancy_id
    ).unwrap()

    image_type_result = image_service.determine_image_type(
        stream, allowed_types
    )
    if image_type_result.is_err():
        return Err(image_type_result.unwrap_err())

    image_type = image_type_result.unwrap()
    image_dimensions = image_service.determine_dimensions(stream)

    image_too_large = image_dimensions > maximum_dimensions
    if image_too_large or not image_dimensions.is_square:
        stream = create_thumbnail(stream, image_type.name, maximum_dimensions)

    avatar = DbBungalowAvatar(creator_id, image_type)
    db.session.add(avatar)
    db.session.commit()

    party_id = db_occupancy.bungalow.party_id
    avatar_path = avatar.get_path(party_id)

    # Create parent path if it doesn't exist.
    parent_path = avatar_path.resolve().parent
    if not parent_path.exists():
        parent_path.mkdir(parents=True)

    # Might raise `FileExistsError`.
    upload.store(stream, avatar_path)

    db_occupancy.avatar_id = avatar.id
    db.session.commit()

    return Ok(None)


def remove_avatar_image(occupancy_id: OccupancyID) -> None:
    """Remove the bungalow occupancy's avatar image.

    The avatar will be unlinked from the bungalow, but the database record
    as well as the image file itself won't be removed, though.
    """
    db_occupancy = bungalow_occupancy_service.get_db_occupancy(
        occupancy_id
    ).unwrap()

    db_occupancy.avatar_id = None
    db.session.commit()

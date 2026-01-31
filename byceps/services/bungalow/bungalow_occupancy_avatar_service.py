"""
byceps.services.bungalow.bungalow_occupancy_avatar_service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from typing import BinaryIO

from byceps.services.user.models import UserID
from byceps.util import upload
from byceps.util.image.dimensions import determine_dimensions, Dimensions
from byceps.util.image.image_type import determine_image_type, ImageType
from byceps.util.image.thumbnail import create_thumbnail
from byceps.util.result import Err, Ok, Result
from byceps.util.uuid import generate_uuid7

from . import bungalow_occupancy_repository
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
    db_occupancy = bungalow_occupancy_repository.get_occupancy(
        occupancy_id
    ).unwrap()

    avatar_id = generate_uuid7()

    match determine_image_type(stream, allowed_types):
        case Ok(image_type):
            pass
        case Err(image_determination_error):
            return Err(image_determination_error)

    image_dimensions = determine_dimensions(stream)

    image_too_large = image_dimensions > maximum_dimensions
    if image_too_large or not image_dimensions.is_square:
        stream = create_thumbnail(stream, image_type.name, maximum_dimensions)

    db_avatar = bungalow_occupancy_repository.create_avatar_image(
        avatar_id, creator_id, image_type
    )

    party_id = db_occupancy.bungalow.party_id
    avatar_path = db_avatar.get_path(party_id)

    # Create parent path if it doesn't exist.
    parent_path = avatar_path.resolve().parent
    if not parent_path.exists():
        parent_path.mkdir(parents=True)

    # Might raise `FileExistsError`.
    upload.store(stream, avatar_path)

    return bungalow_occupancy_repository.assign_avatar_image(
        db_avatar.id, db_occupancy.id
    )


def remove_avatar_image(occupancy_id: OccupancyID) -> None:
    """Remove the bungalow occupancy's avatar image.

    The avatar will be unlinked from the bungalow, but the database record
    as well as the image file itself won't be removed, though.
    """
    bungalow_occupancy_repository.remove_avatar_image(occupancy_id).unwrap()

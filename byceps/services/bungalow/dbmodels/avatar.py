"""
byceps.services.bungalow.dbmodels.avatar
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2023 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from flask import current_app

if TYPE_CHECKING:
    hybrid_property = property
else:
    from sqlalchemy.ext.hybrid import hybrid_property

from ....database import db, generate_uuid7
from ....typing import PartyID, UserID
from ....util.image.models import ImageType
from ....util.instances import ReprBuilder


class DbBungalowAvatar(db.Model):
    """A user-provided avatar image for a bungalow occupancy."""

    __tablename__ = 'bungalow_occupancy_avatars'

    id = db.Column(db.Uuid, default=generate_uuid7, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    creator_id = db.Column(db.Uuid, db.ForeignKey('users.id'), nullable=False)
    _image_type = db.Column('image_type', db.UnicodeText, nullable=False)

    def __init__(self, creator_id: UserID, image_type: ImageType) -> None:
        self.creator_id = creator_id
        self.image_type = image_type

    @hybrid_property
    def image_type(self) -> ImageType:
        image_type_str = self._image_type
        if image_type_str is not None:
            return ImageType[image_type_str]

    @image_type.setter
    def image_type(self, image_type: ImageType) -> None:
        self._image_type = image_type.name if (image_type is not None) else None

    @property
    def filename(self) -> Path:
        name_without_suffix = str(self.id)
        suffix = '.' + self.image_type.name
        return Path(name_without_suffix).with_suffix(suffix)

    def get_path(self, party_id: PartyID) -> Path:
        path_data = current_app.config['PATH_DATA']
        path = path_data / 'parties' / party_id / 'bungalow-avatars'
        return path / self.filename

    def get_url(self, party_id: PartyID) -> str:
        return f'/data/parties/{party_id}/bungalow-avatars/{self.filename}'

    def __repr__(self) -> str:
        return (
            ReprBuilder(self)
            .add_with_lookup('id')
            .add('image_type', self.image_type.name)
            .build()
        )

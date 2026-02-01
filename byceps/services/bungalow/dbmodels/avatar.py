"""
byceps.services.bungalow.dbmodels.avatar
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.orm import Mapped, mapped_column

if TYPE_CHECKING:
    hybrid_property = property
else:
    from sqlalchemy.ext.hybrid import hybrid_property

from byceps.byceps_app import get_current_byceps_app
from byceps.database import db
from byceps.services.party.models import PartyID
from byceps.services.user.models import UserID
from byceps.util.image.image_type import ImageType
from byceps.util.instances import ReprBuilder


class DbBungalowAvatar(db.Model):
    """A user-provided avatar image for a bungalow occupancy."""

    __tablename__ = 'bungalow_occupancy_avatars'

    id: Mapped[UUID] = mapped_column(primary_key=True)
    created_at: Mapped[datetime]
    creator_id: Mapped[UserID] = mapped_column(db.ForeignKey('users.id'))
    _image_type: Mapped[str] = mapped_column('image_type', db.UnicodeText)

    def __init__(
        self,
        avatar_id: UUID,
        created_at: datetime,
        creator_id: UserID,
        image_type: ImageType,
    ) -> None:
        self.id = avatar_id
        self.created_at = created_at
        self.creator_id = creator_id
        self.image_type = image_type

    @hybrid_property
    def image_type(self) -> ImageType:
        return ImageType[self._image_type]

    @image_type.setter
    def image_type(self, image_type: ImageType) -> None:
        self._image_type = image_type.name

    @property
    def filename(self) -> Path:
        name_without_suffix = str(self.id)
        suffix = '.' + self.image_type.name
        return Path(name_without_suffix).with_suffix(suffix)

    def get_path(self, party_id: PartyID) -> Path:
        path_data = get_current_byceps_app().byceps_config.data_path
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

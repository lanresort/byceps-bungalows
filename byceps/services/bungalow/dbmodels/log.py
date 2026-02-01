"""
byceps.services.bungalow.dbmodels.log
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Mapped, mapped_column

from byceps.database import db
from byceps.services.bungalow.models.bungalow import BungalowID
from byceps.services.bungalow.models.log import BungalowLogEntryData
from byceps.util.instances import ReprBuilder


class DbBungalowLogEntry(db.Model):
    """A log entry regarding a bungalow."""

    __tablename__ = 'bungalow_log_entries'

    id: Mapped[UUID] = mapped_column(primary_key=True)
    occurred_at: Mapped[datetime]
    event_type: Mapped[str] = mapped_column(db.UnicodeText, index=True)
    bungalow_id: Mapped[BungalowID] = mapped_column(
        db.ForeignKey('bungalows.id'), index=True
    )
    data: Mapped[BungalowLogEntryData] = mapped_column(db.JSONB)

    def __init__(
        self,
        entry_id: UUID,
        occurred_at: datetime,
        event_type: str,
        bungalow_id: BungalowID,
        data: BungalowLogEntryData,
    ) -> None:
        self.id = entry_id
        self.occurred_at = occurred_at
        self.event_type = event_type
        self.bungalow_id = bungalow_id
        self.data = data

    def __repr__(self) -> str:
        return (
            ReprBuilder(self)
            .add_custom(repr(self.event_type))
            .add_with_lookup('bungalow_id')
            .add_with_lookup('data')
            .build()
        )

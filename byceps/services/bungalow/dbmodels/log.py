"""
byceps.services.bungalow.dbmodels.log
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2023 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from datetime import datetime

from ....database import db, generate_uuid7
from ....util.instances import ReprBuilder

from ..models.bungalow import BungalowID
from ..models.log import BungalowLogEntryData


class DbBungalowLogEntry(db.Model):
    """A log entry regarding a bungalow."""

    __tablename__ = 'bungalow_log_entries'

    id = db.Column(db.Uuid, default=generate_uuid7, primary_key=True)
    occurred_at = db.Column(db.DateTime, nullable=False)
    event_type = db.Column(db.UnicodeText, index=True, nullable=False)
    bungalow_id = db.Column(
        db.Uuid, db.ForeignKey('bungalows.id'), index=True, nullable=False
    )
    data = db.Column(db.JSONB)

    def __init__(
        self,
        occurred_at: datetime,
        event_type: str,
        bungalow_id: BungalowID,
        data: BungalowLogEntryData,
    ) -> None:
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

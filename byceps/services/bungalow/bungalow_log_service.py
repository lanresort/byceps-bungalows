"""
byceps.services.bungalow.bungalow_log_service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from byceps.database import db
from byceps.util.uuid import generate_uuid7

from .dbmodels.log import DbBungalowLogEntry
from .models.bungalow import BungalowID
from .models.log import BungalowLogEntry, BungalowLogEntryData


def create_entry(
    event_type: str,
    bungalow_id: BungalowID,
    data: BungalowLogEntryData,
    *,
    occurred_at: datetime | None = None,
) -> None:
    """Create a bungalow log entry."""
    db_entry = build_entry(
        event_type, bungalow_id, data, occurred_at=occurred_at
    )

    db.session.add(db_entry)
    db.session.commit()


def build_entry(
    event_type: str,
    bungalow_id: BungalowID,
    data: BungalowLogEntryData,
    *,
    occurred_at: datetime | None = None,
) -> DbBungalowLogEntry:
    """Assemble, but not persist, a bungalow log entry."""
    entry_id = generate_uuid7()

    if occurred_at is None:
        occurred_at = datetime.utcnow()

    return DbBungalowLogEntry(
        entry_id, occurred_at, event_type, bungalow_id, data
    )


def get_entries_for_bungalow(bungalow_id: BungalowID) -> list[BungalowLogEntry]:
    """Return the log entries for that bungalow."""
    db_entries = db.session.scalars(
        select(DbBungalowLogEntry)
        .filter_by(bungalow_id=bungalow_id)
        .order_by(DbBungalowLogEntry.occurred_at)
    ).all()

    return [_db_entity_to_entry(db_entry) for db_entry in db_entries]


def get_entries_of_type_for_bungalow(
    bungalow_id: BungalowID, event_type: str
) -> list[BungalowLogEntry]:
    """Return the log entries of that type for that bungalow."""
    db_entries = db.session.scalars(
        select(DbBungalowLogEntry)
        .filter_by(bungalow_id=bungalow_id)
        .filter_by(event_type=event_type)
        .order_by(DbBungalowLogEntry.occurred_at)
    ).all()

    return [_db_entity_to_entry(db_entry) for db_entry in db_entries]


def _db_entity_to_entry(db_entry: DbBungalowLogEntry) -> BungalowLogEntry:
    return BungalowLogEntry(
        id=db_entry.id,
        occurred_at=db_entry.occurred_at,
        event_type=db_entry.event_type,
        bungalow_id=db_entry.bungalow_id,
        data=db_entry.data.copy(),
    )

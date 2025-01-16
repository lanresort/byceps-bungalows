"""
byceps.services.bungalow.models.log
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2025 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from .bungalow import BungalowID


BungalowLogEntryData = dict[str, Any]


@dataclass(frozen=True)
class BungalowLogEntry:
    id: UUID
    occurred_at: datetime
    event_type: str
    bungalow_id: BungalowID
    data: BungalowLogEntryData

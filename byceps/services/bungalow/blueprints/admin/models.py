"""
byceps.services.bungalow.blueprints.admin.models
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from dataclasses import dataclass
from datetime import datetime

from byceps.services.bungalow.models.bungalow import BungalowID
from byceps.services.ticketing.models.ticket import (
    TicketBundleID,
    TicketCategory,
)
from byceps.services.user.models import User


@dataclass(frozen=True, kw_only=True)
class BungalowTicketBundle:
    ticket_bundle_id: TicketBundleID
    created_at: datetime
    ticket_category: TicketCategory
    ticket_quantity: int
    ticket_bundle_owner: User
    bungalow_id: BungalowID | None
    bungalow_number: int | None

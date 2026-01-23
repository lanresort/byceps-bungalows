"""
byceps.services.bungalow.blueprints.admin.service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from collections.abc import Iterator
from typing import Any

from byceps.services.bungalow import bungalow_log_service
from byceps.services.bungalow.models.bungalow import BungalowID
from byceps.services.bungalow.models.log import (
    BungalowLogEntry,
    BungalowLogEntryData,
)
from byceps.services.user import user_service
from byceps.services.user.models import User


def get_log_entries(bungalow_id: BungalowID) -> Iterator[BungalowLogEntryData]:
    log_entries = bungalow_log_service.get_entries_for_bungalow(bungalow_id)

    user_ids = {
        entry.data['initiator_id']
        for entry in log_entries
        if 'initiator_id' in entry.data
    }
    users = user_service.get_users(user_ids, include_avatars=True)
    users_by_id = {str(user.id): user for user in users}

    for entry in log_entries:
        data = {
            'event_type': entry.event_type,
            'occurred_at': entry.occurred_at,
            'data': entry.data,
        }

        additional_data = _get_additional_data(entry, users_by_id)
        data.update(additional_data)

        yield data


def _get_additional_data(
    log_entry: BungalowLogEntry, users_by_id: dict[str, User]
) -> Iterator[tuple[str, Any]]:
    if log_entry.event_type in {
        'bungalow-occupied',
        'bungalow-released',
        'bungalow-reserved',
        'manager-appointed',
        'occupancy-moved-away',
        'occupancy-moved-here',
    }:
        yield from _get_additional_data_for_user_initiated_log_entry(
            log_entry, users_by_id
        )

    if log_entry.event_type == 'manager-appointed':
        new_manager = user_service.get_user(log_entry.data['new_manager_id'])
        yield 'new_manager', new_manager


def _get_additional_data_for_user_initiated_log_entry(
    log_entry: BungalowLogEntry, users_by_id: dict[str, User]
) -> Iterator[tuple[str, Any]]:
    initiator_id = log_entry.data.get('initiator_id')
    if initiator_id is not None:
        yield 'initiator', users_by_id[initiator_id]

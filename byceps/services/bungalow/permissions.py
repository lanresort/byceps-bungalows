"""
byceps.services.bungalow.permissions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2025 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from flask_babel import lazy_gettext

from byceps.util.authz import register_permissions


register_permissions(
    'bungalow',
    [
        ('update', lazy_gettext('Bungalows bearbeiten')),
        ('view', lazy_gettext('Bungalows anzeigen')),
    ],
)


register_permissions(
    'bungalow_building',
    [
        ('create', lazy_gettext('Bungalow-Gebäude erstellen')),
    ],
)


register_permissions(
    'bungalow_offer',
    [
        ('create', lazy_gettext('Bungalow-Angebote erstellen')),
        ('delete', lazy_gettext('Bungalow-Angebote löschen')),
    ],
)

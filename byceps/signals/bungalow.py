"""
byceps.signals.bungalow
~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2025 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from blinker import Namespace


bungalow_signals = Namespace()


bungalow_reserved = bungalow_signals.signal('bungalow-reserved')
bungalow_occupied = bungalow_signals.signal('bungalow-occupied')
bungalow_released = bungalow_signals.signal('bungalow-released')
occupancy_moved = bungalow_signals.signal('occupancy-moved')
avatar_updated = bungalow_signals.signal('avatar-updated')
description_updated = bungalow_signals.signal('description-updated')
occupant_added = bungalow_signals.signal('occupant-added')
occupant_removed = bungalow_signals.signal('occupant-removed')

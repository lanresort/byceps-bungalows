"""
byceps.services.bungalow.errors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class BungalowOrderingError:
    pass


@dataclass(frozen=True)
class ProductTypeUnexpectedError(BungalowOrderingError):
    pass


@dataclass(frozen=True)
class ProductBelongsToDifferentShopError(BungalowOrderingError):
    pass


@dataclass(frozen=True)
class ProductUnavailableError(BungalowOrderingError):
    pass


@dataclass(frozen=True)
class StorefrontClosedError(BungalowOrderingError):
    pass

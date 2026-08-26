"""Backward compatibility shim for Onshape client.

This file provides backward compatibility by importing from the new
connectors/onshape/client.py module. New code should import directly
from connectors.onshape.client instead.

DEPRECATED: Import from connectors.onshape.client instead.
"""

from connectors.onshape.client import OnshapeAPIError, OAuthTokenStore, OnshapeClient

__all__ = ["OnshapeAPIError", "OAuthTokenStore", "OnshapeClient"]
"""Unique identifier generator for protocol-specific network identifiers.

Re-exports from protocol_engines for backwards compatibility.
Canonical implementation lives in app.protocol_engines.unique_identifier_generator.
"""

from app.protocol_engines.unique_identifier_generator import (  # noqa: F401
    UniqueIdentifierGenerator,
)

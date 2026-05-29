# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Fingerprint validation service.

Validates vendor fingerprints for consistency between supported_protocols
declarations and actual identity data. Ensures fingerprints are well-formed
and follow protocol-vendor affinities.
"""

import logging
from typing import Any

from app.protocol_engines.protocols import (
    PROTOCOL_TO_IDENTITY_KEY,
    validate_protocol_vendor_affinity,
)

logger = logging.getLogger(__name__)


class FingerprintValidationError:
    """A fingerprint validation error or warning."""

    def __init__(
        self,
        message: str,
        level: str = "error",  # "error" or "warning"
        field: str | None = None,
    ):
        self.message = message
        self.level = level
        self.field = field

    def __str__(self) -> str:
        prefix = f"[{self.level.upper()}]"
        if self.field:
            return f"{prefix} {self.field}: {self.message}"
        return f"{prefix} {self.message}"


class FingerprintValidator:
    """Validate fingerprint consistency between protocols and identities.

    Validation Rules:
    1. Identity must exist for each supported protocol
    2. Warn if identity exists without protocol declaration
    3. Vendor-protocol affinity warnings
    4. Required fields in identities
    """

    @classmethod
    def validate(
        cls,
        fingerprint: dict[str, Any],
        strict: bool = False,
    ) -> list[FingerprintValidationError]:
        """Validate a fingerprint for consistency.

        Args:
            fingerprint: Vendor fingerprint dictionary
            strict: If True, treat warnings as errors

        Returns:
            List of validation errors/warnings
        """
        errors: list[FingerprintValidationError] = []

        # Get basic fingerprint info
        vendor = fingerprint.get("vendor", "")
        fingerprint.get("model", "")
        supported = fingerprint.get("supported_protocols", [])

        # Rule 1: Identity must exist for each supported protocol
        errors.extend(cls._validate_identities_exist(fingerprint, supported))

        # Rule 2: Warn if identity exists without protocol declaration
        errors.extend(cls._validate_no_orphan_identities(fingerprint, supported))

        # Rule 3: Vendor-protocol affinity warnings
        if vendor and supported:
            affinity_warnings = validate_protocol_vendor_affinity(vendor, supported)
            for warning_msg in affinity_warnings:
                errors.append(
                    FingerprintValidationError(
                        message=warning_msg,
                        level="warning",
                        field="supported_protocols",
                    )
                )

        # Rule 4: Required fields in identities
        errors.extend(cls._validate_identity_required_fields(fingerprint, supported))

        # Convert warnings to errors if strict mode
        if strict:
            for error in errors:
                error.level = "error"

        return errors

    @classmethod
    def _validate_identities_exist(
        cls,
        fingerprint: dict[str, Any],
        supported_protocols: list[str],
    ) -> list[FingerprintValidationError]:
        """Rule 1: Identity must exist for each supported protocol."""
        errors: list[FingerprintValidationError] = []

        for protocol in supported_protocols:
            identity_key = PROTOCOL_TO_IDENTITY_KEY.get(protocol)
            if not identity_key:
                continue  # Unknown protocol

            # Skip protocols that share identity keys
            if protocol in ("profisafe", "s7comm_plus"):
                continue  # These share keys with profinet/s7comm

            identity = fingerprint.get(identity_key)
            if not identity or not isinstance(identity, dict):
                errors.append(
                    FingerprintValidationError(
                        message=(
                            f"Protocol '{protocol}' declared in supported_protocols "
                            f"but '{identity_key}' is missing or invalid"
                        ),
                        level="error",
                        field="supported_protocols",
                    )
                )

        return errors

    @classmethod
    def _validate_no_orphan_identities(
        cls,
        fingerprint: dict[str, Any],
        supported_protocols: list[str],
    ) -> list[FingerprintValidationError]:
        """Rule 2: Warn if identity exists without protocol declaration."""
        errors: list[FingerprintValidationError] = []

        # Build set of allowed identity keys from supported protocols
        allowed_keys = set()
        for protocol in supported_protocols:
            identity_key = PROTOCOL_TO_IDENTITY_KEY.get(protocol)
            if identity_key:
                allowed_keys.add(identity_key)

        # Check for identities not covered by supported_protocols
        identity_keys_to_check = [
            "modbus_identity",
            "ethernet_ip_identity",
            "profinet_identity",
            "s7_identity",
            "bacnet_identity",
            "snmp_identity",
            "cip_identity_object",
        ]

        for identity_key in identity_keys_to_check:
            identity = fingerprint.get(identity_key)
            if identity and isinstance(identity, dict) and identity_key not in allowed_keys:
                errors.append(
                    FingerprintValidationError(
                        message=(
                            f"'{identity_key}' present in fingerprint but corresponding "
                            f"protocol not declared in supported_protocols"
                        ),
                        level="warning",
                        field=identity_key,
                    )
                )

        return errors

    @classmethod
    def _validate_identity_required_fields(
        cls,
        fingerprint: dict[str, Any],
        supported_protocols: list[str],
    ) -> list[FingerprintValidationError]:
        """Rule 4: Required fields in identities."""
        errors: list[FingerprintValidationError] = []

        # Define required fields for each identity type
        required_fields = {
            "modbus_identity": ["vendor_name", "product_code"],
            "ethernet_ip_identity": ["vendor_id", "device_type", "product_code"],
            "profinet_identity": ["vendor_id", "device_id", "device_type"],
            "s7_identity": ["order_code"],
            "bacnet_identity": ["vendor_identifier", "device_instance"],
            "snmp_identity": ["sys_descr"],
        }

        for protocol in supported_protocols:
            identity_key = PROTOCOL_TO_IDENTITY_KEY.get(protocol)
            if not identity_key:
                continue

            # Skip protocols that share identity keys
            if protocol in ("profisafe", "s7comm_plus"):
                continue

            identity = fingerprint.get(identity_key)
            if not identity or not isinstance(identity, dict):
                continue  # Already caught by Rule 1

            required = required_fields.get(identity_key, [])
            for field in required:
                if field not in identity or identity[field] is None:
                    errors.append(
                        FingerprintValidationError(
                            message=f"Required field '{field}' missing",
                            level="warning",
                            field=identity_key,
                        )
                    )

        return errors

    @classmethod
    def validate_all_fingerprints(
        cls,
        fingerprints: list[dict[str, Any]],
        strict: bool = False,
    ) -> dict[str, list[FingerprintValidationError]]:
        """Validate a list of fingerprints.

        Args:
            fingerprints: List of fingerprint dictionaries
            strict: If True, treat warnings as errors

        Returns:
            Dictionary mapping fingerprint model to list of errors
        """
        results: dict[str, list[FingerprintValidationError]] = {}

        for fp in fingerprints:
            model = fp.get("model", "unknown")
            vendor = fp.get("vendor", "unknown")
            key = f"{vendor}/{model}"

            errors = cls.validate(fp, strict=strict)
            if errors:
                results[key] = errors

        return results

    @classmethod
    def is_valid(
        cls,
        fingerprint: dict[str, Any],
        strict: bool = False,
    ) -> bool:
        """Check if a fingerprint is valid (no errors).

        Args:
            fingerprint: Vendor fingerprint dictionary
            strict: If True, treat warnings as errors

        Returns:
            True if no errors (or only warnings in non-strict mode)
        """
        errors = cls.validate(fingerprint, strict=strict)

        if strict:
            return len(errors) == 0

        # In non-strict mode, only actual errors count
        return not any(e.level == "error" for e in errors)

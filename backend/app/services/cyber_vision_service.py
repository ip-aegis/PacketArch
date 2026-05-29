# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Cisco Cyber Vision API service for device discovery and vulnerability data."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from app.protocol_engines.vendor_oui import get_vendor_for_oui

logger = logging.getLogger(__name__)


@dataclass
class CVConnectionResult:
    """Result of a Cyber Vision connection test."""

    success: bool
    message: str
    version: str | None = None
    center_name: str | None = None


@dataclass
class CVDevice:
    """Device discovered by Cyber Vision."""

    id: str
    name: str
    ip: str | None = None
    mac: str | None = None
    vendor: str | None = None
    model: str | None = None
    firmware: str | None = None
    category: str | None = None
    risk_score: int | None = None
    first_seen: str | None = None
    last_seen: str | None = None
    group_name: str | None = None

    @classmethod
    def from_api_response(cls, data: dict) -> "CVDevice":
        """Create CVDevice from API response data."""
        # CV API returns nested structures - extract key fields
        # IP and MAC can be lists in CV API v3 - extract first value
        ip_val = data.get("ip")
        if isinstance(ip_val, list):
            ip_val = ip_val[0] if ip_val else None

        mac_val = data.get("mac")
        if isinstance(mac_val, list):
            mac_val = mac_val[0] if mac_val else None

        # Handle nested dicts that might be None (not just missing)
        vendor_info = data.get("vendorProductInfo") or {}
        group_info = data.get("group") or {}

        # CV API v3 stores enriched fields in normalizedProperties as key-value pairs:
        #   [{"key": "vendor-name", "value": ["Siemens"]}, ...]
        # Values can be strings (component level) or lists (device level).
        norm_props: dict[str, str] = {}
        for prop in data.get("normalizedProperties") or []:
            key = prop.get("key", "")
            val = prop.get("value")
            if isinstance(val, list):
                val = val[0] if val else None
            if key and val:
                norm_props[key] = val

        return cls(
            id=str(data.get("id", "")),
            name=data.get("label") or data.get("name") or "Unknown",
            ip=ip_val,
            mac=mac_val,
            vendor=(data.get("vendor")
                    or vendor_info.get("vendor")
                    or norm_props.get("vendor-name")),
            model=(data.get("model")
                   or vendor_info.get("model")
                   or norm_props.get("model-name")),
            firmware=(data.get("firmware")
                      or vendor_info.get("firmwareVersion")
                      or norm_props.get("fw-version")),
            category=data.get("category") or data.get("deviceType"),
            risk_score=data.get("riskScore") or data.get("risk_score"),
            first_seen=data.get("firstSeen") or data.get("first_seen"),
            last_seen=data.get("lastSeen") or data.get("last_seen"),
            group_name=data.get("groupName") or group_info.get("name"),
        )


@dataclass
class CVVulnerability:
    """Vulnerability detected by Cyber Vision."""

    id: str
    cve_id: str
    title: str
    severity: str
    cvss_score: float | None = None
    affected_device_count: int = 0
    description: str | None = None

    @classmethod
    def from_api_response(cls, data: dict) -> "CVVulnerability":
        """Create CVVulnerability from API response data."""
        # CV API v3 uses 'CVSS' for score (not 'cvssScore')
        cvss = data.get("CVSS")

        # Derive severity from CVSS score (not a direct field in API)
        severity = "unknown"
        if cvss is not None:
            if cvss >= 9.0:
                severity = "critical"
            elif cvss >= 7.0:
                severity = "high"
            elif cvss >= 4.0:
                severity = "medium"
            else:
                severity = "low"

        return cls(
            id=str(data.get("id", "")),
            cve_id=data.get("cve") or "",  # CV API uses 'cve', not 'cveId'
            title=data.get("title") or data.get("summary") or "",
            severity=severity,
            cvss_score=cvss,
            affected_device_count=data.get("affectedDeviceCount") or 0,
            description=data.get("fullDescription") or data.get("summary"),
        )


def normalize_mac(mac: str | None) -> str | None:
    """Normalize MAC address to lowercase with colons (xx:xx:xx:xx:xx:xx)."""
    if not mac:
        return None
    clean = mac.lower().replace(":", "").replace("-", "").replace(".", "")
    if len(clean) == 12:
        return ":".join(clean[i : i + 2] for i in range(0, 12, 2))
    return mac.lower()


def _normalize_cv_vendor(vendor: str) -> str:
    """Extract primary brand from a CV vendor string.

    CV reports full legal entity names that vary for the same brand:
    - "Siemens AG" / "Siemens Numerical Control Ltd., Nanjing" → "siemens"
    - "KUKA Roboter GmbH" / "KUKA WELDING SYSTEMS & ROBOTS" → "kuka"
    - "Rockwell Automation/Allen-Bradley" → "rockwell"
    """
    if not vendor:
        return ""
    # Split on whitespace, slashes, commas → take first token as brand
    for ch in "/,":
        vendor = vendor.replace(ch, " ")
    brand = vendor.split()[0].lower().rstrip(".,;:") if vendor.split() else ""
    aliases = {"allen-bradley": "rockwell", "allen": "rockwell"}
    return aliases.get(brand, brand)


def _classify_severity(mac: str, devices: list[CVDevice]) -> tuple[str, str]:
    """Classify the severity of a duplicate MAC group.

    Returns:
        (severity, reason) tuple.
    """
    vendors = {(d.vendor or "").lower().strip() for d in devices} - {""}
    normalized_vendors = {_normalize_cv_vendor(v) for v in vendors} - {""}
    ips = {d.ip for d in devices if d.ip}
    names = {d.name for d in devices}
    models = {(d.model or "").lower().strip() for d in devices} - {""}

    # Critical: different vendors → spoofing or major misconfiguration
    # Use normalized brands so "Siemens AG" and "Siemens Numerical Control Ltd."
    # are recognized as the same vendor.
    if len(normalized_vendors) > 1:
        return (
            "critical",
            f"Same MAC shared across {len(normalized_vendors)} different vendors "
            f"({', '.join(sorted(vendors))}). "
            "Possible MAC spoofing or major misconfiguration.",
        )

    # High: different IPs → cloned device / network misconfiguration
    if len(ips) > 1:
        return (
            "high",
            f"Same MAC with {len(ips)} different IP addresses "
            f"({', '.join(sorted(ips))}). "
            "Possible cloned device or network misconfiguration.",
        )

    # Medium: same IP but different names or models → data quality issue
    if len(names) > 1 or len(models) > 1:
        return (
            "medium",
            "Same MAC and IP but different device names or models. "
            "Possible duplicate entries from multiple discovery sessions.",
        )

    # Low: devices look nearly identical
    return (
        "low",
        "Devices appear nearly identical. "
        "Likely the same device observed from multiple network segments or sensor paths.",
    )


def analyze_duplicate_macs(devices: list[CVDevice]) -> dict:
    """Analyze a list of CV devices for duplicate MAC addresses.

    Groups devices by normalized MAC, identifies groups with 2+ devices,
    classifies severity, and computes summary statistics.
    """
    devices_with_mac: list[CVDevice] = []
    devices_without_mac: list[CVDevice] = []

    for device in devices:
        norm = normalize_mac(device.mac)
        if norm:
            devices_with_mac.append(device)
        else:
            devices_without_mac.append(device)

    # Group by normalized MAC
    mac_groups: dict[str, list[CVDevice]] = {}
    for device in devices_with_mac:
        norm = normalize_mac(device.mac)
        mac_groups.setdefault(norm, []).append(device)

    # Find duplicates and classify severity
    duplicate_groups = []
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}

    for mac, group_devices in mac_groups.items():
        if len(group_devices) < 2:
            continue

        severity, reason = _classify_severity(mac, group_devices)
        severity_counts[severity] += 1

        # OUI vendor lookup
        oui_prefix = mac[:8].upper()
        oui_vendor = get_vendor_for_oui(oui_prefix)

        duplicate_groups.append({
            "mac": mac,
            "oui_vendor": oui_vendor,
            "severity": severity,
            "reason": reason,
            "device_count": len(group_devices),
            "devices": [
                {
                    "id": d.id,
                    "name": d.name,
                    "ip": d.ip,
                    "mac": d.mac,
                    "vendor": d.vendor,
                    "model": d.model,
                    "firmware": d.firmware,
                    "category": d.category,
                    "risk_score": d.risk_score,
                    "first_seen": d.first_seen,
                    "last_seen": d.last_seen,
                    "group_name": d.group_name,
                }
                for d in group_devices
            ],
        })

    # Sort: critical first, then high, medium, low; within same severity by device count desc
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    duplicate_groups.sort(key=lambda g: (severity_order[g["severity"]], -g["device_count"]))

    return {
        "total_devices_analyzed": len(devices),
        "devices_with_mac": len(devices_with_mac),
        "devices_without_mac": len(devices_without_mac),
        "unique_macs": len(mac_groups),
        "duplicate_groups_count": len(duplicate_groups),
        "severity_counts": severity_counts,
        "duplicate_groups": duplicate_groups,
        "no_mac_devices": [
            {
                "id": d.id,
                "name": d.name,
                "ip": d.ip,
                "vendor": d.vendor,
                "category": d.category,
                "group_name": d.group_name,
            }
            for d in devices_without_mac
        ],
    }


def deduplicate_by_mac(devices: list[CVDevice]) -> list[CVDevice]:
    """Merge CV components that share the same MAC address.

    Cisco Cyber Vision creates separate components for Layer 2 traffic
    (e.g. PROFINET, EtherType 0x8892) and Layer 3 traffic (S7comm, SNMP
    over TCP/UDP).  This produces duplicate entries for the same physical
    device — one with an IP and one without.

    This function groups entries by normalized MAC, keeps the richest
    record (preferring the one with an IP), and merges missing fields
    from the other entries.
    """
    mac_groups: dict[str, list[CVDevice]] = {}
    no_mac: list[CVDevice] = []

    for d in devices:
        norm = normalize_mac(d.mac)
        if norm:
            mac_groups.setdefault(norm, []).append(d)
        else:
            no_mac.append(d)

    merged: list[CVDevice] = []
    for _mac, group in mac_groups.items():
        if len(group) == 1:
            merged.append(group[0])
            continue

        # Prefer the entry that has an IP address
        group.sort(key=lambda d: (d.ip is None, d.name == "Unknown"))
        primary = group[0]

        # Back-fill missing fields from other entries
        for other in group[1:]:
            if not primary.ip and other.ip:
                primary.ip = other.ip
            if not primary.vendor and other.vendor:
                primary.vendor = other.vendor
            if not primary.model and other.model:
                primary.model = other.model
            if not primary.firmware and other.firmware:
                primary.firmware = other.firmware
            if not primary.category and other.category:
                primary.category = other.category
            if not primary.group_name and other.group_name:
                primary.group_name = other.group_name
            if primary.risk_score is None and other.risk_score is not None:
                primary.risk_score = other.risk_score

        merged.append(primary)

    return merged + no_mac


class CyberVisionService:
    """Service for interacting with Cisco Cyber Vision API v3."""

    def __init__(self, base_url: str, api_token: str, verify_ssl: bool = False):
        """Initialize the Cyber Vision service.

        Args:
            base_url: CV center URL (e.g., https://10.10.20.115)
            api_token: API token for authentication
            verify_ssl: Whether to verify SSL certificates (default False for self-signed)
        """
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.verify_ssl = verify_ssl
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                verify=self.verify_ssl,
                timeout=30.0,
                headers={
                    "x-token-id": self.api_token,
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _request(
        self, method: str, endpoint: str, params: dict | None = None, json: dict | None = None
    ) -> dict | list:
        """Make an API request.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., /devices)
            params: Query parameters
            json: JSON body for POST/PUT

        Returns:
            Response data

        Raises:
            httpx.HTTPStatusError: On API errors
        """
        client = await self._get_client()
        url = f"{self.base_url}/api/3.0{endpoint}"

        logger.debug(f"CV API request: {method} {url}")

        response = await client.request(method, url, params=params, json=json)
        response.raise_for_status()

        return response.json()

    async def test_connection(self) -> CVConnectionResult:
        """Test connection to Cyber Vision and return status info.

        Returns:
            Connection test result with version info
        """
        try:
            # Try to fetch center info or a simple endpoint
            # CV API v3 has /info or we can try /devices with limit=1
            client = await self._get_client()
            url = f"{self.base_url}/api/3.0/devices"

            response = await client.get(url, params={"limit": 1})
            response.raise_for_status()

            # If we get here, connection is successful
            return CVConnectionResult(
                success=True,
                message="Connected to Cyber Vision",
                version="3.0",
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"CV API error: {e.response.status_code} - {e.response.text}")
            return CVConnectionResult(
                success=False,
                message=f"API error: {e.response.status_code}",
            )
        except httpx.RequestError as e:
            logger.error(f"CV connection error: {e}")
            return CVConnectionResult(
                success=False,
                message=f"Connection failed: {str(e)}",
            )
        except Exception as e:
            logger.exception("Unexpected error testing CV connection")
            return CVConnectionResult(
                success=False,
                message=f"Unexpected error: {str(e)}",
            )

    async def get_devices(
        self, size: int = 100, page: int = 1
    ) -> list[CVDevice]:
        """Fetch discovered devices from Cyber Vision.

        Args:
            size: Maximum number of devices to return per page
            page: Page number (1-indexed)

        Returns:
            List of discovered devices
        """
        # CV API v3 uses 'page' and 'size' for pagination
        # Note: 'from'/'to' are date/time filters, NOT pagination offset!
        params = {"page": page, "size": size}

        try:
            data = await self._request("GET", "/devices", params=params)

            # Handle both list response and paginated response
            devices_data = data if isinstance(data, list) else data.get("items", data.get("devices", []))

            # Filter out None values that CV API sometimes returns
            devices_data = [d for d in devices_data if d is not None]

            return [CVDevice.from_api_response(d) for d in devices_data]

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to fetch CV devices: {e.response.status_code}")
            raise
        except Exception:
            logger.exception("Error fetching CV devices")
            raise

    async def get_devices_by_preset(
        self, preset_id: str, size: int = 100, page: int = 1
    ) -> list[CVDevice]:
        """Fetch devices from a specific preset.

        Uses the preset-specific endpoint: /presets/{preset_id}/visualisations/networknode-list
        Note: This endpoint is cached. Use refresh_preset_data() first if fresh data is needed.

        Args:
            preset_id: Preset ID to filter by
            size: Maximum number of devices to return per page
            page: Page number (1-indexed)

        Returns:
            List of devices in the preset
        """
        params = {"page": page, "size": size}

        try:
            data = await self._request(
                "GET",
                f"/presets/{preset_id}/visualisations/networknode-list",
                params=params
            )

            # Handle both list response and paginated response
            devices_data = data if isinstance(data, list) else data.get("items", [])

            # Filter out None values that CV API sometimes returns
            devices_data = [d for d in devices_data if d is not None]

            # Log first device's raw data to see available fields
            if devices_data and page == 1:
                logger.info(f"Preset device raw data keys: {list(devices_data[0].keys())}")
                # Log the full first device for debugging
                import json
                logger.info(f"First preset device raw: {json.dumps(devices_data[0], default=str)[:500]}")

            return [CVDevice.from_api_response(d) for d in devices_data]

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to fetch CV devices for preset {preset_id}: {e.response.status_code}")
            raise
        except Exception:
            logger.exception(f"Error fetching CV devices for preset {preset_id}")
            raise

    async def refresh_preset_data(self, preset_id: str) -> None:
        """Refresh cached data for a preset.

        The preset visualization endpoints are cached. Call this to ensure fresh data
        before querying preset devices.

        Args:
            preset_id: Preset ID to refresh
        """
        try:
            await self._request("POST", f"/presets/{preset_id}/refreshData")
            logger.info(f"Refreshed preset data for {preset_id}")
        except Exception as e:
            logger.warning(f"Failed to refresh preset data for {preset_id}: {e}")

    async def get_all_devices(
        self, preset_id: str | None = None
    ) -> list[CVDevice]:
        """Fetch ALL discovered devices from Cyber Vision by paginating through results.

        Args:
            preset_id: Optional preset ID to filter by (uses preset-specific endpoint)

        Returns:
            Complete list of all discovered devices
        """
        all_devices = []
        page_size = 100
        page = 1

        while True:
            if preset_id:
                # Use preset-specific endpoint for filtered results
                devices = await self.get_devices_by_preset(
                    preset_id=preset_id, size=page_size, page=page
                )
            else:
                # Use main devices endpoint for all devices
                devices = await self.get_devices(size=page_size, page=page)

            all_devices.extend(devices)

            # If we got fewer than page_size, we've reached the end
            if len(devices) < page_size:
                break

            page += 1

            # Safety limit to prevent infinite loops (100 pages * 100 = 10000 devices)
            if page > 100:
                logger.warning("CV device fetch hit safety limit of 100 pages")
                break

        logger.info(f"Fetched {len(all_devices)} total devices from Cyber Vision (preset_id={preset_id})")
        return all_devices

    async def get_presets(self) -> list[dict]:
        """Fetch available presets from Cyber Vision.

        Returns:
            List of presets with id and label
        """
        try:
            data = await self._request("GET", "/presets")
            presets = data if isinstance(data, list) else []
            return [{"id": p.get("id"), "label": p.get("label", p.get("name", "Unknown"))} for p in presets]
        except Exception:
            logger.exception("Error fetching CV presets")
            return []

    async def search_device_by_ip(self, ip_address: str) -> CVDevice | None:
        """Search for a device by IP address.

        Args:
            ip_address: IP address to search for

        Returns:
            Matching device or None if not found
        """
        try:
            # CV API search parameter finds devices by IP
            data = await self._request("GET", "/devices", params={"search": ip_address, "size": 10})

            devices_data = data if isinstance(data, list) else data.get("items", data.get("devices", []))

            # Find exact IP match from search results
            for d in devices_data:
                device_ips = d.get("ip", [])
                if isinstance(device_ips, list):
                    if ip_address in device_ips:
                        return CVDevice.from_api_response(d)
                elif device_ips == ip_address:
                    return CVDevice.from_api_response(d)

            return None

        except Exception as e:
            logger.warning(f"Error searching CV for IP {ip_address}: {e}")
            return None

    async def search_device_by_mac(self, mac_address: str) -> CVDevice | None:
        """Search for a device by MAC address.

        Args:
            mac_address: MAC address to search for

        Returns:
            Matching device or None if not found
        """
        try:
            # Normalize MAC for search
            search_mac = mac_address.lower().replace("-", ":").replace(".", ":")
            logger.info(f"Searching for device by MAC: {search_mac}")

            data = await self._request("GET", "/devices", params={"search": search_mac, "size": 10})

            devices_data = data if isinstance(data, list) else data.get("items", data.get("devices", []))
            logger.info(f"MAC search returned {len(devices_data)} devices")

            # Find exact MAC match from search results
            for d in devices_data:
                device_macs = d.get("mac", [])
                logger.info(f"  Search result - Device {d.get('id')}: MACs={device_macs}")
                if isinstance(device_macs, list):
                    for dev_mac in device_macs:
                        if dev_mac.lower().replace("-", ":") == search_mac:
                            logger.info(f"Found device by MAC {search_mac}: {d.get('id')}")
                            return CVDevice.from_api_response(d)
                elif device_macs and device_macs.lower().replace("-", ":") == search_mac:
                    logger.info(f"Found device by MAC {search_mac}: {d.get('id')}")
                    return CVDevice.from_api_response(d)

            logger.debug(f"No exact MAC match found for {search_mac}")
            return None

        except Exception as e:
            logger.warning(f"Error searching CV for MAC {mac_address}: {e}")
            return None

    async def get_device_details(self, device_id: str) -> CVDevice | None:
        """Get detailed information for a specific device.

        Args:
            device_id: Device ID in Cyber Vision

        Returns:
            Device details or None if not found
        """
        try:
            data = await self._request("GET", f"/devices/{device_id}")
            return CVDevice.from_api_response(data)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
        except Exception:
            logger.exception(f"Error fetching CV device {device_id}")
            raise

    async def get_vulnerabilities(
        self, limit: int = 100, offset: int = 0, severity: str | None = None
    ) -> list[CVVulnerability]:
        """Fetch vulnerability data from Cyber Vision.

        Args:
            limit: Maximum number of vulnerabilities to return
            offset: Offset for pagination
            severity: Optional severity filter (critical, high, medium, low)

        Returns:
            List of vulnerabilities
        """
        params = {"limit": limit, "offset": offset}
        if severity:
            params["severity"] = severity

        try:
            data = await self._request("GET", "/vulnerabilities", params=params)

            # Handle both list response and paginated response
            vuln_data = data if isinstance(data, list) else data.get("items", data.get("vulnerabilities", []))

            return [CVVulnerability.from_api_response(v) for v in vuln_data]

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to fetch CV vulnerabilities: {e.response.status_code}")
            raise
        except Exception:
            logger.exception("Error fetching CV vulnerabilities")
            raise

    async def get_components(self, device_id: str | None = None) -> list[dict]:
        """Fetch software components from Cyber Vision.

        Args:
            device_id: Optional device ID to filter by

        Returns:
            List of software components
        """
        params = {}
        if device_id:
            params["deviceId"] = device_id

        try:
            data = await self._request("GET", "/components", params=params)
            return data if isinstance(data, list) else data.get("items", [])

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to fetch CV components: {e.response.status_code}")
            raise

    async def get_flows(
        self, device_id: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[dict]:
        """Fetch network flow data from Cyber Vision.

        Args:
            device_id: Optional device ID to filter by
            limit: Maximum number of flows to return
            offset: Offset for pagination

        Returns:
            List of network flows
        """
        params = {"limit": limit, "offset": offset}
        if device_id:
            params["deviceId"] = device_id

        try:
            data = await self._request("GET", "/flows", params=params)
            return data if isinstance(data, list) else data.get("items", [])

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to fetch CV flows: {e.response.status_code}")
            raise

    async def get_groups(self) -> list[dict]:
        """Fetch device groups from Cyber Vision.

        Returns:
            List of device groups
        """
        try:
            data = await self._request("GET", "/groups")
            return data if isinstance(data, list) else data.get("items", [])

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to fetch CV groups: {e.response.status_code}")
            raise

    # ==================== Write Methods ====================

    async def set_device_label(self, device_id: str, name: str) -> bool:
        """Set a custom label (name) for a device in Cyber Vision.

        Args:
            device_id: CV device ID
            name: Custom name to set

        Returns:
            True if successful
        """
        try:
            await self._request("POST", f"/devices/{device_id}/label", json={"name": name})
            logger.info(f"Set label '{name}' for CV device {device_id}")
            return True
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to set label for device {device_id}: {e.response.status_code}")
            raise

    async def add_device_property(self, device_id: str, label: str, value: str) -> str:
        """Add a user property to a device.

        Args:
            device_id: CV device ID
            label: Property label (max 60 chars)
            value: Property value (max 180 chars)

        Returns:
            Property ID of the created property
        """
        # Truncate to API limits
        label = label[:60]
        value = value[:180]

        try:
            result = await self._request(
                "POST",
                f"/devices/{device_id}/usersProperties",
                json={"label": label, "value": value}
            )
            prop_id = result.get("id", "") if isinstance(result, dict) else ""
            logger.info(f"Added property '{label}' to CV device {device_id}")
            return prop_id
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to add property to device {device_id}: {e.response.status_code}")
            raise

    async def update_device_property(
        self, device_id: str, property_id: str, label: str, value: str
    ) -> bool:
        """Update an existing user property on a device.

        Args:
            device_id: CV device ID
            property_id: Property ID to update
            label: New property label (max 60 chars)
            value: New property value (max 180 chars)

        Returns:
            True if successful
        """
        try:
            await self._request(
                "PUT",
                f"/devices/{device_id}/usersProperties/{property_id}",
                json={"label": label[:60], "value": value[:180]}
            )
            logger.info(f"Updated property {property_id} on CV device {device_id}")
            return True
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to update property {property_id}: {e.response.status_code}")
            raise

    async def delete_device_property(self, device_id: str, property_id: str) -> bool:
        """Delete a user property from a device.

        Args:
            device_id: CV device ID
            property_id: Property ID to delete

        Returns:
            True if successful
        """
        try:
            await self._request("DELETE", f"/devices/{device_id}/usersProperties/{property_id}")
            logger.info(f"Deleted property {property_id} from CV device {device_id}")
            return True
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to delete property {property_id}: {e.response.status_code}")
            raise

    async def get_device_properties(self, device_id: str) -> list[dict]:
        """Get existing user properties for a device.

        Args:
            device_id: CV device ID

        Returns:
            List of properties with id, label, value
        """
        try:
            data = await self._request("GET", f"/devices/{device_id}/usersProperties")
            return data if isinstance(data, list) else []
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return []
            logger.error(f"Failed to get properties for device {device_id}: {e.response.status_code}")
            raise

    async def resolve_device_id(self, device_id: str, mac: str | None = None, ip: str | None = None) -> str | None:
        """Resolve a device ID to a valid main device ID.

        Preset visualization node IDs don't work with /devices/{id} endpoints.
        This method looks up the device by MAC or IP to get a valid ID.

        Args:
            device_id: The ID to validate (might be a preset node ID)
            mac: MAC address to search by if ID fails
            ip: IP address to search by if ID fails

        Returns:
            Valid device ID or None if not found
        """
        # First try if the ID works directly
        try:
            device = await self.get_device_details(device_id)
            if device:
                return device_id
        except Exception:
            pass

        # ID didn't work, try to find by MAC
        if mac:
            logger.info(f"Device ID {device_id} not found, trying MAC lookup: {mac}")
            device = await self.search_device_by_mac(mac)
            if device:
                logger.info(f"Resolved device by MAC {mac}: {device_id} -> {device.id}")
                return device.id
            else:
                logger.info(f"MAC lookup failed for {mac}")

        # Try by IP
        if ip:
            logger.info(f"Trying IP lookup: {ip}")
            device = await self.search_device_by_ip(ip)
            if device:
                logger.info(f"Resolved device by IP {ip}: {device_id} -> {device.id}")
                return device.id
            else:
                logger.info(f"IP lookup failed for {ip}")

        logger.warning(f"Could not resolve device ID {device_id} (MAC: {mac}, IP: {ip})")
        return None

    async def enrich_device(
        self, device_id: str, properties: dict[str, str], skip_existing: bool = True,
        mac: str | None = None, ip: str | None = None
    ) -> dict[str, str]:
        """Add multiple properties to a device.

        Args:
            device_id: CV device ID (may be a preset node ID that needs resolution)
            properties: Dict of label -> value to add
            skip_existing: If True, skip properties that already exist with same label
            mac: MAC address for ID resolution fallback
            ip: IP address for ID resolution fallback

        Returns:
            Dict of label -> property_id for successfully added properties
        """
        # Resolve the device ID (preset node IDs need to be mapped to real device IDs)
        resolved_id = await self.resolve_device_id(device_id, mac, ip)
        if not resolved_id:
            logger.error(f"Cannot enrich device {device_id}: could not resolve to valid device ID")
            return {}

        if resolved_id != device_id:
            logger.info(f"Using resolved device ID: {resolved_id} (was {device_id})")

        results = {}

        # Get existing properties to avoid duplicates
        existing_labels = set()
        if skip_existing:
            try:
                existing = await self.get_device_properties(resolved_id)
                existing_labels = {p.get("label", "").lower() for p in existing}
            except Exception as e:
                logger.warning(f"Could not fetch existing properties: {e}")

        for label, value in properties.items():
            if not value:  # Skip empty values
                continue

            # Skip if property with same label already exists
            if skip_existing and label.lower() in existing_labels:
                logger.debug(f"Skipping existing property '{label}' on device {resolved_id}")
                continue

            try:
                prop_id = await self.add_device_property(resolved_id, label, value)
                results[label] = prop_id
            except Exception as e:
                logger.warning(f"Failed to add property '{label}' to device {resolved_id}: {e}")

        return results

    async def enrich_device_direct(
        self, device_id: str, properties: dict[str, str]
    ) -> dict[str, str]:
        """Add properties to a device using a known-good device ID.

        Unlike enrich_device(), this method does NOT try to resolve the device ID.
        Use this when you've already resolved the ID via MAC/IP lookup.

        Args:
            device_id: Valid CV device ID from main /devices endpoint
            properties: Dict of label -> value to add

        Returns:
            Dict of label -> property_id for successfully added properties
        """
        results = {}

        for label, value in properties.items():
            if not value:  # Skip empty values
                continue

            try:
                prop_id = await self.add_device_property(device_id, label, value)
                if prop_id:
                    results[label] = prop_id
            except Exception as e:
                # Log but don't fail - property might already exist
                logger.debug(f"Could not add property '{label}' to device {device_id}: {e}")

        return results


async def get_cyber_vision_service(
    base_url: str, api_token: str, verify_ssl: bool = False
) -> CyberVisionService:
    """Factory function to create a CyberVisionService instance.

    Args:
        base_url: CV center URL
        api_token: API token
        verify_ssl: Whether to verify SSL

    Returns:
        Configured CyberVisionService instance
    """
    return CyberVisionService(base_url, api_token, verify_ssl)

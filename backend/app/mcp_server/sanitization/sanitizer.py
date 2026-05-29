# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Data sanitization for sharing scenarios with AI."""

import re
from typing import Any


class DataSanitizer:
    """Sanitizes sensitive data before sending to AI."""

    # RFC 5737 documentation IP ranges
    DOC_IP_RANGES = [
        "192.0.2",      # TEST-NET-1
        "198.51.100",   # TEST-NET-2
        "203.0.113",    # TEST-NET-3
    ]

    # Generic MAC prefix (locally administered)
    GENERIC_MAC_PREFIX = "02:00:00"

    def __init__(self) -> None:
        """Initialize sanitizer with IP/MAC mappings."""
        self._ip_mapping: dict[str, str] = {}
        self._mac_mapping: dict[str, str] = {}
        self._hostname_mapping: dict[str, str] = {}
        self._ip_counter = 0
        self._mac_counter = 0
        self._hostname_counter = 0

    def sanitize_scenario(self, scenario_dict: dict[str, Any]) -> dict[str, Any]:
        """Sanitize a complete scenario dictionary.

        Args:
            scenario_dict: Scenario data

        Returns:
            Sanitized scenario
        """
        sanitized = scenario_dict.copy()

        # Sanitize devices
        if "devices" in sanitized:
            sanitized_devices = {}
            for device_id, device in sanitized["devices"].items():
                sanitized_devices[device_id] = self._sanitize_device(device)
            sanitized["devices"] = sanitized_devices

        # Sanitize flows
        if "flows" in sanitized:
            sanitized_flows = {}
            for flow_id, flow in sanitized["flows"].items():
                sanitized_flows[flow_id] = self._sanitize_flow(flow)
            sanitized["flows"] = sanitized_flows

        # Sanitize zones
        if "zones" in sanitized:
            sanitized_zones = {}
            for zone_id, zone in sanitized["zones"].items():
                sanitized_zones[zone_id] = self._sanitize_zone(zone)
            sanitized["zones"] = sanitized_zones

        return sanitized

    def _sanitize_device(self, device: dict[str, Any]) -> dict[str, Any]:
        """Sanitize device data."""
        sanitized = device.copy()

        # Sanitize network configuration
        if "network" in sanitized:
            network = sanitized["network"].copy()

            if "ipAddress" in network:
                network["ipAddress"] = self.sanitize_ip(network["ipAddress"])

            if "macAddress" in network:
                network["macAddress"] = self.sanitize_mac(network["macAddress"])

            if "hostname" in network:
                network["hostname"] = self.sanitize_hostname(network["hostname"])

            if "gateway" in network and network["gateway"]:
                network["gateway"] = self.sanitize_ip(network["gateway"])

            sanitized["network"] = network

        return sanitized

    def _sanitize_flow(self, flow: dict[str, Any]) -> dict[str, Any]:
        """Sanitize flow data."""
        # Flows typically don't contain sensitive data, just return as-is
        return flow.copy()

    def _sanitize_zone(self, zone: dict[str, Any]) -> dict[str, Any]:
        """Sanitize zone data."""
        sanitized = zone.copy()

        # Sanitize network configuration in zone
        if "network" in sanitized and sanitized["network"]:
            network = sanitized["network"].copy()

            if "subnet" in network:
                # Sanitize subnet (e.g., "192.168.1.0/24" -> "192.0.2.0/24")
                subnet = network["subnet"]
                if "/" in subnet:
                    ip_part, cidr = subnet.split("/")
                    sanitized_ip = self.sanitize_ip(ip_part)
                    network["subnet"] = f"{sanitized_ip}/{cidr}"

            if "gateway" in network and network["gateway"]:
                network["gateway"] = self.sanitize_ip(network["gateway"])

            sanitized["network"] = network

        return sanitized

    def sanitize_ip(self, ip: str) -> str:
        """Sanitize IP address using RFC 5737 ranges.

        Args:
            ip: Original IP address

        Returns:
            Anonymized IP address
        """
        if ip in self._ip_mapping:
            return self._ip_mapping[ip]

        # Determine which documentation range to use
        range_index = self._ip_counter // 254
        host_offset = (self._ip_counter % 254) + 1

        if range_index >= len(self.DOC_IP_RANGES):
            # Wrap around if we run out of ranges
            range_index = range_index % len(self.DOC_IP_RANGES)

        # Create sanitized IP
        base_range = self.DOC_IP_RANGES[range_index]
        sanitized_ip = f"{base_range}.{host_offset}"

        self._ip_mapping[ip] = sanitized_ip
        self._ip_counter += 1

        return sanitized_ip

    def sanitize_mac(self, mac: str) -> str:
        """Sanitize MAC address.

        Args:
            mac: Original MAC address

        Returns:
            Anonymized MAC address
        """
        if mac in self._mac_mapping:
            return self._mac_mapping[mac]

        # Generate consistent MAC based on counter
        # Format: 02:00:00:XX:XX:XX
        byte1 = (self._mac_counter >> 16) & 0xFF
        byte2 = (self._mac_counter >> 8) & 0xFF
        byte3 = self._mac_counter & 0xFF

        sanitized_mac = f"{self.GENERIC_MAC_PREFIX}:{byte1:02x}:{byte2:02x}:{byte3:02x}"

        self._mac_mapping[mac] = sanitized_mac
        self._mac_counter += 1

        return sanitized_mac

    def sanitize_hostname(self, hostname: str) -> str:
        """Sanitize hostname.

        Args:
            hostname: Original hostname

        Returns:
            Generic hostname
        """
        if hostname in self._hostname_mapping:
            return self._hostname_mapping[hostname]

        # Try to preserve the device type prefix if present
        # e.g., "plc-123" -> "plc-001", "hmi-production" -> "hmi-001"
        match = re.match(r"^([a-zA-Z]+)[-_]", hostname)
        if match:
            prefix = match.group(1).lower()
            sanitized = f"{prefix}-{self._hostname_counter:03d}"
        else:
            sanitized = f"device-{self._hostname_counter:03d}"

        self._hostname_mapping[hostname] = sanitized
        self._hostname_counter += 1

        return sanitized

    def reset(self) -> None:
        """Reset all mappings and counters."""
        self._ip_mapping.clear()
        self._mac_mapping.clear()
        self._hostname_mapping.clear()
        self._ip_counter = 0
        self._mac_counter = 0
        self._hostname_counter = 0

"""Builtin cloud service endpoint seed data.

Contains pre-configured cloud service endpoints for common
remote access and monitoring services used in OT environments.
"""

from typing import Any

BUILTIN_CLOUD_SERVICES: list[dict[str, Any]] = [
    # ============================================================
    # EWON Talk2M - Industrial Remote Access
    # https://www.ewon.biz/products/talk2m
    # ============================================================
    {
        "name": "Talk2M US-West",
        "provider": "talk2m",
        "ip_addresses": ["13.56.142.1", "54.95.198.117"],
        "primary_ip": "13.56.142.1",
        "port": 443,
        "hostname": "talk2m.ewon.biz",
        "tls_enabled": True,
        "heartbeat_interval_ms": 30000,
        "region": "us-west",
        "description": "EWON Talk2M remote access - US West region VPN server",
        "is_builtin": True,
    },
    {
        "name": "Talk2M US-East",
        "provider": "talk2m",
        "ip_addresses": ["54.95.198.117", "13.56.142.1"],
        "primary_ip": "54.95.198.117",
        "port": 443,
        "hostname": "talk2m.ewon.biz",
        "tls_enabled": True,
        "heartbeat_interval_ms": 30000,
        "region": "us-east",
        "description": "EWON Talk2M remote access - US East region VPN server",
        "is_builtin": True,
    },
    {
        "name": "Talk2M EU",
        "provider": "talk2m",
        "ip_addresses": ["51.38.74.240", "87.98.169.126"],
        "primary_ip": "51.38.74.240",
        "port": 443,
        "hostname": "talk2m.ewon.biz",
        "tls_enabled": True,
        "heartbeat_interval_ms": 30000,
        "region": "eu",
        "description": "EWON Talk2M remote access - EU region VPN server",
        "is_builtin": True,
    },
    {
        "name": "Talk2M Asia-Pacific",
        "provider": "talk2m",
        "ip_addresses": ["87.98.169.126", "51.38.74.240"],
        "primary_ip": "87.98.169.126",
        "port": 443,
        "hostname": "talk2m.ewon.biz",
        "tls_enabled": True,
        "heartbeat_interval_ms": 30000,
        "region": "ap",
        "description": "EWON Talk2M remote access - Asia-Pacific region",
        "is_builtin": True,
    },
    # ============================================================
    # TeamViewer - Remote Desktop Access
    # https://www.teamviewer.com
    # ============================================================
    {
        "name": "TeamViewer Relay",
        "provider": "teamviewer",
        "ip_addresses": ["185.188.32.1", "185.188.32.2", "185.188.32.3"],
        "primary_ip": "185.188.32.1",
        "port": 443,
        "hostname": "router.teamviewer.com",
        "tls_enabled": True,
        "heartbeat_interval_ms": 30000,
        "region": "global",
        "description": "TeamViewer relay servers for remote desktop access",
        "is_builtin": True,
    },
    {
        "name": "TeamViewer EU",
        "provider": "teamviewer",
        "ip_addresses": ["185.188.32.2", "185.188.32.1"],
        "primary_ip": "185.188.32.2",
        "port": 443,
        "hostname": "router.teamviewer.com",
        "tls_enabled": True,
        "heartbeat_interval_ms": 30000,
        "region": "eu",
        "description": "TeamViewer relay servers - EU region",
        "is_builtin": True,
    },
    # ============================================================
    # Azure IoT Hub (Placeholder IPs - would need real Azure IPs)
    # https://azure.microsoft.com/services/iot-hub/
    # ============================================================
    {
        "name": "Azure IoT Hub US",
        "provider": "azure_iot",
        "ip_addresses": ["40.76.4.15", "40.76.4.16"],
        "primary_ip": "40.76.4.15",
        "port": 443,
        "hostname": "iothub.azure-devices.net",
        "tls_enabled": True,
        "heartbeat_interval_ms": 60000,
        "region": "us",
        "description": "Azure IoT Hub - US region (example IPs)",
        "is_builtin": True,
    },
    # ============================================================
    # AWS IoT Core (Placeholder IPs - would need real AWS IPs)
    # https://aws.amazon.com/iot-core/
    # ============================================================
    {
        "name": "AWS IoT Core US",
        "provider": "aws_iot",
        "ip_addresses": ["52.94.230.1", "52.94.230.2"],
        "primary_ip": "52.94.230.1",
        "port": 443,
        "hostname": "iot.us-east-1.amazonaws.com",
        "tls_enabled": True,
        "heartbeat_interval_ms": 60000,
        "region": "us-east-1",
        "description": "AWS IoT Core - US East region (example IPs)",
        "is_builtin": True,
    },
]


def get_cloud_service_by_provider_region(
    provider: str,
    region: str | None = None,
) -> dict[str, Any] | None:
    """Get a builtin cloud service by provider and optional region.

    Args:
        provider: Provider name (talk2m, teamviewer, azure_iot, aws_iot)
        region: Optional region filter (us-west, eu, etc.)

    Returns:
        Cloud service data dict or None if not found
    """
    for service in BUILTIN_CLOUD_SERVICES:
        if service["provider"] == provider:
            if region is None or service.get("region") == region:
                return service
    return None


def get_cloud_services_by_provider(provider: str) -> list[dict[str, Any]]:
    """Get all builtin cloud services for a provider.

    Args:
        provider: Provider name (talk2m, teamviewer, azure_iot, aws_iot)

    Returns:
        List of cloud service data dicts
    """
    return [s for s in BUILTIN_CLOUD_SERVICES if s["provider"] == provider]

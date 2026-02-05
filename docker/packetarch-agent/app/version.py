"""PacketArch Agent version information."""

# Semantic versioning: MAJOR.MINOR.PATCH
# - MAJOR: Breaking changes to agent/server protocol
# - MINOR: New features, backward compatible
# - PATCH: Bug fixes, minor improvements
VERSION = "1.4.2"

# Version history:
# 1.4.2 - Synced PROTOCOL_TO_IDENTITY_KEY with canonical source (added enip, s7, bacnet_ip, opc_ua, dnp3, iec104 aliases)
# 1.4.1 - Fixed NameError in PROFINET DCP response (device.device_id -> src.device_id)
# 1.4.0 - Added fingerprint identity support for OPC UA, IEC104, and DNP3 protocols
# 1.3.0 - Added CDP/LLDP discovery for Cisco switches, fixed BACnet unicast polling, fixed protocol port mappings
# 1.2.5 - Simplified updater (no script file), fixed rw mount for self-update
# 1.2.4 - Fixed updater to use alpine with docker-cli-compose (docker:cli not available)
# 1.2.3 - Fixed self-update to spawn external updater container (survives container stop)
# 1.2.2 - Fixed self-update to use down+up instead of force-recreate (avoids name conflicts)
# 1.2.1 - Fixed self-update to mount install directory for docker compose recreate
# 1.2.0 - Added CloudTrafficScheduler for cloud service heartbeats (Talk2M, TeamViewer)
# 1.1.17 - Simplified HTTPS poll logging with !!! markers
# 1.1.15 - Added event loop debug logging for HTTPS flow poll events
# 1.1.14 - Added debug logging for HTTPS external flows
# 1.1.13 - Added Docker CLI to container for self-update support
# 1.1.12 - Fixed BER integer encoding for negative values (ESS temperature readings)
# 1.1.11 - Fixed external flow handling in orchestrator_pool (allow flows without target device)
# 1.1.10 - Added HTTPS external flow support for EWON Talk2M cloud communication
# 1.1.9 - Fixed ALL DeviceContext creations to pass device_name for unique SNMP/PROFINET identities
# 1.1.8 - Made self-update resilient to different install paths (auto-detect or docker restart fallback)
# 1.1.7 - Fixed SNMP sysName and PROFINET station_name to use device_name for unique identification
# 1.1.6 - Added VENDOR_IDENTIFIER polling for BACnet CV detection, increased poll limit to 4
# 1.1.5 - Added device_name and scenario_id fields to DeviceContext
# 1.1.4 - Fixed self-update to use docker compose (restart doesn't pick up new images)
# 1.1.3 - Fixed scenario_id reference error in orchestrator_pool
# 1.1.2 - Fixed device naming for Cyber Vision (PROFINET station_name from device_name)
# 1.1.1 - Fixed fingerprint field name compatibility (fingerprint vs vendor_fingerprint)
# 1.1.0 - Added self-update capability via UPDATE_AGENT command
# 1.0.0 - Initial release with WebSocket-based command/control

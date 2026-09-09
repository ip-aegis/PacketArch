# Remote Traffic Agent

> Moved out of `CLAUDE.md` on 2026-09-09 so the always-loaded file stays a map. Content unchanged.


Agents connect to PacketArch via WebSocket (`/ws/agent?token=<token>`) — "phone home" model, no inbound ports needed.

# Installing an Agent

```bash
# With auto-registration
curl -fsSL https://<SERVER_IP>/agent/install.sh | sudo bash -s -- \
  --server https://<SERVER_IP> --name "Agent-1" --register

# With existing token
curl -fsSL https://<SERVER_IP>/agent/install.sh | sudo bash -s -- \
  --server https://<SERVER_IP> --token "your-agent-token" --interface eth0
```

# Agent Management

```bash
docker compose -f /opt/packetarch-agent/docker-compose.yml logs -f agent   # logs
docker compose -f /opt/packetarch-agent/docker-compose.yml restart          # restart
sudo /opt/packetarch-agent/install.sh --uninstall                           # uninstall
```

# Central Agent Updates

1. "Build Image" in Settings → Agents (builds + saves tarball)
2. Open online agent details → "Update" (sends `UPDATE_AGENT` via WebSocket)
3. Agent downloads tarball, `docker load`, restarts

Requires Docker socket mounted and agent online.

# WebSocket Protocol

**Server → Agent:** `START_SCENARIO`, `STOP_SCENARIO`, `UPDATE_SCENARIO`, `ADAPT_TRAFFIC`, `LIST_INTERFACES`, `UPDATE_AGENT`, `PING`

**Agent → Server:** `STATUS`, `INTERFACES`, `ERROR`, `HEARTBEAT` (CPU/memory/version), `UPDATE_STATUS`

# Key Files

**Agent (`docker/packetarch-agent/`):** `app/main.py`, `app/websocket_client.py`, `app/orchestrator_pool.py`, `app/version.py`, `app/config.py`

**Backend:** `api/websocket/agent_hub.py`, `services/agent_manager.py`, `api/routes/agents.py`, `api/routes/adaptation.py`, `services/adaptation_service.py`


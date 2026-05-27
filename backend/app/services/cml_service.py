# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Cisco Modeling Labs (CML) API service.

Pure CML client (no PacketArch DB imports) — mirrors CyberVisionService.
Authenticates with username/password to obtain a short-lived JWT (CML 2.x has
no static API token), caches it, and re-auths once on 401. Provides read
methods for the lab/node pickers and a `deploy_agent` orchestration that
auto-provisions a stock Ubuntu node running the PacketArch agent via cloud-init.

Reference topology (the manually-built "PacketAgent-CML" in LAN Lab A):
    ens2 -> unmanaged-switch -> external_connector   (management / phone-home egress)
    ens3 -> lab L2 switch                            (data / traffic injection)
`deploy_agent` reproduces that wiring automatically.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

# Node definitions that are infrastructure, not valid data-attach targets.
_INFRA_NODE_DEFS = {"external_connector", "unmanaged_switch"}


@dataclass
class CMLConnectionResult:
    """Result of a CML connection test."""

    success: bool
    message: str
    version: str | None = None
    ready: bool | None = None


@dataclass
class CMLInterface:
    """An interface on a CML node."""

    id: str
    label: str
    slot: int | None = None
    is_connected: bool = False


@dataclass
class CMLNode:
    """A node inside a CML lab."""

    id: str
    label: str
    node_definition: str
    state: str
    interfaces: list[CMLInterface] = field(default_factory=list)

    @property
    def is_infrastructure(self) -> bool:
        return self.node_definition in _INFRA_NODE_DEFS


@dataclass
class CMLLab:
    """A CML lab summary."""

    id: str
    title: str
    state: str
    node_count: int
    owner: str | None = None


@dataclass
class CMLDeployResult:
    """Result of a deploy_agent operation."""

    success: bool
    message: str
    lab_id: str
    node_id: str | None = None
    node_label: str | None = None
    data_wired: bool = False
    mgmt_wired: bool = False
    started: bool = False
    warnings: list[str] = field(default_factory=list)


@dataclass
class CMLLabBuildResult:
    """Result of a build_lab (self-contained lab) operation."""

    success: bool
    message: str
    lab_id: str | None = None
    agent_node_id: str | None = None
    switch_node_id: str | None = None
    sensor_node_id: str | None = None
    sensor_serial: str | None = None
    started: bool = False
    warnings: list[str] = field(default_factory=list)


class CMLService:
    """Service for interacting with the Cisco Modeling Labs API (v0)."""

    API = "/api/v0"

    def __init__(self, base_url: str, username: str, password: str, verify_ssl: bool = False):
        """Initialize the CML service.

        Args:
            base_url: CML base URL (e.g., https://10.10.20.230)
            username: CML username
            password: CML password
            verify_ssl: Whether to verify SSL certificates (default False for self-signed)
        """
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self._client: httpx.AsyncClient | None = None
        self._jwt: str | None = None
        self._jwt_obtained_at: float = 0.0
        self._jwt_ttl = 23 * 3600  # refresh well before CML's ~24h expiry

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client (JWT injected per-request, not here)."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                verify=self.verify_ssl,
                timeout=30.0,
                headers={"Accept": "application/json", "Content-Type": "application/json"},
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    # --- Auth ---------------------------------------------------------------

    async def _authenticate(self) -> str:
        """Authenticate and cache a JWT. Raises on failure."""
        client = await self._get_client()
        url = f"{self.base_url}{self.API}/authenticate"
        resp = await client.post(url, json={"username": self.username, "password": self.password})
        resp.raise_for_status()
        # CML returns the JWT as a bare JSON string.
        token = resp.json()
        if not isinstance(token, str):
            raise ValueError("Unexpected authentication response from CML")
        self._jwt = token
        self._jwt_obtained_at = time.monotonic()
        return token

    async def _ensure_jwt(self) -> str:
        if self._jwt is None or (time.monotonic() - self._jwt_obtained_at) > self._jwt_ttl:
            await self._authenticate()
        return self._jwt  # type: ignore[return-value]

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict | None = None,
        json: dict | None = None,
        _retry: bool = True,
    ):
        """Make an authenticated CML API request, re-authing once on 401.

        Returns parsed JSON (str, list, or dict). Raises httpx.HTTPStatusError
        on non-2xx (after the single 401 re-auth attempt).
        """
        token = await self._ensure_jwt()
        client = await self._get_client()
        url = f"{self.base_url}{self.API}{endpoint}"
        logger.debug("CML API request: %s %s", method, url)
        resp = await client.request(
            method, url, params=params, json=json,
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code == 401 and _retry:
            self._jwt = None  # force a single re-auth + retry
            return await self._request(method, endpoint, params=params, json=json, _retry=False)
        resp.raise_for_status()
        if not resp.content:
            return None
        try:
            return resp.json()
        except ValueError:
            return resp.text

    # --- Read methods (pickers + status) ------------------------------------

    async def test_connection(self) -> CMLConnectionResult:
        """Test the connection; never raises."""
        try:
            info = await self._request("GET", "/system_information")
            version = info.get("version") if isinstance(info, dict) else None
            ready = info.get("ready") if isinstance(info, dict) else None
            return CMLConnectionResult(
                success=True, message="Connected to Cisco Modeling Labs",
                version=version, ready=ready,
            )
        except httpx.HTTPStatusError as e:
            code = e.response.status_code
            msg = "Invalid username or password" if code in (401, 403) else f"API error: {code}"
            logger.error("CML API error: %s - %s", code, e.response.text[:200])
            return CMLConnectionResult(success=False, message=msg)
        except httpx.RequestError as e:
            logger.error("CML connection error: %s", e)
            return CMLConnectionResult(success=False, message=f"Connection failed: {e}")
        except Exception as e:
            logger.exception("Unexpected error testing CML connection")
            return CMLConnectionResult(success=False, message=f"Unexpected error: {e}")

    async def list_labs(self) -> list[CMLLab]:
        """List all labs the user can see (id, title, state, node_count)."""
        lab_ids = await self._request("GET", "/labs")
        labs: list[CMLLab] = []
        for lab_id in lab_ids or []:
            lab = await self.get_lab(lab_id)
            if lab:
                labs.append(lab)
        return labs

    async def get_lab(self, lab_id: str) -> CMLLab | None:
        """Get a single lab's details."""
        try:
            d = await self._request("GET", f"/labs/{lab_id}")
        except httpx.HTTPStatusError:
            return None
        if not isinstance(d, dict):
            return None
        return CMLLab(
            id=lab_id,
            title=d.get("lab_title") or lab_id,
            state=d.get("state", "UNKNOWN"),
            node_count=d.get("node_count", 0),
            owner=d.get("owner_username"),
        )

    async def list_lab_nodes(self, lab_id: str) -> list[CMLNode]:
        """List nodes in a lab with their interfaces, marking connected ports.

        Powers both the target-node selector and the per-node port selector.
        """
        nodes_raw = await self._request(
            "GET", f"/labs/{lab_id}/nodes", params={"data": "true", "operational": "true"}
        )
        # Map of interface id -> connected (from links)
        connected_ifaces = await self._connected_interface_ids(lab_id)

        nodes: list[CMLNode] = []
        for n in nodes_raw or []:
            if not isinstance(n, dict):
                continue
            node_id = n["id"]
            ifaces_raw = await self._request(
                "GET", f"/labs/{lab_id}/nodes/{node_id}/interfaces", params={"data": "true"}
            )
            interfaces: list[CMLInterface] = []
            for i in ifaces_raw or []:
                if not isinstance(i, dict):
                    continue
                # Skip the internal "loopback"/management port type when present.
                if i.get("type") and i.get("type") != "physical":
                    continue
                interfaces.append(CMLInterface(
                    id=i["id"],
                    label=i.get("label", ""),
                    slot=i.get("slot"),
                    is_connected=i["id"] in connected_ifaces,
                ))
            interfaces.sort(key=lambda x: (x.slot is None, x.slot))
            nodes.append(CMLNode(
                id=node_id,
                label=n.get("label", node_id),
                node_definition=n.get("node_definition", ""),
                state=n.get("state", "UNKNOWN"),
                interfaces=interfaces,
            ))
        return nodes

    async def _connected_interface_ids(self, lab_id: str) -> set[str]:
        """Return the set of interface IDs that already have a link."""
        links = await self._request("GET", f"/labs/{lab_id}/links", params={"data": "true"})
        connected: set[str] = set()
        for link in links or []:
            if isinstance(link, dict):
                for key in ("interface_a", "interface_b", "src_int", "dst_int"):
                    if link.get(key):
                        connected.add(link[key])
        return connected

    # --- Deploy orchestration ----------------------------------------------

    def _build_cloud_init(self, *, agent_name: str, token: str, server: str, insecure: bool,
                          install_url_path: str) -> str:
        """Build the cloud-init user-data that installs the PacketArch agent.

        This is the single install-specific seam: a future pre-baked node
        definition can swap this for a minimal "write .env + docker compose up".
        """
        slug = "".join(c if (c.isalnum() or c == "-") else "-" for c in agent_name).strip("-").lower() or "packetarch-agent"
        insecure_flag = " --insecure" if insecure else ""
        return f"""#cloud-config
hostname: {slug}
manage_etc_hosts: true
write_files:
  - path: /etc/netplan/99-packetarch.yaml
    permissions: '0600'
    content: |
      network:
        version: 2
        ethernets:
          ens2:
            dhcp4: true
            optional: true
          ens3:
            dhcp4: true
            optional: true
runcmd:
  - netplan apply
  - [ bash, -c, "for i in $(seq 1 60); do curl -fsSLk {server}/health >/dev/null 2>&1 && break; sleep 5; done" ]
  - [ bash, -c, "curl -fsSLk {server}{install_url_path} | bash -s -- --server {server} --token '{token}' --name '{agent_name}' --interface ens3{insecure_flag}" ]
"""

    async def _create_node(self, lab_id: str, *, label: str, node_definition: str,
                           image_definition: str, ram_mb: int, cpus: int,
                           configuration: str, x: int, y: int) -> str:
        # Only include optional fields when meaningful — CML rejects an empty
        # image_definition string, and switches/connectors carry no image/ram/cpus.
        body: dict = {"x": x, "y": y, "label": label, "node_definition": node_definition}
        if image_definition:
            body["image_definition"] = image_definition
        if ram_mb:
            body["ram"] = ram_mb
        if cpus:
            body["cpus"] = cpus
        if configuration:
            body["configuration"] = configuration
        node = await self._request("POST", f"/labs/{lab_id}/nodes", json=body)
        if isinstance(node, dict) and node.get("id"):
            return node["id"]
        if isinstance(node, str):  # some CML builds return the bare id
            return node
        raise ValueError(f"Unexpected node-create response: {node!r}")

    async def _create_interface(self, lab_id: str, node_id: str, slot: int) -> str:
        """Create an interface at `slot` on a node; return its id.

        CML may create intermediate slots and return a list; pick the one
        matching the requested slot (else the last).
        """
        result = await self._request(
            "POST", f"/labs/{lab_id}/interfaces", json={"node": node_id, "slot": slot}
        )
        items = result if isinstance(result, list) else [result]
        chosen = None
        for it in items:
            if isinstance(it, dict):
                if it.get("slot") == slot:
                    return it["id"]
                chosen = it
        if isinstance(chosen, dict):
            return chosen["id"]
        raise ValueError(f"Unexpected interface-create response: {result!r}")

    async def _iface_for_slot(self, lab_id: str, node_id: str, slot: int, create: bool = False) -> str | None:
        """Resolve the interface id for a node's slot, optionally creating it."""
        ifaces = await self._request(
            "GET", f"/labs/{lab_id}/nodes/{node_id}/interfaces", params={"data": "true"}
        )
        for i in ifaces or []:
            if isinstance(i, dict) and i.get("slot") == slot:
                return i["id"]
        if create:
            return await self._create_interface(lab_id, node_id, slot)
        return None

    async def _next_switch_port(self, lab_id: str, switch_id: str) -> str:
        """Get a free port on an unmanaged switch, creating a new one."""
        connected = await self._connected_interface_ids(lab_id)
        ifaces = await self._request(
            "GET", f"/labs/{lab_id}/nodes/{switch_id}/interfaces", params={"data": "true"}
        )
        slots = [i.get("slot", 0) for i in (ifaces or []) if isinstance(i, dict)]
        for i in ifaces or []:
            if isinstance(i, dict) and i["id"] not in connected:
                return i["id"]
        next_slot = (max(slots) + 1) if slots else 0
        return await self._create_interface(lab_id, switch_id, next_slot)

    async def _link(self, lab_id: str, src_int: str, dst_int: str) -> None:
        await self._request("POST", f"/labs/{lab_id}/links", json={"src_int": src_int, "dst_int": dst_int})

    async def _ensure_management_switch(self, lab_id: str, nodes: list[dict]) -> tuple[str, list[str]]:
        """Ensure an unmanaged switch bridged to an external connector exists.

        Reuses the reference topology (host -> unmanaged-switch -> external_connector)
        when present, otherwise builds it. Returns (switch_node_id, warnings). Grab
        ports off the returned switch with `_next_switch_port`, linking each before
        requesting the next so free-port detection doesn't hand back the same one.
        """
        warnings: list[str] = []
        connectors = [n for n in nodes if n.get("node_definition") == "external_connector"]
        switches = [n for n in nodes if n.get("node_definition") == "unmanaged_switch"]
        links = await self._request("GET", f"/labs/{lab_id}/links", params={"data": "true"})

        # 1. A switch already wired to a connector -> reuse it.
        connector_ids = {c["id"] for c in connectors}
        for sw in switches:
            for link in links or []:
                if not isinstance(link, dict):
                    continue
                a, b = link.get("node_a"), link.get("node_b")
                if sw["id"] in (a, b) and (a in connector_ids or b in connector_ids):
                    return sw["id"], warnings

        # 2. Connector exists but no switch wired to it -> add a switch and link it.
        if connectors:
            connector = connectors[0]
            switch_id = await self._create_node(
                lab_id, label="pa-mgmt-switch", node_definition="unmanaged_switch",
                image_definition="", ram_mb=0, cpus=0, configuration="", x=-260, y=-120,
            )
            conn_port = await self._iface_for_slot(lab_id, connector["id"], 0, create=True)
            sw_uplink = await self._create_interface(lab_id, switch_id, 0)
            await self._link(lab_id, sw_uplink, conn_port)
            warnings.append("Created a management switch wired to the existing external connector.")
            return switch_id, warnings

        # 3. No connector at all -> build connector + switch.
        connector_id = await self._create_node(
            lab_id, label="pa-ext-conn", node_definition="external_connector",
            image_definition="", ram_mb=0, cpus=0, configuration="System Bridge", x=-340, y=-200,
        )
        switch_id = await self._create_node(
            lab_id, label="pa-mgmt-switch", node_definition="unmanaged_switch",
            image_definition="", ram_mb=0, cpus=0, configuration="", x=-260, y=-120,
        )
        conn_port = await self._create_interface(lab_id, connector_id, 0)
        sw_uplink = await self._create_interface(lab_id, switch_id, 0)
        await self._link(lab_id, sw_uplink, conn_port)
        warnings.append(
            "Created an external connector (System Bridge) and management switch for egress. "
            "Verify the System Bridge has outbound network access in this CML install."
        )
        return switch_id, warnings

    async def _ensure_management_egress(self, lab_id: str, nodes: list[dict]) -> tuple[str, list[str]]:
        """Ensure egress exists; return (free_switch_port_interface_id, warnings)."""
        switch_id, warnings = await self._ensure_management_switch(lab_id, nodes)
        port = await self._next_switch_port(lab_id, switch_id)
        return port, warnings

    async def deploy_agent(
        self,
        *,
        lab_id: str,
        agent_name: str,
        agent_token: str,
        packetarch_server_url: str,
        verify_server_ssl: bool,
        data_attachment: dict | None,
        start_node: bool = False,
        cpus: int = 2,
        ram_mb: int = 3072,
        node_definition: str = "ubuntu",
        image_definition: str = "ubuntu-24-04-20241004",
        install_url_path: str = "/agent/install.sh",
    ) -> CMLDeployResult:
        """Provision a configured agent node in a lab. Never raises; returns a result."""
        warnings: list[str] = []
        try:
            lab = await self.get_lab(lab_id)
            if lab is None:
                return CMLDeployResult(False, f"Lab {lab_id} not found", lab_id)

            # 1. cloud-init user-data (swappable seam)
            cloud_init = self._build_cloud_init(
                agent_name=agent_name, token=agent_token,
                server=packetarch_server_url.rstrip("/"),
                insecure=not verify_server_ssl, install_url_path=install_url_path,
            )

            # 2. create the agent node
            node_id = await self._create_node(
                lab_id, label=agent_name, node_definition=node_definition,
                image_definition=image_definition, ram_mb=ram_mb, cpus=cpus,
                configuration=cloud_init, x=-200, y=40,
            )

            # 3. interfaces: slot 0 = ens2 (mgmt), slot 1 = ens3 (data). Created so
            #    the NICs exist and DEFAULT_INTERFACE=ens3 resolves, even when the
            #    operator wires them manually.
            mgmt_iface = await self._create_interface(lab_id, node_id, 0)
            data_iface = await self._create_interface(lab_id, node_id, 1)

            # 4 + 5. Wiring. "Just drop it in" (data_attachment is None) means NO
            #    links at all — the operator wires management AND data manually.
            #    When a data attachment is chosen we wire management egress (so the
            #    agent can phone home) plus the requested data link.
            data_wired = False
            mgmt_wired = False
            if data_attachment:
                # management egress
                nodes_raw = await self._request("GET", f"/labs/{lab_id}/nodes", params={"data": "true"})
                nodes = [n for n in (nodes_raw or []) if isinstance(n, dict) and n.get("id") != node_id]
                switch_port, mgmt_warnings = await self._ensure_management_egress(lab_id, nodes)
                warnings.extend(mgmt_warnings)
                await self._link(lab_id, mgmt_iface, switch_port)
                mgmt_wired = True
                # data attachment
                target_node = data_attachment["target_node_id"]
                slot = int(data_attachment["slot"])
                connected = await self._connected_interface_ids(lab_id)
                target_iface = await self._iface_for_slot(lab_id, target_node, slot, create=True)
                if target_iface and target_iface in connected:
                    warnings.append(
                        f"Target port (slot {slot}) was already connected; skipped data wiring."
                    )
                elif target_iface:
                    await self._link(lab_id, data_iface, target_iface)
                    data_wired = True
                else:
                    warnings.append("Could not resolve the target data port; skipped data wiring.")

            # 6. start (optional; default off so the operator controls boot)
            started = False
            if start_node:
                if lab.state == "STARTED":
                    await self._request("PUT", f"/labs/{lab_id}/nodes/{node_id}/state/start")
                else:
                    await self._request("PUT", f"/labs/{lab_id}/start")
                    warnings.append(
                        f"Lab was {lab.state}; started the entire lab to bring the agent online."
                    )
                started = True

            # message
            if started:
                msg = "Agent node deployed and started; it will phone home once cloud-init finishes."
            else:
                msg = (
                    "Agent node deployed (not started). Boot it in CML when ready — it installs "
                    "the agent and phones home on first boot."
                )
            if not data_attachment:
                msg += " No links were created; wire the management and data interfaces in CML."

            return CMLDeployResult(
                success=True, message=msg, lab_id=lab_id, node_id=node_id, node_label=agent_name,
                data_wired=data_wired, mgmt_wired=mgmt_wired, started=started, warnings=warnings,
            )

        except httpx.HTTPStatusError as e:
            logger.error("CML deploy API error: %s - %s", e.response.status_code, e.response.text[:300])
            return CMLDeployResult(
                False, f"CML API error {e.response.status_code}: {e.response.text[:200]}",
                lab_id, warnings=warnings,
            )
        except Exception as e:
            logger.exception("CML deploy failed")
            return CMLDeployResult(False, f"Deploy failed: {e}", lab_id, warnings=warnings)

    async def _node_state(self, lab_id: str, node_id: str) -> str | None:
        try:
            d = await self._request("GET", f"/labs/{lab_id}/nodes/{node_id}/state")
        except httpx.HTTPStatusError:
            return None
        if isinstance(d, dict):
            return d.get("state")
        if isinstance(d, str):
            return d
        return None

    async def undeploy_node(self, lab_id: str, node_id: str, *, stop_timeout: float = 120.0) -> None:
        """Decommission a node: stop -> wait -> wipe -> delete links -> delete node.

        CML requires a node to be both STOPPED and WIPED before it can be
        deleted (a running or un-wiped node returns 400). Node stop is
        asynchronous, so we poll the node state until it is stopped, then wipe
        its disks, remove any links, and delete the node.
        """
        import asyncio

        stopped_states = {"STOPPED", "DEFINED_ON_CORE"}

        # 1. Stop (ignore if already stopped / not started).
        try:
            await self._request("PUT", f"/labs/{lab_id}/nodes/{node_id}/state/stop")
        except httpx.HTTPStatusError:
            pass

        # 2. Wait for the node to reach a stopped state.
        deadline = time.monotonic() + stop_timeout
        while time.monotonic() < deadline:
            state = await self._node_state(lab_id, node_id)
            if state is None or state in stopped_states:
                break
            await asyncio.sleep(3)

        # 3. Wipe disks (required before delete; harmless if already wiped).
        try:
            await self._request("PUT", f"/labs/{lab_id}/nodes/{node_id}/wipe_disks")
        except httpx.HTTPStatusError:
            pass

        # 4. Delete links touching this node.
        links = await self._request("GET", f"/labs/{lab_id}/links", params={"data": "true"})
        for link in links or []:
            if isinstance(link, dict) and node_id in (link.get("node_a"), link.get("node_b")):
                try:
                    await self._request("DELETE", f"/labs/{lab_id}/links/{link['id']}")
                except httpx.HTTPStatusError:
                    pass

        # 5. Delete the node.
        await self._request("DELETE", f"/labs/{lab_id}/nodes/{node_id}")

    # --- Self-contained lab builder -----------------------------------------

    async def create_lab(self, title: str, description: str = "") -> str:
        """Create a new (empty) lab; return its id."""
        d = await self._request("POST", "/labs", json={"title": title, "description": description})
        if isinstance(d, dict) and d.get("id"):
            return d["id"]
        if isinstance(d, str):
            return d
        raise ValueError(f"Unexpected lab-create response: {d!r}")

    @staticmethod
    def decode_provisioning_token(token: str) -> dict:
        """Base64-decode the (unverified) JWT payload of a CV provisioning token.

        Returns {serialNumber, centerHost, captureMode, nonce, ...} or {} on failure.
        """
        import base64
        import json
        try:
            payload = token.split(".")[1]
            payload += "=" * (-len(payload) % 4)
            return json.loads(base64.urlsafe_b64decode(payload))
        except Exception:
            return {}

    def _build_iosvl2_span_config(self, hostname: str = "pa-span-sw") -> str:
        """IOSvL2 startup-config: bring up Gi0/0 (agent) + Gi0/1 (sensor) and SPAN
        all Gi0/0 traffic to Gi0/1 (the sensor's capture port)."""
        safe = "".join(c if (c.isalnum() or c in "-_") else "-" for c in hostname)[:60] or "pa-span-sw"
        return (
            f"hostname {safe}\n"
            "!\n"
            "interface GigabitEthernet0/0\n"
            " no shutdown\n"
            "!\n"
            "interface GigabitEthernet0/1\n"
            " no shutdown\n"
            "!\n"
            "monitor session 1 source interface GigabitEthernet0/0 both\n"
            "monitor session 1 destination interface GigabitEthernet0/1\n"
            "!\n"
            "end\n"
        )

    @staticmethod
    def parse_sensor_compose(compose: str) -> dict:
        """Extract token / serial / image / registry from a CV-generated
        docker-compose YAML (the file CV hands you when deploying a docker sensor).
        Returns {token, serial, image, registry} (values may be None)."""
        import re

        def grab(pat: str) -> str | None:
            m = re.search(pat, compose)
            return m.group(1).strip().strip('"').strip("'") if m else None

        token = grab(r"PROVISIONING_TOKEN\s*[=:]\s*(\S+)")
        serial = grab(r"SERIAL_NUMBER\s*[=:]\s*(\S+)")
        image = grab(r"image:\s*(\S+)")
        registry = image.rsplit("/", 1)[0] if image and "/" in image else None
        return {"token": token, "serial": serial, "image": image, "registry": registry}

    def _build_cv_sensor_cloud_init(self, *, sensor_compose: str, registry: str) -> str:
        """cloud-init for the CV sensor host: install Docker, trust the Center
        registry, write the operator-pasted CV docker-compose verbatim (capture
        macvlan parent forced to ens3 = the SPAN-fed NIC on slot 1), and bring it
        up so it ZTP-enrolls."""
        import base64
        import re

        # The sensor node's capture NIC is ens3 (slot 1, wired to the SPAN dest),
        # so force the macvlan parent to ens3 regardless of what CV emitted.
        compose = re.sub(r"parent:\s*\S+", "parent: ens3", sensor_compose)
        compose_b64 = base64.b64encode(compose.encode()).decode()
        return f"""#cloud-config
hostname: cv-sensor
manage_etc_hosts: true
write_files:
  - path: /etc/netplan/99-packetarch.yaml
    permissions: '0600'
    content: |
      network:
        version: 2
        ethernets:
          ens2:
            dhcp4: true
            optional: true
          ens3:
            dhcp4: false
            optional: true
  - path: /etc/docker/daemon.json
    content: |
      {{"insecure-registries": ["{registry}"]}}
  - path: /opt/cv-sensor/docker-compose.yml
    encoding: b64
    content: {compose_b64}
runcmd:
  - netplan apply
  - ip link set ens3 up || true
  - [ bash, -c, "command -v docker >/dev/null 2>&1 || curl -fsSL https://get.docker.com | sh" ]
  - systemctl enable --now docker
  - systemctl restart docker
  - [ bash, -c, "for i in $(seq 1 60); do curl -fsSLk https://{registry}/ >/dev/null 2>&1 && break; sleep 5; done" ]
  - [ bash, -c, "cd /opt/cv-sensor && docker compose up -d" ]
"""

    async def build_lab(
        self,
        *,
        lab_name: str,
        agent_name: str,
        agent_token: str,
        packetarch_server_url: str,
        verify_server_ssl: bool,
        sensor_compose: str,
        sensor_serial: str,
        registry: str,
        start_lab: bool = False,
        agent_cpus: int = 2,
        agent_ram_mb: int = 3072,
        sensor_cpus: int = 2,
        sensor_ram_mb: int = 4096,
    ) -> CMLLabBuildResult:
        """Build a self-contained monitoring lab: external connector + mgmt switch,
        a PacketArch agent, an IOSvL2 switch with a SPAN session, and a CV sensor
        host. Agent ens3 -> Gi0/0 (traffic), sensor ens3 -> Gi0/1 (SPAN capture);
        both mgmt NICs -> the egress switch. Never raises; returns a result."""
        warnings: list[str] = []
        lab_id: str | None = None
        try:
            lab_id = await self.create_lab(
                f"PacketArch Lab — {lab_name}", "Self-contained agent + CV sensor lab built by PacketArch"
            )

            # external connector + mgmt switch (empty lab -> builds both)
            switch_id, w = await self._ensure_management_switch(lab_id, [])
            warnings.extend(w)

            # IOSvL2 switch with SPAN baked into its startup-config
            iosvl2_id = await self._create_node(
                lab_id, label="SPAN-Switch", node_definition="iosvl2",
                image_definition="iosvl2-2020", ram_mb=768, cpus=1,
                configuration=self._build_iosvl2_span_config(), x=-40, y=40,
            )
            gi0 = await self._create_interface(lab_id, iosvl2_id, 0)  # Gi0/0 = agent data
            gi1 = await self._create_interface(lab_id, iosvl2_id, 1)  # Gi0/1 = sensor capture

            # agent node (reuse the same cloud-init installer as deploy_agent)
            agent_ci = self._build_cloud_init(
                agent_name=agent_name, token=agent_token,
                server=packetarch_server_url.rstrip("/"),
                insecure=not verify_server_ssl, install_url_path="/agent/install.sh",
            )
            agent_id = await self._create_node(
                lab_id, label=agent_name, node_definition="ubuntu",
                image_definition="ubuntu-24-04-20241004", ram_mb=agent_ram_mb, cpus=agent_cpus,
                configuration=agent_ci, x=-260, y=-40,
            )
            agent_ens2 = await self._create_interface(lab_id, agent_id, 0)
            agent_ens3 = await self._create_interface(lab_id, agent_id, 1)

            # CV sensor host
            sensor_ci = self._build_cv_sensor_cloud_init(
                sensor_compose=sensor_compose, registry=registry,
            )
            sensor_id = await self._create_node(
                lab_id, label=f"CV-Sensor-{sensor_serial}", node_definition="ubuntu",
                image_definition="ubuntu-24-04-20241004", ram_mb=sensor_ram_mb, cpus=sensor_cpus,
                configuration=sensor_ci, x=-260, y=120,
            )
            sensor_ens2 = await self._create_interface(lab_id, sensor_id, 0)
            sensor_ens3 = await self._create_interface(lab_id, sensor_id, 1)

            # data plane: agent ens3 -> Gi0/0 ; sensor ens3 -> Gi0/1 (SPAN dest)
            await self._link(lab_id, agent_ens3, gi0)
            await self._link(lab_id, sensor_ens3, gi1)

            # management egress: link each before requesting the next free port
            agent_mgmt = await self._next_switch_port(lab_id, switch_id)
            await self._link(lab_id, agent_ens2, agent_mgmt)
            sensor_mgmt = await self._next_switch_port(lab_id, switch_id)
            await self._link(lab_id, sensor_ens2, sensor_mgmt)

            started = False
            if start_lab:
                await self._request("PUT", f"/labs/{lab_id}/start")
                started = True

            msg = "Lab built and started." if started else (
                "Lab built (not started). Start it in CML when ready; the agent and sensor "
                "install + enroll on first boot."
            )
            return CMLLabBuildResult(
                success=True, message=msg, lab_id=lab_id, agent_node_id=agent_id,
                switch_node_id=iosvl2_id, sensor_node_id=sensor_id, sensor_serial=sensor_serial,
                started=started, warnings=warnings,
            )

        except httpx.HTTPStatusError as e:
            logger.error("CML build_lab API error: %s - %s", e.response.status_code, e.response.text[:300])
            return CMLLabBuildResult(
                False, f"CML API error {e.response.status_code}: {e.response.text[:200]}",
                lab_id=lab_id, warnings=warnings,
            )
        except Exception as e:
            logger.exception("CML build_lab failed")
            return CMLLabBuildResult(False, f"Lab build failed: {e}", lab_id=lab_id, warnings=warnings)

    async def teardown_lab(self, lab_id: str, *, stop_timeout: float = 180.0) -> None:
        """Stop -> wait -> wipe all nodes -> delete the lab. Used to decommission a
        PacketArch-built lab in one step."""
        import asyncio

        try:
            await self._request("PUT", f"/labs/{lab_id}/stop")
        except httpx.HTTPStatusError:
            pass

        deadline = time.monotonic() + stop_timeout
        while time.monotonic() < deadline:
            lab = await self.get_lab(lab_id)
            if lab is None or lab.state in ("STOPPED", "DEFINED_ON_CORE"):
                break
            await asyncio.sleep(3)

        node_ids = await self._request("GET", f"/labs/{lab_id}/nodes")
        for nid in node_ids or []:
            try:
                await self._request("PUT", f"/labs/{lab_id}/nodes/{nid}/wipe_disks")
            except httpx.HTTPStatusError:
                pass

        await self._request("DELETE", f"/labs/{lab_id}")


async def get_cml_service(base_url: str, username: str, password: str, verify_ssl: bool = False) -> CMLService:
    """Factory mirroring get_cv_service usage."""
    return CMLService(base_url, username, password, verify_ssl)

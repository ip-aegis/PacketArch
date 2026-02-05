"""WebSocket client for connecting to PacketArch server."""

import asyncio
import json
import logging
import platform
import ssl
import psutil
from typing import Any, Callable, Coroutine

import websockets
from websockets.exceptions import ConnectionClosed, InvalidStatusCode

from app.config import AgentConfig
from app.version import VERSION

logger = logging.getLogger(__name__)


class AgentWebSocket:
    """WebSocket client with auto-reconnect for agent communication."""

    def __init__(
        self,
        config: AgentConfig,
        on_command: Callable[[dict[str, Any]], Coroutine[Any, Any, None]],
    ):
        """Initialize WebSocket client.

        Args:
            config: Agent configuration
            on_command: Async callback for handling commands from server
        """
        self.config = config
        self.on_command = on_command
        self.ws: websockets.WebSocketClientProtocol | None = None
        self._running = False
        self._connected = False
        self._heartbeat_task: asyncio.Task | None = None

    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self._connected and self.ws is not None

    async def connect(self) -> None:
        """Connect to server with auto-reconnect loop."""
        self._running = True

        # Create SSL context for self-signed certificates if needed
        ssl_context = None
        if self.config.websocket_url.startswith("wss://"):
            if self.config.ssl_verify:
                ssl_context = ssl.create_default_context()
            else:
                logger.warning("SSL certificate verification disabled")
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

        while self._running:
            try:
                logger.info(f"Connecting to {self.config.websocket_url}...")
                async with websockets.connect(
                    self.config.websocket_url,
                    ssl=ssl_context,
                    ping_interval=30,
                    ping_timeout=10,
                    close_timeout=5,
                ) as ws:
                    self.ws = ws
                    self._connected = True
                    logger.info("Connected to PacketArch server")

                    # Start heartbeat task
                    self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

                    # Enter message loop
                    await self._message_loop()

            except InvalidStatusCode as e:
                logger.error(f"Authentication failed (HTTP {e.status_code})")
                if e.status_code == 401:
                    logger.error("Invalid agent token. Check AGENT_TOKEN environment variable.")
                    # Don't retry on auth failure
                    self._running = False
                    break
                elif e.status_code == 403:
                    logger.error("Agent not authorized. Check agent registration.")
                    self._running = False
                    break

            except ConnectionClosed as e:
                logger.warning(f"Connection closed: {e.code} - {e.reason}")

            except Exception as e:
                logger.error(f"Connection error: {e}")

            finally:
                self._connected = False
                self.ws = None
                if self._heartbeat_task:
                    self._heartbeat_task.cancel()
                    try:
                        await self._heartbeat_task
                    except asyncio.CancelledError:
                        pass
                    self._heartbeat_task = None

            if self._running:
                logger.info(
                    f"Reconnecting in {self.config.reconnect_delay_seconds}s..."
                )
                await asyncio.sleep(self.config.reconnect_delay_seconds)

    async def _message_loop(self) -> None:
        """Process incoming messages from server."""
        if not self.ws:
            return

        async for message in self.ws:
            try:
                data = json.loads(message)
                msg_type = data.get("type", "")

                if msg_type == "PING":
                    await self.send({"type": "PONG"})
                elif msg_type == "CONNECTED":
                    logger.info(f"Server acknowledged connection: {data}")
                else:
                    # Dispatch to command handler
                    await self.on_command(data)

            except json.JSONDecodeError:
                logger.error(f"Invalid JSON message: {message[:100]}")
            except Exception as e:
                logger.error(f"Error handling message: {e}")

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats with system stats."""
        while self._running and self._connected:
            try:
                await asyncio.sleep(self.config.heartbeat_interval_seconds)

                if self._connected:
                    heartbeat = self._build_heartbeat()
                    await self.send(heartbeat)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

    def _build_heartbeat(self) -> dict[str, Any]:
        """Build heartbeat message with system stats."""
        try:
            cpu_percent = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
        except Exception:
            cpu_percent = 0.0
            memory_percent = 0.0

        return {
            "type": "HEARTBEAT",
            "cpu": cpu_percent,
            "memory": memory_percent,
            "hostname": platform.node(),
            "platform": platform.system(),
            "version": VERSION,
        }

    async def send(self, message: dict[str, Any]) -> bool:
        """Send a message to the server.

        Args:
            message: Message dict to send

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.ws or not self._connected:
            logger.warning("Cannot send message: not connected")
            return False

        try:
            await self.ws.send(json.dumps(message))
            return True
        except Exception as e:
            logger.error(f"Send error: {e}")
            return False

    async def send_status(
        self,
        scenario_id: str,
        state: str,
        packets_sent: int = 0,
        error: str | None = None,
    ) -> bool:
        """Send scenario status update to server.

        Args:
            scenario_id: Scenario UUID
            state: Current state (starting, running, stopping, stopped, error)
            packets_sent: Number of packets sent so far
            error: Error message if state is 'error'

        Returns:
            True if sent successfully
        """
        message: dict[str, Any] = {
            "type": "STATUS",
            "scenario_id": scenario_id,
            "state": state,
            "packets_sent": packets_sent,
        }
        if error:
            message["error"] = error

        return await self.send(message)

    async def send_interfaces(
        self,
        request_id: str,
        interfaces: list[dict[str, Any]],
    ) -> bool:
        """Send interface list response to server.

        Args:
            request_id: Original request ID
            interfaces: List of interface info dicts

        Returns:
            True if sent successfully
        """
        return await self.send({
            "type": "INTERFACES",
            "request_id": request_id,
            "interfaces": interfaces,
        })

    async def send_error(
        self,
        scenario_id: str | None,
        message: str,
        code: str = "UNKNOWN_ERROR",
    ) -> bool:
        """Send error message to server.

        Args:
            scenario_id: Related scenario UUID (if applicable)
            message: Error message
            code: Error code

        Returns:
            True if sent successfully
        """
        return await self.send({
            "type": "ERROR",
            "scenario_id": scenario_id,
            "message": message,
            "code": code,
        })

    def stop(self) -> None:
        """Stop the WebSocket client."""
        self._running = False
        if self.ws:
            asyncio.create_task(self.ws.close())

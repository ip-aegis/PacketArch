# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Integration tests for traffic generation endpoints."""

import pytest
from uuid import uuid4
from httpx import AsyncClient
from unittest.mock import patch, MagicMock



class TestGenerationProtocols:
    """Test supported protocols endpoint."""

    @pytest.mark.asyncio
    async def test_get_supported_protocols(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test getting list of supported protocols."""
        response = await client.get(
            "/api/v1/generation/protocols/supported",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "protocols" in data
        assert isinstance(data["protocols"], list)
        # Should include at least Modbus and EtherNet/IP
        assert "modbus_tcp" in data["protocols"] or "MODBUS_TCP" in data["protocols"]


class TestGenerationStart:
    """Test starting generation jobs."""

    @pytest.fixture
    def mock_celery_task(self):
        """Mock Celery task to avoid Redis dependency."""
        with patch("app.api.routes.generation.generate_traffic") as mock:
            mock_task = MagicMock()
            mock_task.id = "test-task-id"
            mock.apply_async.return_value = mock_task
            yield mock

    @pytest.mark.asyncio
    async def test_start_generation_scenario_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test starting generation with non-existent scenario."""
        response = await client.post(
            "/api/v1/generation",
            json={"scenario_id": str(uuid4())},
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "not found" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_start_generation_no_auth(self, client: AsyncClient):
        """Test starting generation without auth fails."""
        response = await client.post(
            "/api/v1/generation",
            json={"scenario_id": str(uuid4())},
        )

        # HTTPBearer returns 403 when the Authorization header is absent.
        assert response.status_code == 403


class TestGenerationStatus:
    """Test generation job status endpoint."""

    @pytest.mark.asyncio
    async def test_get_status_job_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test getting status for non-existent job."""
        # Valid UUID format so the route reaches the not-found check rather
        # than rejecting the ID format with 400.
        response = await client.get(
            f"/api/v1/generation/{uuid4()}",
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestGenerationDownload:
    """Test PCAP download endpoint."""

    @pytest.mark.asyncio
    async def test_download_job_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test downloading PCAP for non-existent job."""
        response = await client.get(
            f"/api/v1/generation/{uuid4()}/download",
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestGenerationCancel:
    """Test generation cancellation endpoint."""

    @pytest.mark.asyncio
    async def test_cancel_job_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test cancelling non-existent job."""
        response = await client.delete(
            f"/api/v1/generation/{uuid4()}",
            headers=auth_headers,
        )

        assert response.status_code == 404

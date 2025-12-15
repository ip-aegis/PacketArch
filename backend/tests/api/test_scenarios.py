"""Integration tests for scenario endpoints."""

import pytest
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scenario import Scenario
from app.models.user import User


class TestScenarioList:
    """Test scenario list endpoint."""

    @pytest.mark.asyncio
    async def test_list_scenarios_empty(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test listing scenarios when none exist."""
        response = await client.get("/api/v1/scenarios", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1

    @pytest.mark.asyncio
    async def test_list_scenarios_with_data(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        auth_headers: dict,
    ):
        """Test listing scenarios with existing data."""
        # Create test scenarios
        for i in range(3):
            scenario = Scenario(
                user_id=test_user.id,
                name=f"Test Scenario {i}",
                description=f"Description {i}",
                vertical="manufacturing",
                total_duration_ms=60000,
                definition={"devices": {}, "flows": {}},
            )
            db_session.add(scenario)
        await db_session.commit()

        response = await client.get("/api/v1/scenarios", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        assert data["total"] == 3

    @pytest.mark.asyncio
    async def test_list_scenarios_pagination(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        auth_headers: dict,
    ):
        """Test scenario pagination."""
        # Create 5 scenarios
        for i in range(5):
            scenario = Scenario(
                user_id=test_user.id,
                name=f"Scenario {i}",
                vertical="manufacturing",
                total_duration_ms=60000,
                definition={},
            )
            db_session.add(scenario)
        await db_session.commit()

        # Get page 1 with page_size 2
        response = await client.get(
            "/api/v1/scenarios",
            params={"page": 1, "page_size": 2},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["pages"] == 3

    @pytest.mark.asyncio
    async def test_list_scenarios_filter_by_vertical(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        auth_headers: dict,
    ):
        """Test filtering scenarios by vertical."""
        # Create scenarios with different verticals
        for vertical in ["manufacturing", "manufacturing", "water", "energy"]:
            scenario = Scenario(
                user_id=test_user.id,
                name=f"Scenario {vertical}",
                vertical=vertical,
                total_duration_ms=60000,
                definition={},
            )
            db_session.add(scenario)
        await db_session.commit()

        response = await client.get(
            "/api/v1/scenarios",
            params={"vertical": "manufacturing"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    @pytest.mark.asyncio
    async def test_list_scenarios_no_auth(self, client: AsyncClient):
        """Test listing scenarios without auth fails."""
        response = await client.get("/api/v1/scenarios")

        assert response.status_code == 401


class TestScenarioCreate:
    """Test scenario creation endpoint."""

    @pytest.mark.asyncio
    async def test_create_scenario(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test creating a new scenario."""
        scenario_data = {
            "name": "New Manufacturing Scenario",
            "description": "Test scenario for manufacturing",
            "vertical": "manufacturing",
            "total_duration_ms": 120000,
            "definition": {
                "devices": {"plc1": {"type": "plc", "ip": "192.168.1.10"}},
                "flows": {},
            },
            "addressing_config": {
                "base_ip": "192.168.1.0",
                "subnet_mask": "255.255.255.0",
            },
        }

        response = await client.post(
            "/api/v1/scenarios",
            json=scenario_data,
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == scenario_data["name"]
        assert data["description"] == scenario_data["description"]
        assert data["vertical"] == scenario_data["vertical"]
        assert data["version"] == 1
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_scenario_minimal(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test creating scenario with minimal required fields."""
        scenario_data = {
            "name": "Minimal Scenario",
            "vertical": "manufacturing",
            "total_duration_ms": 60000,
        }

        response = await client.post(
            "/api/v1/scenarios",
            json=scenario_data,
            headers=auth_headers,
        )

        assert response.status_code == 201


class TestScenarioGet:
    """Test scenario get endpoint."""

    @pytest.mark.asyncio
    async def test_get_scenario(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        auth_headers: dict,
    ):
        """Test getting a scenario by ID."""
        # Create a scenario
        scenario = Scenario(
            user_id=test_user.id,
            name="Get Test Scenario",
            vertical="manufacturing",
            total_duration_ms=60000,
            definition={"devices": {"dev1": {}}, "flows": {}},
        )
        db_session.add(scenario)
        await db_session.commit()
        await db_session.refresh(scenario)

        response = await client.get(
            f"/api/v1/scenarios/{scenario.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(scenario.id)
        assert data["name"] == scenario.name

    @pytest.mark.asyncio
    async def test_get_scenario_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test getting non-existent scenario returns 404."""
        response = await client.get(
            f"/api/v1/scenarios/{uuid4()}",
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestScenarioUpdate:
    """Test scenario update endpoint."""

    @pytest.mark.asyncio
    async def test_update_scenario(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        auth_headers: dict,
    ):
        """Test updating a scenario."""
        # Create a scenario
        scenario = Scenario(
            user_id=test_user.id,
            name="Original Name",
            vertical="manufacturing",
            total_duration_ms=60000,
            version=1,
            definition={},
        )
        db_session.add(scenario)
        await db_session.commit()
        await db_session.refresh(scenario)

        # Update it
        response = await client.put(
            f"/api/v1/scenarios/{scenario.id}",
            json={
                "name": "Updated Name",
                "description": "New description",
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "New description"
        assert data["version"] == 2  # Version should increment

    @pytest.mark.asyncio
    async def test_update_scenario_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test updating non-existent scenario returns 404."""
        response = await client.put(
            f"/api/v1/scenarios/{uuid4()}",
            json={"name": "Updated"},
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestScenarioDelete:
    """Test scenario deletion endpoint."""

    @pytest.mark.asyncio
    async def test_delete_scenario(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        auth_headers: dict,
    ):
        """Test deleting a scenario."""
        # Create a scenario
        scenario = Scenario(
            user_id=test_user.id,
            name="To Be Deleted",
            vertical="manufacturing",
            total_duration_ms=60000,
            definition={},
        )
        db_session.add(scenario)
        await db_session.commit()
        await db_session.refresh(scenario)

        # Delete it
        response = await client.delete(
            f"/api/v1/scenarios/{scenario.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()

        # Verify it's gone
        get_response = await client.get(
            f"/api/v1/scenarios/{scenario.id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404


class TestScenarioDuplicate:
    """Test scenario duplication endpoint."""

    @pytest.mark.asyncio
    async def test_duplicate_scenario(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        auth_headers: dict,
    ):
        """Test duplicating a scenario."""
        # Create original scenario
        original = Scenario(
            user_id=test_user.id,
            name="Original Scenario",
            description="Original description",
            vertical="manufacturing",
            total_duration_ms=60000,
            definition={"devices": {"plc1": {}}, "flows": {}},
        )
        db_session.add(original)
        await db_session.commit()
        await db_session.refresh(original)

        # Duplicate it
        response = await client.post(
            f"/api/v1/scenarios/{original.id}/duplicate",
            params={"new_name": "Duplicated Scenario"},
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Duplicated Scenario"
        assert data["description"] == original.description
        assert data["version"] == 1  # Duplicates start at version 1
        assert data["id"] != str(original.id)


class TestScenarioExportImport:
    """Test scenario export and import endpoints."""

    @pytest.mark.asyncio
    async def test_export_scenario(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        auth_headers: dict,
    ):
        """Test exporting a scenario."""
        # Create scenario
        scenario = Scenario(
            user_id=test_user.id,
            name="Export Test",
            description="For export",
            vertical="water",
            total_duration_ms=90000,
            definition={"devices": {}, "flows": {}},
            version=3,
        )
        db_session.add(scenario)
        await db_session.commit()
        await db_session.refresh(scenario)

        # Export it
        response = await client.get(
            f"/api/v1/scenarios/{scenario.id}/export",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == scenario.name
        assert data["vertical"] == scenario.vertical
        assert data["version"] == scenario.version
        assert "exported_at" in data

    @pytest.mark.asyncio
    async def test_import_scenario(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test importing a scenario."""
        import_data = {
            "name": "Imported Scenario",
            "description": "Imported from export",
            "vertical": "energy",
            "total_duration_ms": 120000,
            "definition": {
                "devices": {"rtu1": {"type": "rtu"}},
                "flows": {},
            },
        }

        response = await client.post(
            "/api/v1/scenarios/import",
            json=import_data,
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == import_data["name"]
        assert data["vertical"] == import_data["vertical"]
        assert data["version"] == 1  # Imported scenarios start at version 1

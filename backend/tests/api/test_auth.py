# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Integration tests for authentication endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.user import User


class TestAuthRegistration:
    """Test user registration."""

    @pytest.mark.asyncio
    async def test_register_requires_admin(self, client: AsyncClient):
        """Anonymous registration is rejected. The 'first user becomes admin'
        flow now lives in the setup wizard; /auth/register is admin-only.
        With no bearer credentials, HTTPBearer returns 403."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "firstuser",
                "email": "first@example.com",
                "password": "securepassword123",
            },
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_registers_regular_user(
        self, client: AsyncClient, admin_auth_headers: dict
    ):
        """An admin can register a new user, who is non-admin by default."""
        response = await client.post(
            "/api/v1/auth/register",
            headers=admin_auth_headers,
            json={
                "username": "newuser",
                "email": "new@example.com",
                "password": "securepassword123",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "new@example.com"
        assert data["is_admin"] is False
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_register_duplicate_username(
        self, client: AsyncClient, test_user: User, admin_auth_headers: dict
    ):
        """Test registration with duplicate username fails (409 Conflict)."""
        response = await client.post(
            "/api/v1/auth/register",
            headers=admin_auth_headers,
            json={
                "username": test_user.username,
                "email": "different@example.com",
                "password": "password123",
            },
        )

        assert response.status_code == 409
        assert "already registered" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_register_duplicate_email(
        self, client: AsyncClient, test_user: User, admin_auth_headers: dict
    ):
        """Test registration with duplicate email fails (409 Conflict)."""
        response = await client.post(
            "/api/v1/auth/register",
            headers=admin_auth_headers,
            json={
                "username": "differentuser",
                "email": test_user.email,
                "password": "password123",
            },
        )

        assert response.status_code == 409
        assert "already registered" in response.json()["message"]


class TestAuthLogin:
    """Test user login."""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user: User):
        """Test successful login returns tokens."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "testpassword",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert len(data["access_token"]) > 0
        assert len(data["refresh_token"]) > 0

    @pytest.mark.asyncio
    async def test_login_invalid_username(self, client: AsyncClient, test_user: User):
        """Test login with invalid username fails."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "nonexistent",
                "password": "testpassword",
            },
        )

        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_invalid_password(self, client: AsyncClient, test_user: User):
        """Test login with invalid password fails."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_inactive_user(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test login with inactive user fails."""
        # Create inactive user
        inactive_user = User(
            username="inactive",
            email="inactive@example.com",
            password_hash=get_password_hash("password123"),
            is_active=False,
        )
        db_session.add(inactive_user)
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "inactive",
                "password": "password123",
            },
        )

        assert response.status_code == 403
        assert "disabled" in response.json()["detail"]


class TestAuthMe:
    """Test current user endpoint."""

    @pytest.mark.asyncio
    async def test_get_current_user(
        self, client: AsyncClient, test_user: User, auth_headers: dict
    ):
        """Test getting current user info."""
        response = await client.get("/api/v1/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user.username
        assert data["email"] == test_user.email

    @pytest.mark.asyncio
    async def test_get_current_user_no_auth(self, client: AsyncClient):
        """Test getting current user without auth fails. HTTPBearer returns
        403 when the Authorization header is absent."""
        response = await client.get("/api/v1/auth/me")

        assert response.status_code == 403


class TestAuthRefresh:
    """Test token refresh."""

    @pytest.mark.asyncio
    async def test_refresh_token_success(
        self, client: AsyncClient, test_user: User
    ):
        """Test refreshing access token."""
        # First login to get tokens
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "testpassword",
            },
        )
        tokens = login_response.json()

        # Refresh token — rides in the JSON body (RefreshRequest), not a
        # query string, so it stays out of access logs.
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, client: AsyncClient):
        """Test refresh with invalid token fails."""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )

        assert response.status_code == 401

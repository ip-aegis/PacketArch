/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Authentication API functions
 */

import apiClient, { setTokens, clearTokens } from './client';
import type { LoginCredentials, Token, User } from '../types';

const AUTH_PREFIX = '/api/v1/auth';

export const authApi = {
  /**
   * Login with username and password
   */
  async login(credentials: LoginCredentials): Promise<Token> {
    const response = await apiClient.post<Token>(`${AUTH_PREFIX}/login`, credentials);
    const { access_token, refresh_token } = response.data;
    setTokens(access_token, refresh_token);
    return response.data;
  },

  /**
   * Logout and clear tokens
   */
  async logout(): Promise<void> {
    clearTokens();
  },

  /**
   * Get current user info
   */
  async getCurrentUser(): Promise<User> {
    const response = await apiClient.get<User>(`${AUTH_PREFIX}/me`);
    return response.data;
  },

  /**
   * Register a new user
   */
  async register(data: {
    username: string;
    email?: string;
    password: string;
  }): Promise<User> {
    const response = await apiClient.post<User>(`${AUTH_PREFIX}/register`, data);
    return response.data;
  },

  /**
   * Refresh access token
   */
  async refreshToken(refreshToken: string): Promise<Token> {
    const response = await apiClient.post<Token>(`${AUTH_PREFIX}/refresh`, {
      refresh_token: refreshToken,
    });
    const { access_token, refresh_token: newRefreshToken } = response.data;
    setTokens(access_token, newRefreshToken);
    return response.data;
  },
};

export default authApi;

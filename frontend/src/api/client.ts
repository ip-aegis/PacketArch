/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * API client configuration with axios
 */

import axios, { type AxiosError, type AxiosInstance, type InternalAxiosRequestConfig } from 'axios';

const getApiBaseUrl = () => {
  // Use environment variable if explicitly set (for production/custom deployments)
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }

  // In production (HTTPS on port 443), API is proxied through nginx at same origin
  // Use relative URL so it works with same-origin proxy
  if (typeof window !== 'undefined') {
    const port = window.location.port;
    const protocol = window.location.protocol;

    // Production: HTTPS on 443 or HTTP on 80 - use relative URL (same-origin proxy)
    if (protocol === 'https:' || port === '' || port === '443' || port === '80') {
      return '';  // Relative URL - API at /api/v1 on same origin
    }

    // Development: Different port setup - use explicit backend URL
    const hostname = window.location.hostname;
    return `http://${hostname}:8001`;
  }

  return 'http://localhost:8001';
};

const API_BASE_URL = getApiBaseUrl();

// Create axios instance
export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Token storage keys
const ACCESS_TOKEN_KEY = 'packetarch_access_token';
const REFRESH_TOKEN_KEY = 'packetarch_refresh_token';

// Token management functions
export const getAccessToken = (): string | null => {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
};

export const getRefreshToken = (): string | null => {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
};

export const setTokens = (accessToken: string, refreshToken: string): void => {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
};

export const clearTokens = (): void => {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  // Also clear the persisted auth state
  localStorage.removeItem('auth-storage');
};

// Request interceptor to add auth header
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Refresh-in-flight singleton. Concurrent 401s share the same refresh
// call so we don't burn the rotating refresh_token N times in parallel
// (each rotation invalidates the previous one).
let refreshInFlight: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
  if (refreshInFlight) return refreshInFlight;

  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    throw new Error('No refresh token available');
  }

  const refreshUrl = API_BASE_URL ? `${API_BASE_URL}/api/v1/auth/refresh` : '/api/v1/auth/refresh';
  refreshInFlight = axios
    .post(refreshUrl, { refresh_token: refreshToken })
    .then((response) => {
      const { access_token, refresh_token: newRefreshToken } = response.data;
      setTokens(access_token, newRefreshToken);
      return access_token as string;
    })
    .finally(() => {
      refreshInFlight = null;
    });

  return refreshInFlight;
}

// Response interceptor to handle token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // Only handle 401s, and only retry each request once so we don't
    // loop if the refreshed token also returns 401 (corrupt user, etc).
    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const accessToken = await refreshAccessToken();
        originalRequest.headers.Authorization = `Bearer ${accessToken}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        clearTokens();
        if (window.location.pathname !== '/login') {
          window.location.href = '/login';
        }
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default apiClient;

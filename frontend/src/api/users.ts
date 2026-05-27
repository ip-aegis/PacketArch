/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * User management API client
 */

import { apiClient } from './client';

export interface User {
  id: string;
  username: string;
  email?: string;
  is_active: boolean;
  is_admin: boolean;
  auth_source: 'local' | 'ldap';
  created_at: string;
  last_login?: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export interface ResetPasswordRequest {
  new_password: string;
}

export interface PasswordChangeResponse {
  success: boolean;
  message: string;
}

export interface CreateUserRequest {
  username: string;
  email?: string | null;
  password: string;
  is_admin?: boolean;
  is_active?: boolean;
}

export interface UpdateUserRequest {
  username?: string;
  email?: string | null;
  is_admin?: boolean;
  is_active?: boolean;
}

export interface UserAuditEntry {
  id: string;
  created_at: string;
  actor_username: string;
  target_username: string | null;
  action: string;
  detail: string | null;
}

/**
 * Change the current user's password
 */
export async function changePassword(
  currentPassword: string,
  newPassword: string
): Promise<PasswordChangeResponse> {
  const response = await apiClient.post<PasswordChangeResponse>(
    '/api/v1/users/me/password',
    {
      current_password: currentPassword,
      new_password: newPassword,
    }
  );
  return response.data;
}

/**
 * Reset a user's password (admin only)
 */
export async function resetUserPassword(
  userId: string,
  newPassword: string
): Promise<PasswordChangeResponse> {
  const response = await apiClient.post<PasswordChangeResponse>(
    `/api/v1/users/${userId}/reset-password`,
    {
      new_password: newPassword,
    }
  );
  return response.data;
}

/**
 * List all users (admin only)
 */
export async function listUsers(): Promise<User[]> {
  const response = await apiClient.get<User[]>('/api/v1/users');
  return response.data;
}

/**
 * Get a specific user (admin only)
 */
export async function getUser(userId: string): Promise<User> {
  const response = await apiClient.get<User>(`/api/v1/users/${userId}`);
  return response.data;
}

/**
 * Toggle a user's active status (admin only)
 */
export async function toggleUserActive(userId: string): Promise<User> {
  const response = await apiClient.patch<User>(
    `/api/v1/users/${userId}/toggle-active`
  );
  return response.data;
}

/**
 * Create a user (admin only)
 */
export async function createUser(payload: CreateUserRequest): Promise<User> {
  const response = await apiClient.post<User>('/api/v1/users', payload);
  return response.data;
}

/**
 * Update a user's username/email/role/active status (admin only)
 */
export async function updateUser(
  userId: string,
  payload: UpdateUserRequest
): Promise<User> {
  const response = await apiClient.patch<User>(`/api/v1/users/${userId}`, payload);
  return response.data;
}

/**
 * Delete a user (admin only)
 */
export async function deleteUser(userId: string): Promise<void> {
  await apiClient.delete(`/api/v1/users/${userId}`);
}

/**
 * Recent admin user-management actions (admin only)
 */
export async function listUserAudit(limit = 100): Promise<UserAuditEntry[]> {
  const response = await apiClient.get<UserAuditEntry[]>(
    `/api/v1/users/audit?limit=${limit}`
  );
  return response.data;
}

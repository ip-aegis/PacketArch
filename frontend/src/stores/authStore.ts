/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Authentication state management with Zustand
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User, LoginCredentials } from '../types';
import { authApi } from '../api/auth';
import { clearTokens, getAccessToken } from '../api/client';
import { extractErrorMessage } from '../utils/errorUtils';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
  fetchCurrentUser: () => Promise<void>;
  setUser: (user: User) => void;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (credentials: LoginCredentials) => {
        set({ isLoading: true, error: null });
        try {
          await authApi.login(credentials);
          const user = await authApi.getCurrentUser();
          set({ user, isAuthenticated: true, isLoading: false });
        } catch (error: unknown) {
          const message = extractErrorMessage(error, 'Login failed');
          set({ error: message, isLoading: false });
          throw error;
        }
      },

      logout: () => {
        clearTokens();
        set({ user: null, isAuthenticated: false, error: null });
      },

      fetchCurrentUser: async () => {
        const token = getAccessToken();
        if (!token) {
          set({ user: null, isAuthenticated: false });
          return;
        }

        set({ isLoading: true });
        try {
          const user = await authApi.getCurrentUser();
          set({ user, isAuthenticated: true, isLoading: false });
        } catch (error) {
          clearTokens();
          set({ user: null, isAuthenticated: false, isLoading: false });
        }
      },

      setUser: (user: User) => {
        set({ user });
      },

      clearError: () => {
        set({ error: null });
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        // Only persist user info, not loading/error states
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

export default useAuthStore;

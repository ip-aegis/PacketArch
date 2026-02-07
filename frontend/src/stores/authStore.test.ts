import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import type { User, Token } from '../types';

// Mock the auth API module before importing the store
vi.mock('../api/auth', () => ({
  authApi: {
    login: vi.fn(),
    getCurrentUser: vi.fn(),
    logout: vi.fn(),
  },
}));

// Mock the API client module
vi.mock('../api/client', () => {
  const tokens: Record<string, string | null> = {
    access: null,
    refresh: null,
  };
  return {
    default: {
      post: vi.fn(),
      get: vi.fn(),
    },
    setTokens: vi.fn((access: string, refresh: string) => {
      tokens.access = access;
      tokens.refresh = refresh;
    }),
    clearTokens: vi.fn(() => {
      tokens.access = null;
      tokens.refresh = null;
    }),
    getAccessToken: vi.fn(() => tokens.access),
    getRefreshToken: vi.fn(() => tokens.refresh),
  };
});

// Now import the store and mocks
import { useAuthStore } from './authStore';
import { authApi } from '../api/auth';
import { clearTokens, getAccessToken } from '../api/client';

const mockUser: User = {
  id: 'user-1',
  username: 'admin',
  email: 'admin@test.com',
  is_active: true,
  is_admin: true,
  created_at: '2025-01-01T00:00:00Z',
  last_login: null,
};

const mockToken: Token = {
  access_token: 'test-access-token',
  refresh_token: 'test-refresh-token',
  token_type: 'bearer',
};

describe('useAuthStore', () => {
  beforeEach(() => {
    // Reset the store state before each test
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
    });
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ---------------------------------------------------------------------------
  // Initial state
  // ---------------------------------------------------------------------------
  describe('initial state', () => {
    it('starts with null user', () => {
      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
    });

    it('starts not authenticated', () => {
      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(false);
    });

    it('starts not loading', () => {
      const state = useAuthStore.getState();
      expect(state.isLoading).toBe(false);
    });

    it('starts with no error', () => {
      const state = useAuthStore.getState();
      expect(state.error).toBeNull();
    });
  });

  // ---------------------------------------------------------------------------
  // login
  // ---------------------------------------------------------------------------
  describe('login', () => {
    it('sets isLoading true during login', async () => {
      // Make login hang so we can observe isLoading
      vi.mocked(authApi.login).mockImplementation(
        () => new Promise(() => {}) // never resolves
      );

      // Start login but don't await
      useAuthStore.getState().login({ username: 'admin', password: 'pass' });

      // isLoading should be true while login is in progress
      expect(useAuthStore.getState().isLoading).toBe(true);
      expect(useAuthStore.getState().error).toBeNull();
    });

    it('sets user and isAuthenticated on successful login', async () => {
      vi.mocked(authApi.login).mockResolvedValue(mockToken);
      vi.mocked(authApi.getCurrentUser).mockResolvedValue(mockUser);

      await useAuthStore.getState().login({ username: 'admin', password: 'pass' });

      const state = useAuthStore.getState();
      expect(state.user).toEqual(mockUser);
      expect(state.isAuthenticated).toBe(true);
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
    });

    it('calls authApi.login with credentials', async () => {
      vi.mocked(authApi.login).mockResolvedValue(mockToken);
      vi.mocked(authApi.getCurrentUser).mockResolvedValue(mockUser);

      const credentials = { username: 'admin', password: 'C!sco123' };
      await useAuthStore.getState().login(credentials);

      expect(authApi.login).toHaveBeenCalledWith(credentials);
    });

    it('calls authApi.getCurrentUser after successful login', async () => {
      vi.mocked(authApi.login).mockResolvedValue(mockToken);
      vi.mocked(authApi.getCurrentUser).mockResolvedValue(mockUser);

      await useAuthStore.getState().login({ username: 'admin', password: 'pass' });

      expect(authApi.getCurrentUser).toHaveBeenCalled();
    });

    it('sets error on login failure', async () => {
      const loginError = new Error('Invalid credentials');
      vi.mocked(authApi.login).mockRejectedValue(loginError);

      await expect(
        useAuthStore.getState().login({ username: 'admin', password: 'wrong' })
      ).rejects.toThrow();

      const state = useAuthStore.getState();
      expect(state.error).toBe('Invalid credentials');
      expect(state.isLoading).toBe(false);
      expect(state.isAuthenticated).toBe(false);
      expect(state.user).toBeNull();
    });

    it('re-throws error on login failure', async () => {
      const loginError = new Error('Network error');
      vi.mocked(authApi.login).mockRejectedValue(loginError);

      await expect(
        useAuthStore.getState().login({ username: 'admin', password: 'pass' })
      ).rejects.toThrow('Network error');
    });

    it('clears previous error before attempting login', async () => {
      // Set an initial error
      useAuthStore.setState({ error: 'Previous error' });

      vi.mocked(authApi.login).mockResolvedValue(mockToken);
      vi.mocked(authApi.getCurrentUser).mockResolvedValue(mockUser);

      await useAuthStore.getState().login({ username: 'admin', password: 'pass' });

      expect(useAuthStore.getState().error).toBeNull();
    });
  });

  // ---------------------------------------------------------------------------
  // logout
  // ---------------------------------------------------------------------------
  describe('logout', () => {
    it('clears user and authentication state', () => {
      // Set up authenticated state
      useAuthStore.setState({
        user: mockUser,
        isAuthenticated: true,
        error: 'some error',
      });

      useAuthStore.getState().logout();

      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
      expect(state.isAuthenticated).toBe(false);
      expect(state.error).toBeNull();
    });

    it('calls clearTokens', () => {
      useAuthStore.setState({ user: mockUser, isAuthenticated: true });

      useAuthStore.getState().logout();

      expect(clearTokens).toHaveBeenCalled();
    });
  });

  // ---------------------------------------------------------------------------
  // fetchCurrentUser
  // ---------------------------------------------------------------------------
  describe('fetchCurrentUser', () => {
    it('does nothing when no access token exists', async () => {
      vi.mocked(getAccessToken).mockReturnValue(null);

      await useAuthStore.getState().fetchCurrentUser();

      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
      expect(state.isAuthenticated).toBe(false);
      expect(authApi.getCurrentUser).not.toHaveBeenCalled();
    });

    it('fetches and sets user when token exists', async () => {
      vi.mocked(getAccessToken).mockReturnValue('valid-token');
      vi.mocked(authApi.getCurrentUser).mockResolvedValue(mockUser);

      await useAuthStore.getState().fetchCurrentUser();

      const state = useAuthStore.getState();
      expect(state.user).toEqual(mockUser);
      expect(state.isAuthenticated).toBe(true);
      expect(state.isLoading).toBe(false);
    });

    it('clears auth state on fetch failure', async () => {
      vi.mocked(getAccessToken).mockReturnValue('expired-token');
      vi.mocked(authApi.getCurrentUser).mockRejectedValue(new Error('401'));

      // Start with some auth state
      useAuthStore.setState({ user: mockUser, isAuthenticated: true });

      await useAuthStore.getState().fetchCurrentUser();

      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
      expect(state.isAuthenticated).toBe(false);
      expect(state.isLoading).toBe(false);
      expect(clearTokens).toHaveBeenCalled();
    });

    it('sets isLoading during fetch', async () => {
      vi.mocked(getAccessToken).mockReturnValue('valid-token');
      vi.mocked(authApi.getCurrentUser).mockImplementation(
        () => new Promise(() => {}) // never resolves
      );

      useAuthStore.getState().fetchCurrentUser();

      expect(useAuthStore.getState().isLoading).toBe(true);
    });
  });

  // ---------------------------------------------------------------------------
  // clearError
  // ---------------------------------------------------------------------------
  describe('clearError', () => {
    it('clears error from state', () => {
      useAuthStore.setState({ error: 'Login failed' });

      useAuthStore.getState().clearError();

      expect(useAuthStore.getState().error).toBeNull();
    });

    it('does nothing if error is already null', () => {
      useAuthStore.setState({ error: null });

      useAuthStore.getState().clearError();

      expect(useAuthStore.getState().error).toBeNull();
    });
  });
});

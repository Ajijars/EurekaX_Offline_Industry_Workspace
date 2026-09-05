/**
 * Auth Zustand Store — manages authentication state globally.
 */

import { create } from 'zustand';
import type { AuthUser } from '@/lib/auth';
import { getStoredUser, getStoredToken } from '@/lib/auth';

interface AuthState {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  setUser: (user: AuthUser | null) => void;
  setLoading: (loading: boolean) => void;
  hydrate: () => void;
  clear: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,

  setUser: (user) =>
    set({ user, isAuthenticated: !!user, isLoading: false }),

  setLoading: (isLoading) => set({ isLoading }),

  hydrate: () => {
    const user = getStoredUser();
    const token = getStoredToken();
    set({
      user: token ? user : null,
      isAuthenticated: !!(token && user),
      isLoading: false,
    });
  },

  clear: () =>
    set({ user: null, isAuthenticated: false, isLoading: false }),
}));

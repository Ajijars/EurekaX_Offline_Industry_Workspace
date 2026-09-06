/**
 * Auth API Client — typed wrappers for authentication endpoints.
 */

import { API_BASE } from './constants';

// ── Types ──

export interface AuthUser {
  id: string;
  email: string;
  username: string;
  role: 'admin' | 'employee';
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: AuthUser;
}

export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

// ── Token Storage ──

const TOKEN_KEY = 'eurekax_access_token';
const REFRESH_KEY = 'eurekax_refresh_token';
const USER_KEY = 'eurekax_user';

export function getStoredToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredRefreshToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(REFRESH_KEY);
}

export function getStoredUser(): AuthUser | null {
  if (typeof window === 'undefined') return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try { return JSON.parse(raw); } catch { return null; }
}

export function storeAuth(data: TokenResponse): void {
  localStorage.setItem(TOKEN_KEY, data.access_token);
  localStorage.setItem(REFRESH_KEY, data.refresh_token);
  localStorage.setItem(USER_KEY, JSON.stringify(data.user));
}

export function clearAuth(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(USER_KEY);
}

// ── Authenticated Fetch Helper ──

export async function authFetch(url: string, init?: RequestInit): Promise<Response> {
  const token = getStoredToken();
  const headers = new Headers(init?.headers);
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  return fetch(url, { ...init, headers });
}

async function authJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await authFetch(url, init);
  if (res.status === 401) {
    // Try refreshing the token
    const refreshed = await tryRefresh();
    if (refreshed) {
      const retryHeaders = new Headers(init?.headers);
      retryHeaders.set('Authorization', `Bearer ${getStoredToken()}`);
      const retryRes = await fetch(url, { ...init, headers: retryHeaders });
      if (!retryRes.ok) {
        const body = await retryRes.json().catch(() => ({ detail: retryRes.statusText }));
        throw new Error(body.detail || `API error ${retryRes.status}`);
      }
      return retryRes.json();
    }
    clearAuth();
    window.location.href = '/login';
    throw new Error('Session expired');
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `API error ${res.status}`);
  }
  return res.json();
}

// ── Auth API Functions ──

export async function register(req: RegisterRequest): Promise<TokenResponse> {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `Registration failed: ${res.status}`);
  }
  const data: TokenResponse = await res.json();
  storeAuth(data);
  return data;
}

export async function login(req: LoginRequest): Promise<TokenResponse> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `Login failed: ${res.status}`);
  }
  const data: TokenResponse = await res.json();
  storeAuth(data);
  return data;
}

export async function tryRefresh(): Promise<boolean> {
  const refreshToken = getStoredRefreshToken();
  if (!refreshToken) return false;

  try {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) return false;
    const data: TokenResponse = await res.json();
    storeAuth(data);
    return true;
  } catch {
    return false;
  }
}

export async function getMe(): Promise<AuthUser> {
  return authJson<AuthUser>(`${API_BASE}/auth/me`);
}

export async function listUsers(): Promise<AuthUser[]> {
  return authJson<AuthUser[]>(`${API_BASE}/auth/users`);
}

export async function changeUserRole(userId: string, role: string): Promise<AuthUser> {
  return authJson<AuthUser>(`${API_BASE}/auth/users/${userId}/role`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ role }),
  });
}

export async function deactivateUser(userId: string): Promise<void> {
  const res = await authFetch(`${API_BASE}/auth/users/${userId}`, { method: 'DELETE' });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `API error ${res.status}`);
  }
}

export function logout(): void {
  clearAuth();
  window.location.href = '/login';
}

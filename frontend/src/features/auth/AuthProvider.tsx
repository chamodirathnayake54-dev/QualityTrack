import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { ApiClient } from '../../api/client';
import type { Identity, TokenResponse } from '../../api/contracts';

type Auth = {
  identity: Identity | null;
  pending: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
};
const AuthContext = createContext<Auth | null>(null);

// PUBLIC_INTERFACE
export function AuthProvider({ client, children }: { client: ApiClient; children: ReactNode }) {
  /** Own the ephemeral session; generation guards prevent late identity restoration. */
  const queryClient = useQueryClient();
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [pending, setPending] = useState(false);
  const generation = useRef(0);
  const expiry = useRef<ReturnType<typeof setTimeout>>();

  const logout = useCallback(() => {
    generation.current += 1;
    clearTimeout(expiry.current);
    client.setSession(null);
    queryClient.clear();
    setIdentity(null);
    setPending(false);
  }, [client, queryClient]);

  useEffect(() => () => {
    generation.current += 1;
    clearTimeout(expiry.current);
    client.setSession(null);
    queryClient.clear();
  }, [client, queryClient]);

  const login = async (username: string, password: string) => {
    logout();
    const attempt = generation.current;
    setPending(true);
    const started = Date.now();
    try {
      const { data: token } = await client.request<TokenResponse>('/auth/login', {
        method: 'POST', anonymous: true, body: { username, password },
      });
      if (attempt !== generation.current) return;
      const { data: caller } = await client.request<Identity>('/me', { token: token.access_token });
      if (attempt !== generation.current) return;
      const remaining = token.expires_in * 1000 - (Date.now() - started);
      if (remaining <= 0) throw new Error('The session expired. Sign in again.');
      client.setSession(token.access_token, logout);
      setIdentity(caller);
      expiry.current = setTimeout(logout, remaining);
    } finally {
      if (attempt === generation.current) setPending(false);
    }
  };

  return <AuthContext.Provider value={{ identity, pending, login, logout }}>{children}</AuthContext.Provider>;
}

// PUBLIC_INTERFACE
export function useAuth() {
  /** Access the active memory-only session within AuthProvider. */
  const auth = useContext(AuthContext);
  if (!auth) throw new Error('AuthProvider is required.');
  return auth;
}

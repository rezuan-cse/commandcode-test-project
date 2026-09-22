import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  api,
  getAccessToken,
  setAccessToken,
  setUnauthorizedHandler,
} from "./api";
import { canRead, canWrite } from "./permissions";
import type { Access, UserRow } from "./types";

/**
 * Session state for the whole app.
 *
 * On first load a stored token is verified against the server rather than
 * trusted, so a token that has expired or whose account was disabled lands the
 * user back on the sign-in screen instead of a half-broken interface.
 */
interface AuthState {
  user: UserRow | null;
  /** True while a stored session is being checked on first load. */
  checking: boolean;
  signIn: (
    email: string,
    password: string,
  ) => Promise<{ needsTwoFactor: boolean; challengeToken: string | null }>;
  submitCode: (challengeToken: string, code: string) => Promise<void>;
  signOut: () => void;
  refreshUser: () => Promise<void>;
  /** This user's access level for a resource. */
  level: (resource: string) => Access | undefined;
  /** Whether this user may read, or change, a resource. */
  can: (resource: string, write?: boolean) => boolean;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserRow | null>(null);
  const [checking, setChecking] = useState(true);

  const signOut = useCallback(() => {
    setAccessToken(null);
    setUser(null);
  }, []);

  // The API client calls this when the server rejects our token for any reason.
  useEffect(() => {
    setUnauthorizedHandler(() => setUser(null));
    return () => setUnauthorizedHandler(null);
  }, []);

  useEffect(() => {
    let cancelled = false;
    if (!getAccessToken()) {
      setChecking(false);
      return;
    }
    api
      .me()
      .then((me) => {
        if (!cancelled) setUser(me);
      })
      .catch(() => {
        if (!cancelled) signOut();
      })
      .finally(() => {
        if (!cancelled) setChecking(false);
      });
    return () => {
      cancelled = true;
    };
  }, [signOut]);

  const signIn = useCallback(async (email: string, password: string) => {
    const result = await api.login(email, password);
    if (result.needs_2fa) {
      return { needsTwoFactor: true, challengeToken: result.challenge_token };
    }
    setAccessToken(result.access_token!);
    setUser(result.user);
    return { needsTwoFactor: false, challengeToken: null };
  }, []);

  const submitCode = useCallback(async (challengeToken: string, code: string) => {
    const session = await api.loginWithTotp(challengeToken, code);
    setAccessToken(session.access_token);
    setUser(session.user);
  }, []);

  const refreshUser = useCallback(async () => {
    setUser(await api.me());
  }, []);

  const level = useCallback(
    (resource: string): Access | undefined => user?.permissions?.[resource],
    [user],
  );

  const can = useCallback(
    (resource: string, write = false): boolean =>
      write ? canWrite(level(resource)) : canRead(level(resource)),
    [level],
  );

  const value = useMemo(
    () => ({ user, checking, signIn, submitCode, signOut, refreshUser, level, can }),
    [user, checking, signIn, submitCode, signOut, refreshUser, level, can],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}

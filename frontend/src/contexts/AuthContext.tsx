import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { apiFetch } from "../api/client";
import type {
  AuthStatusResponse,
  LoginRequest,
  RegisterRequest,
  UserResponse
} from "../api/types";

type AuthContextValue = {
  user: UserResponse | null;
  loading: boolean;
  login: (payload: LoginRequest) => Promise<void>;
  register: (payload: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = async () => {
    try {
      const currentUser = await apiFetch<UserResponse>("/auth/me");
      setUser(currentUser);
    } catch {
      setUser(null);
    }
  };

  useEffect(() => {
    void (async () => {
      await refreshUser();
      setLoading(false);
    })();
  }, []);

  const login = async (payload: LoginRequest) => {
    await apiFetch<AuthStatusResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify(payload)
    });
    await refreshUser();
  };

  const register = async (payload: RegisterRequest) => {
    await apiFetch<UserResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  };

  const logout = async () => {
    await apiFetch<AuthStatusResponse>("/auth/logout", {
      method: "POST"
    });
    setUser(null);
  };

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      login,
      register,
      logout,
      refreshUser
    }),
    [user, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}

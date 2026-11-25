import { createContext, ReactNode, useContext, useState } from "react";

import { login as apiLogin } from "../../lib/api";

interface AuthState {
  username: string | null;
  role: string | null;
  token: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("staff_token"));
  const [username, setUsername] = useState<string | null>(() => localStorage.getItem("staff_username"));
  const [role, setRole] = useState<string | null>(() => localStorage.getItem("staff_role"));

  const login = async (u: string, p: string) => {
    const res = await apiLogin(u, p);
    localStorage.setItem("staff_token", res.access_token);
    localStorage.setItem("staff_username", res.username);
    localStorage.setItem("staff_role", res.role);
    setToken(res.access_token);
    setUsername(res.username);
    setRole(res.role);
  };

  const logout = () => {
    localStorage.removeItem("staff_token");
    localStorage.removeItem("staff_username");
    localStorage.removeItem("staff_role");
    setToken(null);
    setUsername(null);
    setRole(null);
  };

  return <AuthContext.Provider value={{ token, username, role, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

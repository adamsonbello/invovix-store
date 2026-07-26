import React, { createContext, useContext, useEffect, useState } from "react";
import api from "../lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("invovix_token");
    if (!token) {
      setLoading(false);
      return;
    }
    api
      .get("/auth/me")
      .then((res) => setUser(res.data.user))
      .catch(() => {
        localStorage.removeItem("invovix_token");
      })
      .finally(() => setLoading(false));
  }, []);

  const persist = (data) => {
    localStorage.setItem("invovix_token", data.token);
    setUser(data.user);
  };

  const login = async (email, password) => {
    const res = await api.post("/auth/login", { email, password });
    if (res.data.twofa_required) {
      return { twofa_required: true, temp_token: res.data.temp_token };
    }
    persist(res.data);
    return res.data.user;
  };

  const verify2fa = async (temp_token, code) => {
    const res = await api.post("/auth/2fa/login", { temp_token, code });
    persist(res.data);
    return res.data.user;
  };

  const register = async (email, password, name) => {
    const res = await api.post("/auth/register", { email, password, name });
    persist(res.data);
    return res.data.user;
  };

  const logout = () => {
    localStorage.removeItem("invovix_token");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, verify2fa, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}

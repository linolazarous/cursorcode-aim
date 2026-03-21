import { createContext, useContext, useState, useEffect, useCallback } from "react";
import api from "../lib/api";

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Load user from localStorage instantly (for faster UI) + verify with backend
  const fetchUser = useCallback(async () => {
    const token = localStorage.getItem("access_token");
    const savedUser = localStorage.getItem("user");

    // Instant hydration from localStorage
    if (savedUser) {
      setUser(JSON.parse(savedUser));
    }

    if (!token) {
      setLoading(false);
      return;
    }

    try {
      const response = await api.get("/auth/me");
      const userData = response.data;

      setUser(userData);
      localStorage.setItem("user", JSON.stringify(userData)); // keep in sync
    } catch (error) {
      console.error("Failed to fetch user:", error);
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("user");
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  // =====================================================
  // LOGIN – matches backend exactly
  // POST /api/auth/login      → normal or { requires_2fa: true }
  // POST /api/auth/login-2fa  → full TokenResponse
  // =====================================================
  const login = async (email, password, totpCode = null) => {
    if (totpCode) {
      // 2FA step
      const response = await api.post("/auth/login-2fa", {
        email,
        password,
        totp_code: totpCode,
      });

      const { access_token, refresh_token, user: userData } = response.data;

      localStorage.setItem("access_token", access_token);
      localStorage.setItem("refresh_token", refresh_token);
      localStorage.setItem("user", JSON.stringify(userData));

      setUser(userData);
      return userData;
    }

    // First step (normal login or 2FA required)
    const response = await api.post("/auth/login", { email, password });

    if (response.data.requires_2fa) {
      return { requires_2fa: true, email: response.data.email };
    }

    const { access_token, refresh_token, user: userData } = response.data;

    localStorage.setItem("access_token", access_token);
    localStorage.setItem("refresh_token", refresh_token);
    localStorage.setItem("user", JSON.stringify(userData));

    setUser(userData);
    return userData;
  };

  // =====================================================
  // SIGNUP – matches backend /api/auth/signup
  // Returns full TokenResponse (even before email verification)
  // =====================================================
  const signup = async (name, email, password) => {
    const response = await api.post("/auth/signup", { name, email, password });
    const { access_token, refresh_token, user: userData } = response.data;

    localStorage.setItem("access_token", access_token);
    localStorage.setItem("refresh_token", refresh_token);
    localStorage.setItem("user", JSON.stringify(userData));

    setUser(userData);
    return userData;
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
    setUser(null);
  };

  const refreshUser = async () => {
    await fetchUser();
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        signup,
        logout,
        refreshUser,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

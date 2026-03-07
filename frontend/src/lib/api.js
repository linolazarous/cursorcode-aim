import axios from "axios";

// Use the correct environment variable
const BACKEND_URL =
  process.env.REACT_APP_API_URL || "http://localhost:8000";

if (!process.env.REACT_APP_API_URL) {
  console.warn("REACT_APP_API_URL is not set, using localhost fallback");
}

// Axios instance
const api = axios.create({
  baseURL: `${BACKEND_URL}/api`,
  headers: {
    "Content-Type": "application/json",
  },
});

// Add auth token to requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // If token expired or unauthorized
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");

      // Redirect to login
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }

    // Handle non-JSON responses (like Render cold start HTML)
    let message = "Unknown error";

    if (error.response?.data) {
      if (typeof error.response.data === "string") {
        message = error.response.data;
      } else if (error.response.data.detail) {
        message = error.response.data.detail;
      }
    }

    return Promise.reject({ ...error, message });
  }
);

export default api;

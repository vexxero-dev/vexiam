import axios from "axios";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "https://api.vexxero.com/api/v1";

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("vex_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Response interceptor to handle authentication errors gracefully
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (typeof window !== "undefined" && error.response?.status === 401) {
      const url = error.config?.url || "";
      // Ignore auth endpoints themselves (e.g., failed login attempt)
      if (!url.includes("/auth/login") && !url.includes("/auth/register")) {
        localStorage.removeItem("vex_token");
        localStorage.removeItem("vex_user");
        window.dispatchEvent(new Event("vex_auth_expired"));
      }
    }
    return Promise.reject(error);
  }
);

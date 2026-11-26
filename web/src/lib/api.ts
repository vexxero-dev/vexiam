import axios from "axios";
import type {
  Location,
  LocationApplication,
  LocationCreatePayload,
  LocationPosPolicyPayload,
  LocationStatus,
  LocationUpdatePayload,
} from "@/types";

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

export const locationsApi = {
  list: async (orgId: string, status?: LocationStatus): Promise<Location[]> => {
    const res = await api.get<Location[]>(`/organizations/${orgId}/locations`, {
      params: status ? { status } : undefined,
    });
    return res.data;
  },
  create: async (orgId: string, payload: LocationCreatePayload): Promise<Location> => {
    const res = await api.post<Location>(`/organizations/${orgId}/locations`, payload);
    return res.data;
  },
  update: async (locationId: string, payload: LocationUpdatePayload): Promise<Location> => {
    const res = await api.put<Location>(`/locations/${locationId}`, payload);
    return res.data;
  },
  archive: async (locationId: string): Promise<Location> => {
    const res = await api.post<Location>(`/locations/${locationId}/archive`);
    return res.data;
  },
  enableApplication: async (
    locationId: string,
    applicationId: string
  ): Promise<LocationApplication> => {
    const res = await api.post<LocationApplication>(`/locations/${locationId}/applications`, {
      application_id: applicationId,
    });
    return res.data;
  },
  deactivateApplication: async (
    locationId: string,
    applicationId: string
  ): Promise<LocationApplication> => {
    const res = await api.delete<LocationApplication>(
      `/locations/${locationId}/applications/${applicationId}`
    );
    return res.data;
  },
  updatePosPolicy: async (
    locationId: string,
    payload: LocationPosPolicyPayload
  ): Promise<Location> => {
    const res = await api.put<Location>(`/locations/${locationId}/pos-policy`, payload);
    return res.data;
  },
};

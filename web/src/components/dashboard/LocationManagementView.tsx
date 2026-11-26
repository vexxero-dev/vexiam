"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  MapPin,
  Plus,
  Search,
  Edit3,
  Archive,
  Layers,
  Sliders,
  X,
  CheckCircle2,
  AlertCircle,
  Globe,
  Clock,
  Power,
  PowerOff,
} from "lucide-react";
import { locationsApi } from "@/lib/api";
import {
  Application,
  Location,
  LocationCreatePayload,
  LocationPosModePolicy,
  LocationPosPolicyPayload,
  LocationStatus,
  LocationUpdatePayload,
  Organization,
} from "@/types";

interface LocationManagementViewProps {
  selectedOrg: Organization | null;
  applications: Application[];
}

const COMMON_TIMEZONES = [
  "UTC",
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "Europe/London",
  "Europe/Berlin",
  "Asia/Colombo",
  "Asia/Kolkata",
  "Asia/Singapore",
  "Asia/Tokyo",
  "Australia/Sydney",
];

function getErrorMessage(err: unknown, fallback: string): string {
  if (
    typeof err === "object" &&
    err !== null &&
    "response" in err &&
    typeof (err as { response?: { data?: { detail?: string } } }).response?.data?.detail === "string"
  ) {
    return (err as { response: { data: { detail: string } } }).response.data.detail;
  }
  return fallback;
}

export function LocationManagementView({
  selectedOrg,
  applications,
}: LocationManagementViewProps) {
  const [locations, setLocations] = useState<Location[]>([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<"ALL" | LocationStatus>("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [banner, setBanner] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Create / Edit Modal
  const [formOpen, setFormOpen] = useState(false);
  const [editingLocation, setEditingLocation] = useState<Location | null>(null);
  const [saving, setSaving] = useState(false);
  const [formState, setFormState] = useState<LocationCreatePayload>({
    code: "",
    name: "",
    description: "",
    address_line1: "",
    address_line2: "",
    city: "",
    state_province: "",
    postal_code: "",
    country_code: "",
    timezone: "UTC",
  });

  // POS Policy Modal
  const [policyLocation, setPolicyLocation] = useState<Location | null>(null);
  const [policyState, setPolicyState] = useState<LocationPosPolicyPayload>({
    pos_mode_policy: "ANY_ALLOWED",
    pos_default_mode: "LOCAL",
    pos_sync_allowed: true,
  });
  const [savingPolicy, setSavingPolicy] = useState(false);

  // Applications Modal
  const [appsLocation, setAppsLocation] = useState<Location | null>(null);
  const [togglingAppId, setTogglingAppId] = useState<string | null>(null);

  const loadLocations = useCallback(async () => {
    if (!selectedOrg) {
      setLocations([]);
      return;
    }
    setLoading(true);
    try {
      const data = await locationsApi.list(
        selectedOrg.id,
        statusFilter === "ALL" ? undefined : statusFilter
      );
      setLocations(data);
    } catch (err) {
      setBanner({
        type: "error",
        message: getErrorMessage(err, "Failed to load locations."),
      });
    } finally {
      setLoading(false);
    }
  }, [selectedOrg, statusFilter]);

  useEffect(() => {
    loadLocations();
  }, [loadLocations]);

  const openCreateModal = () => {
    setEditingLocation(null);
    setFormState({
      code: "",
      name: "",
      description: "",
      address_line1: "",
      address_line2: "",
      city: "",
      state_province: "",
      postal_code: "",
      country_code: "",
      timezone: "UTC",
    });
    setFormOpen(true);
  };

  const openEditModal = (loc: Location) => {
    setEditingLocation(loc);
    setFormState({
      code: loc.code,
      name: loc.name,
      description: loc.description || "",
      address_line1: loc.address_line1 || "",
      address_line2: loc.address_line2 || "",
      city: loc.city || "",
      state_province: loc.state_province || "",
      postal_code: loc.postal_code || "",
      country_code: loc.country_code || "",
      timezone: loc.timezone || "UTC",
    });
    setFormOpen(true);
  };

  const handleSaveLocation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOrg) return;
    setSaving(true);
    setBanner(null);

    try {
      if (editingLocation) {
        const payload: LocationUpdatePayload = {
          name: formState.name,
          description: formState.description || undefined,
          address_line1: formState.address_line1 || undefined,
          address_line2: formState.address_line2 || undefined,
          city: formState.city || undefined,
          state_province: formState.state_province || undefined,
          postal_code: formState.postal_code || undefined,
          country_code: formState.country_code || undefined,
          timezone: formState.timezone || "UTC",
        };
        await locationsApi.update(editingLocation.id, payload);
        setBanner({ type: "success", message: `Location "${formState.name}" updated.` });
      } else {
        const payload: LocationCreatePayload = {
          code: formState.code.trim(),
          name: formState.name.trim(),
          description: formState.description || undefined,
          address_line1: formState.address_line1 || undefined,
          address_line2: formState.address_line2 || undefined,
          city: formState.city || undefined,
          state_province: formState.state_province || undefined,
          postal_code: formState.postal_code || undefined,
          country_code: formState.country_code || undefined,
          timezone: formState.timezone || "UTC",
        };
        await locationsApi.create(selectedOrg.id, payload);
        setBanner({ type: "success", message: `Location "${payload.name}" created.` });
      }
      setFormOpen(false);
      await loadLocations();
    } catch (err) {
      setBanner({
        type: "error",
        message: getErrorMessage(err, "Failed to save location."),
      });
    } finally {
      setSaving(false);
    }
  };

  const handleArchive = async (loc: Location) => {
    setBanner(null);
    try {
      await locationsApi.archive(loc.id);
      setBanner({ type: "success", message: `Location "${loc.name}" archived.` });
      await loadLocations();
    } catch (err) {
      setBanner({
        type: "error",
        message: getErrorMessage(
          err,
          "Unable to archive location. Deactivate all active applications first."
        ),
      });
    }
  };

  const openPolicyModal = (loc: Location) => {
    setPolicyLocation(loc);
    setPolicyState({
      pos_mode_policy: loc.pos_mode_policy,
      pos_default_mode: loc.pos_default_mode === "CLOUD" ? "CLOUD" : "LOCAL",
      pos_sync_allowed: loc.pos_sync_allowed,
    });
  };

  const handleSavePolicy = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!policyLocation) return;
    setSavingPolicy(true);
    setBanner(null);
    try {
      await locationsApi.updatePosPolicy(policyLocation.id, policyState);
      setBanner({
        type: "success",
        message: `POS policy updated for "${policyLocation.name}".`,
      });
      setPolicyLocation(null);
      await loadLocations();
    } catch (err) {
      setBanner({
        type: "error",
        message: getErrorMessage(err, "Failed to update POS policy."),
      });
    } finally {
      setSavingPolicy(false);
    }
  };

  const handleToggleApplication = async (loc: Location, app: Application, isActive: boolean) => {
    setTogglingAppId(app.id);
    setBanner(null);
    try {
      if (isActive) {
        await locationsApi.deactivateApplication(loc.id, app.id);
      } else {
        await locationsApi.enableApplication(loc.id, app.id);
      }
      await loadLocations();
      // Refresh modal location reference
      const updated = await locationsApi.list(selectedOrg!.id);
      const refreshed = updated.find((l) => l.id === loc.id) || null;
      setAppsLocation(refreshed);
    } catch (err) {
      setBanner({
        type: "error",
        message: getErrorMessage(err, "Failed to update location application."),
      });
    } finally {
      setTogglingAppId(null);
    }
  };

  const filteredLocations = locations.filter((loc) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      loc.name.toLowerCase().includes(q) ||
      loc.code.toLowerCase().includes(q) ||
      (loc.city || "").toLowerCase().includes(q)
    );
  });

  if (!selectedOrg) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-10 text-center">
        <MapPin className="w-10 h-10 text-slate-600 mx-auto mb-3" />
        <h3 className="text-lg font-semibold text-white">No Organization Selected</h3>
        <p className="text-sm text-slate-400 mt-1">
          Select or create an organization in the sidebar to manage its locations.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <MapPin className="w-5 h-5 text-indigo-400" />
            Location Management
          </h2>
          <p className="text-sm text-slate-400 mt-0.5">
            Manage operational branches, application scopes, and POS policies for{" "}
            <span className="text-slate-200 font-medium">{selectedOrg.name}</span>.
          </p>
        </div>
        <button
          onClick={openCreateModal}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold transition shadow-lg shadow-indigo-600/20"
        >
          <Plus className="w-4 h-4" />
          New Location
        </button>
      </div>

      {/* Feedback Banner */}
      {banner && (
        <div
          className={`flex items-center justify-between px-4 py-3 rounded-xl border text-sm ${
            banner.type === "success"
              ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
              : "bg-rose-500/10 border-rose-500/30 text-rose-300"
          }`}
        >
          <span className="flex items-center gap-2">
            {banner.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 shrink-0" />
            )}
            {banner.message}
          </span>
          <button onClick={() => setBanner(null)} className="opacity-70 hover:opacity-100">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by name, code, or city..."
            className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-10 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>
        <div className="flex items-center gap-1 bg-slate-900 border border-slate-800 rounded-xl p-1">
          {(["ALL", "ACTIVE", "ARCHIVED"] as const).map((status) => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                statusFilter === status
                  ? "bg-indigo-600 text-white"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              {status}
            </button>
          ))}
        </div>
      </div>

      {/* Locations Grid */}
      {loading ? (
        <div className="text-center py-12 text-slate-400 text-sm">Loading locations...</div>
      ) : filteredLocations.length === 0 ? (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-10 text-center">
          <MapPin className="w-9 h-9 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-white">No locations found</h3>
          <p className="text-sm text-slate-400 mt-1">
            {searchQuery
              ? "Try adjusting your search or status filter."
              : "Create your first location to scope applications and POS terminals."}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {filteredLocations.map((loc) => {
            const activeApps = loc.applications.filter((a) => a.status === "ACTIVE");
            const addressParts = [loc.city, loc.state_province, loc.country_code]
              .filter(Boolean)
              .join(", ");

            return (
              <div
                key={loc.id}
                className="bg-slate-900 border border-slate-800 rounded-2xl p-5 flex flex-col justify-between gap-4 hover:border-slate-700 transition"
              >
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-base font-bold text-white">{loc.name}</h3>
                        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                          {loc.code}
                        </span>
                      </div>
                      {loc.description && (
                        <p className="text-xs text-slate-400 mt-1">{loc.description}</p>
                      )}
                    </div>
                    <span
                      className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full border ${
                        loc.status === "ACTIVE"
                          ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                          : "bg-slate-800 text-slate-400 border-slate-700"
                      }`}
                    >
                      {loc.status}
                    </span>
                  </div>

                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-slate-400">
                    {addressParts && (
                      <span className="flex items-center gap-1">
                        <Globe className="w-3.5 h-3.5 text-slate-500" />
                        {addressParts}
                      </span>
                    )}
                    <span className="flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5 text-slate-500" />
                      {loc.timezone}
                    </span>
                  </div>

                  {/* POS Policy & Apps summary */}
                  <div className="flex flex-wrap gap-2 pt-1">
                    <span className="text-[11px] px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-slate-300">
                      POS Policy: <strong className="text-indigo-400">{loc.pos_mode_policy}</strong>
                    </span>
                    <span className="text-[11px] px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-slate-300">
                      Default: <strong className="text-white">{loc.pos_default_mode}</strong>
                    </span>
                    <span className="text-[11px] px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-slate-300">
                      Active Apps: <strong className="text-emerald-400">{activeApps.length}</strong>
                    </span>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex flex-wrap items-center gap-2 pt-3 border-t border-slate-800">
                  <button
                    onClick={() => setAppsLocation(loc)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 transition"
                  >
                    <Layers className="w-3.5 h-3.5 text-indigo-400" />
                    Apps ({activeApps.length})
                  </button>
                  <button
                    onClick={() => openPolicyModal(loc)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 transition"
                  >
                    <Sliders className="w-3.5 h-3.5 text-amber-400" />
                    POS Policy
                  </button>
                  <button
                    onClick={() => openEditModal(loc)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 transition"
                  >
                    <Edit3 className="w-3.5 h-3.5 text-slate-300" />
                    Edit
                  </button>
                  {loc.status === "ACTIVE" && (
                    <button
                      onClick={() => handleArchive(loc)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-xs font-medium text-rose-300 border border-rose-500/20 transition ml-auto"
                    >
                      <Archive className="w-3.5 h-3.5" />
                      Archive
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create / Edit Location Modal */}
      {formOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-white">
                {editingLocation ? `Edit ${editingLocation.name}` : "Create Location"}
              </h3>
              <button
                onClick={() => setFormOpen(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveLocation} className="space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">
                    Location Code *
                  </label>
                  <input
                    type="text"
                    required
                    disabled={!!editingLocation}
                    value={formState.code}
                    onChange={(e) => setFormState({ ...formState, code: e.target.value })}
                    placeholder="e.g. NYC-01"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white disabled:opacity-50 focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">
                    Location Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={formState.name}
                    onChange={(e) => setFormState({ ...formState, name: e.target.value })}
                    placeholder="e.g. Manhattan Flagship"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">
                  Description
                </label>
                <input
                  type="text"
                  value={formState.description || ""}
                  onChange={(e) => setFormState({ ...formState, description: e.target.value })}
                  placeholder="Optional branch notes"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">
                  Address Line 1
                </label>
                <input
                  type="text"
                  value={formState.address_line1 || ""}
                  onChange={(e) => setFormState({ ...formState, address_line1: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">City</label>
                  <input
                    type="text"
                    value={formState.city || ""}
                    onChange={(e) => setFormState({ ...formState, city: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">
                    State / Province
                  </label>
                  <input
                    type="text"
                    value={formState.state_province || ""}
                    onChange={(e) =>
                      setFormState({ ...formState, state_province: e.target.value })
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">
                    Postal Code
                  </label>
                  <input
                    type="text"
                    value={formState.postal_code || ""}
                    onChange={(e) => setFormState({ ...formState, postal_code: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">
                    Country Code
                  </label>
                  <input
                    type="text"
                    maxLength={10}
                    value={formState.country_code || ""}
                    onChange={(e) => setFormState({ ...formState, country_code: e.target.value })}
                    placeholder="e.g. US, LK"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Timezone</label>
                <select
                  value={formState.timezone || "UTC"}
                  onChange={(e) => setFormState({ ...formState, timezone: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                >
                  {COMMON_TIMEZONES.map((tz) => (
                    <option key={tz} value={tz}>
                      {tz}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-3">
                <button
                  type="button"
                  onClick={() => setFormOpen(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-sm font-medium hover:bg-slate-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold disabled:opacity-50"
                >
                  {saving ? "Saving..." : editingLocation ? "Save Changes" : "Create Location"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* POS Policy Modal */}
      {policyLocation && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-white">
                POS Policy — {policyLocation.name}
              </h3>
              <button
                onClick={() => setPolicyLocation(null)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSavePolicy} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">
                  Allowed Terminal Mode Policy
                </label>
                <select
                  value={policyState.pos_mode_policy}
                  onChange={(e) =>
                    setPolicyState({
                      ...policyState,
                      pos_mode_policy: e.target.value as LocationPosModePolicy,
                    })
                  }
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="ANY_ALLOWED">ANY_ALLOWED</option>
                  <option value="LOCAL_ONLY">LOCAL_ONLY</option>
                  <option value="CLOUD_ONLY">CLOUD_ONLY</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">
                  Default Terminal Operating Mode
                </label>
                <select
                  value={policyState.pos_default_mode}
                  onChange={(e) =>
                    setPolicyState({
                      ...policyState,
                      pos_default_mode: e.target.value as "LOCAL" | "CLOUD",
                    })
                  }
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="LOCAL">LOCAL</option>
                  <option value="CLOUD">CLOUD</option>
                </select>
              </div>

              <label className="flex items-center gap-2.5 text-sm text-slate-200 cursor-pointer">
                <input
                  type="checkbox"
                  checked={!!policyState.pos_sync_allowed}
                  onChange={(e) =>
                    setPolicyState({ ...policyState, pos_sync_allowed: e.target.checked })
                  }
                  className="rounded border-slate-700 bg-slate-950 text-indigo-600 focus:ring-indigo-500"
                />
                Allow Cloud Sync for POS Terminals
              </label>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setPolicyLocation(null)}
                  className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-sm font-medium hover:bg-slate-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingPolicy}
                  className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold disabled:opacity-50"
                >
                  {savingPolicy ? "Saving..." : "Save Policy"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Location Applications Modal */}
      {appsLocation && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-white">
                  Applications — {appsLocation.name}
                </h3>
                <p className="text-xs text-slate-400">
                  Enable or deactivate VEX applications at this location.
                </p>
              </div>
              <button
                onClick={() => setAppsLocation(null)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-2 max-h-80 overflow-y-auto">
              {applications.length === 0 ? (
                <p className="text-sm text-slate-400 py-4 text-center">
                  No applications available in the catalog.
                </p>
              ) : (
                applications.map((app) => {
                  const existing = appsLocation.applications.find(
                    (la) => la.application_id === app.id && la.status === "ACTIVE"
                  );
                  const isActive = !!existing;
                  const busy = togglingAppId === app.id;

                  return (
                    <div
                      key={app.id}
                      className="flex items-center justify-between p-3 rounded-xl bg-slate-950 border border-slate-800"
                    >
                      <div>
                        <div className="text-sm font-semibold text-white">{app.name}</div>
                        <div className="text-xs text-slate-400 font-mono">{app.code}</div>
                      </div>
                      <button
                        disabled={busy}
                        onClick={() => handleToggleApplication(appsLocation, app, isActive)}
                        className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition disabled:opacity-50 ${
                          isActive
                            ? "bg-rose-500/10 text-rose-300 border border-rose-500/30 hover:bg-rose-500/20"
                            : "bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/20"
                        }`}
                      >
                        {isActive ? (
                          <>
                            <PowerOff className="w-3.5 h-3.5" />
                            {busy ? "Updating..." : "Deactivate"}
                          </>
                        ) : (
                          <>
                            <Power className="w-3.5 h-3.5" />
                            {busy ? "Updating..." : "Enable"}
                          </>
                        )}
                      </button>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

"use client";

import React, { useState } from "react";
import {
  Store,
  PlusCircle,
  MapPin,
  Globe,
  Edit2,
  Trash2,
  Copy,
  Check,
  Search,
  Filter,
  Cloud,
  Laptop,
  CheckCircle2,
  X,
  ChevronRight
} from "lucide-react";
import { OrgLocation, Device } from "@/types";

interface LocationManagementViewProps {
  locations: OrgLocation[];
  devices: Device[];
  copiedId: string | null;
  onCopy: (text: string, id: string) => void;
  onOpenCreateModal: () => void;
  onOpenEditModal: (loc: OrgLocation) => void;
  onArchiveLocation: (loc: OrgLocation) => void;
  onViewTerminalsForLocation: (locId: string) => void;
}

export function LocationManagementView({
  locations,
  devices,
  copiedId,
  onCopy,
  onOpenCreateModal,
  onOpenEditModal,
  onArchiveLocation,
  onViewTerminalsForLocation,
}: LocationManagementViewProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<"ALL" | "ACTIVE" | "ARCHIVED">("ALL");
  const [syncFilter, setSyncFilter] = useState<"ALL" | "SYNC_ACTIVE" | "SYNC_DISABLED">("ALL");
  const [selectedDetailLocation, setSelectedDetailLocation] = useState<OrgLocation | null>(null);

  const filteredLocations = locations.filter((loc) => {
    if (statusFilter !== "ALL" && loc.status !== statusFilter) return false;
    const isSyncActive =
      (loc.metadata as any)?.["pos.sync"] !== false && (loc.metadata as any)?.["cloud_sync"] !== false;
    if (syncFilter === "SYNC_ACTIVE" && !isSyncActive) return false;
    if (syncFilter === "SYNC_DISABLED" && isSyncActive) return false;

    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      loc.name.toLowerCase().includes(q) ||
      loc.code.toLowerCase().includes(q) ||
      (loc.city && loc.city.toLowerCase().includes(q)) ||
      (loc.description && loc.description.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Store className="w-5 h-5 text-emerald-400" />
            <span>Store Locations & Operating Branches</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Authoritative operating scopes for regional licensing, multi-branch POS deployment, and Cloud Synchronization policy.
          </p>
        </div>
        <button
          onClick={onOpenCreateModal}
          className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold transition self-start sm:self-auto shadow-sm shadow-emerald-600/20"
        >
          <PlusCircle className="w-4 h-4" />
          <span>Add Location</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-slate-900/60 p-3 rounded-xl border border-slate-800">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search location by name, code, or city..."
            className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as any)}
            className="bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-300 px-3 py-1.5 focus:outline-none focus:border-indigo-500"
          >
            <option value="ALL">All Statuses ({locations.length})</option>
            <option value="ACTIVE">Active</option>
            <option value="ARCHIVED">Archived</option>
          </select>

          <select
            value={syncFilter}
            onChange={(e) => setSyncFilter(e.target.value as any)}
            className="bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-300 px-3 py-1.5 focus:outline-none focus:border-indigo-500"
          >
            <option value="ALL">All Sync Policies</option>
            <option value="SYNC_ACTIVE">Sync Active</option>
            <option value="SYNC_DISABLED">Sync Disabled</option>
          </select>
        </div>
      </div>

      {/* Scalable Data Table */}
      {filteredLocations.length === 0 ? (
        <div className="p-12 bg-slate-900/40 border border-slate-800 rounded-2xl text-center">
          <Store className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <p className="text-sm text-slate-300 font-medium">No store locations match your filter.</p>
          <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 mb-4">
            Create an operational branch location to connect POS terminals and establish inventory replication scopes.
          </p>
          <button
            onClick={onOpenCreateModal}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold transition"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span>Create First Location</span>
          </button>
        </div>
      ) : (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-950/60 text-slate-400 font-semibold uppercase tracking-wider text-[10px]">
                  <th className="py-3 px-4">Location Name & Code</th>
                  <th className="py-3 px-4">Physical Address</th>
                  <th className="py-3 px-4">Timezone</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Terminals</th>
                  <th className="py-3 px-4">POS Cloud Sync</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-medium">
                {filteredLocations.map((loc) => {
                  const isArchived = loc.status === "ARCHIVED";
                  const isActive = loc.status === "ACTIVE";
                  const assignedDevicesCount = devices.filter((d) => d.location_id === loc.id).length;
                  const isSyncActive =
                    (loc.metadata as any)?.["pos.sync"] !== false && (loc.metadata as any)?.["cloud_sync"] !== false;

                  return (
                    <tr
                      key={loc.id}
                      onClick={() => setSelectedDetailLocation(loc)}
                      className="hover:bg-slate-800/40 transition cursor-pointer"
                    >
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded text-[11px]">
                            {loc.code}
                          </span>
                          <div>
                            <div className="font-bold text-white text-xs hover:text-indigo-300 transition-colors">
                              {loc.name}
                            </div>
                            <div className="text-[10px] text-slate-500 font-mono truncate max-w-[140px] flex items-center gap-1">
                              <span>{loc.id.slice(0, 8)}...</span>
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onCopy(loc.id, loc.id);
                                }}
                                title="Copy UUID"
                                className="text-slate-500 hover:text-slate-300"
                              >
                                {copiedId === loc.id ? (
                                  <Check className="w-3 h-3 text-emerald-400" />
                                ) : (
                                  <Copy className="w-3 h-3" />
                                )}
                              </button>
                            </div>
                          </div>
                        </div>
                      </td>

                      <td className="py-3.5 px-4 text-slate-300 max-w-xs truncate">
                        <div className="flex items-center gap-1.5">
                          <MapPin className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                          <span className="truncate">
                            {[loc.address_line1, loc.city, loc.country_code].filter(Boolean).join(", ") || "No address provided"}
                          </span>
                        </div>
                      </td>

                      <td className="py-3.5 px-4 text-slate-400 font-mono text-[11px]">
                        <div className="flex items-center gap-1">
                          <Globe className="w-3 h-3 text-cyan-400 shrink-0" />
                          <span>{loc.timezone || "UTC"}</span>
                        </div>
                      </td>

                      <td className="py-3.5 px-4">
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded-full font-semibold border ${
                            isActive
                              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                              : isArchived
                              ? "bg-rose-500/10 text-rose-400 border-rose-500/20"
                              : "bg-slate-700/50 text-slate-300 border-slate-600"
                          }`}
                        >
                          {loc.status}
                        </span>
                      </td>

                      <td className="py-3.5 px-4">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            onViewTerminalsForLocation(loc.id);
                          }}
                          className="inline-flex items-center gap-1 font-mono font-bold text-indigo-400 hover:underline"
                        >
                          <Laptop className="w-3 h-3 text-indigo-400" />
                          <span>{assignedDevicesCount} POS</span>
                        </button>
                      </td>

                      <td className="py-3.5 px-4">
                        <span
                          className={`inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full font-semibold border ${
                            isSyncActive
                              ? "bg-indigo-500/10 text-indigo-300 border-indigo-500/20"
                              : "bg-slate-800 text-slate-400 border-slate-700"
                          }`}
                        >
                          <Cloud className="w-2.5 h-2.5" />
                          <span>{isSyncActive ? "Sync Active" : "Disabled"}</span>
                        </span>
                      </td>

                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5" onClick={(e) => e.stopPropagation()}>
                          {!isArchived && (
                            <button
                              onClick={() => onOpenEditModal(loc)}
                              className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg transition"
                              title="Edit location"
                            >
                              <Edit2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                          {!isArchived && (
                            <button
                              onClick={() => onArchiveLocation(loc)}
                              className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition"
                              title="Archive location"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Location Detail Slide-Over Modal */}
      {selectedDetailLocation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 font-bold text-xs">
                  {selectedDetailLocation.code}
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">{selectedDetailLocation.name}</h3>
                  <p className="text-[11px] text-slate-400 font-mono">{selectedDetailLocation.id}</p>
                </div>
              </div>
              <button
                onClick={() => setSelectedDetailLocation(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
                  <div className="text-[10px] uppercase font-bold text-slate-400 mb-0.5">Status</div>
                  <div className="text-white font-semibold">{selectedDetailLocation.status}</div>
                </div>
                <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
                  <div className="text-[10px] uppercase font-bold text-slate-400 mb-0.5">Timezone</div>
                  <div className="text-white font-semibold">{selectedDetailLocation.timezone || "UTC"}</div>
                </div>
              </div>

              <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
                <div className="text-[10px] uppercase font-bold text-slate-400 mb-0.5">Physical Address</div>
                <div className="text-slate-200">
                  {[
                    selectedDetailLocation.address_line1,
                    selectedDetailLocation.address_line2,
                    selectedDetailLocation.city,
                    selectedDetailLocation.state_province,
                    selectedDetailLocation.postal_code,
                    selectedDetailLocation.country_code,
                  ]
                    .filter(Boolean)
                    .join(", ") || "No physical address provided"}
                </div>
              </div>

              <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
                <div className="text-[10px] uppercase font-bold text-slate-400 mb-0.5">Deployment Policy</div>
                <div className="flex items-center justify-between text-slate-300 mt-1">
                  <span>Operating Policy:</span>
                  <span className="font-mono font-bold text-indigo-400">
                    {selectedDetailLocation.pos_mode_policy || "ANY_ALLOWED"}
                  </span>
                </div>
                <div className="flex items-center justify-between text-slate-300 mt-1">
                  <span>Default Menu Mode:</span>
                  <span className="font-mono font-bold text-emerald-400">
                    {selectedDetailLocation.pos_default_mode || "LOCAL"}
                  </span>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => {
                  const locId = selectedDetailLocation.id;
                  setSelectedDetailLocation(null);
                  onViewTerminalsForLocation(locId);
                }}
                className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
              >
                <span>View Assigned POS Terminals</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>

              <button
                type="button"
                onClick={() => {
                  const loc = selectedDetailLocation;
                  setSelectedDetailLocation(null);
                  onOpenEditModal(loc);
                }}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs font-semibold"
              >
                Edit Location
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

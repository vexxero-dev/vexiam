"use client";

import React, { useState } from "react";
import {
  Laptop,
  PlusCircle,
  Activity,
  MapPin,
  KeyRound,
  RefreshCw,
  CloudOff,
  Trash2,
  CheckCircle2,
  Search,
  Filter,
  Copy,
  Check,
  Cpu,
  Clock
} from "lucide-react";
import { Device, OrgLocation, Application, ActivatedSyncTicket } from "@/types";

interface TerminalManagementViewProps {
  devices: Device[];
  locations: OrgLocation[];
  applications: Application[];
  activatedLicense: string | null;
  activatedSyncTicket: ActivatedSyncTicket | null;
  syncActivatingDeviceId: string | null;
  copiedId: string | null;
  onCopy: (text: string, id: string) => void;
  onRegisterDevice: (e: React.FormEvent) => void;
  newDeviceName: string;
  setNewDeviceName: (v: string) => void;
  newDeviceFingerprint: string;
  setNewDeviceFingerprint: (v: string) => void;
  newDevicePublicKey: string;
  setNewDevicePublicKey: (v: string) => void;
  onReassignDevice: (deviceId: string, locationId: string) => void;
  onUpdateMenuMode: (deviceId: string, mode: string) => void;
  onIssueLicense: (deviceId: string, appId: string) => void;
  onActivateSync: (deviceId: string, appCode?: string) => void;
  onDeactivateSync: (deviceId: string) => void;
  onDeleteDevice: (deviceId: string, deviceName: string) => void;
  formatHeartbeatTime: (timestamp?: string | null) => string;
}

export function TerminalManagementView({
  devices,
  locations,
  applications,
  activatedLicense,
  activatedSyncTicket,
  syncActivatingDeviceId,
  copiedId,
  onCopy,
  onRegisterDevice,
  newDeviceName,
  setNewDeviceName,
  newDeviceFingerprint,
  setNewDeviceFingerprint,
  newDevicePublicKey,
  setNewDevicePublicKey,
  onReassignDevice,
  onUpdateMenuMode,
  onIssueLicense,
  onActivateSync,
  onDeactivateSync,
  onDeleteDevice,
  formatHeartbeatTime,
}: TerminalManagementViewProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [locationFilter, setLocationFilter] = useState<string>("ALL");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");

  const filteredDevices = devices.filter((dev) => {
    if (locationFilter !== "ALL") {
      if (locationFilter === "UNASSIGNED" && dev.location_id) return false;
      if (locationFilter !== "UNASSIGNED" && dev.location_id !== locationFilter) return false;
    }
    if (statusFilter !== "ALL" && dev.status !== statusFilter) return false;

    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      dev.name.toLowerCase().includes(q) ||
      dev.fingerprint.toLowerCase().includes(q) ||
      dev.id.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Laptop className="w-5 h-5 text-cyan-400" />
            <span>Hardware Terminals & POS Devices</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Authoritative device register for hardware fingerprints, Ed25519 offline licenses, and POS Cloud Sync session tickets.
          </p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-slate-900/60 p-3 rounded-xl border border-slate-800">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search terminal by name or fingerprint..."
            className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <select
            value={locationFilter}
            onChange={(e) => setLocationFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-300 px-3 py-1.5 focus:outline-none focus:border-indigo-500"
          >
            <option value="ALL">All Locations ({devices.length})</option>
            <option value="UNASSIGNED">Unassigned Terminals</option>
            {locations.map((l) => (
              <option key={l.id} value={l.id}>
                {l.name} ({l.code})
              </option>
            ))}
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-300 px-3 py-1.5 focus:outline-none focus:border-indigo-500"
          >
            <option value="ALL">All Statuses</option>
            <option value="ACTIVE">Active</option>
            <option value="SUSPENDED">Suspended</option>
          </select>
        </div>
      </div>

      {/* Scalable Data Table */}
      {filteredDevices.length === 0 ? (
        <div className="p-12 bg-slate-900/40 border border-slate-800 rounded-2xl text-center">
          <Laptop className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <p className="text-sm text-slate-300 font-medium">No terminals match your filter.</p>
          <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 mb-4">
            Register hardware terminals below to issue cryptographic offline licenses and activate POS Cloud synchronization.
          </p>
        </div>
      ) : (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-950/60 text-slate-400 font-semibold uppercase tracking-wider text-[10px]">
                  <th className="py-3 px-4">Terminal Name & Fingerprint</th>
                  <th className="py-3 px-4">Store Location</th>
                  <th className="py-3 px-4">Operating Mode</th>
                  <th className="py-3 px-4">Heartbeat</th>
                  <th className="py-3 px-4">Offline License</th>
                  <th className="py-3 px-4">Sync Token</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-medium">
                {filteredDevices.map((dev) => {
                  const subLic = dev.licenses?.[0];
                  const hasActiveLicense = subLic?.status === "ACTIVE";
                  const assignedLoc = locations.find((l) => l.id === dev.location_id);
                  const isSyncActive = dev.sync_enabled || (activatedSyncTicket && activatedSyncTicket.device_id === dev.id);

                  return (
                    <tr key={dev.id} className="hover:bg-slate-800/40 transition">
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-2">
                          <div className="w-7 h-7 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 shrink-0">
                            <Laptop className="w-3.5 h-3.5" />
                          </div>
                          <div>
                            <div className="font-bold text-white text-xs">{dev.name}</div>
                            <div className="text-[10px] text-slate-400 font-mono truncate max-w-[180px] flex items-center gap-1">
                              <span>HW: {dev.fingerprint}</span>
                              <button
                                type="button"
                                onClick={() => onCopy(dev.fingerprint, dev.fingerprint)}
                                title="Copy Fingerprint"
                                className="text-slate-500 hover:text-slate-300"
                              >
                                {copiedId === dev.fingerprint ? (
                                  <Check className="w-3 h-3 text-emerald-400" />
                                ) : (
                                  <Copy className="w-3 h-3" />
                                )}
                              </button>
                            </div>
                          </div>
                        </div>
                      </td>

                      <td className="py-3.5 px-4">
                        <select
                          value={dev.location_id || ""}
                          onChange={(e) => onReassignDevice(dev.id, e.target.value)}
                          className="bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded-lg px-2.5 py-1 focus:outline-none focus:border-indigo-500 max-w-[160px] truncate"
                        >
                          <option value="">Unassigned</option>
                          {locations.map((l) => (
                            <option key={l.id} value={l.id}>
                              {l.name} ({l.code})
                            </option>
                          ))}
                        </select>
                      </td>

                      <td className="py-3.5 px-4">
                        <div className="space-y-1">
                          <select
                            value={dev.menu_mode || (assignedLoc?.pos_default_mode || "LOCAL")}
                            onChange={(e) => onUpdateMenuMode(dev.id, e.target.value)}
                            className={`border text-[11px] rounded-lg px-2 py-0.5 focus:outline-none ${
                              (dev.menu_mode || assignedLoc?.pos_default_mode) === "CLOUD"
                                ? "bg-indigo-950/60 border-indigo-700/60 text-indigo-300"
                                : "bg-slate-950 border-slate-800 text-slate-300"
                            }`}
                          >
                            <option value="LOCAL">Local POS</option>
                            <option value="CLOUD">Cloud Replica</option>
                          </select>
                          <div className="text-[9px] text-slate-500 font-mono">
                            Effective: {dev.effective_menu_mode || dev.menu_mode || assignedLoc?.pos_default_mode || "LOCAL"}
                          </div>
                        </div>
                      </td>

                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-1.5 text-slate-400 text-[11px]">
                          <Activity
                            className={`w-3.5 h-3.5 ${
                              dev.last_heartbeat_at ? "text-emerald-400" : "text-slate-600"
                            }`}
                          />
                          <span className={dev.last_heartbeat_at ? "text-slate-300 font-medium" : "text-slate-500 font-normal"}>
                            {formatHeartbeatTime(dev.last_heartbeat_at)}
                          </span>
                        </div>
                      </td>

                      <td className="py-3.5 px-4">
                        {hasActiveLicense ? (
                          <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                            <CheckCircle2 className="w-3 h-3 text-cyan-400" />
                            <span>Active 30d</span>
                          </span>
                        ) : (
                          <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-slate-800 text-slate-400 border border-slate-700">
                            Unlicensed
                          </span>
                        )}
                      </td>

                      <td className="py-3.5 px-4">
                        <span
                          className={`inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full font-semibold border ${
                            isSyncActive
                              ? "bg-indigo-500/10 text-indigo-300 border-indigo-500/20"
                              : "bg-slate-800 text-slate-400 border-slate-700"
                          }`}
                        >
                          <RefreshCw className={`w-2.5 h-2.5 ${isSyncActive ? "text-indigo-400" : "text-slate-500"}`} />
                          <span>{isSyncActive ? "Sync Enabled" : "Disabled"}</span>
                        </span>
                      </td>

                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {applications.length > 0 && (
                            <button
                              onClick={() => onIssueLicense(dev.id, applications[0].id)}
                              className="px-2.5 py-1 bg-cyan-600/90 hover:bg-cyan-600 text-white rounded-lg text-xs font-semibold transition flex items-center gap-1 shadow-sm"
                              title="Issue or renew Ed25519 cryptographic offline license"
                            >
                              <KeyRound className="w-3 h-3" />
                              <span>{hasActiveLicense ? "Renew" : "License"}</span>
                            </button>
                          )}

                          {isSyncActive ? (
                            <button
                              onClick={() => onDeactivateSync(dev.id)}
                              disabled={syncActivatingDeviceId === dev.id}
                              title="Disable POS Cloud Sync ticket"
                              className="px-2.5 py-1 bg-rose-600/80 hover:bg-rose-600 text-white rounded-lg text-xs font-semibold transition flex items-center gap-1"
                            >
                              <CloudOff className="w-3 h-3" />
                              <span>{syncActivatingDeviceId === dev.id ? "..." : "Disable"}</span>
                            </button>
                          ) : (
                            <button
                              onClick={() => onActivateSync(dev.id, "VEX-POS")}
                              disabled={syncActivatingDeviceId === dev.id}
                              title="Activate POS Cloud Synchronization"
                              className="px-2.5 py-1 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold transition flex items-center gap-1"
                            >
                              <RefreshCw className={`w-3 h-3 ${syncActivatingDeviceId === dev.id ? "animate-spin" : ""}`} />
                              <span>{syncActivatingDeviceId === dev.id ? "..." : "Sync"}</span>
                            </button>
                          )}

                          <button
                            onClick={() => onDeleteDevice(dev.id, dev.name)}
                            title="Delete terminal registration"
                            className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
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

      {/* Cryptographic License & Sync Ticket Display Banners */}
      {activatedLicense && (
        <div className="p-4 bg-cyan-950/40 border border-cyan-800/50 rounded-xl">
          <p className="text-xs font-bold text-cyan-300 mb-1 flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4 text-cyan-400" />
            <span>Cryptographic Ed25519 Offline License Generated:</span>
          </p>
          <p className="text-[11px] text-slate-300 mb-2">
            Install this offline license on the local VEX POS terminal. It cryptographically authenticates offline for 30 days without an internet connection.
          </p>
          <textarea
            readOnly
            rows={3}
            value={activatedLicense}
            className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 font-mono text-[11px] text-cyan-200 select-all"
          />
        </div>
      )}

      {activatedSyncTicket && (
        <div className="p-4 bg-indigo-950/40 border border-indigo-800/50 rounded-xl">
          <p className="text-xs font-bold text-indigo-300 mb-1 flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4 text-indigo-400" />
            <span>Activated POS Cloud Synchronization Ticket:</span>
          </p>
          <p className="text-[11px] text-slate-300 mb-1">
            Gateway Endpoint: <strong className="font-mono text-indigo-300">{activatedSyncTicket.sync_endpoint}</strong>
          </p>
          <textarea
            readOnly
            rows={3}
            value={activatedSyncTicket.signed_ticket}
            className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 font-mono text-[11px] text-indigo-200 select-all"
          />
        </div>
      )}

      {/* Register New Terminal Form */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
        <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
          <PlusCircle className="w-4 h-4 text-indigo-400" />
          <span>Register New Hardware POS Terminal</span>
        </h3>
        <p className="text-xs text-slate-400 mb-4">
          Register the physical device hardware fingerprint generated by the VEX POS native workstation.
        </p>

        <form onSubmit={onRegisterDevice} className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <input
            type="text"
            required
            value={newDeviceName}
            onChange={(e) => setNewDeviceName(e.target.value)}
            placeholder="Device Name (e.g. Counter POS #1)"
            className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
          />
          <input
            type="text"
            required
            value={newDeviceFingerprint}
            onChange={(e) => setNewDeviceFingerprint(e.target.value)}
            placeholder="Hardware Fingerprint (e.g. HW-8934FA-X)"
            className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
          />
          <input
            type="text"
            required
            value={newDevicePublicKey}
            onChange={(e) => setNewDevicePublicKey(e.target.value)}
            placeholder="Device Ed25519 Public Key"
            className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-indigo-500"
          />
          <button
            type="submit"
            className="bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold py-2 transition shadow-sm shadow-indigo-600/20"
          >
            Register Terminal
          </button>
        </form>
      </div>
    </div>
  );
}

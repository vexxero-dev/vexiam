"use client";

import React from "react";
import {
  Users,
  Store,
  Laptop,
  CreditCard,
  Building2,
  ArrowRight,
  ShieldCheck,
  Activity,
  CheckCircle2,
  PlusCircle,
  ExternalLink
} from "lucide-react";
import { Organization, Member, OrgLocation, Device, Subscription, MainNavSection } from "@/types";

interface ExecutiveOverviewViewProps {
  selectedOrg: Organization | null;
  members: Member[];
  locations: OrgLocation[];
  devices: Device[];
  subscriptions: Subscription[];
  onNavigateSection: (section: MainNavSection) => void;
  onOpenCreateLocation: () => void;
  formatHeartbeatTime: (timestamp?: string | null) => string;
}

export function ExecutiveOverviewView({
  selectedOrg,
  members,
  locations,
  devices,
  subscriptions,
  onNavigateSection,
  onOpenCreateLocation,
  formatHeartbeatTime,
}: ExecutiveOverviewViewProps) {
  const activeTerminalsCount = devices.filter((d) => d.status === "ACTIVE").length;
  const activeLocationsCount = locations.filter((l) => l.status === "ACTIVE").length;
  const activeSubscriptionsCount = subscriptions.filter((s) => s.status === "ACTIVE").length;

  return (
    <div className="space-y-6">
      {/* Entity Welcome Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950/30 to-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
              WORKSPACE
            </span>
            <span className="text-xs text-slate-400">
              {selectedOrg?.registration_number ? `Reg # ${selectedOrg.registration_number}` : "Central Business Workspace"}
            </span>
          </div>
          <h2 className="text-2xl font-bold text-white tracking-tight">
            {selectedOrg ? selectedOrg.name : "Select a Business Entity"}
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Federated access control, multi-location POS deployment, and cryptographic license orchestration.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => onNavigateSection("org_locations")}
            className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-semibold transition flex items-center gap-1.5"
          >
            <Store className="w-3.5 h-3.5 text-emerald-400" />
            <span>Manage Locations</span>
          </button>
          <button
            onClick={() => onNavigateSection("org_terminals")}
            className="px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold transition flex items-center gap-1.5 shadow-sm shadow-indigo-600/30"
          >
            <Laptop className="w-3.5 h-3.5" />
            <span>Terminals</span>
          </button>
        </div>
      </div>

      {/* Metric Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total User Pool"
          value={String(members.length)}
          subtitle="Assigned members"
          icon={Users}
          iconColor="text-indigo-400"
          onClick={() => onNavigateSection("org_team")}
        />
        <MetricCard
          title="Store Locations"
          value={String(locations.length)}
          subtitle={`${activeLocationsCount} active branches`}
          icon={Store}
          iconColor="text-emerald-400"
          onClick={() => onNavigateSection("org_locations")}
        />
        <MetricCard
          title="Hardware Terminals"
          value={String(devices.length)}
          subtitle={`${activeTerminalsCount} online replicas`}
          icon={Laptop}
          iconColor="text-cyan-400"
          onClick={() => onNavigateSection("org_terminals")}
        />
        <MetricCard
          title="Active Subscriptions"
          value={String(subscriptions.length)}
          subtitle={`${activeSubscriptionsCount} plan entitlements`}
          icon={CreditCard}
          iconColor="text-purple-400"
          onClick={() => onNavigateSection("org_subscriptions")}
        />
      </div>

      {/* Two Column Section: Quick Recent Activity / Terminal Status & Location Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Terminals Online Status */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Laptop className="w-4 h-4 text-cyan-400" />
                <span>Recent Terminal Heartbeats</span>
              </h3>
              <p className="text-xs text-slate-400">Live POS terminals reporting to VEX Cloud</p>
            </div>
            <button
              onClick={() => onNavigateSection("org_terminals")}
              className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
            >
              <span>View All</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {devices.length === 0 ? (
            <div className="p-8 bg-slate-950 rounded-xl border border-slate-800 text-center">
              <Laptop className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <p className="text-xs text-slate-400">No terminals registered yet.</p>
            </div>
          ) : (
            <div className="space-y-2.5">
              {devices.slice(0, 5).map((dev) => (
                <div
                  key={dev.id}
                  className="p-3 bg-slate-950 border border-slate-800 rounded-xl flex items-center justify-between text-xs"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full bg-emerald-400"></div>
                    <div>
                      <div className="font-semibold text-white">{dev.name}</div>
                      <div className="text-[10px] text-slate-500 font-mono">HW: {dev.fingerprint}</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] text-slate-400">
                      Heartbeat: <strong>{formatHeartbeatTime(dev.last_heartbeat_at)}</strong>
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Operating Branches Quick List */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Store className="w-4 h-4 text-emerald-400" />
                <span>Operational Store Branches</span>
              </h3>
              <p className="text-xs text-slate-400">Physical branches configured for POS sync</p>
            </div>
            <button
              onClick={() => onNavigateSection("org_locations")}
              className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
            >
              <span>View All</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {locations.length === 0 ? (
            <div className="p-8 bg-slate-950 rounded-xl border border-slate-800 text-center">
              <Store className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <p className="text-xs text-slate-400 mb-3">No store branches created yet.</p>
              <button
                onClick={onOpenCreateLocation}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold transition"
              >
                <PlusCircle className="w-3.5 h-3.5" />
                <span>Add Branch</span>
              </button>
            </div>
          ) : (
            <div className="space-y-2.5">
              {locations.slice(0, 5).map((loc) => {
                const assignedCount = devices.filter((d) => d.location_id === loc.id).length;
                return (
                  <div
                    key={loc.id}
                    className="p-3 bg-slate-950 border border-slate-800 rounded-xl flex items-center justify-between text-xs"
                  >
                    <div>
                      <div className="font-semibold text-white flex items-center gap-2">
                        <span>{loc.name}</span>
                        <span className="font-mono text-[10px] text-emerald-400 bg-emerald-500/10 px-1.5 py-0.2 rounded border border-emerald-500/20">
                          {loc.code}
                        </span>
                      </div>
                      <div className="text-[10px] text-slate-500">{loc.city || "Primary Branch"} • {loc.timezone || "UTC"}</div>
                    </div>
                    <div className="font-mono text-xs text-indigo-400 font-bold">
                      {assignedCount} {assignedCount === 1 ? "POS" : "POS devices"}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
  iconColor,
  onClick,
}: {
  title: string;
  value: string;
  subtitle: string;
  icon: React.ComponentType<{ className?: string }>;
  iconColor: string;
  onClick: () => void;
}) {
  return (
    <div
      onClick={onClick}
      className="p-5 bg-slate-900 border border-slate-800 rounded-2xl hover:border-slate-700 transition cursor-pointer shadow-sm group"
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold text-slate-400">{title}</span>
        <div className="p-2 rounded-xl bg-slate-950 border border-slate-800 group-hover:border-slate-700 transition">
          <Icon className={`w-4 h-4 ${iconColor}`} />
        </div>
      </div>
      <div className="text-2xl font-black text-white font-mono">{value}</div>
      <div className="text-[11px] text-slate-500 mt-1 flex items-center justify-between">
        <span>{subtitle}</span>
        <ArrowRight className="w-3 h-3 text-slate-600 group-hover:text-white transition-colors" />
      </div>
    </div>
  );
}

"use client";

import React from "react";
import {
  Users,
  CreditCard,
  Building2,
  ArrowRight,
  Layers,
  ShieldCheck,
  Activity,
  CheckCircle2,
  PlusCircle,
  ExternalLink
} from "lucide-react";
import { Organization, Member, Subscription, Application, MainNavSection } from "@/types";

interface ExecutiveOverviewViewProps {
  selectedOrg: Organization | null;
  members: Member[];
  subscriptions: Subscription[];
  applications: Application[];
  onNavigateSection: (section: MainNavSection) => void;
  onOpenCreateOrg: () => void;
}

export function ExecutiveOverviewView({
  selectedOrg,
  members,
  subscriptions,
  applications,
  onNavigateSection,
  onOpenCreateOrg,
}: ExecutiveOverviewViewProps) {
  const activeSubscriptionsCount = subscriptions.filter((s) => s.status === "ACTIVE").length;
  const ownerMembersCount = members.filter((m) => m.role === "OWNER").length;
  const adminMembersCount = members.filter((m) => m.role === "ADMIN").length;

  return (
    <div className="space-y-6">
      {/* Entity Welcome Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950/30 to-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
              CENTRAL IAM WORKSPACE
            </span>
            <span className="text-xs text-slate-400">
              {selectedOrg?.registration_number ? `Reg # ${selectedOrg.registration_number}` : "Enterprise Organization"}
            </span>
          </div>
          <h2 className="text-2xl font-bold text-white tracking-tight">
            {selectedOrg ? selectedOrg.name : "Select or Establish a Business Entity"}
          </h2>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl leading-relaxed">
            Centralized federated authentication, user pool memberships, and application subscriptions across the VEX software ecosystem.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => onNavigateSection("org_members")}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-semibold transition flex items-center gap-1.5 border border-slate-700"
          >
            <Users className="w-3.5 h-3.5 text-indigo-400" />
            <span>Manage Members</span>
          </button>
          <button
            onClick={() => onNavigateSection("subscriptions")}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold transition flex items-center gap-1.5 shadow-sm shadow-indigo-600/30"
          >
            <CreditCard className="w-3.5 h-3.5" />
            <span>View Subscriptions</span>
          </button>
        </div>
      </div>

      {/* Metric Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Organization Members"
          value={String(members.length)}
          subtitle={`${ownerMembersCount} Owner, ${adminMembersCount} Admins`}
          icon={Users}
          iconColor="text-indigo-400"
          onClick={() => onNavigateSection("org_members")}
        />
        <MetricCard
          title="Active Subscriptions"
          value={String(activeSubscriptionsCount)}
          subtitle="Commercial entitlements"
          icon={CreditCard}
          iconColor="text-emerald-400"
          onClick={() => onNavigateSection("subscriptions")}
        />
        <MetricCard
          title="Application Catalog"
          value={String(applications.length)}
          subtitle="Verified ecosystem apps"
          icon={Layers}
          iconColor="text-cyan-400"
          onClick={() => onNavigateSection("app_catalog")}
        />
        <MetricCard
          title="IAM Authority Status"
          value="OIDC 2.1"
          subtitle="Ed25519 Token Signing"
          icon={ShieldCheck}
          iconColor="text-purple-400"
          onClick={() => onNavigateSection("security")}
        />
      </div>

      {/* Two Column Summary: Subscribed Applications & Member Pool Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Subscribed Applications with Direct Launch Link */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Layers className="w-4 h-4 text-indigo-400" />
                <span>Entitled Ecosystem Applications</span>
              </h3>
              <p className="text-xs text-slate-400">Applications authorized for this business entity</p>
            </div>
            <button
              onClick={() => onNavigateSection("app_catalog")}
              className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
            >
              <span>Catalog</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {subscriptions.length === 0 ? (
            <div className="p-8 bg-slate-950 rounded-xl border border-slate-800 text-center">
              <Layers className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <p className="text-xs text-slate-400 mb-2">No active subscriptions registered yet.</p>
              <button
                onClick={() => onNavigateSection("subscriptions")}
                className="text-xs font-semibold text-indigo-400 hover:underline"
              >
                Browse Subscriptions →
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {subscriptions.slice(0, 4).map((sub) => {
                const appObj = applications.find((a) => a.id === sub.plan?.application_id);
                const isPos = appObj?.code.toLowerCase().includes("pos");
                const consoleUrl = isPos ? "https://pos-console.vexxero.com" : "#";

                return (
                  <div
                    key={sub.id}
                    className="p-3.5 bg-slate-950 border border-slate-800 rounded-xl flex items-center justify-between text-xs hover:border-slate-700 transition"
                  >
                    <div>
                      <div className="font-bold text-white flex items-center gap-2">
                        <span>{appObj?.name || sub.plan?.name}</span>
                        <span className="font-mono text-[9px] text-indigo-400 bg-indigo-500/10 px-1.5 py-0.2 rounded border border-indigo-500/20">
                          {sub.plan?.code}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-400 mt-0.5">
                        Capacity: {sub.plan?.user_seats} User Seats • {sub.plan?.device_seats} Device Limit
                      </div>
                    </div>

                    <a
                      href={consoleUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 px-3 py-1 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 rounded-lg text-xs font-semibold transition"
                    >
                      <span>Launch</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Member Directory Snapshot */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Users className="w-4 h-4 text-emerald-400" />
                <span>Organization Member Pool</span>
              </h3>
              <p className="text-xs text-slate-400">Personnel with workspace privileges</p>
            </div>
            <button
              onClick={() => onNavigateSection("org_members")}
              className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
            >
              <span>View All</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {members.length === 0 ? (
            <div className="p-8 bg-slate-950 rounded-xl border border-slate-800 text-center">
              <Users className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <p className="text-xs text-slate-400">No members in user pool yet.</p>
            </div>
          ) : (
            <div className="space-y-2.5">
              {members.slice(0, 5).map((m) => (
                <div
                  key={m.id}
                  className="p-3 bg-slate-950 border border-slate-800 rounded-xl flex items-center justify-between text-xs"
                >
                  <div className="flex items-center gap-2.5">
                    <div className="w-7 h-7 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-xs font-bold text-indigo-400">
                      {m.user?.profile?.first_name ? m.user.profile.first_name[0] : (m.user?.email[0] || "U").toUpperCase()}
                    </div>
                    <div>
                      <div className="font-semibold text-white">
                        {m.user?.profile?.first_name} {m.user?.profile?.last_name || ""}
                      </div>
                      <div className="text-[10px] text-slate-400">{m.user?.email}</div>
                    </div>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${
                      m.role === "OWNER"
                        ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                        : m.role === "ADMIN"
                        ? "bg-indigo-500/10 text-indigo-400 border-indigo-500/20"
                        : "bg-slate-800 text-slate-300 border-slate-700"
                    }`}
                  >
                    {m.role}
                  </span>
                </div>
              ))}
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

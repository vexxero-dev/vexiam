"use client";

import React from "react";
import {
  LayoutDashboard,
  ShieldCheck,
  Building2,
  Users,
  Layers,
  CreditCard,
  Lock,
  FileText,
  Settings,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
} from "lucide-react";
import { Organization, MainNavSection } from "@/types";

interface SidebarProps {
  collapsed: boolean;
  onToggleCollapse: () => void;
  activeSection: MainNavSection;
  onSelectSection: (section: MainNavSection) => void;
  organizations: Organization[];
  selectedOrg: Organization | null;
  onSelectOrg: (org: Organization) => void;
  onOpenCreateOrg: () => void;
}

export function Sidebar({
  collapsed,
  onToggleCollapse,
  activeSection,
  onSelectSection,
  organizations,
  selectedOrg,
  onSelectOrg,
  onOpenCreateOrg,
}: SidebarProps) {
  return (
    <aside
      className={`bg-slate-950 border-r border-slate-800 text-slate-200 flex flex-col shrink-0 transition-all duration-300 select-none ${
        collapsed ? "w-16" : "w-64"
      }`}
    >
      {/* Brand Header */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-slate-800">
        <div className="flex items-center gap-3 overflow-hidden">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-700 to-purple-600 flex items-center justify-center font-black text-white shadow-lg shadow-indigo-600/30 shrink-0">
            V
          </div>
          {!collapsed && (
            <div className="truncate">
              <div className="font-bold text-sm tracking-wide text-white flex items-center gap-1.5">
                VEX IAM
                <span className="text-[9px] uppercase font-mono font-bold px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                  Global
                </span>
              </div>
              <div className="text-[11px] text-slate-400 truncate">Identity & Orgs</div>
            </div>
          )}
        </div>
        <button
          onClick={onToggleCollapse}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* Organization / Workspace Switcher */}
      <div className="p-3 border-b border-slate-800">
        {!collapsed ? (
          <div>
            <div className="text-[10px] uppercase font-bold tracking-wider text-slate-400 mb-1.5 flex items-center justify-between">
              <span className="flex items-center gap-1">
                <Building2 className="w-3 h-3 text-indigo-400" /> Active Entity
              </span>
              <button
                type="button"
                onClick={onOpenCreateOrg}
                className="text-[10px] text-indigo-400 hover:text-indigo-300 font-semibold"
              >
                + New
              </button>
            </div>
            {organizations.length > 0 ? (
              <div className="relative">
                <select
                  value={selectedOrg?.id || ""}
                  onChange={(e) => {
                    const found = organizations.find((o) => o.id === e.target.value);
                    if (found) onSelectOrg(found);
                  }}
                  className="w-full appearance-none bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-white pr-7 focus:outline-none focus:border-indigo-500 font-medium truncate cursor-pointer"
                >
                  {organizations.map((org) => (
                    <option key={org.id} value={org.id} className="bg-slate-900 text-slate-200">
                      {org.name}
                    </option>
                  ))}
                </select>
                <ChevronDown className="w-3.5 h-3.5 absolute right-2 top-2.5 text-slate-400 pointer-events-none" />
              </div>
            ) : (
              <div className="p-2 rounded-lg bg-slate-900/60 border border-slate-800 text-[11px] text-slate-400 text-center">
                No organizations registered
              </div>
            )}
          </div>
        ) : (
          <div className="flex justify-center" title={selectedOrg ? `Active: ${selectedOrg.name}` : "Entity"}>
            <div className="w-9 h-9 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-center text-xs font-bold text-indigo-400">
              {selectedOrg?.name?.slice(0, 2).toUpperCase() || <Building2 className="w-4 h-4" />}
            </div>
          </div>
        )}
      </div>

      {/* Nav Items (Strictly Architecture-Aligned 9 Navigation Items) */}
      <nav className="flex-1 px-2.5 py-4 space-y-6 overflow-y-auto">
        {/* Section 1: Central Identity & Organizations */}
        <div>
          {!collapsed && (
            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 px-2.5 mb-1.5">
              Core Identity
            </div>
          )}
          <div className="space-y-1">
            <NavItem
              collapsed={collapsed}
              active={activeSection === "overview"}
              onClick={() => onSelectSection("overview")}
              icon={LayoutDashboard}
              label="Overview"
            />
            <NavItem
              collapsed={collapsed}
              active={activeSection === "identity"}
              onClick={() => onSelectSection("identity")}
              icon={ShieldCheck}
              label="Individual Identity"
            />
            <NavItem
              collapsed={collapsed}
              active={activeSection === "business_entities"}
              onClick={() => onSelectSection("business_entities")}
              icon={Building2}
              label="Business Entities"
              badge={organizations.length > 0 ? String(organizations.length) : undefined}
            />
            <NavItem
              collapsed={collapsed}
              active={activeSection === "org_members"}
              onClick={() => onSelectSection("org_members")}
              icon={Users}
              label="Organization Members"
            />
          </div>
        </div>

        {/* Section 2: Ecosystem & Entitlements */}
        <div>
          {!collapsed && (
            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 px-2.5 mb-1.5">
              Ecosystem & Billing
            </div>
          )}
          <div className="space-y-1">
            <NavItem
              collapsed={collapsed}
              active={activeSection === "app_catalog"}
              onClick={() => onSelectSection("app_catalog")}
              icon={Layers}
              label="Application Catalog"
            />
            <NavItem
              collapsed={collapsed}
              active={activeSection === "subscriptions"}
              onClick={() => onSelectSection("subscriptions")}
              icon={CreditCard}
              label="Subscriptions & Entitlements"
            />
          </div>
        </div>

        {/* Section 3: Platform Governance */}
        <div>
          {!collapsed && (
            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 px-2.5 mb-1.5">
              Governance
            </div>
          )}
          <div className="space-y-1">
            <NavItem
              collapsed={collapsed}
              active={activeSection === "security"}
              onClick={() => onSelectSection("security")}
              icon={Lock}
              label="Security & Access"
            />
            <NavItem
              collapsed={collapsed}
              active={activeSection === "audit"}
              onClick={() => onSelectSection("audit")}
              icon={FileText}
              label="Audit Logs"
            />
            <NavItem
              collapsed={collapsed}
              active={activeSection === "settings"}
              onClick={() => onSelectSection("settings")}
              icon={Settings}
              label="Platform Settings"
            />
          </div>
        </div>
      </nav>

      {/* Footer Info */}
      {!collapsed && (
        <div className="p-3 border-t border-slate-800 text-[11px] text-slate-400 flex items-center justify-between">
          <span className="flex items-center gap-1 font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            VEX IAM Platform
          </span>
          <span className="font-mono text-[10px] text-slate-500">OAuth 2.1 / OIDC</span>
        </div>
      )}
    </aside>
  );
}

function NavItem({
  collapsed,
  active,
  onClick,
  icon: Icon,
  label,
  badge,
}: {
  collapsed: boolean;
  active: boolean;
  onClick: () => void;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  badge?: string;
}) {
  return (
    <button
      type="button"
      data-active={active ? "true" : "false"}
      onClick={onClick}
      title={collapsed ? label : undefined}
      className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-semibold transition-all group ${
        active
          ? "bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 shadow-sm shadow-indigo-500/10 font-bold"
          : "text-slate-400 hover:text-slate-200 hover:bg-slate-900 border border-transparent"
      } ${collapsed ? "justify-center px-0" : ""}`}
    >
      <Icon
        className={`w-4 h-4 shrink-0 transition-colors ${
          active ? "text-indigo-400" : "text-slate-400 group-hover:text-slate-200"
        }`}
      />
      {!collapsed && (
        <span className="flex-1 text-left truncate">{label}</span>
      )}
      {!collapsed && badge && (
        <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
          active ? "bg-indigo-500/20 text-indigo-300 font-bold" : "bg-slate-800 text-slate-400"
        }`}>
          {badge}
        </span>
      )}
    </button>
  );
}

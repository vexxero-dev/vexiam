"use client";

import React, { useState } from "react";
import {
  ChevronRight,
  LogOut,
  User as UserIcon,
  ShieldCheck,
  Building2,
  Sun,
  Moon,
} from "lucide-react";
import { User, Organization, MainNavSection } from "@/types";
import { useTheme } from "@/components/theme-provider";

interface TopbarProps {
  user: User;
  activeSection: MainNavSection;
  selectedOrg: Organization | null;
  onLogout: () => void;
  onNavigateSection: (section: MainNavSection) => void;
}

const sectionTitles: Record<MainNavSection, { title: string; category: string }> = {
  overview: { title: "Executive Overview", category: "IAM Workspace" },
  identity: { title: "Individual Identity", category: "Core Identity" },
  business_entities: { title: "Business Entities Directory", category: "Core Identity" },
  org_members: { title: "Organization Members", category: "Core Identity" },
  app_catalog: { title: "Application Catalog", category: "Ecosystem & Billing" },
  subscriptions: { title: "Subscriptions & Entitlements", category: "Ecosystem & Billing" },
  security: { title: "Security & Access", category: "Platform Governance" },
  audit: { title: "Audit & Security Ledger", category: "Platform Governance" },
  settings: { title: "Platform Settings", category: "Platform Governance" },
};

export function Topbar({
  user,
  activeSection,
  selectedOrg,
  onLogout,
  onNavigateSection,
}: TopbarProps) {
  const [userDropdownOpen, setUserDropdownOpen] = useState(false);
  const { theme, toggleTheme } = useTheme();
  const currentMeta = sectionTitles[activeSection] || { title: "Workspace", category: "IAM" };

  return (
    <header className="h-16 bg-slate-950/80 backdrop-blur-md border-b border-slate-800 px-6 flex items-center justify-between shrink-0 sticky top-0 z-30 transition-colors">
      {/* Breadcrumb Navigation */}
      <nav aria-label="Breadcrumb" className="flex items-center gap-2 text-xs">
        <span className="text-slate-400 font-medium">VEX IAM</span>
        <ChevronRight className="w-3.5 h-3.5 text-slate-600" />
        
        {/* Category */}
        <span className="text-slate-400">{currentMeta.category}</span>
        <ChevronRight className="w-3.5 h-3.5 text-slate-600" />

        {/* Current Page Title */}
        <span className="text-white font-semibold flex items-center gap-1.5">
          {currentMeta.title}
        </span>

        {/* Active Organization Context Pill */}
        {selectedOrg && (
          <>
            <span className="text-slate-600 mx-1">•</span>
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 text-[11px] font-medium">
              <Building2 className="w-3 h-3 text-indigo-400" />
              {selectedOrg.name}
            </span>
          </>
        )}
      </nav>

      {/* Right Controls */}
      <div className="flex items-center gap-3">
        {/* Theme Toggle Button */}
        <button
          type="button"
          onClick={toggleTheme}
          title={theme === "dark" ? "Switch to Light Theme" : "Switch to Dark Theme"}
          className="p-2 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-400 hover:text-white transition flex items-center justify-center shadow-sm"
        >
          {theme === "dark" ? (
            <Sun className="w-4 h-4 text-amber-400" />
          ) : (
            <Moon className="w-4 h-4 text-indigo-600" />
          )}
        </button>

        {/* User Identity Pill */}
        <div className="relative">
          <button
            onClick={() => setUserDropdownOpen(!userDropdownOpen)}
            className="flex items-center gap-3 p-1.5 pr-2.5 rounded-xl hover:bg-slate-900 border border-transparent hover:border-slate-800 transition"
          >
            <div className="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-xs font-bold text-indigo-400">
              {user.profile?.first_name ? user.profile.first_name[0] : user.email[0].toUpperCase()}
            </div>
            <div className="text-left hidden sm:block">
              <div className="text-xs font-semibold text-white leading-tight">
                {user.profile?.first_name} {user.profile?.last_name || ""}
              </div>
              <div className="text-[10px] text-slate-400 leading-tight truncate max-w-[160px]">
                {user.email}
              </div>
            </div>
          </button>

          {/* User Dropdown */}
          {userDropdownOpen && (
            <div
              className="absolute right-0 mt-2 w-56 bg-slate-900 border border-slate-800 rounded-xl shadow-2xl p-2 z-50 animate-in fade-in zoom-in-95 duration-100"
              onMouseLeave={() => setUserDropdownOpen(false)}
            >
              <div className="px-3 py-2 border-b border-slate-800 mb-1">
                <p className="text-[11px] font-bold text-white">Signed in as</p>
                <p className="text-[11px] text-slate-400 truncate">{user.email}</p>
                <div className="mt-1 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                  <span className="text-[10px] text-emerald-400 font-mono">Authenticated</span>
                </div>
              </div>

              <button
                onClick={() => {
                  setUserDropdownOpen(false);
                  onNavigateSection("identity");
                }}
                className="w-full text-left px-3 py-2 text-xs text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg flex items-center gap-2"
              >
                <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
                <span>Identity Profile</span>
              </button>

              <button
                onClick={() => {
                  setUserDropdownOpen(false);
                  toggleTheme();
                }}
                className="w-full text-left px-3 py-2 text-xs text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg flex items-center gap-2"
              >
                {theme === "dark" ? (
                  <>
                    <Sun className="w-3.5 h-3.5 text-amber-400" />
                    <span>Light Theme Mode</span>
                  </>
                ) : (
                  <>
                    <Moon className="w-3.5 h-3.5 text-indigo-600" />
                    <span>Dark Theme Mode</span>
                  </>
                )}
              </button>

              <button
                onClick={() => {
                  setUserDropdownOpen(false);
                  onNavigateSection("settings");
                }}
                className="w-full text-left px-3 py-2 text-xs text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg flex items-center gap-2"
              >
                <UserIcon className="w-3.5 h-3.5 text-slate-400" />
                <span>Account Settings</span>
              </button>

              <div className="border-t border-slate-800 my-1"></div>

              <button
                onClick={() => {
                  setUserDropdownOpen(false);
                  onLogout();
                }}
                className="w-full text-left px-3 py-2 text-xs text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 rounded-lg flex items-center gap-2"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span>Sign Out</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

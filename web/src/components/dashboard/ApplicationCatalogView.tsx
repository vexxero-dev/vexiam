"use client";

import React, { useState } from "react";
import {
  Layers,
  CheckCircle2,
  Search,
  ExternalLink,
  Shield,
  Smartphone,
  Globe,
  Database
} from "lucide-react";
import { Application } from "@/types";

interface ApplicationCatalogViewProps {
  applications: Application[];
}

export function ApplicationCatalogView({ applications }: ApplicationCatalogViewProps) {
  const [searchQuery, setSearchQuery] = useState("");

  const filteredApps = applications.filter((app) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      app.name.toLowerCase().includes(q) ||
      app.code.toLowerCase().includes(q) ||
      (app.description && app.description.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Layers className="w-5 h-5 text-indigo-400" />
            <span>VEX Ecosystem Application Catalog</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Global verified ecosystem applications authorized for OAuth 2.1 / OIDC federated single sign-on across Vexxero Cloud.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Verified First-Party</span>
          </span>
        </div>
      </div>

      {/* Search */}
      <div className="relative w-full sm:w-80">
        <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search ecosystem applications..."
          className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
        />
      </div>

      {/* Grid of Applications */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {filteredApps.map((app) => (
          <div
            key={app.id}
            className="p-5 bg-slate-900 border border-slate-800 rounded-2xl flex flex-col justify-between hover:border-slate-700 transition shadow-sm"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="font-mono text-[10px] font-bold text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 rounded">
                  {app.code}
                </span>
                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider font-mono">
                  {app.type}
                </span>
              </div>
              <h4 className="text-base font-bold text-white mb-1">{app.name}</h4>
              <p className="text-xs text-slate-400 leading-relaxed mb-4">
                {app.description || "First-party enterprise application within the VEX ecosystem."}
              </p>
            </div>

            <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs">
              <span className="text-[11px] text-emerald-400 font-medium flex items-center gap-1">
                <Shield className="w-3 h-3" />
                <span>OIDC Protected</span>
              </span>
              <span className="text-[10px] text-slate-500 font-mono">UUID: {app.id.slice(0, 8)}...</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

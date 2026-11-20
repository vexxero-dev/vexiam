"use client";

import React, { useState } from "react";
import { CheckCircle2, ChevronDown, ChevronUp, Sparkles, X, ArrowRight } from "lucide-react";
import { MainNavSection } from "@/types";

interface SetupChecklistProps {
  hasOrg: boolean;
  hasLocation: boolean;
  hasTerminal: boolean;
  hasSubscription: boolean;
  onNavigateSection: (section: MainNavSection) => void;
}

export function SetupChecklist({
  hasOrg,
  hasLocation,
  hasTerminal,
  hasSubscription,
  onNavigateSection,
}: SetupChecklistProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  const steps = [
    {
      id: "org",
      label: "Establish Business Entity",
      completed: hasOrg,
      action: () => onNavigateSection("business_entities"),
      desc: "Register legal entity name and identifier",
    },
    {
      id: "sub",
      label: "Activate Plan Subscription",
      completed: hasSubscription,
      action: () => onNavigateSection("org_subscriptions"),
      desc: "Assign user seats & terminal quotas",
    },
    {
      id: "loc",
      label: "Create Store Location",
      completed: hasLocation,
      action: () => onNavigateSection("org_locations"),
      desc: "Establish physical branches & POS sync policy",
    },
    {
      id: "term",
      label: "Connect POS Terminals",
      completed: hasTerminal,
      action: () => onNavigateSection("org_terminals"),
      desc: "Register hardware fingerprints & offline licenses",
    },
  ];

  const completedCount = steps.filter((s) => s.completed).length;
  const isAllComplete = completedCount === steps.length;

  // If dismissed or everything is complete, render minimal banner or nothing
  if (dismissed) return null;

  return (
    <div className="bg-gradient-to-r from-slate-900 via-indigo-950/20 to-slate-900 border border-slate-800 rounded-2xl p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shrink-0">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h4 className="text-xs font-bold text-white tracking-wide">
                Organization Setup Checklist
              </h4>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-indigo-300 border border-slate-700">
                {completedCount} of {steps.length} completed
              </span>
              {isAllComplete && (
                <span className="text-[10px] font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                  Fully Configured
                </span>
              )}
            </div>
            <p className="text-[11px] text-slate-400">
              Complete these steps to establish terminal synchronization with VEX POS Cloud.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setCollapsed(!collapsed)}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
            title={collapsed ? "Expand checklist" : "Collapse checklist"}
          >
            {collapsed ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
          </button>
          <button
            type="button"
            onClick={() => setDismissed(true)}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
            title="Dismiss checklist"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {!collapsed && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mt-4 pt-3 border-t border-slate-800/80">
          {steps.map((step, idx) => (
            <div
              key={step.id}
              onClick={step.action}
              className={`p-3 rounded-xl border transition-all cursor-pointer group ${
                step.completed
                  ? "bg-slate-900/60 border-emerald-500/30 hover:border-emerald-500/50"
                  : "bg-slate-900/90 border-slate-800 hover:border-indigo-500/50"
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] uppercase font-bold tracking-wider font-mono text-slate-400">
                  Step 0{idx + 1}
                </span>
                {step.completed ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                ) : (
                  <div className="w-3.5 h-3.5 rounded-full border border-slate-600 group-hover:border-indigo-400" />
                )}
              </div>
              <h5 className="text-xs font-semibold text-white group-hover:text-indigo-300 transition-colors">
                {step.label}
              </h5>
              <p className="text-[10px] text-slate-400 mt-0.5 line-clamp-1">{step.desc}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

"use client";

import React, { useState } from "react";
import {
  CreditCard,
  Layers,
  Cpu,
  UserPlus,
  Trash2,
  ChevronDown,
  ChevronUp,
  Laptop,
  CheckCircle2,
  Sparkles,
  ArrowRight
} from "lucide-react";
import { Subscription, Plan, Application, ApplicationAssignment } from "@/types";

interface SubscriptionManagementViewProps {
  subscriptions: Subscription[];
  plans: Plan[];
  applications: Application[];
  assignments: ApplicationAssignment[];
  subscribingPlanId: string | null;
  onBuySubscription: (planId: string) => void;
  onOpenAssignModal: (appId: string, appName: string) => void;
  onRevokeAssignment: (assignmentId: string, memberLabel: string) => void;
}

export function SubscriptionManagementView({
  subscriptions,
  plans,
  applications,
  assignments,
  subscribingPlanId,
  onBuySubscription,
  onOpenAssignModal,
  onRevokeAssignment,
}: SubscriptionManagementViewProps) {
  const [expandedSubId, setExpandedSubId] = useState<string | null>(null);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <CreditCard className="w-5 h-5 text-indigo-400" />
            <span>Subscriptions, Entitlements & Seat Quotas</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Commercial enterprise software packages, operator seat allowances, and authorized device quotas across the VEX ecosystem.
          </p>
        </div>
      </div>

      {/* Active Subscriptions List */}
      {subscriptions.length === 0 ? (
        <div className="p-12 bg-slate-900 border border-slate-800 rounded-2xl text-center shadow-sm">
          <CreditCard className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <p className="text-sm text-slate-300 font-medium">No active subscriptions for this organization.</p>
          <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 mb-4">
            Select an ecosystem plan below to activate commercial software entitlements and operator seat quotas.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {subscriptions.map((sub) => {
            const appId = sub.plan?.application_id;
            const appAssignments = assignments.filter(
              (a) => a.application_id === appId && a.status === "ACTIVE"
            );
            const usedSeats = appAssignments.length;
            const totalSeats = sub.plan?.user_seats || 0;
            const isSeatFull = totalSeats > 0 && usedSeats >= totalSeats;
            const totalTerminals = sub.plan?.device_seats || 0;
            const isExpanded = expandedSubId === sub.id;

            return (
              <div
                key={sub.id}
                className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden transition-all shadow-sm"
              >
                <div
                  onClick={() => setExpandedSubId(isExpanded ? null : sub.id)}
                  className="p-5 cursor-pointer hover:bg-slate-800/40 transition flex flex-col md:flex-row md:items-center justify-between gap-4 select-none"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-mono font-bold text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 rounded">
                        {sub.plan?.code}
                      </span>
                      <span className="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full font-semibold">
                        {sub.status}
                      </span>
                      <span className="text-[11px] bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 px-2.5 py-0.5 rounded-full font-medium">
                        Quota: {totalTerminals} Terminals Entitled
                      </span>
                    </div>
                    <h4 className="text-base font-bold text-white">{sub.plan?.name}</h4>
                    <p className="text-xs text-slate-400">{sub.plan?.description}</p>
                  </div>

                  <div className="flex items-center gap-3 self-end md:self-auto">
                    <span className="text-xs text-indigo-400 font-semibold hidden sm:inline">
                      {isExpanded ? "Hide Details & Quotas" : "View Details & Quotas"}
                    </span>
                    <div className="p-1.5 rounded-lg bg-slate-800 text-slate-300">
                      {isExpanded ? <ChevronUp className="w-4 h-4 text-indigo-400" /> : <ChevronDown className="w-4 h-4 text-indigo-400" />}
                    </div>
                  </div>
                </div>

                {isExpanded && (
                  <div className="p-6 border-t border-slate-800 bg-slate-950/40 space-y-6">
                    {/* Quota Progress Bar */}
                    <div className="p-4 bg-slate-900 rounded-xl border border-slate-800">
                      <div className="flex items-center justify-between text-xs mb-1.5">
                        <span className="text-slate-300 font-medium">Assigned User Seats:</span>
                        <span className={`font-mono font-bold ${isSeatFull ? "text-amber-400" : "text-indigo-400"}`}>
                          {usedSeats} / {totalSeats} seats used
                        </span>
                      </div>
                      <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                        <div
                          className={`h-full transition-all ${isSeatFull ? "bg-amber-400" : "bg-indigo-500"}`}
                          style={{
                            width: `${Math.min(100, totalSeats > 0 ? (usedSeats / totalSeats) * 100 : 0)}%`,
                          }}
                        />
                      </div>
                      <div className="flex items-center justify-end text-[11px] text-slate-400 mt-3">
                        {appId && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              onOpenAssignModal(appId, sub.plan?.name || "Application");
                            }}
                            disabled={isSeatFull}
                            className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 rounded-lg text-xs font-semibold disabled:opacity-50 transition"
                          >
                            <UserPlus className="w-3.5 h-3.5" />
                            <span>{isSeatFull ? "Seats Full" : "Assign User Seat"}</span>
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Assigned Users List */}
                    <div>
                      <h5 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">
                        Assigned Users with Access Seats ({appAssignments.length})
                      </h5>
                      {appAssignments.length === 0 ? (
                        <p className="text-xs text-slate-500 italic py-2">
                          No members assigned yet. Users in the organization cannot sign into applications until granted a seat.
                        </p>
                      ) : (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-52 overflow-y-auto pr-1">
                          {appAssignments.map((assign) => {
                            const userName = assign.user?.profile
                              ? `${assign.user.profile.first_name} ${assign.user.profile.last_name}`
                              : assign.user?.email || "Unknown User";
                            const userEmail = assign.user?.email;

                            return (
                              <div
                                key={assign.id}
                                className="flex items-center justify-between p-2.5 bg-slate-900 border border-slate-800 rounded-xl text-xs"
                              >
                                <div className="min-w-0 pr-2">
                                  <div className="font-semibold text-white truncate">{userName}</div>
                                  <div className="text-[10px] text-slate-400 truncate">{userEmail}</div>
                                  <div className="flex gap-1 mt-1">
                                    {assign.roles?.map((r) => (
                                      <span
                                        key={r.id}
                                        className="text-[9px] bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 px-1.5 py-0.2 rounded"
                                      >
                                        {r.name || r.code}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                                <button
                                  onClick={() => onRevokeAssignment(assign.id, userName)}
                                  title="Revoke seat access"
                                  className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Available Plans to Subscribe */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm">
        <h3 className="text-sm font-bold text-white mb-2 flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-indigo-400" />
          <span>Subscribe to Additional Ecosystem Packages</span>
        </h3>
        <p className="text-xs text-slate-400 mb-4">
          Add additional commercial software licenses or upgrade user seat quotas for your business entity.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {plans.map((p) => (
            <div
              key={p.id}
              className="p-4 bg-slate-950 border border-slate-800 rounded-xl flex flex-col justify-between hover:border-slate-700 transition"
            >
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="font-mono text-[10px] text-indigo-400 font-bold">{p.code}</span>
                </div>
                <h5 className="font-bold text-sm text-white">{p.name}</h5>
                <p className="text-[11px] text-slate-400 my-1">{p.description}</p>
                <div className="text-[11px] text-slate-300 space-y-0.5 my-3">
                  <div>• <strong>{p.user_seats}</strong> User Seats</div>
                  <div>• <strong>{p.device_seats}</strong> Authorized Terminals Allowance</div>
                </div>
              </div>
              <button
                onClick={() => onBuySubscription(p.id)}
                disabled={subscribingPlanId === p.id}
                className="w-full mt-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 text-white rounded-xl text-xs font-semibold py-2 transition shadow-sm shadow-indigo-600/20"
              >
                {subscribingPlanId === p.id ? "Activating..." : "Subscribe / Purchase"}
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

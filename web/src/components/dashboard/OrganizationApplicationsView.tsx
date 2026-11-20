"use client";

import React, { useState } from "react";
import {
  Layers,
  ExternalLink,
  ShieldCheck,
  Users,
  CreditCard,
  PlusCircle,
  UserPlus,
  Trash2,
  CheckCircle2,
  Building2,
  ArrowRight
} from "lucide-react";
import { Organization, Application, Subscription, ApplicationAssignment, Member } from "@/types";

interface OrganizationApplicationsViewProps {
  selectedOrg: Organization | null;
  applications: Application[];
  subscriptions: Subscription[];
  assignments: ApplicationAssignment[];
  members: Member[];
  onOpenAssignModal: (appId: string, appName: string) => void;
  onRevokeAssignment: (assignmentId: string, memberLabel: string) => void;
  onNavigateToCatalog: () => void;
}

export function OrganizationApplicationsView({
  selectedOrg,
  applications,
  subscriptions,
  assignments,
  members,
  onOpenAssignModal,
  onRevokeAssignment,
  onNavigateToCatalog,
}: OrganizationApplicationsViewProps) {
  // Identify which ecosystem applications are active for this organization via its subscriptions
  const activeAppIds = new Set(
    subscriptions
      .filter((s) => s.status === "ACTIVE" && s.plan?.application_id)
      .map((s) => s.plan!.application_id)
  );

  const activeApps = applications.filter((app) => activeAppIds.has(app.id));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Layers className="w-5 h-5 text-indigo-400" />
            <span>Subscribed Organization Applications</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Central software entitlements, operator access seats, and contextual links to application-specific cloud consoles.
          </p>
        </div>
        <button
          onClick={onNavigateToCatalog}
          className="inline-flex items-center gap-2 px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold transition self-start sm:self-auto shadow-sm shadow-indigo-600/20"
        >
          <span>Browse Ecosystem Catalog</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Applications Cards */}
      {activeApps.length === 0 ? (
        <div className="p-12 bg-slate-900 border border-slate-800 rounded-2xl text-center shadow-sm">
          <Layers className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <p className="text-sm text-slate-300 font-medium">No applications subscribed yet for this business entity.</p>
          <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 mb-4">
            Subscribe to an ecosystem package (such as VEX POS or FinCloud ERP) to grant user seats and activate cloud management.
          </p>
          <button
            onClick={onNavigateToCatalog}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold transition"
          >
            <span>Explore Application Catalog</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      ) : (
        <div className="space-y-5">
          {activeApps.map((app) => {
            const sub = subscriptions.find(
              (s) => s.plan?.application_id === app.id && s.status === "ACTIVE"
            );
            const appAssignments = assignments.filter(
              (a) => a.application_id === app.id && a.status === "ACTIVE"
            );
            const totalSeats = sub?.plan?.user_seats || 0;
            const usedSeats = appAssignments.length;
            const isSeatFull = totalSeats > 0 && usedSeats >= totalSeats;

            // Contextual Launch Console URL
            const isPosApp = app.code.toLowerCase().includes("pos");
            const consoleUrl = isPosApp
              ? "https://pos-console.vexxero.com"
              : app.console_url || "#";

            return (
              <div
                key={app.id}
                className="p-6 bg-slate-900 border border-slate-800 rounded-2xl shadow-sm space-y-5"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono text-[10px] font-bold text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 rounded">
                        {app.code}
                      </span>
                      <span className="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full font-semibold">
                        Entitled
                      </span>
                      {sub && (
                        <span className="text-[11px] text-slate-400">
                          Plan: <strong className="text-slate-200">{sub.plan?.name}</strong>
                        </span>
                      )}
                    </div>
                    <h3 className="text-lg font-bold text-white">{app.name}</h3>
                    <p className="text-xs text-slate-400 max-w-2xl">{app.description}</p>
                  </div>

                  {/* Contextual Action Button to Launch Application Console */}
                  <div className="flex items-center gap-2 self-start sm:self-auto shrink-0">
                    <a
                      href={consoleUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white rounded-xl text-xs font-bold transition shadow-md shadow-indigo-600/30"
                    >
                      <span>Open {app.name} Console</span>
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  </div>
                </div>

                {/* Operator Seats Quota & Allocation */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="text-xs font-bold text-white flex items-center gap-1.5">
                        <Users className="w-3.5 h-3.5 text-indigo-400" />
                        <span>Assigned Operator Seats ({usedSeats} / {totalSeats})</span>
                      </h4>
                      <p className="text-[11px] text-slate-400">
                        Members granted access to log into {app.name} with this organization's context.
                      </p>
                    </div>

                    <button
                      onClick={() => onOpenAssignModal(app.id, app.name)}
                      disabled={isSeatFull}
                      className="inline-flex items-center gap-1 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs font-semibold disabled:opacity-50 transition border border-slate-700"
                    >
                      <UserPlus className="w-3.5 h-3.5 text-indigo-400" />
                      <span>{isSeatFull ? "Seats Full" : "Grant Access Seat"}</span>
                    </button>
                  </div>

                  {/* Assigned Members Table */}
                  {appAssignments.length === 0 ? (
                    <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-500 italic">
                      No members assigned yet. Members cannot sign into {app.name} until granted an operator seat here.
                    </div>
                  ) : (
                    <div className="bg-slate-950 border border-slate-800 rounded-xl overflow-hidden">
                      <table className="w-full text-left text-xs">
                        <thead>
                          <tr className="border-b border-slate-800 text-slate-400 text-[10px] uppercase font-semibold">
                            <th className="py-2.5 px-4">Operator Name</th>
                            <th className="py-2.5 px-4">Email</th>
                            <th className="py-2.5 px-4">Application Roles</th>
                            <th className="py-2.5 px-4 text-right">Action</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60">
                          {appAssignments.map((assign) => {
                            const name = assign.user?.profile
                              ? `${assign.user.profile.first_name} ${assign.user.profile.last_name}`
                              : assign.user?.email || "Unknown";

                            return (
                              <tr key={assign.id} className="hover:bg-slate-900/50">
                                <td className="py-2.5 px-4 font-semibold text-white">{name}</td>
                                <td className="py-2.5 px-4 text-slate-400 font-mono text-[11px]">
                                  {assign.user?.email}
                                </td>
                                <td className="py-2.5 px-4">
                                  <div className="flex gap-1 flex-wrap">
                                    {assign.roles?.map((r) => (
                                      <span
                                        key={r.id}
                                        className="text-[9px] bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 px-1.5 py-0.2 rounded font-mono"
                                      >
                                        {r.name || r.code}
                                      </span>
                                    ))}
                                    {(!assign.roles || assign.roles.length === 0) && (
                                      <span className="text-[10px] text-slate-500">Default Access</span>
                                    )}
                                  </div>
                                </td>
                                <td className="py-2.5 px-4 text-right">
                                  <button
                                    onClick={() => onRevokeAssignment(assign.id, name)}
                                    title="Revoke access seat"
                                    className="p-1 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded transition"
                                  >
                                    <Trash2 className="w-3.5 h-3.5" />
                                  </button>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

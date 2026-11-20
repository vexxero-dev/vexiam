"use client";

import React, { useState } from "react";
import {
  Building2,
  PlusCircle,
  Search,
  Check,
  Copy,
  ChevronRight,
  ShieldCheck,
  Users
} from "lucide-react";
import { Organization, Member } from "@/types";

interface BusinessEntitiesViewProps {
  organizations: Organization[];
  selectedOrg: Organization | null;
  onSelectOrg: (org: Organization) => void;
  copiedId: string | null;
  onCopy: (text: string, id: string) => void;
  onOpenCreateOrg: () => void;
  onNavigateToSection: (section: any) => void;
  members: Member[];
}

export function BusinessEntitiesView({
  organizations,
  selectedOrg,
  onSelectOrg,
  copiedId,
  onCopy,
  onOpenCreateOrg,
  onNavigateToSection,
  members,
}: BusinessEntitiesViewProps) {
  const [searchQuery, setSearchQuery] = useState("");

  const filteredOrgs = organizations.filter((org) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      org.name.toLowerCase().includes(q) ||
      org.id.toLowerCase().includes(q) ||
      (org.registration_number && org.registration_number.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Building2 className="w-5 h-5 text-indigo-400" />
            <span>Business Entities Directory</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Enterprise multi-tenant organizations registered under your VEX IAM global identity.
          </p>
        </div>
        <button
          onClick={onOpenCreateOrg}
          className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold transition self-start sm:self-auto shadow-sm shadow-indigo-600/20"
        >
          <PlusCircle className="w-4 h-4" />
          <span>Establish Business Entity</span>
        </button>
      </div>

      {/* Search Bar */}
      <div className="flex items-center justify-between gap-3 bg-slate-900/60 p-3 rounded-xl border border-slate-800">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search business entities by name or reg #..."
            className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>
        <div className="text-xs text-slate-400 font-medium">
          Showing <strong>{filteredOrgs.length}</strong> of {organizations.length} entities
        </div>
      </div>

      {/* Scalable Table */}
      {filteredOrgs.length === 0 ? (
        <div className="p-12 bg-slate-900/40 border border-slate-800 rounded-2xl text-center">
          <Building2 className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <p className="text-sm text-slate-300 font-medium">No business entities found.</p>
          <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 mb-4">
            Register your company or café organization to create store branches and deploy POS terminals.
          </p>
          <button
            onClick={onOpenCreateOrg}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold transition"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span>Create Entity</span>
          </button>
        </div>
      ) : (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-950/60 text-slate-400 font-semibold uppercase tracking-wider text-[10px]">
                  <th className="py-3 px-4">Business Name & UUID</th>
                  <th className="py-3 px-4">Registration Number</th>
                  <th className="py-3 px-4">Account Status</th>
                  <th className="py-3 px-4">Members</th>
                  <th className="py-3 px-4 text-right">Workspace Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-medium">
                {filteredOrgs.map((org) => {
                  const isSelected = selectedOrg?.id === org.id;

                  return (
                    <tr
                      key={org.id}
                      onClick={() => onSelectOrg(org)}
                      className={`hover:bg-slate-800/40 transition cursor-pointer ${
                        isSelected ? "bg-indigo-950/20" : ""
                      }`}
                    >
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center font-bold text-xs text-indigo-400 shrink-0">
                            {org.name.slice(0, 2).toUpperCase()}
                          </div>
                          <div>
                            <div className="font-bold text-white text-xs flex items-center gap-1.5">
                              <span>{org.name}</span>
                              {isSelected && (
                                <span className="text-[9px] bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 px-1.5 py-0.2 rounded font-mono">
                                  ACTIVE
                                </span>
                              )}
                            </div>
                            <div className="text-[10px] text-slate-500 font-mono flex items-center gap-1 mt-0.5">
                              <span>{org.id.slice(0, 8)}...</span>
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onCopy(org.id, org.id);
                                }}
                                title="Copy Org ID"
                                className="text-slate-500 hover:text-slate-300"
                              >
                                {copiedId === org.id ? (
                                  <Check className="w-3 h-3 text-emerald-400" />
                                ) : (
                                  <Copy className="w-3 h-3" />
                                )}
                              </button>
                            </div>
                          </div>
                        </div>
                      </td>

                      <td className="py-3.5 px-4 text-slate-300 font-mono text-[11px]">
                        {org.registration_number || <span className="text-slate-500 italic">Not registered</span>}
                      </td>

                      <td className="py-3.5 px-4">
                        <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold border bg-emerald-500/10 text-emerald-400 border-emerald-500/20">
                          {org.status}
                        </span>
                      </td>

                      <td className="py-3.5 px-4 text-slate-300">
                        <span className="inline-flex items-center gap-1 font-mono text-xs">
                          <Users className="w-3.5 h-3.5 text-slate-500" />
                          <span>{isSelected ? members.length : "—"}</span>
                        </span>
                      </td>

                      <td className="py-3.5 px-4 text-right">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectOrg(org);
                            onNavigateToSection("overview");
                          }}
                          className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-400 hover:text-indigo-300"
                        >
                          <span>Open Workspace</span>
                          <ChevronRight className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

"use client";

import React, { useState } from "react";
import {
  Users,
  Mail,
  UserPlus,
  Shield,
  Search,
  Filter,
  Check,
  Copy,
  UserCheck
} from "lucide-react";
import { Member, Organization } from "@/types";

interface TeamManagementViewProps {
  members: Member[];
  selectedOrg: Organization | null;
  copiedId: string | null;
  onCopy: (text: string, id: string) => void;
  inviteEmail: string;
  setInviteEmail: (v: string) => void;
  inviteRole: string;
  setInviteRole: (v: string) => void;
  onSendInvite: (e: React.FormEvent) => void;
  generatedInviteToken: string | null;
}

export function TeamManagementView({
  members,
  selectedOrg,
  copiedId,
  onCopy,
  inviteEmail,
  setInviteEmail,
  inviteRole,
  setInviteRole,
  onSendInvite,
  generatedInviteToken,
}: TeamManagementViewProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState<string>("ALL");

  const filteredMembers = members.filter((m) => {
    if (roleFilter !== "ALL" && m.role !== roleFilter) return false;
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    const name = `${m.user?.profile?.first_name || ""} ${m.user?.profile?.last_name || ""}`.toLowerCase();
    const email = (m.user?.email || "").toLowerCase();
    return name.includes(q) || email.includes(q);
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Users className="w-5 h-5 text-indigo-400" />
            <span>Team & Active User Pool</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Manage organization members, workspace roles (OWNER, ADMIN, MEMBER), and invite individual VEX IAM identities.
          </p>
        </div>
      </div>

      {/* Invite Box */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm">
        <h4 className="text-xs font-bold text-slate-200 mb-2 flex items-center gap-2">
          <Mail className="w-4 h-4 text-indigo-400" />
          <span>Invite Individual VEX IAM Identity</span>
        </h4>
        <p className="text-xs text-slate-400 mb-4">
          Invited users receive secure cryptographic admission tokens linked to their global VEX email identity.
        </p>

        <form onSubmit={onSendInvite} className="flex gap-3 flex-col sm:flex-row">
          <input
            type="email"
            required
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
            placeholder="colleague@domain.com"
            className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
          />
          <select
            value={inviteRole}
            onChange={(e) => setInviteRole(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500 font-medium"
          >
            <option value="MEMBER">MEMBER</option>
            <option value="ADMIN">ADMIN</option>
          </select>
          <button
            type="submit"
            className="bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2 rounded-xl text-xs font-semibold transition shadow-sm shadow-indigo-600/20"
          >
            Send Invitation
          </button>
        </form>

        {generatedInviteToken && (
          <div className="mt-4 p-4 bg-indigo-950/40 border border-indigo-800/50 rounded-xl text-xs">
            <div className="flex items-center justify-between mb-1">
              <span className="text-indigo-300 font-semibold">Secure Invitation Token Generated:</span>
              <button
                type="button"
                onClick={() => onCopy(generatedInviteToken, "inv-token")}
                className="text-[11px] text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
              >
                {copiedId === "inv-token" ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copiedId === "inv-token" ? "Copied" : "Copy Token"}</span>
              </button>
            </div>
            <p className="font-mono text-[11px] text-slate-300 break-all select-all bg-slate-950/80 p-2 rounded-lg border border-slate-800">
              {generatedInviteToken}
            </p>
          </div>
        )}
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-slate-900/60 p-3 rounded-xl border border-slate-800">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search member by name or email..."
            className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-300 px-3 py-1.5 focus:outline-none focus:border-indigo-500"
          >
            <option value="ALL">All Roles ({members.length})</option>
            <option value="OWNER">OWNER</option>
            <option value="ADMIN">ADMIN</option>
            <option value="MEMBER">MEMBER</option>
          </select>
        </div>
      </div>

      {/* Scalable Data Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-950/60 text-slate-400 font-semibold uppercase tracking-wider text-[10px]">
                <th className="py-3 px-4">User</th>
                <th className="py-3 px-4">Global VEX Email</th>
                <th className="py-3 px-4">Organization Role</th>
                <th className="py-3 px-4">Account Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-medium">
              {filteredMembers.map((m) => (
                <tr key={m.id} className="hover:bg-slate-800/40 transition">
                  <td className="py-3.5 px-4 font-semibold text-white">
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-xs font-bold text-indigo-400">
                        {m.user?.profile?.first_name ? m.user.profile.first_name[0] : (m.user?.email[0] || "U").toUpperCase()}
                      </div>
                      <div>
                        <div>{m.user?.profile?.first_name} {m.user?.profile?.last_name || "—"}</div>
                        <div className="text-[10px] text-slate-500 font-mono truncate max-w-[120px]">{m.user_id.slice(0, 8)}...</div>
                      </div>
                    </div>
                  </td>
                  <td className="py-3.5 px-4 text-slate-300">{m.user?.email}</td>
                  <td className="py-3.5 px-4">
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
                  </td>
                  <td className="py-3.5 px-4">
                    <span className="inline-flex items-center gap-1 text-[10px] text-emerald-400">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                      <span>Active</span>
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
